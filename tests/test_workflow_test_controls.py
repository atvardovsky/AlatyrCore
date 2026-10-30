from __future__ import annotations

import copy
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from jsonschema import Draft202012Validator
from test_execution_contract import TestExecutionContract
from test_selection import MAX_BYTES, MAX_CASES, MAX_FILES, observed_selection, read_selection_json, selection_report
from testing_controls import MAX_PEERS, qualification_failures
from target_adapter_validation.context import TargetRepositoryView
from tests import test_test_execution_contract as execution_fixtures
from tests.test_test_execution_contract import nested_paths, policy, record, set_path
from yaml_support import safe_load


class HostedFixtureIsolationTests(unittest.TestCase):
    def test_portable_groups_preserve_the_exact_original_inventories(self):
        from check_source_unit_tests import explicit_test_modules
        workflow = safe_load((ROOT / ".github/workflows/cross-platform-source-checks.yml").read_text())
        steps = workflow["jobs"]["portable-source-checks"]["steps"]
        expected = {
            "Run portable support authoring regressions": (32, "19fda75427046a126feff993c29db5ebf350c4f37ccb7ec622f4a4a5b0b378e1"),
            "Run filesystem and session regressions": (5, "5ac0abeaa6fb1379b3c8cfeaf9739e11b113037951fb366a05a24f1740e5a20c"),
        }
        for name, (count, digest) in expected.items():
            step = next(row for row in steps if row.get("name") == name)
            arguments = shlex.split(step["run"])
            self.assertEqual(arguments[:4], ["python", "-B", "tools/check_source_unit_tests.py", "--test-module"])
            modules = arguments[4:]
            self.assertEqual(len(modules), count)
            self.assertEqual(hashlib.sha256("\0".join(modules).encode()).hexdigest(), digest)
            self.assertEqual(len(explicit_test_modules(modules)), count)
            self.assertEqual(step["env"]["ALATYR_CHILD_CAPACITY"], "2")
        setup = next(row for row in steps if row.get("name") == "Set up Python")
        self.assertEqual(setup["with"]["cache"], "${{ runner.os != 'Windows' && 'pip' || '' }}")
        self.assertNotIn("continue-on-error", setup)
        self.assertTrue(any(row.get("run") == "python -m pip check" for row in steps))

    def test_hosted_git_settings_are_effective_in_an_isolated_config(self):
        workflow = safe_load((ROOT / ".github/workflows/cross-platform-source-checks.yml").read_text())
        expected = {"gc.auto": "0", "gc.autoDetach": "false", "maintenance.auto": "false", "maintenance.autoDetach": "false"}
        for name in ("linux-source-checks", "portable-source-checks"):
            steps = workflow["jobs"][name]["steps"]
            matching = [(i, step) for i, step in enumerate(steps) if step.get("name") == "Keep disposable Git fixtures synchronous"]
            self.assertEqual(len(matching), 1)
            index, step = matching[0]
            self.assertLess(index, next(i for i, item in enumerate(steps) if item.get("name") in {"Run full source checks", "Run portable source checks"}))
            commands = [shlex.split(line) for line in step["run"].splitlines() if line.strip()]
            self.assertEqual(len(commands), len(expected))
            with tempfile.TemporaryDirectory() as directory:
                env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
                env.update(GIT_CONFIG_GLOBAL=str(Path(directory) / "fixture.gitconfig"), GIT_CONFIG_NOSYSTEM="1")
                for command in commands:
                    self.assertEqual(command[:3], ["git", "config", "--global"])
                    self.assertEqual(len(command), 5)
                    subprocess.run(command, cwd=directory, env=env, check=True, capture_output=True)
                for key, value in expected.items():
                    observed = subprocess.check_output(["git", "config", "--global", "--get", key], cwd=directory, env=env, text=True).strip()
                    self.assertEqual(observed, value)


def request():
    return {"schema_version": 1, "record_kind": "target-test-selection-request", "command_id": "unit",
            "files": ["tests/a.py"], "cases": [{"file": "tests/a.py", "id": "original-case"}]}


def observation():
    return {"schema_version": 1, "record_kind": "target-test-selection-observation", "command_id": "unit",
            "discovered_files": ["tests/a.py"], "executed_files": ["tests/a.py"],
            "cases": [{"file": "tests/a.py", "id": "original-case", "status": "passed"}]}


def window():
    return {"started_at": "2026-01-01T10:00:00Z", "finished_at": "2026-01-01T10:01:00Z",
            "clock_id": "fixture-host", "peer_coverage": "complete-observed-set", "peer_windows": []}


class SelectionResolverTests(unittest.TestCase):
    def test_complete_request_and_missing_files_or_cases(self):
        self.assertEqual(selection_report(request(), observation(), command_id="unit")["failures"], [])
        for field in ("files", "cases"):
            changed = request()
            changed[field].append("tests/missing.py" if field == "files" else {"file": "tests/a.py", "id": "absent-case"})
            result = selection_report(changed, observation(), command_id="unit")
            self.assertEqual(result["state"], "blocked")
            self.assertTrue(result["missing_files"] or result["missing_cases"])

    def test_execution_counts_and_focused_scope_cannot_hide_an_omission(self):
        rec = record()
        self.assertEqual(selection_report(request(), observation(), command_id="unit", phase="execution", record=rec, require_success=True)["failures"], [])
        for change in ("not-run", "skipped", "failed", "discovered"):
            obs = observation(); obs["cases"][0]["status"] = change
            self.assertTrue(selection_report(request(), obs, command_id="unit", phase="execution", record=rec, require_success=True)["failures"])
        rec["counts"]["passed"] = 2
        self.assertTrue(selection_report(request(), observation(), command_id="unit", phase="execution", record=rec)["failures"])

    def test_each_requested_file_needs_case_evidence_before_success(self):
        req = request(); req.update(files=["tests/a.py", "tests/b.py"], cases=[])
        obs = observation(); obs.update(discovered_files=req["files"], executed_files=req["files"])
        rec = record(); rec["files"].update(universe=req["files"], selected=req["files"], executed=req["files"])
        self.assertTrue(selection_report(req, obs, command_id="unit", phase="execution", record=rec, require_success=True)["failures"])
        obs["cases"].append({"file": "tests/b.py", "id": "second-case", "status": "passed"})
        rec["counts"].update(discovered=2, executed=2, passed=2)
        self.assertEqual(selection_report(req, obs, command_id="unit", phase="execution", record=rec, require_success=True)["failures"], [])

    def test_every_json_field_mutation_is_bounded_and_non_crashing(self):
        for original, which in ((request(), "request"), (observation(), "observations")):
            for path in nested_paths(original):
                for bad in (None, True, 7, "unknown", [], {}, [{}]):
                    changed = copy.deepcopy(original); set_path(changed, path, bad)
                    args = {"request": request(), "observations": observation()}; args[which] = changed
                    with self.subTest(which=which, path=path, bad=bad):
                        self.assertIsInstance(selection_report(**args, command_id="unit")["failures"], list)

    def test_exact_paths_and_case_identity_aliases_do_not_broaden_scope(self):
        for path in ("../a.py", "/a.py", "C:/a.py", "\\\\server\\a.py", "./tests/a.py", "tests//a.py", "tests\\a.py"):
            req = request(); req["files"] = [path]
            self.assertTrue(selection_report(req, observation(), command_id="unit")["failures"], path)
        obs = observation(); obs["cases"].append(copy.deepcopy(obs["cases"][0]))
        self.assertTrue(selection_report(request(), obs, command_id="unit")["failures"])

    def test_file_and_case_limits_below_at_above(self):
        for count in (MAX_FILES - 1, MAX_FILES, MAX_FILES + 1):
            req = request(); req["files"] = [f"tests/{i}.py" for i in range(count)]; req["cases"] = []
            obs = observation(); obs.update(discovered_files=req["files"], executed_files=[], cases=[])
            self.assertEqual(bool(selection_report(req, obs, command_id="unit")["failures"]), count > MAX_FILES)
        for count in (MAX_CASES - 1, MAX_CASES, MAX_CASES + 1):
            req = request(); req["cases"] = [{"file": "tests/a.py", "id": str(i)} for i in range(count)]
            obs = observation(); obs["cases"] = [{**row, "status": "passed"} for row in req["cases"]]
            self.assertEqual(bool(selection_report(req, obs, command_id="unit")["failures"]), count > MAX_CASES)

    def test_discovered_missing_target_file_is_not_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            result = observed_selection(TargetRepositoryView(Path(directory)), request(), observation(), command_id="unit")
            self.assertTrue(result["failures"])

    def test_artifact_bytes_below_at_above_and_digest_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for size in (MAX_BYTES - 1, MAX_BYTES, MAX_BYTES + 1):
                content = b"{}" + b" " * (size - 2)
                (root / "result.json").write_bytes(content)
                view = TargetRepositoryView(root)
                if size > MAX_BYTES:
                    with self.assertRaises(ValueError):
                        read_selection_json(view, "result.json")
                else:
                    self.assertEqual(read_selection_json(view, "result.json"), {})
                    with self.assertRaises(ValueError):
                        read_selection_json(view, "result.json", "0" * 64)


class TimingQualificationTests(unittest.TestCase):
    def test_overlapping_conflicting_windows_fail_touching_windows_pass(self):
        rec = record(); rec["qualification_window"] = window()
        peer = {"run_id": "peer", "started_at": "2026-01-01T10:00:30Z", "finished_at": "2026-01-01T10:02:00Z", "clock_id": "fixture-host", "resources": rec["resources"]}
        rec["qualification_window"]["peer_windows"] = [peer]
        self.assertTrue(qualification_failures(rec))
        peer["started_at"] = "2026-01-01T10:01:00Z"
        self.assertEqual(qualification_failures(rec), [])

    def test_canonical_read_and_isolated_namespace_exceptions_are_preserved(self):
        rec = record(); rec["resources"][0]["access"] = "read"; rec["qualification_window"] = window()
        peer = {"run_id": "peer", **{k: v for k, v in window().items() if k in ("started_at", "finished_at", "clock_id")}, "resources": copy.deepcopy(rec["resources"])}
        rec["qualification_window"]["peer_windows"] = [peer]
        self.assertEqual(qualification_failures(rec), [])
        for resource, namespace in ((rec["resources"][0], "a"), (peer["resources"][0], "b")):
            resource.update(namespace=namespace, access="write", isolation="verified-isolated")
        self.assertEqual(qualification_failures(rec), [])

    def test_malformed_enum_timestamp_and_peer_fields_return_findings(self):
        baseline = record(); baseline["qualification_window"] = window()
        baseline["qualification_window"]["peer_windows"] = [{"run_id": "peer", "started_at": "2026-01-01T09:00:00Z", "finished_at": "2026-01-01T09:01:00Z", "clock_id": "fixture-host", "resources": copy.deepcopy(baseline["resources"])}]
        for path in nested_paths(baseline["qualification_window"]):
            for bad in (None, True, 7, "unknown", [], {}, [{}]):
                rec = copy.deepcopy(baseline); set_path(rec["qualification_window"], path, bad)
                with self.subTest(path=path, bad=bad):
                    self.assertIsInstance(qualification_failures(rec), list)
        for value in ("2026-01-01T09:00:00", "2999-01-01T00:00:00Z", "not-a-date"):
            rec = record(); rec["qualification_window"] = window(); rec["qualification_window"]["started_at"] = value
            self.assertTrue(qualification_failures(rec))

    def test_peer_limit_below_at_above_and_incomparable_clock(self):
        for count in (MAX_PEERS - 1, MAX_PEERS, MAX_PEERS + 1):
            rec = record(); rec["qualification_window"] = window()
            rec["qualification_window"]["peer_windows"] = [{"run_id": str(i), "started_at": "2026-01-01T09:00:00Z", "finished_at": "2026-01-01T09:01:00Z", "clock_id": "fixture-host", "resources": []} for i in range(count)]
            self.assertEqual(bool(qualification_failures(rec)), count > MAX_PEERS)
        rec["qualification_window"]["peer_windows"] = [{"run_id": "peer", "started_at": "2026-01-01T09:00:00Z", "finished_at": "2026-01-01T09:01:00Z", "clock_id": "other-host", "resources": []}]
        self.assertTrue(qualification_failures(rec))


class VersionBoundaryTests(unittest.TestCase):
    def test_legacy_records_stay_readable_but_cannot_adopt_new_required_controls(self):
        contract = TestExecutionContract(); p = policy(); rec = record()
        self.assertEqual(contract.policy_failures(p), [])
        self.assertEqual(contract.evidence_failures(rec, p["commands"][0], p["execution_contract"]), [])
        p["commands"][0]["execution"]["selection_contract"] = "required"
        self.assertTrue(contract.policy_failures(p))
        p["execution_contract"]["schema_version"] = 3
        self.assertEqual(contract.policy_failures(p), [])
        legacy = json.loads((ROOT / "schemas/test-execution-contract-v2.schema.json").read_text())
        old = {"$ref": "#/$defs/policy", "$defs": legacy["$defs"]}
        self.assertTrue(list(Draft202012Validator(old).iter_errors(p)))
        self.assertTrue(contract.evidence_failures(rec, p["commands"][0], p["execution_contract"]))

    def test_wrong_command_binding_and_unadopted_claims_fail(self):
        contract = TestExecutionContract(); p = policy(); rec = record(); rec["command_id"] = "other"
        self.assertTrue(contract.evidence_failures(rec, p["commands"][0], p["execution_contract"]))
        rec = record(); rec["selection_evidence"] = {}
        self.assertTrue(contract.evidence_failures(rec, p["commands"][0], p["execution_contract"]))


class RegisteredSelectionTests(unittest.TestCase):
    fixture = execution_fixtures.RegisteredTestingExecutionTests.fixture
    write = execution_fixtures.RegisteredTestingExecutionTests.write
    findings = execution_fixtures.RegisteredTestingExecutionTests.findings

    def prepare(self, root):
        p, rec = self.fixture(root)
        p["execution_contract"]["schema_version"] = rec["schema_version"] = 3
        p["commands"][0]["execution"]["selection_contract"] = "required"
        self.write(root, ".ai/project/testing/test-first-policy.json", p)
        self.write(root, ".ai/framework/test-execution-selection.md", "conditional fixture guidance")
        self.write(root, "selection-request.json", request())
        self.write(root, "selection-result.json", {"selection": observation()})
        sha = lambda name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        rec["policy_sha256"] = sha(".ai/project/testing/test-first-policy.json")
        rec["selection_evidence"] = {"request": {"path": "selection-request.json", "sha256": sha("selection-request.json")}, "observations_pointer": "/selection"}
        rec["input_sha256"]["selection-request.json"] = sha("selection-request.json")
        rec["input_sha256"][".ai/framework/test-execution-selection.md"] = sha(".ai/framework/test-execution-selection.md")
        rec["result_artifact"] = {"path": "selection-result.json", "sha256": sha("selection-result.json")}
        self.write(root, "current.json", rec)
        return p, rec

    def test_registered_path_reads_actual_observations_and_rejects_contradiction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); _, rec = self.prepare(root)
            self.assertEqual([x.code for x in self.findings(root) if x.level == "error"], [])
            changed = observation(); changed["cases"][0]["id"] = "different-case"
            self.write(root, "selection-result.json", {"selection": changed})
            rec["result_artifact"]["sha256"] = hashlib.sha256((root / "selection-result.json").read_bytes()).hexdigest()
            self.write(root, "current.json", rec)
            findings = self.findings(root)
            self.assertIn("TDD_EXECUTION_EVIDENCE", {x.code for x in findings if x.level == "error"})

    def test_adopted_control_requires_guidance_and_bound_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); _, rec = self.prepare(root)
            (root / ".ai/framework/test-execution-selection.md").unlink()
            self.assertTrue(any(x.code == "TDD_EXECUTION_CONTRACT" for x in self.findings(root)))
            self.write(root, ".ai/framework/test-execution-selection.md", "conditional fixture guidance")
            for value in (None, {"path": "selection-result.json", "sha256": "0" * 64}):
                rec["result_artifact"] = value
                self.write(root, "current.json", rec)
                self.assertTrue(any(x.code in {"TDD_EXECUTION_EVIDENCE", "TDD_EXECUTION_EVIDENCE_STALE"} for x in self.findings(root)))

    def test_registered_path_rejects_requested_file_without_case_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); _, rec = self.prepare(root)
            self.write(root, "tests/b.py", "fixture")
            req = request(); req.update(files=["tests/a.py", "tests/b.py"], cases=[])
            obs = observation(); obs.update(discovered_files=req["files"], executed_files=req["files"])
            self.write(root, "selection-request.json", req)
            self.write(root, "selection-result.json", {"selection": obs})
            digest = lambda path: hashlib.sha256((root / path).read_bytes()).hexdigest()
            rec["files"].update(universe=req["files"], selected=req["files"], executed=req["files"])
            rec["input_sha256"]["tests/b.py"] = digest("tests/b.py")
            rec["input_sha256"]["selection-request.json"] = digest("selection-request.json")
            rec["selection_evidence"]["request"]["sha256"] = digest("selection-request.json")
            rec["result_artifact"]["sha256"] = digest("selection-result.json")
            self.write(root, "current.json", rec)
            self.assertTrue(any(x.code == "TDD_EXECUTION_EVIDENCE" and "completely passed" in x.message for x in self.findings(root)))
            obs["cases"].append({"file": "tests/b.py", "id": "second-case", "status": "passed"})
            self.write(root, "selection-result.json", {"selection": obs})
            rec["result_artifact"]["sha256"] = digest("selection-result.json")
            rec["counts"].update(discovered=2, executed=2, passed=2)
            self.write(root, "current.json", rec)
            self.assertEqual([x.code for x in self.findings(root) if x.level == "error"], [])

    def test_public_preflight_and_validator_use_same_selection_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); self.prepare(root)
            self.write(root, "discovery.json", observation())
            argv = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "plan-test-selection", "--target", str(root), "--command", "unit", "--request", "selection-request.json", "--observations", "discovery.json"]
            result = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            req = request(); req["files"].append("tests/missing.py"); self.write(root, "selection-request.json", req)
            result = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["missing_files"], ["tests/missing.py"])
            result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/validate_target_adapter.py"), "--target", str(root), "--json"], capture_output=True, text=True)
            self.assertNotIn("Traceback", result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(any(x["code"] in {"TDD_EXECUTION_EVIDENCE", "TDD_EXECUTION_EVIDENCE_STALE"} for x in payload["findings"]))

    def test_registered_timing_control_rejects_actual_overlapping_peer_windows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); p, rec = self.prepare(root)
            rec["resources"][0]["access"] = "exclusive"
            p["commands"][0]["execution"].update(resources=copy.deepcopy(rec["resources"]), timing_qualification="required")
            self.write(root, ".ai/project/testing/test-first-policy.json", p)
            rec["policy_sha256"] = hashlib.sha256((root / ".ai/project/testing/test-first-policy.json").read_bytes()).hexdigest()
            rec["qualification_window"] = {"observations_pointer": "/qualification"}
            actual_window = window()
            self.write(root, "selection-result.json", {"selection": observation(), "qualification": actual_window})
            rec["result_artifact"]["sha256"] = hashlib.sha256((root / "selection-result.json").read_bytes()).hexdigest()
            self.write(root, "current.json", rec)
            self.assertEqual([x.code for x in self.findings(root) if x.level == "error"], [])
            actual_window["peer_windows"] = [{"run_id": "peer", "started_at": "2026-01-01T10:00:30Z", "finished_at": "2026-01-01T10:02:00Z", "clock_id": "fixture-host", "resources": copy.deepcopy(rec["resources"])}]
            self.write(root, "selection-result.json", {"selection": observation(), "qualification": actual_window})
            rec["result_artifact"]["sha256"] = hashlib.sha256((root / "selection-result.json").read_bytes()).hexdigest()
            self.write(root, "current.json", rec)
            findings = self.findings(root)
            self.assertTrue(any(x.code == "TDD_EXECUTION_EVIDENCE" and "overlaps" in x.message for x in findings))


if __name__ == "__main__":
    unittest.main()
