from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from support_state import (
    SupportStateError,
    build_support_state,
    render_state,
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
        self.assertTrue(state_is_current(before, after))

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
