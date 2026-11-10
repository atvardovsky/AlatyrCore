from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.source_adoption_fixture import SourceAdoptionFixture, ROOT, git
from tests.test_approval_scope_command import approval_record
import source_adoption as adoption
import lifecycle_checkpoints as hooks
from inspect_source_adoption import bridge, knowledge, status
from inspect_session_context import check_retained_context
from source_scope import bind_scope, review_scope, validate_scope
from validate_target_adapter import Validator
from source_context_selection import workflow_route


class SourceAdoptionTests(SourceAdoptionFixture):
    def test_reconcile_is_idempotent_and_preserves_task_index(self):
        before = (self.target / adoption.INDEX).read_bytes()
        self.assertEqual(adoption.reconcile(self.target)["changed_paths"], [])
        adoption.reconcile(self.target, write=True)
        self.assertEqual((self.target / adoption.INDEX).read_bytes(), before)
        self.assertFalse((self.target / ".ai/framework").exists())
        self.assertFalse((self.target / ".ai/alatyr.yaml").exists())

    def test_existing_index_and_writer_lock_cannot_be_tracked(self):
        for path in (adoption.INDEX, ".ai/.runtime/support-writer/transaction.lock"):
            destination = self.target / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                destination.write_bytes(b"fixture\n")
            git(self.target, "add", "-f", path)
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "ignored and untracked"):
                adoption.reconcile(self.target, write=True)
            git(self.target, "reset", "--", path)

    def test_strategy_status_checks_missing_modified_and_added_descriptors(self):
        path = self.target / ".ai/assistant/analysis-strategies/invariant-first.json"
        raw = path.read_bytes()
        for changed in (None, raw + b" "):
            if changed is None:
                path.unlink()
            else:
                path.write_bytes(changed)
            self.assertEqual(status(self.target)["strategy_projection"], "reconciliation-required")
        path.write_bytes(raw)
        source = self.target / "templates/target/.ai/assistant/analysis-strategies/new-strategy.json"
        source.write_bytes(raw)
        self.assertEqual(status(self.target)["strategy_projection"], "reconciliation-required")

    def test_knowledge_lookup_reads_only_matching_owners(self):
        original = __import__("inspect_source_adoption").read_output
        reads = []
        def observed(root, path, **kwargs):
            reads.append(path.relative_to(root).as_posix())
            return original(root, path, **kwargs)
        with patch("inspect_source_adoption.read_output", side_effect=observed):
            knowledge(self.target, "no-such-term")
            self.assertEqual(reads, [])
            knowledge(self.target, "parser parity")
        self.assertEqual(reads, ["docs/source-optimization/source-management.md"])

    def test_malformed_bridge_catalogs_fail_with_value_diagnostics(self):
        path = self.target / "conformance/runs/assistant-surfaces.json"
        for value in ({}, {"surfaces": [None]}, {"surfaces": [{"id": "claude"}]},
                      {"surfaces": [{"id": "claude", "support_status": "unverified", "bridge_paths": {}}]}):
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.subTest(value=value), self.assertRaises(ValueError):
                bridge(self.target, "claude", write=False)

    def test_module_status_and_reference_lookup_do_not_claim_exercise(self):
        report = status(self.target)
        self.assertEqual(len(report["modules"]), 25)
        self.assertEqual(report["runtime"], "current-policy-projection")
        self.assertTrue(all(value is None for value in report["measurements"].values()))
        self.assertIn("not-established", report["module_exercise"])
        match = knowledge(self.target, "parser parity")["matches"]["canonical-parser-parity"]
        self.assertEqual(match["kind"], "incident-learning")
        self.assertEqual(knowledge(self.target, "no-such-term")["matches"], {})

    def test_workflow_adoption_routes_to_conditional_source_owners(self):
        report = status(self.target)
        for module in ("subagent-delegation", "large-task-orchestration"):
            self.assertIn("docs/workflow-efficiency.md", report["modules"][module]["references"])
        for query in ("parallel admission", "workflow efficiency"):
            match = knowledge(self.target, query)["matches"]["ready-work-refill"]
            self.assertEqual(match["owner"], "docs/source-worker-strategy.md")
            self.assertEqual(match["heading"], "Activation")
        self.assertFalse(workflow_route("small-task")["registered_task_required"])
        self.assertFalse((self.target / ".ai/alatyr.yaml").exists())
        self.assertIn("not-established", report["module_exercise"])

    def test_small_task_routing_performs_no_adoption_reads(self):
        with patch.object(adoption, "source_object", side_effect=AssertionError("no reads")):
            route = workflow_route("small-task")
        self.assertFalse(route["registered_task_required"])
        self.assertEqual(route["additional_bootstrap"], [])
        self.assertTrue(workflow_route("standard-task")["registered_task_required"])

    def test_projection_update_requires_explicit_consent_and_preserves_local_edits(self):
        path = self.target / "tools/source_lifecycle_policy.json"
        policy = json.loads(path.read_bytes())
        policy["binding_ttl_seconds"] -= 1
        path.write_text(json.dumps(policy), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed"):
            adoption.assert_current(self.target)
        with self.assertRaisesRegex(ValueError, "approval"):
            adoption.reconcile(self.target, write=True)
        adoption.reconcile(self.target, write=True, approve_policy_update=True)
        adoption.assert_current(self.target)
        projected = self.target / hooks.POLICY
        projected.write_bytes(projected.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "locally modified"):
            adoption.reconcile(self.target, write=True, approve_policy_update=True)

    def test_malformed_marker_and_policy_fields_are_diagnostics(self):
        original = json.loads((self.target / adoption.MARKER).read_bytes())
        for field in original:
            for value in ({}, [], None, True, 1):
                if type(value) is int and field == "schema_version" and value == 1:
                    continue
                row = copy.deepcopy(original); row[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    adoption.projection_marker(row)
        for field in ("lifecycle_policy", "guide", "knowledge_catalog", "schema_version", "scope"):
            policy = json.loads((self.target / adoption.POLICY).read_bytes()); policy[field] = {}
            with self.subTest(field=field), self.assertRaises(ValueError):
                adoption.parse_source_policy(policy)

    def test_source_root_and_installed_adapter_are_not_interchangeable(self):
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaisesRegex(ValueError, "restricted"):
                adoption.reconcile(Path(other), write=True)
        (self.target / ".ai/alatyr.yaml").write_text("schema_version: 111\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "installed target"):
            adoption.assert_current(self.target)

    def test_invalid_capability_catalog_is_an_actionable_policy_error(self):
        (self.target / "framework/capabilities.json").write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "classify every capability"):
            adoption.policy_inputs(self.target)

    def test_strategy_projection_rejects_symlinked_source_parents(self):
        directory = self.target / "templates/target/.ai/assistant/analysis-strategies"
        with tempfile.TemporaryDirectory() as external:
            outside = Path(external) / "descriptors"
            shutil.copytree(directory, outside)
            moved = directory.with_name("retained-descriptors")
            directory.rename(moved)
            try:
                directory.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                moved.rename(directory)
                self.skipTest("host cannot create a directory symlink")
            with self.assertRaisesRegex(ValueError, "unsafe parent"):
                adoption.reconcile(self.target, write=True)

    def test_all_bridges_preserve_catalog_levels_and_protect_existing_files(self):
        catalog = json.loads((ROOT / "conformance/runs/assistant-surfaces.json").read_bytes())
        for row in catalog["surfaces"]:
            result = bridge(self.target, row["id"], write=False)
            self.assertEqual(result["support_status"], row["support_status"])
            self.assertFalse(result["client_loading_verified"])
            for value in result["previews"].values():
                self.assertIn("AGENTS.md", value)
                self.assertNotIn(".ai/README.md", value)
        bridge(self.target, "claude", write=True)
        bridge(self.target, "claude", write=True)
        (self.target / "CLAUDE.md").write_text("user rules\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "preserve existing"):
            bridge(self.target, "claude", write=True)
        with self.assertRaisesRegex(ValueError, "ignored"):
            bridge(self.target, "zed-agent", write=True)

    def test_read_only_request_roundtrip_uses_source_baseline_and_isolated_runtime(self):
        self.brief["authorized_phases"] = ["inspect"]; self.write_brief()
        self.refresh_baseline()
        self.assertEqual(self.bind_request()["status"], "bound")
        action = self.action(kind="answer", phase="inspect", paths=[])
        self.assertEqual(self.event("before-action", alatyr_action=action)["status"], "request-consistent")
        self.assertTrue((self.target / ".ai/.runtime/source-lifecycle-hooks").is_dir())
        self.assertFalse((self.target / hooks.RUNTIME).exists())
        self.assertEqual(check_retained_context(self.target, self.target / self.baseline, source_contour=True)["status"], "current")
        with self.assertRaises((ValueError, OSError)):
            check_retained_context(self.target, self.target / self.baseline)

    def test_state_changing_source_request_requires_explicit_approval(self):
        self.refresh_baseline()
        with self.assertRaisesRegex(ValueError, "approval-record"):
            self.bind_request()
        result = hooks.review_request(self.target, self.brief_path, self.action(), source_contour=True)
        self.assertTrue(result["checkpoint_required"])
        self.assertIn("retained approval", result["reason"])

    def approval(self):
        path = ".ai/.runtime/source-approval.json"
        row = approval_record(["src/**"])
        row["operation"]["id"] = self.model["operation_id"]
        row["diff"]["base"] = self.source_base
        row["approval"]["source_or_message"] = self.brief["source_ref"]
        (self.target / path).write_text(json.dumps(row), encoding="utf-8")
        return path

    def test_actual_diff_rejects_unrelated_staged_untracked_deleted_and_renamed_paths(self):
        approval = self.approval()
        self.refresh_baseline([approval])
        self.assertEqual(self.bind_request(diff_ref=self.source_base, approval_records=[approval])["status"], "bound")
        (self.target / "src/example.txt").write_text("changed\n", encoding="utf-8")
        self.assertFalse(self.event("before-action", alatyr_action=self.action())["checkpoint_required"])
        outside = self.target / "outside.txt"
        outside.write_text("not approved\n", encoding="utf-8")
        result = self.event("before-action", alatyr_action=self.action())
        self.assertTrue(result["checkpoint_required"])
        self.assertIn("APPROVAL_SCOPE_MISMATCH", result["reason"])
        git(self.target, "add", "outside.txt")
        self.assertTrue(self.event("before-action", alatyr_action=self.action())["checkpoint_required"])
        git(self.target, "reset", "--", "outside.txt"); outside.unlink()
        (self.target / "design.md").unlink()
        self.assertTrue(self.event("before-action", alatyr_action=self.action())["checkpoint_required"])
        (self.target / "design.md").write_text("accepted design\n", encoding="utf-8")
        git(self.target, "mv", "design.md", "renamed.md")
        self.assertTrue(self.event("before-action", alatyr_action=self.action())["checkpoint_required"])

    def test_rebind_resume_and_new_request_preserve_or_reset_scope_explicitly(self):
        approval = self.approval()
        self.refresh_baseline([approval]); self.bind_request(diff_ref=self.source_base, approval_records=[approval])
        with self.assertRaisesRegex(ValueError, "explicit"):
            self.bind_request()
        row = json.loads((self.target / approval).read_bytes())
        row["scope"]["allowed_files_or_surfaces"].append("docs/**")
        (self.target / approval).write_text(json.dumps(row), encoding="utf-8")
        self.refresh_baseline([approval])
        with self.assertRaisesRegex(ValueError, "same-request"):
            self.bind_request(diff_ref=self.source_base, approval_records=[approval])
        self.request = self.event("resume")
        self.brief["request_id"] = self.request["request_id"]; self.write_brief(); self.refresh_baseline([approval])
        with self.assertRaisesRegex(ValueError, "same-request"):
            self.bind_request(diff_ref=self.source_base, approval_records=[approval])
        self.request = self.event("request")
        self.brief["request_id"] = self.request["request_id"]; self.write_brief(); self.refresh_baseline([approval])
        self.assertEqual(self.bind_request(diff_ref=self.source_base, approval_records=[approval])["status"], "bound")

    def test_proposed_path_is_checked_before_it_enters_git_diff(self):
        approval = self.approval()
        row = json.loads((self.target / approval).read_bytes())
        row["scope"]["allowed_files_or_surfaces"] = ["src/example.txt"]
        (self.target / approval).write_text(json.dumps(row), encoding="utf-8")
        self.refresh_baseline([approval]); self.bind_request(diff_ref=self.source_base, approval_records=[approval])
        self.assertFalse((self.target / "src/not-yet-written.txt").exists())
        result = self.event("before-action", alatyr_action=self.action(paths=["src/not-yet-written.txt"]))
        self.assertTrue(result["checkpoint_required"])
        self.assertIn("proposed source path exceeds", result["reason"])

    def test_bound_approval_cannot_be_replaced_during_canonical_consumption(self):
        approval = self.approval()
        path = self.target / approval
        original_raw = path.read_bytes()
        scope = bind_scope(self.target, {"diff_ref": self.source_base, "approval_records": [approval]}, None, self.brief, self.model)
        (self.target / "outside.txt").write_text("outside\n", encoding="utf-8")
        replacement = json.loads(original_raw)
        replacement["scope"]["allowed_files_or_surfaces"].append("outside.txt")
        canonical = Validator.check_approval_scope
        def substitute(validator):
            path.write_text(json.dumps(replacement), encoding="utf-8")
            try:
                return canonical(validator)
            finally:
                path.write_bytes(original_raw)
        with patch.object(Validator, "check_approval_scope", substitute):
            failures = review_scope(self.target, scope, self.action(), self.brief, self.model)
        self.assertTrue(failures)
        self.assertEqual(path.read_bytes(), original_raw)

    def test_empty_commit_path_list_does_not_hide_actual_scope_or_publication_exclusion(self):
        self.brief["authorized_phases"] += ["commit", "publish"]
        self.brief["effect_scope"] = ["git:commit", "git:push"]
        self.write_brief()
        approval = self.approval(); self.refresh_baseline([approval])
        self.bind_request(diff_ref=self.source_base, approval_records=[approval])
        (self.target / "outside.txt").write_text("outside\n", encoding="utf-8")
        result = self.event("before-action", alatyr_action=self.action(phase="commit", paths=[], effects=["git:commit"]))
        self.assertIn("APPROVAL_SCOPE_MISMATCH", result["reason"])
        result = self.event("before-action", alatyr_action=self.action(phase="publish", paths=[], effects=["git:push"]))
        self.assertIn("excludes action phase", result["reason"])

    def test_read_only_binding_cannot_acquire_new_scope_without_new_request(self):
        self.brief["authorized_phases"] = ["inspect"]; self.write_brief(); self.refresh_baseline(); self.bind_request()
        self.brief["authorized_phases"].append("modify"); self.write_brief()
        approval = self.approval(); self.refresh_baseline([approval])
        with self.assertRaisesRegex(ValueError, "read-only binding"):
            self.bind_request(diff_ref=self.source_base, approval_records=[approval])

    def test_scope_shape_budgets_and_bad_git_base_fail_closed(self):
        approval = self.approval()
        for value in (None, True, {}, [], 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_scope(value)
        for count, passes in ((0, False), (1, True), (32, True), (33, False)):
            scope = {"diff_base": self.source_base, "approval_records": {f"approval-{i}.json": "0"*64 for i in range(count)}}
            if passes:
                self.assertEqual(validate_scope(scope), scope)
            else:
                with self.assertRaises(ValueError): validate_scope(scope)
        with self.assertRaisesRegex(ValueError, "cannot be resolved"):
            bind_scope(self.target, {"diff_ref": "refs/missing-source-base", "approval_records": [approval]}, None, self.brief, self.model)

    def test_required_control_cannot_be_omitted_during_read_only_recovery(self):
        self.brief["authorized_phases"] = ["inspect"]; self.write_brief(); self.refresh_baseline()
        path = self.target / "tools/source_knowledge.json"
        path.write_bytes(path.read_bytes() + b" ")
        result = check_retained_context(self.target, self.target / self.baseline, source_contour=True,
                                        inspection_omissions=["tools/source_knowledge.json"],
                                        protected_inputs=adoption.assert_current(self.target))
        self.assertNotEqual(result["status"], "current")

    def test_public_cli_in_relocated_source_and_installed_target_parity(self):
        shutil.copytree(ROOT / "tools", self.target / "tools", dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(ROOT / "schemas", self.target / "schemas", dirs_exist_ok=True)
        shutil.copytree(ROOT / "framework", self.target / "framework", dirs_exist_ok=True)
        adoption.reconcile(self.target, write=True, approve_policy_update=True)
        command = [sys.executable, "-B", str(self.target / "tools/alatyr.py")]
        result = subprocess.run(command + ["source-adoption", "reconcile"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.brief["authorized_phases"] = ["inspect"]; self.write_brief(); self.refresh_baseline()
        result = subprocess.run(command + ["lifecycle-checkpoint", "--target", str(self.target), "--source-contour", "bind",
            "--session-id", "source-fixture", "--request-id", self.request["request_id"], "--baseline", self.baseline,
            "--task-id", "fixture-task", "--request-brief", self.brief_path], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        action = self.action(kind="answer", phase="inspect", paths=[])
        result = subprocess.run(command + ["lifecycle-checkpoint", "--target", str(self.target), "--source-contour",
            "checkpoint", "--event", "before-action"], input=json.dumps({"session_id": "source-fixture", "alatyr_action": action}), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        draft = ".ai/.runtime/source-authoring-draft.json"
        (self.target / draft).write_text(json.dumps(self.model), encoding="utf-8")
        publish = command + ["publish-task", "--target", str(self.target), "--source-contour", "--task-id", "fixture-task", "--draft", draft]
        result = subprocess.run(publish + ["--write"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        git(self.target, "add", "-f", adoption.INDEX)
        result = subprocess.run(publish + ["--write"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        git(self.target, "reset", "--", adoption.INDEX)
        with tempfile.TemporaryDirectory() as other:
            result = subprocess.run(command + ["lifecycle-checkpoint", "--target", other, "--source-contour", "status",
                "--session-id", "source-fixture"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("restricted", result.stdout)


if __name__ == "__main__":
    unittest.main()
