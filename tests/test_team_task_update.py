from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_team_collaboration_scenarios import task, write_fixture, write_json
from commit_admission_packet import packet
from team_task_update import update
from team_task_control import takeover_tasks


class TaskUpdateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.target = Path(temporary.name).resolve()
        self.original = task()
        write_fixture(self.target, self.original)
        (self.target / ".ai/alatyr.yaml").write_text("project: fixture\n")
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Initial")
        self.record = self.target / ".ai/assistant/team/tasks/task-1.json"
        self.digest = hashlib.sha256(self.record.read_bytes()).hexdigest()
        self.point = self.original["id"]
        self.revision = self.original["record_revision"] + 1
        self.draft = {**self.original, "record_revision": self.revision, "expected_revision": self.revision,
                      "next_action": "Check the selected invariant before continuing."}

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.target, text=True).strip()

    def preview(self, **changes):
        write_json(self.target / "draft.json", {**self.draft, **changes})
        before = self.git("status", "--porcelain")
        command = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "team-task-update",
                   "--target", str(self.target), "--point", self.point, "--draft", "draft.json",
                   "--expected-sha256", self.digest]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(before, self.git("status", "--porcelain"))
        self.assertTrue(result.stdout, result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_registered_preview_and_exact_metadata_apply(self):
        code, report = self.preview()
        self.assertEqual(code, 0, report)
        self.assertFalse(report["write_performed"])
        self.assertEqual(len(report["paths"]), 2)
        with patch("target_tool_compat.assert_write_compatible"):
            with self.assertRaisesRegex(ValueError, "reviewed SHA-256"):
                update(self.target, self.point, "draft.json", self.digest, write=True, draft_sha256="a" * 64)
            result = update(self.target, self.point, "draft.json", self.digest,
                            write=True, draft_sha256=report["draft_sha256"])
            self.assertTrue(result["write_performed"])
            self.assertFalse(result["acceptance_granted"])
            with self.assertRaisesRegex(ValueError, "record changed"):
                update(self.target, self.point, "draft.json", self.digest)

    def test_draft_does_not_create_authority_and_invalid_diagnostics_are_grouped(self):
        code, report = self.preview(allowed_actions=["not-a-real-action"])
        self.assertEqual(code, 1, report)
        self.assertIn("allowed_actions", report["protected_fields"])
        self.assertGreater(report["error_count"], 0)
        self.assertEqual(hashlib.sha256(self.record.read_bytes()).hexdigest(), self.digest)
        code, report = self.preview(expected_revision=self.revision - 1)
        self.assertEqual(code, 1, report)
        self.assertFalse(report["revision_valid"])
        code, report = self.preview(next_action="Read /tmp/local/receipt.json")
        self.assertEqual(code, 1, report)
        self.assertIn("LOCAL_PATH_LEAKAGE", report["error_groups"])

    def test_commit_packet_explains_message_and_patch_changes_without_committing(self):
        (self.target / "message.md").write_text("Review exact change\n")
        self.record.write_text(self.record.read_text() + " ")
        self.git("add", self.record.relative_to(self.target).as_posix())
        first = packet(self.target, "message.md")
        self.assertEqual(first["state"], "awaiting-client-admission")
        self.assertFalse(first["authorization_granted"])
        write_json(self.target / "previous.json", first)
        (self.target / "message.md").write_text("New commit message\n")
        next_packet = packet(self.target, "message.md", "previous.json")
        self.assertEqual(next_packet["changed_bindings"], ["message_sha256"])
        write_json(self.target / "validation.json", {
            "status": "passed", "counts": {"errors": 0},
            "evidence": {"observed_revision": first["binding"]["base_revision"]}})
        qualified = packet(self.target, "message.md", "previous.json", "validation.json")
        self.assertIn("validation_report", qualified["changed_bindings"])
        self.assertTrue(qualified["binding"]["validation_report"]["observed_base_matches"])
        self.assertFalse(qualified["binding"]["validation_report"]["staged_patch_qualified"])
        self.assertEqual(self.git("rev-parse", "HEAD"), first["binding"]["base_revision"])

    def test_takeover_is_bounded_to_selected_task_and_dependencies(self):
        records = {"parent": ("parent.json", {"status": "active", "dependencies": ["dep"]}),
                   "dep": ("dep.json", {"status": "blocked", "blockers": ["Owner hold"]}),
                   "other": ("other.json", {"status": "active", "dependencies": [None]})}
        result = takeover_tasks(records, "parent")
        self.assertEqual([row["task_id"] for row in result], ["parent", "dep"])
        self.assertEqual(result[1]["hold"], "task-not-runnable")
        records["dep"][1]["dependencies"] = ["parent"]
        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            takeover_tasks(records, "parent")
