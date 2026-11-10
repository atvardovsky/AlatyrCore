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
sys.path.insert(0, str(ROOT / "tools"))
from execution_admission import admission_plan, inspect_admission
from target_adapter_validation.context import TargetRepositoryView
from cooperation_preflight import preflight


def task(identity, **changes):
    return {"id": identity, "requires": [], "state": "READY", "slots": 1,
            "resources": [], "write_scope": [], **changes}


def projection(*rows, **changes):
    return {"schema_version": 1, "plan": {"path": "plan.md", "sha256": "a" * 64},
            "capacity": 2, "max_parallel": 2, "accepted_ids": [], "retry_ids": [],
            "tasks": list(rows) or [task("a")], **changes}


def resource(**changes):
    return {"kind": "database", "id": "fixture-db", "namespace": None,
            "access": "write", "isolation": "shared", **changes}


class AdmissionTests(unittest.TestCase):
    def test_capacity_boundaries_and_no_execution_grant(self):
        for size in (1, 2, 3):
            result = admission_plan(projection(*(task(str(i)) for i in range(size))))
            self.assertEqual(len(result["selected_ids"]), min(size, 2))
            self.assertFalse(result["execution_authorized"])
            self.assertFalse(result["acceptance_granted"])

    def test_return_is_not_acceptance_and_accepted_result_unlocks(self):
        for state in ("RUNNING", "REVIEW_REQUIRED", "DONE", "FAILED", "BLOCKED", "CANCELLED"):
            value = projection(task("a", state=state), task("b", requires=["a"]))
            self.assertNotIn("b", admission_plan(value)["selected_ids"])
        value = projection(task("a", state="DONE"), task("b", requires=["a"]), accepted_ids=["a"])
        self.assertEqual(admission_plan(value)["selected_ids"], ["b"])
        self.assertEqual(admission_plan(projection(task("planned", state="PLANNED")))["selected_ids"], [])

    def test_retry_is_explicit_and_does_not_unlock_dependent(self):
        value = projection(task("a", state="FAILED"), task("b", requires=["a"]))
        self.assertEqual(admission_plan(value)["selected_ids"], [])
        value["retry_ids"] = ["a"]
        self.assertEqual(admission_plan(value)["selected_ids"], ["a"])

    def test_refill_does_not_wait_for_whole_wave(self):
        value = projection(task("a", state="RUNNING"), task("b", state="DONE"),
                           task("c", requires=["b"]), accepted_ids=["b"])
        self.assertEqual(admission_plan(value)["selected_ids"], ["c"])

    def test_unknown_resources_do_not_block_unrelated_ready_task(self):
        value = projection(task("unresolved-work", resources=None), task("oversized", slots=3), task("ready"))
        self.assertEqual(admission_plan(value)["selected_ids"], ["ready"])
        value = projection(task("running", state="RUNNING", resources=None), task("ready"))
        self.assertEqual(admission_plan(value)["selected_ids"], [])

    def test_resource_and_write_conflicts(self):
        for first, second, expected in [
            (resource(), resource(), ["a"]),
            (resource(access="read"), resource(access="read"), ["a", "b"]),
            (resource(namespace="one", isolation="verified-isolated"), resource(namespace="two", isolation="verified-isolated"), ["a", "b"]),
            (resource(access="exclusive"), resource(namespace="two", isolation="verified-isolated"), ["a"]),
        ]:
            self.assertEqual(admission_plan(projection(task("a", resources=[first]), task("b", resources=[second])))["selected_ids"], expected)
        for path in ("src", "src/file.py", "SRC/file.py", "."):
            value = projection(task("a", write_scope=["src"]), task("b", write_scope=[path]))
            self.assertEqual(admission_plan(value)["selected_ids"], ["a"])

    def test_review_backlog_retains_scope_and_bounds_admission(self):
        value = projection(task("a", state="REVIEW_REQUIRED", write_scope=["src"]),
                           task("b", write_scope=["src/a.py"]), task("c"))
        self.assertEqual(admission_plan(value)["selected_ids"], ["c"])
        value["max_parallel"] = 1
        self.assertEqual(admission_plan(value)["selected_ids"], [])
        value = projection(task("review", state="REVIEW_REQUIRED", slots=64), task("ready"))
        result = admission_plan(value)
        self.assertEqual(result["running_slots"], 0)
        self.assertEqual(result["allocated_slots"], 1)

    def test_numeric_and_nested_value_boundaries(self):
        for field in ("capacity", "max_parallel"):
            for value in (0, 1, 63, 64, 65):
                if 1 <= value <= 64:
                    admission_plan(projection(**{field: value}))
                else:
                    with self.assertRaises(ValueError):
                        admission_plan(projection(**{field: value}))
        for value in (0, 1, 63, 64, 65):
            if 1 <= value <= 64:
                admission_plan(projection(task("a", slots=value)))
            else:
                with self.assertRaises(ValueError):
                    admission_plan(projection(task("a", slots=value)))
        for malformed in (None, {}, [], True, 1, "unknown"):
            for field in resource():
                if field == "namespace" and malformed is None:
                    continue
                value = projection(task("a", resources=[resource(**{field: malformed})]))
                with self.subTest(field=field, value=malformed), self.assertRaises(ValueError):
                    admission_plan(value)
            for field in ("path", "sha256"):
                value = projection()
                value["plan"][field] = malformed
                if field == "path" and malformed == "unknown":
                    continue
                with self.subTest(field=field, value=malformed), self.assertRaises(ValueError):
                    admission_plan(value)

    def test_peer_holds_preserve_running_capacity_and_include_resource_scopes(self):
        plan = admission_plan(projection(task("running", state="RUNNING"), task("ready", resources=[resource()])))
        presence = {"enabled": True, "sessions": [], "omitted_sessions": 0,
                    "coordination": {"reported_overlaps": 0, "unknown_scope_peers": 0, "same_worktree_uncertain": 0}}
        for decision in ("unknown", "coordinate-before-work"):
            observed = copy.deepcopy(presence)
            if decision == "unknown":
                observed["coordination"]["unknown_scope_peers"] = 1
            else:
                observed["coordination"]["reported_overlaps"] = 1
            with patch("cooperation_preflight.operate", return_value=observed) as status:
                result = preflight(ROOT, ["path:src"], admission=plan)
            self.assertEqual(result["decision"], decision)
            self.assertEqual(result["admission"]["selected_ids"], [])
            self.assertEqual(result["admission"]["allocated_slots"], 1)
            self.assertEqual(result["admission"]["held"]["ready"], decision)
            self.assertTrue(set(plan["presence_scope_refs"]) <= set(status.call_args.kwargs["scope"]))

    def test_invalid_values_and_missing_fields_are_errors_not_crashes(self):
        samples = [None, {}, [], True, 1, "unknown"]
        for key in ("capacity", "max_parallel", "accepted_ids", "retry_ids", "tasks", "plan"):
            for sample in samples:
                value = projection()
                value[key] = sample
                if key in ("capacity", "max_parallel") and sample == 1 and type(sample) is int:
                    continue
                if key in ("accepted_ids", "retry_ids") and sample == []:
                    continue
                with self.subTest(key=key, sample=sample), self.assertRaises(ValueError):
                    admission_plan(value)
        for key in task("a"):
            value = projection()
            del value["tasks"][0][key]
            with self.assertRaises(ValueError):
                admission_plan(value)
        for key in ("id", "state", "slots", "requires", "resources", "write_scope"):
            for sample in samples:
                value = projection()
                value["tasks"][0][key] = sample
                if key in ("resources", "write_scope") and sample is None or key in ("resources", "write_scope", "requires") and sample == [] or key == "slots" and type(sample) is int and sample == 1:
                    continue
                with self.subTest(key=key, sample=sample), self.assertRaises(ValueError):
                    admission_plan(value)

    def test_graph_and_acceptance_corruption(self):
        cases = [projection(task("a"), task("a")), projection(task("a", requires=["missing"])),
                 projection(task("a", requires=["b"]), task("b", requires=["a"])),
                 projection(accepted_ids=["a"]), projection(retry_ids=["a"]),
                 projection(task("a", state="RUNNING", slots=3)),
                 projection(task("a", write_scope=["../escape"]))]
        for value in cases:
            with self.assertRaises(ValueError):
                admission_plan(value)

    def test_accepted_dependency_closure_is_required(self):
        for state in ("FAILED", "REVIEW_REQUIRED", "DONE"):
            value = projection(task("a", state=state), task("b", state="DONE", requires=["a"]),
                               task("c", requires=["b"]), accepted_ids=["b"])
            with self.assertRaisesRegex(ValueError, "prerequisite closure"):
                admission_plan(value)

    def test_existing_active_conflicts_require_reconciliation(self):
        for state in ("RUNNING", "REVIEW_REQUIRED"):
            value = projection(task("a", state="RUNNING", resources=[resource()]),
                               task("b", state=state, resources=[resource()]), task("c"))
            with self.assertRaisesRegex(ValueError, "active allocations conflict"):
                admission_plan(value)
        with self.assertRaisesRegex(ValueError, "unaccepted prerequisites"):
            admission_plan(projection(task("a"), task("b", state="RUNNING", requires=["a"])))

    def test_sequential_and_parallel_plans_preserve_same_dependency_coverage(self):
        rows = [task(str(i), requires=[str(i // 2)] if i else []) for i in range(16)]
        completed = []
        for capacity in (1, 2, 4):
            value = projection(*copy.deepcopy(rows), capacity=capacity, max_parallel=capacity)
            accepted = set()
            for iteration in range(16):
                result = admission_plan(value)
                for identity in result["selected_ids"]:
                    row = next(row for row in value["tasks"] if row["id"] == identity)
                    self.assertTrue(set(row["requires"]) <= accepted)
                    row["state"] = "DONE"
                    accepted.add(identity)
                value["accepted_ids"] = sorted(accepted)
                if len(accepted) == len(rows):
                    break
            completed.append(accepted)
        self.assertEqual(completed, [set(str(i) for i in range(16))] * 3)

    def test_boundary_size_64_and_65(self):
        for count in (63, 64):
            result = admission_plan(projection(*(task(str(i)) for i in range(count))))
            self.assertEqual(len(result["selected_ids"]), 2)
        with self.assertRaises(ValueError):
            admission_plan(projection(*(task(str(i)) for i in range(65))))

    def test_content_binding_and_duplicate_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            owner = root / "plan.md"
            owner.write_bytes(b"owned task graph\n")
            value = projection()
            value["plan"]["sha256"] = hashlib.sha256(owner.read_bytes()).hexdigest()
            path = root / "admission.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            self.assertEqual(inspect_admission(TargetRepositoryView(root), "admission.json")["selected_ids"], ["a"])
            owner.write_bytes(b"changed graph\n")
            with self.assertRaisesRegex(ValueError, "stale"):
                inspect_admission(TargetRepositoryView(root), "admission.json")
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(ValueError):
                inspect_admission(TargetRepositoryView(root), "admission.json")

    def test_cli_unknown_peer_state_suppresses_proposals_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "plan.md").write_bytes(b"graph")
            value = projection()
            value["plan"]["sha256"] = hashlib.sha256(b"graph").hexdigest()
            (root / "admission.json").write_text(json.dumps(value), encoding="utf-8")
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            command = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "cooperation-preflight", "--target", str(root), "--scope", "path:src", "--admission", "admission.json"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["admission"]["selected_ids"], [])
            self.assertEqual(json.loads(result.stdout)["admission"]["allocated_slots"], 0)
            self.assertIn("a", json.loads(result.stdout)["admission"]["held"])
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})


if __name__ == "__main__":
    unittest.main()
