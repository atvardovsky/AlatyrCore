from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from qualification_evidence import review_qualification
from target_adapter_validation.context import TargetRepositoryView


class QualificationEvidenceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.target = Path(directory.name)
        self.put("source.txt", b"current source")
        current = hashlib.sha256((self.target / "source.txt").read_bytes()).hexdigest()
        self.manifest = {"schema_version": 1, "required_case_ids": ["one", "two"],
                         "current_input_sha256": {"source.txt": current}, "runs": []}
        self.add_run("current", [{"id": "one", "status": "passed"}], "current")
        self.add_run("historical", [{"id": "two", "status": "passed"}], "retained")

    def put(self, path, value):
        selected = self.target / path
        selected.parent.mkdir(parents=True, exist_ok=True)
        raw = value if isinstance(value, bytes) else json.dumps(value).encode()
        selected.write_bytes(raw)
        return {"path": path, "sha256": hashlib.sha256(raw).hexdigest()}

    def add_run(self, identity, cases, disposition, *, result="passed"):
        now = datetime.now(timezone.utc).isoformat()
        output = self.put(identity + "-result.json", {"cases": cases})
        inputs = self.manifest["current_input_sha256"] if disposition == "current" else {"source.txt": "0" * 64}
        receipt = self.put(identity + "-receipt.json", {"schema_version": 1, "record_kind": "alatyr-delivery-run-receipt",
            "request_id": "request", "task_id": "task", "command_id": "native-browser",
            "started_at": now, "finished_at": now, "result": result, "exit_code": 0 if result == "passed" else 1,
            "input_sha256": inputs, "result_artifact": output})
        review = None if disposition == "current" else self.put(identity + "-review.json", {
            "schema_version": 1, "receipt_sha256": receipt["sha256"],
            "current_input_sha256": self.manifest["current_input_sha256"],
            "case_ids": [c["id"] for c in cases if c["status"] == "passed"],
            "owner_ref": "architecture/test-policy.md", "reason": "Reviewed as historical scoped evidence, not a fresh run"})
        self.manifest["runs"].append({"id": identity, "receipt": receipt, "disposition": disposition, "equivalence_review": review})

    def review(self):
        return review_qualification(TargetRepositoryView(self.target), self.target, self.manifest)

    def test_retained_pass_is_separate_from_fresh_coverage_and_grants_no_acceptance(self):
        result = self.review()
        self.assertEqual(result["current_passed_case_ids"], ["one"])
        self.assertEqual(result["retained_reviewed_case_ids"], ["two"])
        self.assertEqual(result["fresh_missing_case_ids"], ["two"])
        self.assertEqual(result["uncovered_case_ids"], [])
        self.assertFalse(result["acceptance_granted"])
        self.assertFalse(result["authorization_granted"])

    def test_current_bindings_and_retained_review_cannot_be_asserted_or_stale(self):
        original = copy.deepcopy(self.manifest)
        self.manifest["runs"][1]["equivalence_review"] = None
        with self.assertRaises(ValueError): self.review()
        self.manifest = original
        self.put("source.txt", b"changed source")
        with self.assertRaisesRegex(ValueError, "digest"): self.review()

    def test_failed_runs_and_conflicting_current_cases_remain_visible(self):
        self.add_run("failure", [{"id": "one", "status": "failed"}], "current", result="failed")
        result = self.review()
        self.assertEqual(result["failed_or_interrupted_run_ids"], ["failure"])
        self.assertEqual(result["contradictory_case_ids"], ["one"])
        self.assertNotIn("one", result["current_passed_case_ids"])

    def test_passed_receipt_and_malformed_or_negative_statuses_cannot_hide_failure(self):
        for bad in ({}, [], None, True, 1, "incomplete", "unvalidated", "not completed", "failed"):
            with self.subTest(bad=bad):
                original = copy.deepcopy(self.manifest)
                self.manifest["runs"] = []
                self.add_run("bad", [{"id": "one", "status": bad}], "current")
                with self.assertRaises(ValueError): self.review()
                self.manifest = original

    def test_case_bounds_and_duplicates_fail_instead_of_truncating(self):
        for values in ([], ["one", "one"], [str(i) for i in range(257)]):
            with self.subTest(values=values[:2]):
                self.manifest["required_case_ids"] = values
                with self.assertRaises(ValueError): self.review()

    def test_failed_retained_run_never_becomes_current_and_malformed_ids_fail_safely(self):
        self.add_run("retained-failed", [{"id": "one", "status": "passed"}], "retained", result="failed")
        result = self.review()
        self.assertEqual(result["status"], "target-review-required")
        self.assertIn("retained-failed", result["failed_or_interrupted_run_ids"])
        self.assertEqual(result["current_passed_case_ids"], ["one"])
        for bad in ({}, [], None, True, 1):
            with self.subTest(bad=bad):
                original = self.manifest["required_case_ids"]
                self.manifest["required_case_ids"] = [bad]
                with self.assertRaises(ValueError): self.review()
                self.manifest["required_case_ids"] = original

    def test_actual_cli_and_installed_delegate_preserve_review_only_semantics(self):
        self.put("manifest.json", self.manifest)
        commands = [
            [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "review-qualification", "--target", str(self.target), "--manifest", "manifest.json"],
            [sys.executable, "-B", str(ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"), "review-qualification",
             "--target", str(self.target), "--framework-source", str(ROOT), "--manifest", "manifest.json"]]
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "target-review-required")
            self.assertFalse(json.loads(result.stdout)["acceptance_granted"])


if __name__ == "__main__":
    unittest.main()
