"""Readiness is early structural evidence, never execution or acceptance."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from tests.active_task_fixture import ActiveTaskFixture, ROOT
from check_change_packages import changed_index_validator
from initialization_readiness import initialization_readiness
from architecture_review import review_frontier, review_routes


class InitializationReadinessTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        self.model["protected_change"] = False
        self.write_model(); self.write_index()

    def inspect(self, identity="fixture-task"):
        checked = changed_index_validator(self.target)
        checked.enforce_approval_scope = True
        result = initialization_readiness(checked, identity)
        return checked, result

    def test_registered_pending_task_is_readiness_not_acceptance(self):
        self.model["proof_obligations"][0]["status"] = "open"
        self.write_model(); self.write_index()
        checked, result = self.inspect()
        self.assertEqual(result["state"], "prerequisites-consistent-not-acceptance", checked.findings)
        self.assertFalse(result["authorization_granted"])
        self.assertFalse(result["acceptance_eligible"])
        self.assertTrue(result["full_acceptance_required"])

    def test_missing_registration_model_and_closed_task_block(self):
        self.assertEqual(self.inspect("unknown-task")[1]["state"], "blocked")
        self.close()
        self.assertEqual(self.inspect()[1]["state"], "blocked")
        self.task["state"] = "active"; self.task["completion_evidence"] = None
        self.write_index(); self.model_path.unlink()
        self.assertEqual(self.inspect()[1]["state"], "blocked")

    def test_old_approval_missing_fields_is_detected_before_project_execution(self):
        directory = self.target / ".ai/assistant/approvals"
        directory.mkdir(parents=True)
        (directory / "old.json").write_text(json.dumps({"schema_version": 2, "scope": {}}))
        checked, result = self.inspect()
        self.assertEqual(result["state"], "blocked")
        self.assertIn("APPROVAL_RECORD_FIELD_MISSING", self.errors(checked))

    def test_protected_work_requires_explicit_approval_selection(self):
        self.model["protected_change"] = True
        self.write_model(); self.write_index()
        checked, result = self.inspect()
        self.assertEqual(result["state"], "blocked")
        self.assertIn("INITIALIZATION_APPROVAL_REQUIRED", self.errors(checked))

    def test_input_mutation_invalidates_early_readiness(self):
        checked = changed_index_validator(self.target)
        def change_after_reads():
            (self.target / ".ai/assistant/active-tasks.json").write_bytes(b"{}")
        with patch.object(checked, "check_change_packages", side_effect=change_after_reads):
            result = initialization_readiness(checked, "fixture-task")
        self.assertEqual(result["state"], "blocked")
        self.assertIn("TARGET_INPUT_MUTATED", self.errors(checked))

    def test_selected_approval_metadata_matches_operation_but_grants_no_authority(self):
        from tests.test_approval_scope_command import approval_record
        self.model["protected_change"] = True
        self.write_model(); self.write_index()
        record = approval_record(["src/**", "design.md"])
        record["operation"]["id"] = self.task["operation_id"]
        record["plan"].update(file="design.md", sha256=self.bind(self.target / "design.md")["sha256"])
        path = self.target / ".ai/assistant/approvals/current.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(record))
        checked = changed_index_validator(self.target)
        checked.enforce_approval_scope = True; checked.approval_records = [path]
        result = initialization_readiness(checked, "fixture-task")
        self.assertEqual(result["state"], "prerequisites-consistent-not-acceptance", checked.findings)
        self.assertFalse(result["authorization_granted"])
        record["operation"]["id"] = "different-operation"; path.write_text(json.dumps(record))
        checked = changed_index_validator(self.target)
        checked.enforce_approval_scope = True; checked.approval_records = [path]
        self.assertEqual(initialization_readiness(checked, "fixture-task")["state"], "blocked")
        self.assertIn("INITIALIZATION_APPROVAL_IDENTITY", self.errors(checked))

    def test_real_doctor_cli_initialization_cannot_claim_acceptance(self):
        completed = subprocess.run([sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "doctor",
            "--target", str(self.target), "--initialization", "--current-task", "fixture-task", "--json"],
            capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        result = json.loads(completed.stdout)
        self.assertFalse(result["placeholder_validation"]["acceptance_eligible"])
        self.assertEqual(result["initialization_readiness"]["state"], "prerequisites-consistent-not-acceptance")

    def test_architecture_frontier_preserves_fact_or_owner_routes_and_coalesces_inputs(self):
        digest = hashlib.sha256((self.target / "design.md").read_bytes()).hexdigest()
        review = {"state": "reviewed", "reason": "Accepted source review", "reviewer": "fixture owner",
            "reviewed_at": "2026-10-01T00:00:00Z", "changed_fact_ids": ["fact-1"],
            "inputs": [{"path": "design.md", "sha256": digest}]}
        items = [{"id": "area-a", "source_review": review}, {"id": "pattern-a", "source_review": copy.deepcopy(review)}]
        self.assertEqual(set(review_routes(items, [], ["fact-1"])), {"area-a", "pattern-a"})
        self.assertEqual(set(review_routes(items, ["./design.md"], [])), {"area-a", "pattern-a"})
        path = self.target / ".ai/project/architecture/catalog.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"schema_version": 2, "areas": items[:1], "patterns": items[1:]}))
        checked = changed_index_validator(self.target)
        self.assertEqual(review_frontier(checked, ["design.md"], [])["input_groups"], [])
        (self.target / "design.md").write_text("changed source")
        checked = changed_index_validator(self.target)
        result = review_frontier(checked, ["design.md"], [])
        self.assertEqual(len(result["input_groups"]), 1)
        self.assertEqual(set(result["input_groups"][0]["item_ids"]), {"area-a", "pattern-a"})
        self.assertEqual(result["state"], "revalidation-required")
        items[1]["id"] = "area-a"
        path.write_text(json.dumps({"schema_version": 2, "areas": items[:1], "patterns": items[1:]}))
        self.assertEqual(review_frontier(changed_index_validator(self.target), [], [])["state"], "unavailable")
        items[1]["id"] = "pattern-a"
        del items[1]["source_review"]
        path.write_text(json.dumps({"schema_version": 2, "areas": items[:1], "patterns": items[1:]}))
        self.assertEqual(review_frontier(changed_index_validator(self.target), [], [])["state"], "unavailable")
