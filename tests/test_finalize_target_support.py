from __future__ import annotations

import hashlib
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from finalize_target_support import Step, build_steps, execute_write_steps, generated_paths, main, restore, snapshot  # noqa: E402
from render_change_package_index import expected_outputs  # noqa: E402


def package(package_id: str, status: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "record_kind": "alatyr-change-package",
        "package_id": package_id,
        "status": status,
        "changed_facts": [
            {"id": f"FACT-{package_id}", "canonical_owner": "docs/architecture.md"}
        ],
        "routing": {"project_areas": ["core"]},
        "provenance": {"evidence_quality": "git-range"},
        "approved_scope": {"approval_records": [".ai/assistant/approvals/A.json"]},
        "operation": {"active_workstream": "not active"},
    }


def stale_entry(package_id: str, record: str) -> dict[str, object]:
    return {
        "package_id": package_id,
        "status": "validated",
        "record": record,
        "changed_fact_ids": [],
        "canonical_owners": [],
        "project_areas": [],
        "evidence_quality": "unknown",
        "approval_records": [],
        "active_workstream": "unknown",
        "residual_risk": "none",
        "incident_family_id": "STALE",
        "corrective_iteration": 3,
        "latest_failed_gate_state": "open",
    }


class ChangePackageProjectionTests(unittest.TestCase):
    def test_root_projection_converges_and_removes_legacy_incident_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            package_path = target / ".ai/assistant/change-packages/P.json"
            index_path = target / ".ai/assistant/change-packages/index.json"
            package_path.parent.mkdir(parents=True)
            package_path.write_text(
                json.dumps(package("P", "complete")), encoding="utf-8"
            )
            index_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "index_kind": "target-change-package-index",
                        "records": [
                            stale_entry(
                                "P", ".ai/assistant/change-packages/P.json"
                            )
                        ],
                        "shards": [],
                    }
                ),
                encoding="utf-8",
            )

            rendered = expected_outputs(target)[index_path.resolve()]
            projected = json.loads(rendered)

        entry = projected["records"][0]
        self.assertEqual(entry["status"], "complete")
        self.assertEqual(entry["changed_fact_ids"], ["FACT-P"])
        self.assertNotIn("incident_family_id", entry)
        self.assertNotIn("corrective_iteration", entry)
        self.assertNotIn("latest_failed_gate_state", entry)

    def test_shard_projection_refreshes_root_digest_and_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            root = target / ".ai/assistant/change-packages/index.json"
            record = target / ".ai/assistant/change-packages/P.json"
            shard = (
                target
                / ".ai/assistant/change-packages/archive/2026-10/index.json"
            )
            shard.parent.mkdir(parents=True)
            record.write_text(json.dumps(package("P", "blocked")), encoding="utf-8")
            shard.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "index_kind": "target-change-package-index-shard",
                        "shard_id": "2026-10",
                        "records": [
                            stale_entry(
                                "P", ".ai/assistant/change-packages/P.json"
                            )
                        ],
                    }
                ),
                encoding="utf-8",
            )
            root.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "index_kind": "target-change-package-index",
                        "records": [],
                        "shards": [
                            {
                                "shard_id": "2026-10",
                                "path": ".ai/assistant/change-packages/archive/2026-10/index.json",
                                "sha256": "0" * 64,
                                "record_count": 0,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            outputs = expected_outputs(target)
            shard_text = outputs[shard.resolve()]
            projected_root = json.loads(outputs[root.resolve()])

        descriptor = projected_root["shards"][0]
        self.assertEqual(descriptor["record_count"], 1)
        self.assertEqual(
            descriptor["sha256"],
            hashlib.sha256(shard_text.encode("utf-8")).hexdigest(),
        )


class FinalizeTargetSupportTests(unittest.TestCase):
    def test_reviewed_history_selection_reaches_canonical_validator(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            steps = build_steps(target=Path(directory), write=False,
                migration_staging=False, diff_ref=None, approval_records=[],
                change_packages=[], historical_evidence_index=Path("history/index.json"))
        command = steps[-1].arguments
        self.assertEqual(Path(command[command.index("--historical-evidence-index") + 1]), Path("history/index.json"))

    def set_module(self, target: Path, *, enabled: bool) -> None:
        manifest = target / ".ai/alatyr.yaml"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        modules = "[change-packages]" if enabled else "[]"
        manifest.write_text(
            f"modules:\n  selected: {modules}\n  enabled: {modules}\n", encoding="utf-8"
        )

    def test_disabled_current_change_does_not_require_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.set_module(target, enabled=False)
            steps = build_steps(
                target=target, write=False, migration_staging=False,
                diff_ref="HEAD", approval_records=[Path("approval.json")],
                change_packages=[], require_current_change=True,
            )
            self.assertIn("--enforce-approval-scope", steps[-1].arguments)
            self.assertNotIn("--enforce-change-package", steps[-1].arguments)
            with patch("sys.argv", ["finalize_target_support.py", "--target", str(target),
                       "--require-current-change", "--diff-ref", "HEAD", "--approval-record", "approval.json"]), \
                    patch("finalize_target_support.execute_steps", return_value=(0, None)) as execute, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
            self.assertNotIn("--enforce-change-package", execute.call_args.args[0][-1].arguments)

    def test_enabled_current_change_requires_package_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.set_module(target, enabled=True)
            with self.assertRaisesRegex(ValueError, "--change-package"):
                build_steps(
                    target=target, write=False, migration_staging=False,
                    diff_ref="HEAD", approval_records=[Path("approval.json")],
                    change_packages=[], require_current_change=True,
                )
            with patch("sys.argv", ["finalize_target_support.py", "--target", str(target),
                       "--require-current-change", "--diff-ref", "HEAD", "--approval-record", "approval.json"]), \
                    patch("finalize_target_support.execute_steps") as execute, \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as failure:
                    main()
            self.assertEqual(failure.exception.code, 2)
            execute.assert_not_called()

    def test_current_change_keeps_diff_and_approval_required(self) -> None:
        for diff_ref, approvals in ((None, [Path("approval.json")]), ("HEAD", [])):
            with self.subTest(diff_ref=diff_ref, approvals=approvals):
                with self.assertRaisesRegex(ValueError, "--diff-ref and --approval-record"):
                    build_steps(
                        target=Path("/target"), write=False, migration_staging=False,
                        diff_ref=diff_ref, approval_records=approvals, change_packages=[],
                        require_current_change=True,
                    )

    def test_non_current_change_preserves_explicit_package_enforcement(self) -> None:
        for packages in ([], [Path("package.json")]):
            steps = build_steps(
                target=Path("/target"), write=False, migration_staging=False,
                diff_ref=None, approval_records=[], change_packages=packages,
            )
            self.assertEqual("--enforce-change-package" in steps[-1].arguments, bool(packages))
            self.assertNotIn("--enforce-approval-scope", steps[-1].arguments)

    def test_unexpected_builder_failure_restores_only_owned_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            entry = target / ".ai/assistant/entry-packet.json"
            entry.parent.mkdir(parents=True)
            entry.write_bytes(b"before")
            peer = target / ".ai/assistant/peer-note.md"
            peer.write_bytes(b"peer work")
            steps = [Step("entry-packet", "unused", ()), Step("bootstrap-pass-1", "unused", ())]
            with patch("finalize_target_support.step_outputs", side_effect=[{entry: b"after"}, RuntimeError("builder failed")]):
                result, failed, conflicts = execute_write_steps(target, steps)
            self.assertNotEqual(result, 0)
            self.assertEqual(failed, "bootstrap-pass-1")
            self.assertEqual(conflicts, [])
            self.assertEqual(entry.read_bytes(), b"before")
            self.assertEqual(peer.read_bytes(), b"peer work")

    def test_task_binding_and_models_reach_canonical_validation(self) -> None:
        steps = build_steps(target=Path("/target"), write=False, migration_staging=False,
            diff_ref="HEAD~1", approval_records=[], change_packages=[], task_id="task-1",
            task_class="protected-or-sensitive", problem_models=[Path("model.json")], require_task_acceptance=True)
        arguments = steps[-1].arguments
        for option, value in (("--task-id", "task-1"), ("--task-class", "protected-or-sensitive"), ("--problem-model", "model.json")):
            self.assertEqual(arguments[arguments.index(option) + 1], value)
        self.assertIn("--require-task-acceptance", arguments)
        with self.assertRaises(ValueError):
            build_steps(target=Path("/target"), write=False, migration_staging=False,
                diff_ref=None, approval_records=[], change_packages=[], require_task_acceptance=True)

    def test_conformance_scaffold_converges_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            scaffold = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/scaffold_target_structure.py"),
                    "--target",
                    str(target),
                    "--profile",
                    "full",
                    "--write",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stderr)

            write = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/finalize_target_support.py"),
                    "--target",
                    str(target),
                    "--write",
                    "--migration-staging",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            check = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/finalize_target_support.py"),
                    "--target",
                    str(target),
                    "--migration-staging",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(write.returncode, 0, write.stderr)
        self.assertEqual(check.returncode, 0, check.stderr)

    def test_current_change_inputs_reach_final_canonical_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.set_module(target, enabled=True)
            steps = build_steps(
                target=target,
                write=True,
                migration_staging=False,
                diff_ref="HEAD~1",
                approval_records=[Path("approval.json")],
                change_packages=[Path("package.json")],
                require_current_change=True,
            )

        self.assertEqual(steps[-1].step_id, "canonical-validation")
        arguments = steps[-1].arguments
        self.assertIn("--diff-ref", arguments)
        self.assertIn("--approval-record", arguments)
        self.assertIn("--change-package", arguments)
        self.assertIn("--enforce-change-package", arguments)
        self.assertIn("--enforce-approval-scope", arguments)
        self.assertLess(
            [step.step_id for step in steps].index("support-state"),
            [step.step_id for step in steps].index("canonical-validation"),
        )

    def test_restore_reverts_modified_and_removes_new_generated_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            entry = target / ".ai/assistant/entry-packet.json"
            entry.parent.mkdir(parents=True)
            entry.write_text("before", encoding="utf-8")
            before = snapshot(generated_paths(target), target=target)
            entry.write_text("after", encoding="utf-8")
            generated = target / ".ai/assistant/nested/context-index.json"
            generated.parent.mkdir(parents=True)
            generated.write_text("new", encoding="utf-8")

            before[generated] = None
            restore(target, before, owned={entry: b"after", generated: b"new"})

            self.assertEqual(entry.read_text(encoding="utf-8"), "before")
            self.assertFalse(generated.exists())


if __name__ == "__main__":
    unittest.main()
