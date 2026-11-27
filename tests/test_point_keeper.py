from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REV = "a" * 40


class PointKeeperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name) / "target"
        self.tasks = self.target / ".ai/assistant/team/tasks"
        self.tasks.mkdir(parents=True)
        self.write_packages(
            {
                "D1": "complete",
                "D2": "complete",
                "D3": "validated",
                "D5": "blocked",
            }
        )
        self.write_point("P1", "pending", related=["D1"], validation="not-run")
        self.write_point(
            "P2", "in_review", review_state="in-review", reviewers=["reviewer"],
            evidence=[], related=["D1"], validation="not-run",
        )
        self.write_point(
            "P3", "done", review_state="reviewed", reviewers=["reviewer"],
            evidence=[".ai/assistant/reports/P3/review.json"], related=["D2"],
            reviewed=REV, validation="passed",
        )
        self.write_point(
            "P4", "done", review_state="reviewed", reviewers=["reviewer"],
            evidence=[], related=["D1"], reviewed=REV, validation="passed",
        )
        self.write_point("P5", "blocked", blockers=["DB window"], related=["D1"])
        self.write_point(
            "P6", "done", review_state="reviewed", reviewers=["reviewer"],
            evidence=[".ai/assistant/reports/P6/review.json"], related=["D3"],
            reviewed="b" * 40, validation="passed",
        )
        self.write_point(
            "P7", "done", review_state="reviewed", reviewers=["reviewer"],
            evidence=[".ai/assistant/reports/P7/review.json"], related=["D3"],
            reviewed=REV, validation="passed",
        )

    def write_packages(self, records: dict[str, str]) -> None:
        path = self.target / ".ai/assistant/change-packages/index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "index_kind": "target-change-package-index",
                    "records": [
                        {"package_id": package_id, "status": status}
                        for package_id, status in records.items()
                    ],
                }
            ),
            encoding="utf-8",
        )

    def write_point(
        self,
        point_id: str,
        status: str,
        *,
        review_state: str = "not-required",
        reviewers: list[str] | None = None,
        evidence: list[str] | None = None,
        related: list[str] | None = None,
        reviewed: str = "none",
        validation: str = "passed",
        blockers: list[str] | None = None,
    ) -> Path:
        path = self.tasks / f"{point_id}.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "record_kind": "target-team-task",
                    "id": point_id,
                    "goal": f"Point {point_id}",
                    "status": status,
                    "review_state": review_state,
                    "reviewer_actor_ids": reviewers or [],
                    "review_evidence_refs": evidence or [],
                    "reviewed_head_revision": reviewed,
                    "reviewed_base_revision": "none",
                    "validation_state": validation,
                    "blockers": blockers or [],
                    "related_task_ids": related or [],
                    "branch_or_worktree": "preDev-alatyr",
                    "priority": "normal",
                    "next_action": "test fixture",
                }
            ),
            encoding="utf-8",
        )
        return path

    def cli(self, *arguments: str):
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/point_keeper.py"),
                "--target",
                str(self.target),
                *arguments,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def payload(self, result):
        self.assertIn(result.returncode, {0, 1}, result.stderr)
        return json.loads(result.stdout)

    def test_status_counts_and_attention(self) -> None:
        result = self.cli("status", "--current-revision", REV)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["points"], 7)
        self.assertEqual(payload["counts"]["pending"], 1)
        self.assertEqual(payload["counts"]["in_review"], 1)
        self.assertEqual(payload["counts"]["blocked"], 1)
        self.assertEqual(payload["frozen"], 3)
        attention = {item["point_id"]: item["reasons"] for item in payload["attention"]}
        self.assertIn("P1", attention)
        self.assertIn("P2", attention)
        self.assertIn("P4", attention)
        self.assertIn("P5", attention)
        self.assertIn("frozen-drift", attention["P6"])
        self.assertFalse(payload["authority_granted"])

    def test_scoped_check_does_not_leak_other_points(self) -> None:
        result = self.cli("check", "--point", "P1", "--role", "implementer", "--current-revision", REV)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["point"]["id"], "P1")
        self.assertIn("modify", payload["allowed_actions"])
        self.assertIn("freeze", payload["forbidden_actions"])
        self.assertNotIn("P2", result.stdout)
        self.assertNotIn("P3", result.stdout)

    def test_generated_catalog_is_not_a_point_and_hold_overrides_role(self):
        (self.tasks / "context-index.json").write_text('{"entries":[]}', encoding="utf-8")
        for role in ("test-runner", "implementer", "reviewer", "deploy"):
            with self.subTest(role=role):
                report = self.payload(self.cli("check", "--point", "P5", "--role", role))
                self.assertEqual(report["allowed_actions"], ["read"])
                self.assertEqual(report["next_decision"], "require-owner-resumption")
                self.assertFalse(report["authority_granted"])
        (self.tasks / "bad-record.json").write_text('{}', encoding="utf-8")
        self.assertEqual(self.cli("check", "--point", "P5", "--role", "test-runner").returncode, 1)

    def test_frozen_point_is_read_only_for_implementer(self) -> None:
        result = self.cli("check", "--point", "P3", "--role", "implementer", "--current-revision", REV)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["point"]["frozen"])
        self.assertNotIn("modify", payload["allowed_actions"])
        self.assertIn("modify", payload["forbidden_actions"])

    def test_reviewer_and_deploy_roles(self) -> None:
        reviewer = self.cli("check", "--point", "P2", "--role", "reviewer", "--current-revision", REV)
        reviewer_payload = json.loads(reviewer.stdout)
        self.assertIn("review", reviewer_payload["allowed_actions"])
        self.assertIn("review-evidence-missing", reviewer_payload["blockers"])

        deploy = self.cli("check", "--point", "P3", "--role", "deploy", "--current-revision", REV)
        self.assertIn("deploy", json.loads(deploy.stdout)["allowed_actions"])

        pending = self.cli("check", "--point", "P1", "--role", "deploy", "--current-revision", REV)
        self.assertIn("deploy", json.loads(pending.stdout)["forbidden_actions"])

    def test_preflight_ready(self) -> None:
        result = self.cli("preflight", "--deploy-set", "D2", "--current-revision", REV)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["state"], "ready")
        self.assertEqual([item["point_id"] for item in payload["points"]], ["P3"])

    def test_preflight_blocks_pending_review_blocked_and_missing_evidence(self) -> None:
        result = self.cli("preflight", "--deploy-set", "D1", "--current-revision", REV)
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        blockers = " ".join(payload["blockers"])
        for value in ("P1", "P2", "P4", "P5"):
            self.assertIn(value, blockers)
        self.assertIn("review-evidence-missing", blockers)

    def test_preflight_blocks_frozen_drift(self) -> None:
        result = self.cli("preflight", "--deploy-set", "D3", "--current-revision", REV)
        self.assertEqual(result.returncode, 1)
        blockers = " ".join(json.loads(result.stdout)["blockers"])
        self.assertIn("P6", blockers)
        self.assertIn("frozen-drift", blockers)
        self.assertIn("P7", json.loads(result.stdout)["points"][1]["point_id"])

    def test_preflight_requires_known_current_revision(self) -> None:
        result = self.cli("preflight", "--deploy-set", "D2")
        self.assertEqual(result.returncode, 1)
        self.assertIn("revision-unknown", " ".join(json.loads(result.stdout)["blockers"]))

    def test_preflight_blocks_unknown_or_blocked_package(self) -> None:
        unknown = self.cli("preflight", "--deploy-set", "D4", "--current-revision", REV)
        self.assertEqual(unknown.returncode, 1)
        self.assertIn("deploy-set-unknown", " ".join(json.loads(unknown.stdout)["blockers"]))

        point = self.write_point(
            "P8", "done", review_state="reviewed", reviewers=["reviewer"],
            evidence=[".ai/assistant/reports/P8/review.json"], related=["D5"],
            reviewed=REV, validation="passed",
        )
        self.assertTrue(point.is_file())
        blocked = self.cli("preflight", "--deploy-set", "D5", "--current-revision", REV)
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("deploy-package-blocked", " ".join(json.loads(blocked.stdout)["blockers"]))

    def test_missing_tasks_directory_is_unavailable(self) -> None:
        empty = Path(self.temporary.name) / "empty"
        empty.mkdir()
        result = subprocess.run(
            [
                sys.executable, "-B", str(ROOT / "tools/point_keeper.py"),
                "--target", str(empty), "status",
            ],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["state"], "unavailable")

    def test_invalid_point_record_blocks_preflight(self) -> None:
        (self.tasks / "bad.json").write_text("{}", encoding="utf-8")
        result = self.cli("preflight", "--deploy-set", "D2", "--current-revision", REV)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid-point-record", " ".join(json.loads(result.stdout)["blockers"]))

        status = self.cli("status", "--current-revision", REV)
        self.assertEqual(json.loads(status.stdout)["invalid_point_count"], 1)

    def test_preflight_checks_inventory_below_at_and_above_limit(self) -> None:
        for number in range(8, 4096):
            self.write_point(f"P{number:04}", "pending")
        command = ("preflight", "--deploy-set", "D2", "--current-revision", REV)
        self.assertEqual(self.cli(*command).returncode, 0)  # 4095 records.
        self.write_point("P4096", "pending")
        self.assertEqual(self.cli(*command).returncode, 0)  # 4096 records.
        self.write_point("zz-blocked", "blocked", related=["D2"])
        overflow = self.cli(*command)
        self.assertEqual(overflow.returncode, 1)
        self.assertIn("point-inventory-exceeds-limit:4096", overflow.stdout)
        self.assertNotEqual(self.cli("check", "--point", "P3", "--role", "deploy").returncode, 0)
        (self.tasks / "P4096.json").unlink()
        blocked = self.cli(*command)
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("zz-blocked: not-done:blocked", blocked.stdout)

    def test_duplicate_package_id_cannot_override_blocked_package(self) -> None:
        index = self.target / ".ai/assistant/change-packages/index.json"
        index.write_text(json.dumps({"records": [{"package_id": "D2", "status": "blocked"},
            {"package_id": "D2", "status": "complete"}]}), encoding="utf-8")
        result = self.cli("preflight", "--deploy-set", "D2", "--current-revision", REV)
        self.assertEqual(result.returncode, 1)
        self.assertIn("package-index-duplicate-id", result.stdout)

    def test_digest_is_stable_and_authority_is_none(self) -> None:
        first = self.cli("check", "--point", "P3", "--role", "deploy", "--current-revision", REV)
        second = self.cli("check", "--point", "P3", "--role", "deploy", "--current-revision", REV)
        one = json.loads(first.stdout)
        two = json.loads(second.stdout)
        self.assertEqual(one["keeper_digest"], two["keeper_digest"])
        self.assertTrue(one["keeper_digest"].startswith("sha256:"))
        self.assertEqual(one["authority"], "none")
        self.assertFalse(one["authority_granted"])


if __name__ == "__main__":
    unittest.main()
