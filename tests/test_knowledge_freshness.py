from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import inspect_session_context as session
import session_knowledge
from check_project_knowledge import fixture as knowledge_fixture
from context_planning import ContextPlanRequest, plan_target_context
from knowledge_freshness import MAX_SOURCE_BINDINGS, review_deadlines, source_bindings
from target_adapter_validation.project_knowledge import validate_project_knowledge_contract
from tests.test_context_planning import TargetFixture, write_json
from tests.test_target_validator_installation_state import validator, write_accepted_record, write_state


class SourceBindingTests(unittest.TestCase):
    def trigger(self, **changes):
        return dict(kind="source-sha256", subject="src/rule.py", expected=hashlib.sha256(b"rule").hexdigest(),
                    evidence="reviewed source dependency", action="revalidate", **changes)

    def test_source_binding_type_path_hash_and_size_boundaries(self):
        trigger = self.trigger()
        self.assertEqual(source_bindings([trigger], lambda _: b"rule"), {"src/rule.py": trigger["expected"]})
        with self.assertRaisesRegex(ValueError, "changed"):
            source_bindings([trigger], lambda _: b"new rule")
        for field in ("subject", "expected"):
            for invalid in ({}, [], None, True, 4, "unknown", "../escape"):
                with self.subTest(field=field, invalid=invalid), self.assertRaises(ValueError):
                    source_bindings([dict(trigger, **{field: invalid})])
        for count in (MAX_SOURCE_BINDINGS - 1, MAX_SOURCE_BINDINGS, MAX_SOURCE_BINDINGS + 1):
            triggers = [dict(trigger, subject=f"src/file-{index}.py") for index in range(count)]
            with self.subTest(count=count):
                if count > MAX_SOURCE_BINDINGS:
                    with self.assertRaises(ValueError): source_bindings(triggers)
                else:
                    self.assertEqual(len(source_bindings(triggers)), count)
        with self.assertRaisesRegex(ValueError, "repeated"):
            source_bindings([trigger, trigger])

    def test_review_dates_are_strict_and_do_not_accept_invalid_defaults(self):
        self.assertEqual(review_deadlines([{"kind": "review-expiry", "expected": "2099-01-01"}]), ["2099-01-01"])
        for invalid in ({}, [], None, True, 9, "unknown", "2099-02-30", "20990101"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                review_deadlines([{"kind": "review-expiry", "expected": invalid}])

    def test_new_modules_route_through_existing_transitive_check_ownership(self):
        from source_check_manifest import load_manifest, routes
        checks = {check["id"]: check for check in load_manifest()}
        for check_id, path in (("project-knowledge", "tools/knowledge_freshness.py"),
                               ("session-continuity", "tools/session_knowledge.py"),
                               ("session-continuity", "tools/knowledge_freshness.py")):
            with self.subTest(check_id=check_id, path=path):
                self.assertTrue(routes(checks[check_id], path))


class KnowledgeCheckpointTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.target = Path(directory.name).resolve()
        TargetFixture(self.target).build()
        for name in session.TARGET_ANCHORS:
            path = self.target / name
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"{}\n")
        write_state(self.target, "accepted")
        write_accepted_record(self.target)
        self.index, self.shard, _ = knowledge_fixture(self.target)
        self.source = self.target / "src/payment/retry.py"
        self.shard["entries"][0]["freshness"]["triggers"] = self.shard["entries"][0]["freshness"]["triggers"][:1] + [{
            "kind": "source-sha256", "subject": "src/payment/retry.py",
            "expected": hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "evidence": "source dependency accepted with this knowledge", "action": "revalidate",
        }]
        self.query = {"schema_version": 1, "stage": "initial", "shard_ids": ["hydration"],
                      "selectors": {"project_areas": ["hydration"]}, "limit": 1}
        self.plan_path = ".ai/.runtime/context-plan.json"
        self.baseline_path = self.target / ".ai/.runtime/session-baseline.json"
        self.save()

    def save(self):
        write_json(self.target / ".ai/project/knowledge/index.json", self.index)
        write_json(self.target / ".ai/project/knowledge/routes/hydration.json", self.shard)
        write_json(self.target / ".ai/.runtime/query.json", self.query)

    def make_plan(self):
        plan = plan_target_context(ContextPlanRequest(self.target, "code-local", "product-change",
                                   knowledge_request=".ai/.runtime/query.json"))
        self.assertEqual(plan["status"], "ready", plan)
        write_json(self.target / self.plan_path, plan)
        return plan

    def capture(self):
        self.make_plan()
        baseline, _, _ = session.capture(self.target, [], context_plans=[self.plan_path])
        write_json(self.baseline_path, baseline)
        return baseline

    def invoke(self, *arguments, cli=False):
        arguments = ["--target", str(self.target), *arguments]
        if cli:
            return subprocess.run([sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "session-context", *arguments],
                                  capture_output=True, text=True, cwd=ROOT)
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["session-context", *arguments]), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = session.main()
        return subprocess.CompletedProcess(arguments, code, stdout.getvalue(), stderr.getvalue())

    def check(self, **kwargs):
        return self.invoke("check", "--baseline", str(self.baseline_path), **kwargs)

    def test_public_cli_plan_capture_and_same_version_source_drift(self):
        self.make_plan()
        result = self.invoke("capture", "--context-plan", self.plan_path, "--output", str(self.baseline_path), cli=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        saved = self.baseline_path.read_bytes()
        result = self.check(cli=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.source.write_bytes(b"changed rule; canonical prose and framework versions unchanged\n")
        result = self.check(cli=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["changed_paths"], ["src/payment/retry.py"])
        self.assertEqual(report["knowledge"]["affected_ids"], [self.shard["entries"][0]["knowledge_id"]])
        self.assertFalse(report["knowledge"]["reroute_required"])
        self.assertFalse(report["acceptance_granted"])
        self.assertFalse(report["knowledge"]["authority_promoted"])
        self.assertEqual(self.baseline_path.read_bytes(), saved)

    def test_installed_delegate_uses_the_same_plan_bound_checkpoint(self):
        self.make_plan()
        command = [sys.executable, "-B", str(ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"),
                   "session-context", "--target", str(self.target), "--framework-source", str(ROOT)]
        captured = subprocess.run([*command, "capture", "--context-plan", self.plan_path,
                                   "--output", str(self.baseline_path)], capture_output=True, text=True)
        self.assertEqual(captured.returncode, 0, captured.stdout + captured.stderr)
        self.source.write_bytes(b"changed after delegated capture\n")
        checked = subprocess.run([*command, "check", "--baseline", str(self.baseline_path)], capture_output=True, text=True)
        self.assertEqual(checked.returncode, 1, checked.stdout + checked.stderr)
        self.assertEqual(json.loads(checked.stdout)["knowledge"]["affected_ids"], [self.shard["entries"][0]["knowledge_id"]])

    def test_capture_rejects_stale_or_incomplete_ready_plan(self):
        plan = self.make_plan()
        original = self.source.read_bytes()
        self.source.write_bytes(original + b"changed\n")
        with self.assertRaisesRegex(ValueError, "changed"):
            session.capture(self.target, [], context_plans=[self.plan_path])
        self.source.write_bytes(original)
        for mutation in ("missing-source", "missing-owner", "missing-shard", "stale-summary", "blocked"):
            changed = copy.deepcopy(plan)
            if mutation == "missing-source":
                changed["routing_sources"]["knowledge_inputs"].pop("src/payment/retry.py")
            elif mutation == "missing-shard":
                changed["routing_sources"]["knowledge_inputs"].pop(".ai/project/knowledge/routes/hydration.json")
            elif mutation == "missing-owner":
                changed["context_packet"]["selected_items"] = [row for row in changed["context_packet"]["selected_items"]
                                                                if row["path"] != "docs/contracts/result-mapping.md"]
            elif mutation == "stale-summary":
                changed["knowledge"]["selection"]["constraints"][0]["summary"] = "stale fabricated summary"
            else:
                changed["status"] = "blocked"
            write_json(self.target / self.plan_path, changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                session.capture(self.target, [], context_plans=[self.plan_path])

    def test_retained_binding_completeness_is_checked_beyond_recomputed_fingerprint(self):
        original = self.capture()
        for path in ("src/payment/retry.py", ".ai/project/knowledge/routes/hydration.json"):
            for remove_projection in (False, True):
                baseline = copy.deepcopy(original)
                baseline["inputs"] = [item for item in baseline["inputs"] if item["path"] != path]
                if remove_projection:
                    for item in baseline["knowledge"]["items"]:
                        item["source_paths"] = [value for value in item["source_paths"] if value != path]
                    for descriptor in baseline["knowledge"]["plans"]:
                        descriptor["routing_paths"] = [value for value in descriptor["routing_paths"] if value != path]
                baseline["fingerprint"] = session.fingerprint(baseline)
                write_json(self.baseline_path, baseline)
                result = self.check()
                with self.subTest(path=path, remove_projection=remove_projection):
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_empty_selection_still_detects_added_knowledge_and_query_index_changes(self):
        self.query["selectors"] = {"project_areas": ["no-prior-match"]}
        self.save()
        baseline = self.capture()
        self.assertEqual(baseline["knowledge"]["items"], [])
        for relpath in (".ai/project/knowledge/index.json", ".ai/project/knowledge/routes/hydration.json", ".ai/.runtime/query.json"):
            path = self.target / relpath
            original = path.read_bytes()
            document = json.loads(original)
            if relpath.endswith("hydration.json"):
                document["entries"][0]["applicability"]["project_areas"].append("no-prior-match")
            elif relpath.endswith("query.json"):
                document["selectors"] = {"project_areas": ["hydration"]}
            else:
                document["owner"] += " reviewed"
            write_json(path, document)
            result = self.check()
            with self.subTest(path=relpath):
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertTrue(json.loads(result.stdout)["knowledge"]["reroute_required"])
            path.write_bytes(original)

    def test_expiry_is_checked_without_changing_content_identity(self):
        self.shard["entries"][0]["freshness"]["triggers"].append({
            "kind": "review-expiry", "subject": "review", "expected": "2099-01-01",
            "evidence": "accepted review deadline", "action": "revalidate"})
        self.save()
        baseline = self.capture()
        original_delta = session_knowledge.knowledge_delta
        for observed in (date(2098, 12, 31), date(2099, 1, 1), date(2099, 1, 2)):
            with patch.object(session_knowledge, "knowledge_delta", lambda binding, changed: original_delta(binding, changed, today=observed)):
                result = self.check()
            report = json.loads(result.stdout)
            with self.subTest(observed=observed):
                self.assertEqual(result.returncode, 1 if observed > date(2099, 1, 1) else 0, report)
                self.assertEqual(report["fingerprint"], baseline["fingerprint"])
                self.assertEqual(report["changed_paths"], [])
                self.assertIn("checked_at", report)

    def test_unchanged_check_does_not_rerun_query_and_preserves_warnings(self):
        self.shard["entries"][0]["freshness"]["triggers"].append({
            "kind": "dependency-version", "subject": "example/package", "expected": "1",
            "evidence": "external behavior unverified", "action": "revalidate"})
        self.save()
        baseline = self.capture()
        self.assertEqual(baseline["knowledge"]["items"][0]["freshness_state"], "revalidation-required")
        with patch("knowledge_context.select_context_knowledge", side_effect=AssertionError("unexpected query")), \
                patch.object(Path, "rglob", side_effect=AssertionError("unexpected recursive scan")):
            result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["knowledge"]["warning_ids"], [self.shard["entries"][0]["knowledge_id"]])
        self.assertEqual(report["knowledge"]["unverified_trigger_kinds"], ["dependency-version"])
        self.assertFalse(report["authorization_granted"])

    def test_unselected_changes_and_no_query_plans_do_not_expand_knowledge(self):
        baseline = self.capture()
        unrelated = self.target / ".ai/project/knowledge/routes/unselected.json"
        write_json(unrelated, {"unrelated": "not routed"})
        self.assertEqual(self.check().returncode, 0)
        self.assertNotIn(unrelated.relative_to(self.target).as_posix(), {item["path"] for item in baseline["inputs"]})
        plan = plan_target_context(ContextPlanRequest(self.target, "code-local", "product-change"))
        self.assertEqual(plan["status"], "ready", plan)
        write_json(self.target / self.plan_path, plan)
        with patch("knowledge_context.select_context_knowledge", side_effect=AssertionError("unexpected query")):
            captured, _, _ = session.capture(self.target, [], context_plans=[self.plan_path])
        self.assertEqual(captured["knowledge"]["items"], [])
        self.assertNotIn(".ai/project/knowledge/index.json", {item["path"] for item in captured["inputs"]})

    def test_registered_validator_and_planner_reject_source_drift_and_bad_expiry(self):
        self.make_plan()
        self.source.write_bytes(b"changed implementation\n")
        checked = validator(self.target)
        validate_project_knowledge_contract(checked, None)
        self.assertTrue(any(f.code == "PROJECT_KNOWLEDGE_FRESHNESS_TRIGGER" and "changed" in f.message for f in checked.findings))
        plan = plan_target_context(ContextPlanRequest(self.target, "code-local", "product-change", knowledge_request=".ai/.runtime/query.json"))
        self.assertEqual(plan["status"], "blocked", plan)
        self.shard["entries"][0]["freshness"]["triggers"] = self.shard["entries"][0]["freshness"]["triggers"][:1] + [{
            "kind": "review-expiry", "subject": "review", "expected": "unknown", "evidence": "invalid", "action": "revalidate"}]
        self.save()
        checked = validator(self.target)
        validate_project_knowledge_contract(checked, None)
        self.assertTrue(any(f.code == "PROJECT_KNOWLEDGE_FRESHNESS_TRIGGER" and "ISO date" in f.message for f in checked.findings))

    def test_registered_source_reads_join_the_validation_mutation_guard(self):
        self.make_plan()
        checked = validator(self.target)
        validate_project_knowledge_contract(checked, None)
        self.assertFalse(any(f.code == "PROJECT_KNOWLEDGE_FRESHNESS_TRIGGER" for f in checked.findings), checked.findings)
        self.source.write_bytes(b"changed after validation read\n")
        self.assertIn(self.source, {mutation.path for mutation in checked.context.finalize()})

    def test_plan_count_boundaries_and_retained_baseline_byte_limit(self):
        plan = self.make_plan()
        paths = [f".ai/.runtime/plan-{index}.json" for index in range(9)]
        for path in paths:
            write_json(self.target / path, plan)
        for count in (7, 8, 9):
            with self.subTest(count=count):
                if count > 8:
                    with self.assertRaisesRegex(ValueError, "1..8"):
                        session.capture(self.target, [], context_plans=paths[:count])
                else:
                    baseline, _, _ = session.capture(self.target, [], context_plans=paths[:count])
                    self.assertEqual(len(baseline["knowledge"]["plans"]), count)
        first = self.target / ".ai/.runtime/size.json"
        result = self.invoke("capture", "--context-plan", self.plan_path, "--output", str(first))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        size = len(first.read_bytes())
        for maximum in (size - 1, size, size + 1):
            output = self.target / f".ai/.runtime/size-{maximum}.json"
            with self.subTest(maximum=maximum), patch.object(session, "MAX_BASELINE_BYTES", maximum):
                result = self.invoke("capture", "--context-plan", self.plan_path, "--output", str(output))
                self.assertEqual(result.returncode, 2 if maximum < size else 0, result.stdout + result.stderr)
                self.assertEqual(output.exists(), maximum >= size)

    def test_aggregate_byte_boundaries_allow_a_final_empty_input(self):
        for size in (14, 15, 16):
            (self.target / "anchor").write_bytes(b"a" * 5)
            (self.target / "remaining").write_bytes(b"b" * size)
            (self.target / "zz-empty").write_bytes(b"")
            with self.subTest(size=size), patch.object(session, "SOURCE_ANCHORS", frozenset({"anchor"})), \
                    patch.object(session, "MAX_TOTAL_BYTES", 20):
                if size > 15:
                    with self.assertRaises(ValueError):
                        session.capture(self.target, ["remaining", "zz-empty"], source_contour=True)
                else:
                    _, _, measured = session.capture(self.target, ["remaining", "zz-empty"], source_contour=True)
                    self.assertEqual(measured["input_bytes"], 5 + size)

    def test_knowledge_query_byte_boundary_also_allows_a_final_empty_source(self):
        empty = self.target / "src/payment/empty.py"
        empty.write_bytes(b"")
        self.shard["entries"][0]["freshness"]["triggers"].append({
            "kind": "source-sha256", "subject": "src/payment/empty.py", "expected": hashlib.sha256(b"").hexdigest(),
            "evidence": "reviewed empty source", "action": "revalidate"})
        self.save()
        plan = self.make_plan()
        total = sum(len((self.target / path).read_bytes()) for path in plan["routing_sources"]["knowledge_inputs"])
        for maximum in (total - 1, total, total + 1):
            with self.subTest(maximum=maximum), patch("knowledge_context.MAX_INPUT_BYTES", maximum):
                result = plan_target_context(ContextPlanRequest(self.target, "code-local", "product-change", knowledge_request=".ai/.runtime/query.json"))
                self.assertEqual(result["status"], "blocked" if maximum < total else "ready", result)

    def test_knowledge_metadata_file_limit_boundaries(self):
        maximum_size = max(len((self.target / path).read_bytes()) for path in (
            ".ai/.runtime/query.json", ".ai/project/knowledge/index.json", ".ai/project/knowledge/routes/hydration.json"))
        for maximum in (maximum_size - 1, maximum_size, maximum_size + 1):
            with self.subTest(maximum=maximum), patch("knowledge_context.MAX_METADATA_BYTES", maximum):
                result = plan_target_context(ContextPlanRequest(self.target, "code-local", "product-change", knowledge_request=".ai/.runtime/query.json"))
                self.assertEqual(result["status"], "blocked" if maximum < maximum_size else "ready", result)

    def test_forged_current_warning_is_not_a_canonical_selection(self):
        plan = self.make_plan()
        plan["knowledge"]["selection"]["warnings"] = plan["knowledge"]["selection"]["constraints"]
        plan["knowledge"]["selection"]["constraints"] = []
        write_json(self.target / self.plan_path, plan)
        with self.assertRaisesRegex(ValueError, "knowledge bindings"):
            session.capture(self.target, [], context_plans=[self.plan_path])

    def test_plan_is_target_only_and_missing_sources_cannot_establish_current(self):
        self.capture()
        self.source.unlink()
        result = self.check()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "unavailable")
        with self.assertRaisesRegex(ValueError, "source-contour"):
            session.capture(ROOT, [], source_contour=True, context_plans=[self.plan_path])

    def test_malformed_plan_and_baseline_fields_return_diagnostics(self):
        plan = self.make_plan()
        for key in ("request", "context_packet", "knowledge", "routing_sources"):
            for value in ({}, [], None, True, 5, "unknown"):
                document = copy.deepcopy(plan)
                document[key] = value
                write_json(self.target / self.plan_path, document)
                result = self.invoke("capture", "--context-plan", self.plan_path)
                with self.subTest(key=key, value=value):
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
        self.make_plan()
        baseline = self.capture()
        for key in baseline["knowledge"]["items"][0]:
            for value in ({}, [], None, True, 8, "unknown"):
                if value == baseline["knowledge"]["items"][0][key]:
                    continue
                document = copy.deepcopy(baseline)
                document["knowledge"]["items"][0][key] = value
                document["fingerprint"] = session.fingerprint(document)
                write_json(self.baseline_path, document)
                result = self.check()
                with self.subTest(key=key, value=value):
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
