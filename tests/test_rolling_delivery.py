from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tests")]
from cooperation_preflight import preflight
from execution_admission import admission_plan, inspect_admission
from target_adapter_validation.context import TargetRepositoryView
from test_execution_admission import projection, task


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True).encode()


def brief():
    return {"schema_version": 1, "record_kind": "alatyr-request-brief", "request_id": "request-a",
            "task_id": "parent-task", "source_ref": "owner-message", "objective": "Deliver requested work",
            "outcomes": [{"id": "outcome-a", "statement": "Keep the original outcome", "rejection_case": "Component progress only",
                          "proof_obligation_ids": ["proof-a"]}],
            "constraints": [], "non_goals": [], "requested_order": [], "authorized_phases": ["inspect"],
            "write_scope": [], "effect_scope": []}


def rolling(*rows, **kwargs):
    value = projection(*rows, **kwargs)
    value["schema_version"] = 2
    value["delivery"] = {"operation_id": "operation-a",
                         "requests": [{"id": "request-a", "source": {"path": "brief.json", "sha256": digest(encoded(brief()))}}],
                         "items": [{"task_id": row["id"], "request_id": "request-a", "outcome_ids": ["outcome-a"], "owner_ref": "primary"}
                                   for row in value["tasks"]], "active_wave": None, "final_barrier": None}
    return value


class RollingDeliveryTests(unittest.TestCase):
    def fixture(self, root, value=None):
        value = copy.deepcopy(value or rolling())
        (root / "plan.md").write_bytes(b"primary-owned plan\n")
        (root / "brief.json").write_bytes(encoded(brief()))
        value["plan"]["sha256"] = digest((root / "plan.md").read_bytes())
        (root / "admission.json").write_bytes(encoded(value))
        return value

    def inspect(self, root):
        return inspect_admission(TargetRepositoryView(root), "admission.json")

    def wave(self, root, value):
        (root / "code.py").write_bytes(b"unchanged candidate\n")
        manifest = {"schema_version": 1, "record_kind": "alatyr-delivery-wave", "operation_id": "operation-a",
                    "wave_id": "wave-a", "task_ids": ["a"],
                    "items": [copy.deepcopy(next(row for row in value["delivery"]["items"] if row["task_id"] == "a"))],
                    "requests": copy.deepcopy(value["delivery"]["requests"]),
                    "inputs": [{"path": "code.py", "sha256": digest((root / "code.py").read_bytes())}]}
        (root / "wave.json").write_bytes(encoded(manifest))
        value["delivery"]["active_wave"] = {"id": "wave-a", "task_ids": ["a"],
                                              "manifest": {"path": "wave.json", "sha256": digest(encoded(manifest))}}
        (root / "admission.json").write_bytes(encoded(value))
        return manifest

    def test_schema1_selection_is_identical_for_opted_in_views(self):
        for capacity in (1, 2, 4):
            for state in ("READY", "RUNNING", "REVIEW_REQUIRED", "BLOCKED", "FAILED"):
                old = projection(task("a", state=state), task("b"), capacity=capacity, max_parallel=4)
                new = rolling(*old["tasks"], capacity=capacity, max_parallel=4)
                left, right = admission_plan(old), admission_plan(new)
                for field in ("selected_ids", "held", "allocated_slots", "running_slots", "presence_scope_refs"):
                    self.assertEqual(left[field], right[field])
                self.assertNotIn("delivery", left)
                self.assertFalse(right["execution_authorized"])
                self.assertFalse(right["acceptance_granted"])

    def test_review_recovery_independent_work_and_no_delivery_claim(self):
        value = rolling(task("a", state="RUNNING"), task("b", state="REVIEW_REQUIRED"), task("c"))
        result = admission_plan(value)
        self.assertEqual(result["delivery"]["review_due_ids"], ["b"])
        self.assertEqual(result["selected_ids"], [])
        value["tasks"][1]["state"] = "DONE"
        value["accepted_ids"] = ["b"]
        result = admission_plan(value)
        self.assertEqual(result["selected_ids"], ["c"])
        self.assertFalse(result["delivery"]["delivery_acceptance_granted"])
        self.assertEqual(admission_plan(rolling(task("blocked", state="BLOCKED"), task("independent")))["selected_ids"], ["independent"])

    def test_barrier_uses_fixed_snapshot_and_does_not_grant_execution(self):
        value = rolling(task("a", state="DONE"), task("final", requires=["a"]), accepted_ids=["a"])
        value["delivery"]["final_barrier"] = {"task_id": "final", "requires": ["a"]}
        result = admission_plan(value)
        self.assertEqual(result["selected_ids"], [])
        self.assertEqual(result["allocated_slots"], 0)
        self.assertEqual(result["delivery"]["next_decision"], "review-final-barrier")
        self.assertFalse(result["delivery"]["final_barrier"]["delivery_prerequisites_verified"])
        value["tasks"].append(task("late"))
        value["delivery"]["items"].append({"task_id": "late", "request_id": "request-a", "outcome_ids": ["outcome-a"], "owner_ref": "primary"})
        with self.assertRaisesRegex(ValueError, "complete task snapshot"):
            admission_plan(value)

    def test_malformed_nested_fields_produce_diagnostics(self):
        mutations = [(lambda v, x: v.update(delivery=x)),
                     (lambda v, x: v["delivery"].update(requests=x)),
                     (lambda v, x: v["delivery"].update(items=x)),
                     (lambda v, x: v["delivery"].update(operation_id=x)),
                     (lambda v, x: v["delivery"]["items"][0].update(task_id=x)),
                     (lambda v, x: v["delivery"]["items"][0].update(request_id=x)),
                     (lambda v, x: v["delivery"]["items"][0].update(outcome_ids=x)),
                     (lambda v, x: v["delivery"]["items"][0].update(owner_ref=x)),
                     (lambda v, x: v["delivery"]["requests"][0].update(source=x))]
        for mutate in mutations:
            for bad in (None, {}, [], True, False, 0, 1, "unknown"):
                value = rolling(); mutate(value, bad)
                with self.subTest(mutation=mutations.index(mutate), bad=bad), self.assertRaises(ValueError):
                    admission_plan(value)
        for field in ("active_wave", "final_barrier"):
            for bad in ({}, [], True, 1, "unknown"):
                value = rolling(); value["delivery"][field] = bad
                with self.subTest(field=field, bad=bad), self.assertRaises(ValueError):
                    admission_plan(value)

    def test_all_task_and_request_mapping_is_preserved(self):
        for mutate in (
            lambda v: v["delivery"]["items"].clear(),
            lambda v: v["delivery"]["items"].append(copy.deepcopy(v["delivery"]["items"][0])),
            lambda v: v["delivery"]["items"][0].update(request_id="foreign"),
            lambda v: v["delivery"]["requests"].append(copy.deepcopy(v["delivery"]["requests"][0])),
            lambda v: v["delivery"]["requests"][0]["source"].update(path="../outside"),
            lambda v: v["delivery"]["requests"][0]["source"].update(sha256="invalid"),
            lambda v: v["delivery"]["items"][0].update(outcome_ids=["outcome-a", "outcome-a"]),
        ):
            value = rolling(); mutate(value)
            with self.assertRaises(ValueError): admission_plan(value)

    def test_json_type_mutations_never_raise_unhandled_exceptions(self):
        value = rolling(task("a", state="DONE"), task("final", requires=["a"]), accepted_ids=["a"])
        value["delivery"]["active_wave"] = {"id": "wave-a", "task_ids": ["a"], "manifest": {"path": "wave.json", "sha256": "b" * 64}}
        value["delivery"]["final_barrier"] = {"task_id": "final", "requires": ["a"]}
        paths = []
        def collect(item, prefix=()):
            paths.append(prefix)
            if isinstance(item, dict):
                for key, child in item.items(): collect(child, (*prefix, key))
            elif isinstance(item, list):
                for index, child in enumerate(item): collect(child, (*prefix, index))
        collect(value)
        for path in paths:
            for bad in (None, {}, [], True, 1, 1.5, "unknown"):
                mutant = copy.deepcopy(value)
                if path:
                    container = mutant
                    for key in path[:-1]: container = container[key]
                    container[path[-1]] = bad
                else:
                    mutant = bad
                try: admission_plan(mutant)
                except ValueError: pass

    def test_task_request_and_owner_boundaries(self):
        for count in (63, 64):
            self.assertEqual(admission_plan(rolling(*(task("t" + str(i)) for i in range(count))))["delivery"]["item_count"], count)
        with self.assertRaises(ValueError): admission_plan(rolling(*(task("t" + str(i)) for i in range(65))))
        for count in (15, 16, 17):
            value = rolling(*(task("t" + str(i)) for i in range(count)))
            value["delivery"]["requests"] = [{"id": "r" + str(i), "source": {"path": "brief-" + str(i) + ".json", "sha256": "a" * 64}} for i in range(count)]
            for i, row in enumerate(value["delivery"]["items"]): row["request_id"] = "r" + str(i)
            if count <= 16: admission_plan(value)
            else:
                with self.assertRaises(ValueError): admission_plan(value)
        for length in (255, 256, 257):
            value = rolling(); value["delivery"]["items"][0]["owner_ref"] = "x" * length
            if length <= 256: admission_plan(value)
            else:
                with self.assertRaises(ValueError): admission_plan(value)

    def test_material_file_and_total_read_boundaries(self):
        from rolling_delivery import MAX_SOURCE_BYTES, MAX_TOTAL_BYTES
        for size in (MAX_SOURCE_BYTES - 1, MAX_SOURCE_BYTES, MAX_SOURCE_BYTES + 1):
            with self.subTest(size=size), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                value = self.fixture(root, rolling(task("a", state="DONE"), accepted_ids=["a"]))
                manifest = self.wave(root, value)
                content = b"x" * size
                (root / "code.py").write_bytes(content)
                manifest["inputs"][0]["sha256"] = digest(content)
                (root / "wave.json").write_bytes(encoded(manifest))
                value["delivery"]["active_wave"]["manifest"]["sha256"] = digest(encoded(manifest))
                (root / "admission.json").write_bytes(encoded(value))
                if size <= MAX_SOURCE_BYTES: self.inspect(root)
                else:
                    with self.assertRaisesRegex(ValueError, "oversized"): self.inspect(root)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            value = self.fixture(root, rolling(task("a", state="DONE"), accepted_ids=["a"]))
            manifest = self.wave(root, value)
            manifest["inputs"] = []
            for i in range(8):
                content = b"x" * MAX_SOURCE_BYTES
                name = "part-" + str(i)
                (root / name).write_bytes(content)
                manifest["inputs"].append({"path": name, "sha256": digest(content)})
            # Request and manifest bytes count too; eight full MiB must fail.
            self.assertEqual(sum((root / row["path"]).stat().st_size for row in manifest["inputs"]), MAX_TOTAL_BYTES)
            (root / "wave.json").write_bytes(encoded(manifest))
            value["delivery"]["active_wave"]["manifest"]["sha256"] = digest(encoded(manifest))
            (root / "admission.json").write_bytes(encoded(value))
            with self.assertRaisesRegex(ValueError, "oversized"): self.inspect(root)

    def test_bound_request_checks_real_content_and_complete_outcome_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            value = self.fixture(root)
            result = self.inspect(root)
            self.assertEqual(result["delivery"]["source_state"], "current-bound-requests")
            for mutate in (lambda v: v["delivery"]["requests"][0].update(id="different"),
                           lambda v: v["delivery"]["items"][0].update(outcome_ids=["missing"])):
                bad = copy.deepcopy(value); mutate(bad)
                (root / "admission.json").write_bytes(encoded(bad))
                with self.assertRaises(ValueError): self.inspect(root)
            self.fixture(root, value)
            (root / "brief.json").write_bytes(b"changed request")
            with self.assertRaisesRegex(ValueError, "request.*stale"): self.inspect(root)
            (root / "brief.json").unlink()
            with self.assertRaisesRegex(ValueError, "request.*unavailable"): self.inspect(root)

    def test_frozen_wave_is_bound_to_actual_inputs_and_late_arrivals_stay_outside(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            value = self.fixture(root, rolling(task("a", state="DONE"), task("later"), accepted_ids=["a"]))
            self.wave(root, value)
            result = self.inspect(root)
            self.assertEqual(result["delivery"]["wave"]["task_ids"], ["a"])
            self.assertEqual(result["selected_ids"], ["later"])
            self.assertEqual(result["delivery"]["wave"]["input_state"], "current-declared-inputs")
            (root / "code.py").write_bytes(b"changed candidate")
            with self.assertRaisesRegex(ValueError, "wave input.*stale"): self.inspect(root)

    def test_changed_frozen_owner_or_outcome_mapping_requires_new_review(self):
        for field, changed in (("owner_ref", "another-worker"), ("outcome_ids", ["other-outcome"])):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                value = self.fixture(root, rolling(task("a", state="DONE"), accepted_ids=["a"]))
                self.wave(root, value)
                value["delivery"]["items"][0][field] = changed
                (root / "admission.json").write_bytes(encoded(value))
                with self.assertRaises(ValueError): self.inspect(root)

    def test_large_view_falls_back_without_actionable_truncation(self):
        rows = [task("task-" + str(i) + "x" * 120, state="REVIEW_REQUIRED") for i in range(64)]
        result = admission_plan(rolling(*rows, max_parallel=64))
        self.assertEqual(result["delivery"]["state"], "reference-required")
        self.assertEqual(result["delivery"]["review_due_count"], 64)
        self.assertNotIn("review_due_ids", result["delivery"])

    def near_limit(self, size):
        from analysis_strategy_contract import canonical_utf8_size
        value = rolling(*(task("t" + str(i), state="REVIEW_REQUIRED") for i in range(64)), max_parallel=64)
        remaining = size - canonical_utf8_size(admission_plan(value)["delivery"])
        for row, item in zip(value["tasks"], value["delivery"]["items"]):
            addition = min(remaining, 128 - len(row["id"]))
            row["id"] += "x" * addition; item["task_id"] = row["id"]
            remaining -= addition
        self.assertEqual(remaining, 0)
        self.assertEqual(canonical_utf8_size(admission_plan(value)["delivery"]), size)
        return value

    def test_final_view_limits_include_verification_and_peer_hold_updates(self):
        from analysis_strategy_contract import canonical_utf8_size
        from rolling_delivery import coordination_hold
        growth = len("current-bound-requests") - len("not-verified")
        for final_size in (8191, 8192, 8193):
            with self.subTest(final_size=final_size), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                self.fixture(root, self.near_limit(final_size - growth))
                result = self.inspect(root)
                self.assertLessEqual(canonical_utf8_size(result["delivery"]), 8192)
                self.assertEqual(result["delivery"].get("state") == "reference-required", final_size > 8192)
                coordination_hold(result, "unknown")
                self.assertLessEqual(canonical_utf8_size(result["delivery"]), 8192)
                self.assertEqual(result["delivery"]["next_decision"], "coordinate-before-work")

    def test_shared_or_noncanonical_plan_request_paths_are_rejected_consistently(self):
        for plan_path in ("brief.json", "BRIEF.JSON", "./plan.md", "x" * 1025):
            value = rolling(); value["plan"]["path"] = plan_path
            value["plan"]["sha256"] = value["delivery"]["requests"][0]["source"]["sha256"]
            with self.subTest(path=plan_path), self.assertRaises(ValueError): admission_plan(value)
        for path in ("PLAN.MD", "BRIEF.JSON"):
            value = rolling(task("a", state="DONE"), accepted_ids=["a"])
            value["delivery"]["active_wave"] = {"id": "wave-a", "task_ids": ["a"],
                                                   "manifest": {"path": path, "sha256": "a" * 64}}
            with self.subTest(manifest=path), self.assertRaisesRegex(ValueError, "distinct"):
                admission_plan(value)
        value = rolling(task("a"), task("b"))
        value["delivery"]["requests"].append({"id": "request-b", "source": {
            "path": "BRIEF.JSON", "sha256": "a" * 64}})
        value["delivery"]["items"][1]["request_id"] = "request-b"
        with self.assertRaisesRegex(ValueError, "unique"):
            admission_plan(value)

    def test_context_checker_counts_large_task_conditional_owners(self):
        import contextlib
        import io
        import check_context_router
        original = check_context_router.load_json
        def omit(path):
            value = original(path)
            if str(path).endswith("task-scales/large-or-resumable.json"):
                value["conditional_context"] = [row for row in value["conditional_context"] if row["path"] != ".ai/framework/rolling-delivery.md"]
            return value
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(check_context_router.main(), 0)
        output = io.StringIO()
        with patch.object(check_context_router, "load_json", side_effect=omit), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.assertEqual(check_context_router.main(), 1)
        self.assertIn("omits framework files", output.getvalue())

    def test_source_mutation_during_cooperation_is_rejected_before_report(self):
        import contextlib
        import io
        import cooperation_preflight
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self.fixture(root)
            original = cooperation_preflight.preflight
            def mutate(*args, **kwargs):
                result = original(*args, **kwargs)
                (root / "brief.json").write_bytes(b"request changed during peer inspection")
                return result
            error = io.StringIO()
            args = ["cooperation-preflight", "--target", str(root), "--scope", "path:src", "--admission", "admission.json"]
            with patch.object(sys, "argv", args), patch.object(cooperation_preflight, "preflight", side_effect=mutate), contextlib.redirect_stderr(error):
                code = cooperation_preflight.main()
            self.assertEqual(code, 2)
            self.assertIn("delivery inputs changed", error.getvalue())

    def test_wave_mutations_fail_through_actual_inspector(self):
        mutations = [lambda m: m.update(task_ids=["foreign"]), lambda m: m.update(operation_id="foreign"),
                     lambda m: m.update(wave_id="foreign"), lambda m: m.update(schema_version=True),
                     lambda m: m.update(inputs=[]), lambda m: m.update(inputs=[{}]),
                     lambda m: m["inputs"][0].update(path="../outside"),
                     lambda m: m["inputs"].append(copy.deepcopy(m["inputs"][0]))]
        for mutate in mutations:
            with self.subTest(mutation=mutations.index(mutate)), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                value = self.fixture(root, rolling(task("a", state="DONE"), accepted_ids=["a"]))
                manifest = self.wave(root, value); mutate(manifest)
                (root / "wave.json").write_bytes(encoded(manifest))
                value["delivery"]["active_wave"]["manifest"]["sha256"] = digest(encoded(manifest))
                (root / "admission.json").write_bytes(encoded(value))
                with self.assertRaises(ValueError): self.inspect(root)

    def test_peer_uncertainty_suppresses_delivery_advice(self):
        report = admission_plan(rolling())
        observed = {"enabled": False, "sessions": [], "omitted_sessions": 0,
                    "coordination": {"reported_overlaps": 0, "unknown_scope_peers": 0, "same_worktree_uncertain": 0}}
        with patch("cooperation_preflight.operate", return_value=observed):
            result = preflight(ROOT, ["path:src"], admission=report)
        self.assertEqual(result["admission"]["selected_ids"], [])
        self.assertEqual(result["admission"]["delivery"]["next_decision"], "coordinate-before-work")

    def test_public_cli_and_installed_delegate_are_read_only_and_reject_stale_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            suffix = ["cooperation-preflight", "--target", str(root), "--scope", "path:src", "--admission", "admission.json"]
            commands = [[sys.executable, "-B", str(ROOT / "tools/alatyr.py"), *suffix],
                        [sys.executable, "-B", str(ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"),
                         *suffix, "--framework-source", str(ROOT)]]
            for command in commands:
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report["admission"]["delivery"]["source_state"], "current-bound-requests")
                self.assertEqual(report["admission"]["selected_ids"], [])
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
            (root / "brief.json").write_bytes(b"different request")
            for command in commands:
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("stale", result.stderr)
                self.assertNotIn("Traceback", result.stderr)


class RollingWorkerTests(unittest.TestCase):
    from test_prepare_delegation_context import WorkerContextTests as _Fixture
    setUp = _Fixture.setUp
    bundle = _Fixture.bundle

    def admission(self, *, state="READY", owner="primary"):
        value = rolling(task("worker", state=state), capacity=1, max_parallel=1)
        value["delivery"]["items"][0]["owner_ref"] = owner
        (self.root / "plan.md").write_bytes(b"stable rolling work plan")
        value["plan"]["sha256"] = digest((self.root / "plan.md").read_bytes())
        (self.root / "brief.json").write_bytes(encoded(brief()))
        (self.root / "admission.json").write_bytes(encoded(value))
        return {"admission_path": "admission.json", "allocation_id": "worker", "admission_sha256": digest(encoded(value))}

    def test_worker_preparation_retains_delivery_sources_and_owner_on_continuation(self):
        from execution_admission import worker_admission_binding
        prior = self.bundle(**self.admission())
        binding = prior[0]["admission"]
        self.assertEqual(binding["delivery"]["request_source"]["path"], "brief.json")
        self.assertIn("brief.json", binding["input_sha256"])
        worker_admission_binding(binding)
        expanded = self.bundle(previous=prior, prompt=None, bootstrap={}, expansions=["detail.txt"], **self.admission(state="RUNNING"))
        self.assertEqual(expanded[0]["admission"]["origin"], binding["origin"])
        with self.assertRaisesRegex(ValueError, "delivery request or ownership"):
            self.bundle(previous=expanded, prompt=None, bootstrap={}, **self.admission(state="RUNNING", owner="foreign-worker"))
        broken = copy.deepcopy(binding); del broken["input_sha256"]["brief.json"]
        with self.assertRaises(ValueError): worker_admission_binding(broken)
        for field in binding["delivery"]:
            for bad in (None, {}, [], True, 1, "unknown"):
                mutant = copy.deepcopy(binding); mutant["delivery"][field] = bad
                with self.subTest(field=field, bad=bad), self.assertRaises(ValueError): worker_admission_binding(mutant)


if __name__ == "__main__":
    unittest.main()
