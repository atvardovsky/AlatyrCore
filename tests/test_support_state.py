from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from support_state import (
    SupportStateError,
    build_support_state,
    is_inert_support_path,
    render_state,
    select_support_paths,
    state_differences,
    state_is_current,
)


def policy() -> dict[str, object]:
    return {
        "schema_version": 1,
        "policy_kind": "target-support-policy",
        "managed_roots": [".ai"],
        "optional_entrypoints": ["AGENTS.md"],
        "exclusions": [
            {"pattern": ".ai/support-state.json", "reason": "self exclusion"},
            {"pattern": ".ai/local/**", "reason": "local state"},
        ],
        "classifications": [
            {
                "id": "adapter",
                "classification": "exact-contract",
                "patterns": [".ai/**", "AGENTS.md"],
            }
        ],
    }


class SupportStateTests(unittest.TestCase):
    def test_compact_records_preserve_every_parsed_field_and_order(self):
        value = {"schema_version": 1, "files": [{"path": "a.md", "digest": "sha256:first", "canonical_size": 3}, {"path": "b.md", "digest": "sha256:second", "canonical_size": 4}], "metadata": {"description": "Unicode and nested values: \u00e9", "items": [1, 2]}}
        rendered = render_state(value)
        self.assertEqual(json.loads(rendered), value)
        self.assertEqual(rendered, render_state(value))
        self.assertEqual(json.loads(rendered)["files"], value["files"])
        self.assertLess(len(rendered), len(json.dumps(value, indent=2, ensure_ascii=True)))

    def make_target(self) -> Path:
        root = Path(self.addCleanupDirectory())
        (root / ".ai/project").mkdir(parents=True)
        (root / ".ai/project/support-policy.json").write_bytes(
            (json.dumps(policy(), indent=2) + "\n").encode("utf-8")
        )
        (root / ".ai/project/rule.md").write_bytes(b"rule\n")
        (root / "AGENTS.md").write_bytes(b"instructions\n")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
        return root

    def addCleanupDirectory(self) -> str:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return directory.name

    def test_state_detects_created_modified_and_removed_support_files(self) -> None:
        target = self.make_target()
        before = build_support_state(target)
        (target / ".ai/project/rule.md").write_bytes(b"changed\n")
        (target / ".ai/project/new.md").write_bytes(b"new\n")
        (target / "AGENTS.md").unlink()
        after = build_support_state(target)
        changes = {(item.path, item.change) for item in state_differences(before, after)}
        self.assertEqual(
            changes,
            {
                (".ai/project/new.md", "created"),
                (".ai/project/rule.md", "modified"),
                ("AGENTS.md", "removed"),
            },
        )

    def test_line_ending_only_change_is_canonical(self) -> None:
        target = self.make_target()
        before = build_support_state(target)
        (target / ".ai/project/rule.md").write_bytes(b"rule\r\n")
        after = build_support_state(target)
        self.assertTrue(state_is_current(before, after))

    def test_source_revision_is_evidence_not_drift(self) -> None:
        target = self.make_target()
        before = build_support_state(target)
        after = json.loads(render_state(before))
        after["source_revision"] = "different-revision"
        after["generated_by"]["source_revision"] = "different-source"
        after["generated_by"]["source_worktree_state"] = "dirty"
        after["generated_by"]["source_dirty_paths"] = ["tools/support_state.py"]
        self.assertTrue(state_is_current(before, after))

    def test_stable_generation_provenance_is_part_of_freshness(self) -> None:
        target = self.make_target()
        before = build_support_state(target)
        after = json.loads(render_state(before))
        after["generated_by"]["template_version"] = "different-template"
        self.assertFalse(state_is_current(before, after))

    def test_state_records_generation_provenance(self) -> None:
        target = self.make_target()
        state = build_support_state(target)
        generated_by = state["generated_by"]
        self.assertEqual(generated_by["schema_version"], 2)
        self.assertEqual(generated_by["tool"], "snapshot_target_support.py")
        self.assertEqual(generated_by["target_manifest"], ".ai/alatyr.yaml")
        self.assertIn(generated_by["source_worktree_state"], {"clean", "dirty"})
        self.assertIn(generated_by["target_worktree_state"], {"clean", "dirty"})

    def test_historical_task_evidence_is_inert_and_not_current_support(self) -> None:
        target = self.make_target()
        historical = (
            target
            / ".ai/assistant/task-evidence/historical-git-trees/abc123"
            / ".ai/project/context-index.json"
        )
        historical.parent.mkdir(parents=True)
        historical.write_bytes(b'{"entries": []}\n')

        state = build_support_state(target)
        paths = {item["path"] for item in state["files"]}
        self.assertNotIn(
            ".ai/assistant/task-evidence/historical-git-trees/abc123/"
            ".ai/project/context-index.json",
            paths,
        )
        self.assertIn(".ai/project/rule.md", paths)
        self.assertIn("AGENTS.md", paths)

    def test_inert_paths_do_not_become_unmanaged_support(self) -> None:
        restricted = policy()
        restricted["classifications"] = [
            {
                "id": "entrypoint-only",
                "classification": "exact-contract",
                "patterns": ["AGENTS.md"],
            }
        ]
        self.assertEqual(
            select_support_paths(
                [
                    ".ai/assistant/task-evidence/historical-git-trees/abc/.ai/project/x.json",
                    "AGENTS.md",
                ],
                restricted,
            ),
            {"AGENTS.md": ("entrypoint-only", "exact-contract")},
        )

    def test_support_and_catalog_inert_predicates_agree(self) -> None:
        from render_context_catalogs import _is_inert_task_evidence

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            historical = root / "task-evidence/historical-git-trees/abc/.ai/project/x.json"
            historical.parent.mkdir(parents=True)
            historical.write_text("{}\n", encoding="utf-8")
            current = root / "project/x.json"
            current.parent.mkdir(parents=True)
            current.write_text("{}\n", encoding="utf-8")

            self.assertTrue(
                is_inert_support_path(
                    ".ai/assistant/task-evidence/historical-git-trees/abc/.ai/project/x.json"
                )
            )
            self.assertTrue(_is_inert_task_evidence(root, "assistant", historical))
            self.assertFalse(is_inert_support_path(".ai/project/x.json"))
            self.assertFalse(_is_inert_task_evidence(root, "assistant", current))

    def test_legacy_state_with_only_inert_entries_remains_current(self) -> None:
        target = self.make_target()
        current = build_support_state(target)
        recorded = json.loads(render_state(current))
        recorded["files"].append(
            {
                "path": ".ai/assistant/task-evidence/historical-git-trees/abc/.ai/project/x.json",
                "kind": "file",
                "classification": "exact-contract",
                "classification_id": "adapter",
                "group": "assistant",
                "digest": "sha256:legacy",
                "canonical_size": 1,
            }
        )
        recorded["root_digest"] = "sha256:legacy-root"
        recorded["groups"] = [
            {"id": "legacy", "file_count": 1, "digest": "sha256:legacy-group"}
        ]
        self.assertTrue(state_is_current(recorded, current))

        recorded["files"].append(
            {
                "path": ".ai/project/current-new.md",
                "kind": "file",
                "classification": "exact-contract",
                "classification_id": "adapter",
                "group": "project",
                "digest": "sha256:new",
                "canonical_size": 1,
            }
        )
        self.assertFalse(state_is_current(recorded, current))

    def test_non_inert_metadata_difference_still_fails_freshness(self) -> None:
        target = self.make_target()
        current = build_support_state(target)
        recorded = json.loads(render_state(current))
        recorded["files"][0]["classification"] = "derived"
        self.assertFalse(state_is_current(recorded, current))

    def test_unclassified_file_fails_closed(self) -> None:
        target = self.make_target()
        restricted = policy()
        restricted["classifications"] = [
            {
                "id": "entrypoint-only",
                "classification": "exact-contract",
                "patterns": ["AGENTS.md"],
            }
        ]
        with self.assertRaisesRegex(SupportStateError, "unclassified support paths"):
            build_support_state(target, restricted)

    def test_untracked_ignored_support_file_is_not_hashed(self) -> None:
        target = self.make_target()
        (target / ".gitignore").write_bytes(b".ai/local-secret.txt\n")
        (target / ".ai/local-secret.txt").write_bytes(b"secret\n")
        state = build_support_state(target)
        self.assertNotIn(
            ".ai/local-secret.txt",
            {item["path"] for item in state["files"]},
        )

    def test_case_colliding_support_paths_fail_closed(self) -> None:
        target = self.make_target()
        (target / ".ai/project/Rule.md").write_bytes(b"collision\n")
        with self.assertRaisesRegex(SupportStateError, "case-colliding"):
            build_support_state(target)


if __name__ == "__main__":
    unittest.main()
