from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from finalize_target_support import build_steps, generated_paths, restore, snapshot  # noqa: E402
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
        steps = build_steps(
            target=Path("/target"),
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
            before = snapshot(generated_paths(target))
            entry.write_text("after", encoding="utf-8")
            generated = target / ".ai/assistant/nested/context-index.json"
            generated.parent.mkdir(parents=True)
            generated.write_text("new", encoding="utf-8")

            restore(target, before)

            self.assertEqual(entry.read_text(encoding="utf-8"), "before")
            self.assertFalse(generated.exists())


if __name__ == "__main__":
    unittest.main()
