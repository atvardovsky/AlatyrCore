from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_all import (  # noqa: E402
    RunnerResult,
    available_cpu_count,
    build_run_identity,
    default_changed_from,
    effective_baseline,
    execute_checks,
    historical_duration_estimates,
    load_manifest,
    print_check_result,
    render_report,
    render_timed_report,
    resolve_report_path,
    resolve_changed_from,
    resolve_job_count,
    run_check,
    reusable_results,
    selection_report,
    select_check_plan,
    select_checks,
)
from source_state import snapshot_changes, source_snapshot  # noqa: E402


def check(check_id: str, *dependencies: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "command": [f"tools/{check_id}.py"],
        "depends_on": list(dependencies),
        "contract_inputs": [f"area/{check_id}/**"],
        "implementation_paths": [f"tools/{check_id}.py"],
        "trigger_paths": [f"area/{check_id}/**", f"tools/{check_id}.py"],
        "always_for_changed": False,
        "timeout_seconds": 30,
        "resource_class": "standard",
    }


class CheckGraphTests(unittest.TestCase):
    def test_historical_durations_require_matching_platform_and_python_family(self) -> None:
        report = {
            "schema_version": 3,
            "source": {"check_manifest_schema_version": 4},
            "environment": {"platform": "linux", "python": "3.13.1 build"},
            "checks": [{"id": "one", "status": "passed", "duration_seconds": 2.5}],
        }
        current_source = {"check_manifest_schema_version": 4}

        self.assertEqual(
            historical_duration_estimates(
                report,
                current_source=current_source,
                current_environment={"platform": "linux", "python": "3.13.2 build"},
            ),
            {"one": 2.5},
        )
        self.assertEqual(
            historical_duration_estimates(
                report,
                current_source=current_source,
                current_environment={"platform": "windows", "python": "3.13.2 build"},
            ),
            {},
        )

    def test_historical_duration_hint_survives_a_reused_result(self) -> None:
        report = {
            "schema_version": 3,
            "source": {"check_manifest_schema_version": 4},
            "environment": {"platform": "linux", "python": "3.13.1 build"},
            "checks": [
                {
                    "id": "one",
                    "status": "reused-pass",
                    "duration_seconds": 0.0,
                    "duration_hint_seconds": 2.5,
                }
            ],
        }

        self.assertEqual(
            historical_duration_estimates(
                report,
                current_source={"check_manifest_schema_version": 4},
                current_environment={"platform": "linux", "python": "3.13.2 build"},
            ),
            {"one": 2.5},
        )

    def test_auto_jobs_respect_host_affinity_and_quota(self) -> None:
        from unittest.mock import patch

        with patch("check_all.os.cpu_count", return_value=16):
            with patch(
                "check_all.os.sched_getaffinity",
                return_value=set(range(6)),
                create=True,
            ):
                with patch("check_all._cpu_quota_count", return_value=4):
                    self.assertEqual(available_cpu_count(), 4)
                    self.assertEqual(resolve_job_count("auto"), 4)

    def test_numeric_jobs_remain_exact_and_invalid_values_fail(self) -> None:
        self.assertEqual(resolve_job_count(3), 3)
        self.assertEqual(resolve_job_count("7"), 7)
        with self.assertRaisesRegex(ValueError, "positive"):
            resolve_job_count(0)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            resolve_job_count("many")

    def test_concise_success_keeps_warnings_and_suppresses_routine_output(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            print_check_result(
                check_id="example",
                result=(0, "OK detail\nWARN: review this\n", "", ["python", "check.py"]),
                observation={"duration_seconds": 1.25},
                verbose=False,
            )

        self.assertIn("PASS example (1.250s)", stdout.getvalue())
        self.assertIn("WARN: review this", stdout.getvalue())
        self.assertNotIn("OK detail", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_failure_output_is_complete_even_when_not_verbose(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            print_check_result(
                check_id="example",
                result=(1, "partial\n", "failure\n", ["python", "check.py"]),
                observation={"duration_seconds": 0.5},
                verbose=False,
            )

        self.assertIn("$ python check.py", stdout.getvalue())
        self.assertIn("partial", stdout.getvalue())
        self.assertIn("failure", stderr.getvalue())

    def test_timed_report_preserves_phase_telemetry(self) -> None:
        selected = [check("example")]
        report = render_timed_report(
            profile="full",
            selected=selected,
            results={"example": (0, "detail", "", ["python", "check.py"])},
            blocked={},
            source_changes=[],
            telemetry={
                "example": {"duration_seconds": 0.2},
                "_summary": {
                    "wall_seconds": 0.2,
                    "setup_seconds": 0.1,
                    "fingerprint_seconds": 0.05,
                    "execution_seconds": 0.2,
                },
            },
            input_fingerprints={},
            reuse={},
            selection={"selected_check_ids": ["example"]},
            source={"source_commit": "abc", "manifest_sha256": "digest"},
            environment={"platform": "linux", "python": "3.13"},
            run_identity={"selected_check_ids": ["example"]},
        )

        self.assertEqual(report["timing"]["setup_seconds"], 0.1)
        self.assertEqual(report["timing"]["fingerprint_seconds"], 0.05)
        self.assertEqual(report["timing"]["execution_seconds"], 0.2)
        self.assertGreaterEqual(report["timing"]["report_preparation_seconds"], 0)
        self.assertIn("before final JSON", report["timing"]["report_timing_scope"])
    def test_profile_selection_respects_platform_contract(self) -> None:
        checks = [
            {
                **check("portable"),
                "profiles": ["platform"],
                "platforms": ["all"],
            },
            {
                **check("linux-only"),
                "profiles": ["platform"],
                "platforms": ["linux"],
            },
        ]

        selected, _fell_back = select_checks(
            checks, "platform", None, platform="windows"
        )

        self.assertEqual([item["id"] for item in selected], ["portable"])

    def test_live_platform_profile_omits_full_source_unit_suite(self) -> None:
        checks = load_manifest()

        platform_ids = {
            item["id"]
            for item in select_check_plan(
                checks,
                "platform",
                None,
                platform="windows",
            ).selected
        }
        full_ids = {
            item["id"]
            for item in select_check_plan(
                checks,
                "full",
                None,
                platform="linux",
            ).selected
        }

        self.assertNotIn("source-unit-tests", platform_ids)
        self.assertIn("source-unit-tests", full_ids)

    def test_shared_dependency_selection_reason_is_deterministic(self) -> None:
        dependency = {
            **check("dependency"),
            "profiles": ["full"],
            "platforms": ["all"],
        }
        alpha = {
            **check("alpha", "dependency"),
            "profiles": ["quick"],
            "platforms": ["all"],
        }
        omega = {
            **check("omega", "dependency"),
            "profiles": ["quick"],
            "platforms": ["all"],
        }

        plan = select_check_plan(
            [dependency, omega, alpha],
            "quick",
            None,
            platform="linux",
        )
        selected_dependency = next(
            item for item in plan.selected if item["id"] == "dependency"
        )

        self.assertEqual(
            selected_dependency["_selection"]["reasons"],
            ["dependency-of:alpha"],
        )

    def test_live_fast_docs_change_omits_source_unit_suite(self) -> None:
        from unittest.mock import patch

        with patch("check_all.git_changed_paths", return_value=["docs/human/faq.md"]):
            selected, fell_back = select_checks(
                load_manifest(),
                "fast",
                "HEAD~1",
                platform="linux",
            )

        selected_ids = {item["id"] for item in selected}
        self.assertFalse(fell_back)
        self.assertNotIn("source-unit-tests", selected_ids)
        self.assertIn("markdown-links", selected_ids)

    def test_changed_fast_profile_selects_invariants_and_matching_routes(self) -> None:
        checks = [
            {
                **check("invariant"),
                "profiles": ["fast", "full"],
                "platforms": ["all"],
                "always_for_changed": True,
            },
            {
                **check("matched"),
                "profiles": ["fast", "full"],
                "platforms": ["all"],
            },
            {
                **check("unrelated"),
                "profiles": ["fast", "full"],
                "platforms": ["all"],
            },
        ]

        from unittest.mock import patch

        with patch("check_all.git_changed_paths", return_value=["area/matched/file.md"]):
            selected, fell_back = select_checks(
                checks, "fast", "HEAD~1", platform="linux"
            )

        self.assertFalse(fell_back)
        self.assertEqual([item["id"] for item in selected], ["invariant", "matched"])

    def test_micro_profile_selects_explicit_micro_routes(self) -> None:
        checks = [
            {
                **check("markdown"),
                "profiles": ["micro", "full"],
                "platforms": ["all"],
                "trigger_paths": ["**/*.md"],
                "micro_trigger_paths": ["docs/human/**"],
            }
        ]

        from unittest.mock import patch

        with patch("check_all.git_changed_paths", return_value=["docs/human/faq.md"]):
            plan = select_check_plan(checks, "micro", "HEAD~1", platform="linux")

        self.assertFalse(plan.escalated_from_micro)
        self.assertEqual(plan.effective_profile, "micro")
        self.assertEqual([entry["id"] for entry in plan.selected], ["markdown"])
        self.assertEqual(
            plan.selection_details["markdown"]["reasons"],
            ["micro-changed-path-trigger"],
        )

    def test_micro_profile_escalates_to_fast_for_non_micro_route(self) -> None:
        checks = [
            {
                **check("markdown"),
                "profiles": ["micro", "full"],
                "platforms": ["all"],
                "trigger_paths": ["**/*.md"],
                "micro_trigger_paths": ["docs/human/**"],
            },
            {
                **check("framework"),
                "profiles": ["fast", "full"],
                "platforms": ["all"],
                "trigger_paths": ["README.md", "tools/framework.py"],
            },
        ]

        from unittest.mock import patch

        with patch("check_all.git_changed_paths", return_value=["README.md"]):
            plan = select_check_plan(checks, "micro", "HEAD~1", platform="linux")

        self.assertTrue(plan.escalated_from_micro)
        self.assertEqual(plan.effective_profile, "fast")
        self.assertEqual([entry["id"] for entry in plan.selected], ["framework"])
        self.assertEqual(
            plan.micro_escalation_reasons,
            ["path requires non-micro checks: README.md"],
        )

    def test_micro_profile_escalates_for_non_micro_dependency(self) -> None:
        checks = [
            {
                **check("micro", "owner"),
                "profiles": ["micro", "full"],
                "platforms": ["all"],
                "trigger_paths": ["docs/human/**"],
                "micro_trigger_paths": ["docs/human/**"],
            },
            {
                **check("owner"),
                "profiles": ["fast", "full"],
                "platforms": ["all"],
            },
        ]

        from unittest.mock import patch

        with patch("check_all.git_changed_paths", return_value=["docs/human/faq.md"]):
            plan = select_check_plan(checks, "micro", "HEAD~1", platform="linux")

        self.assertTrue(plan.escalated_from_micro)
        self.assertEqual(plan.effective_profile, "fast")
        self.assertEqual(
            plan.micro_escalation_reasons,
            ["micro check dependency is not micro-eligible: owner"],
        )

    def test_contract_inputs_always_trigger_focused_validation(self) -> None:
        item = {
            **check("contract-owner"),
            "profiles": ["full"],
            "platforms": ["all"],
            "contract_inputs": ["area/**"],
            "trigger_paths": ["area/**", "tools/contract-owner.py"],
        }
        fallback = {
            **check("fallback"),
            "profiles": ["full"],
            "platforms": ["all"],
            "owned_paths": ["**"],
            "trigger_paths": ["**"],
        }

        from unittest.mock import patch

        with patch("check_all.git_changed_paths", return_value=["area/docs/note.md"]):
            selected, _fell_back = select_checks(
                [item, fallback], "fast", "HEAD~1", platform="linux"
            )

        self.assertEqual(
            [entry["id"] for entry in selected], ["contract-owner", "fallback"]
        )

    def test_fast_profile_records_unmatched_fallback_paths(self) -> None:
        item = {**check("matched"), "profiles": ["full"], "platforms": ["all"]}

        from unittest.mock import patch

        with patch(
            "check_all.git_changed_paths",
            return_value=["area/matched/file.md", "unrouted/file.md"],
        ):
            plan = select_check_plan([item], "fast", "HEAD~1", platform="linux")

        self.assertTrue(plan.fell_back_to_full)
        self.assertEqual(plan.changed_paths, ["area/matched/file.md", "unrouted/file.md"])
        self.assertEqual(plan.unmatched_changed_paths, ["unrouted/file.md"])
        self.assertEqual([entry["id"] for entry in plan.selected], ["matched"])

    def test_implementation_change_triggers_its_check(self) -> None:
        item = {**check("implementation"), "profiles": ["full"], "platforms": ["all"]}

        from unittest.mock import patch

        with patch(
            "check_all.git_changed_paths", return_value=["tools/implementation.py"]
        ):
            selected, fell_back = select_checks(
                [item], "fast", "HEAD~1", platform="linux"
            )

        self.assertFalse(fell_back)
        self.assertEqual([entry["id"] for entry in selected], ["implementation"])

    def test_change_and_full_profiles_use_changed_from_as_default_baseline(self) -> None:
        self.assertEqual(
            effective_baseline("change", "HEAD~1", None),
            "HEAD~1",
        )
        self.assertEqual(
            effective_baseline("change", "HEAD~1", "main"),
            "main",
        )
        self.assertEqual(
            effective_baseline("full", "origin/main", None),
            "origin/main",
        )
        self.assertIsNone(effective_baseline("fast", "HEAD~1", None))

    def test_fast_and_full_profiles_resolve_default_changed_from(self) -> None:
        from unittest.mock import patch

        with patch("check_all.git_ref_exists", return_value=True):
            self.assertEqual(default_changed_from(), "origin/main")
            self.assertEqual(resolve_changed_from("fast", None), "origin/main")
            self.assertEqual(resolve_changed_from("full", None), "origin/main")
        with patch("check_all.git_ref_exists", return_value=False):
            self.assertEqual(default_changed_from(), "HEAD")
            self.assertEqual(resolve_changed_from("fast", None), "HEAD")
            self.assertEqual(resolve_changed_from("full", None), "HEAD")
        self.assertEqual(resolve_changed_from("fast", "main"), "main")
        self.assertIsNone(resolve_changed_from("fast", None, all_fast=True))
        self.assertIsNone(resolve_changed_from("quick", None))

    def test_run_identity_resolves_each_relevant_ref_once(self) -> None:
        from unittest.mock import patch

        selection = {
            "effective_profile": "full",
            "platform": "linux",
            "selected_check_ids": ["example"],
            "changed_paths": ["docs/example.md"],
            "unmatched_changed_paths": [],
            "fell_back_to_full": False,
            "escalated_from_micro": False,
            "micro_escalation_reasons": [],
            "checks": [],
        }
        with patch("check_all.resolve_ref_oid", return_value="resolved-oid") as resolve:
            identity = build_run_identity(
                requested_profile="full",
                selection=selection,
                changed_from="main",
                baseline="main",
                source={
                    "source_commit": "head-oid",
                    "source_snapshot_sha256": "snapshot",
                    "manifest_sha256": "manifest",
                },
                jobs=4,
            )

        resolve.assert_called_once_with("main")
        self.assertEqual(identity["changed_from"]["commit_oid"], "resolved-oid")
        self.assertEqual(identity["baseline"]["commit_oid"], "resolved-oid")
        self.assertEqual(identity["jobs"], 4)
        self.assertEqual(identity["source_snapshot_sha256"], "snapshot")

    def test_live_full_profile_includes_change_release_drift(self) -> None:
        selected = select_check_plan(
            load_manifest(), "full", "origin/main", platform="linux"
        ).selected

        self.assertIn("release-drift-change", {item["id"] for item in selected})

    def test_dependency_runs_only_after_successful_prerequisite(self) -> None:
        completed: list[str] = []

        def runner(item: dict[str, Any], _baseline: str | None):
            if item["id"] == "dependent":
                self.assertIn("prerequisite", completed)
            completed.append(item["id"])
            return 0, "", "", [item["id"]]

        results, blocked = execute_checks(
            [check("prerequisite"), check("dependent", "prerequisite")],
            None,
            2,
            runner=runner,
        )

        self.assertEqual(set(results), {"prerequisite", "dependent"})
        self.assertEqual(blocked, {})

    def test_failed_prerequisite_blocks_transitive_dependents(self) -> None:
        executed: list[str] = []

        def runner(item: dict[str, Any], _baseline: str | None):
            executed.append(item["id"])
            return (1 if item["id"] == "first" else 0), "", "", [item["id"]]

        results, blocked = execute_checks(
            [check("first"), check("second", "first"), check("third", "second")],
            None,
            3,
            runner=runner,
        )

        self.assertEqual(executed, ["first"])
        self.assertEqual(set(results), {"first"})
        self.assertEqual(blocked["second"], ["first"])
        self.assertEqual(blocked["third"], ["second"])

    def test_independent_checks_remain_runnable_after_other_failure(self) -> None:
        executed: list[str] = []

        def runner(item: dict[str, Any], _baseline: str | None):
            executed.append(item["id"])
            return (1 if item["id"] == "failed" else 0), "", "", [item["id"]]

        results, blocked = execute_checks(
            [check("failed"), check("independent"), check("blocked", "failed")],
            None,
            2,
            runner=runner,
        )

        self.assertEqual(set(executed), {"failed", "independent"})
        self.assertEqual(results["independent"][0], 0)
        self.assertEqual(blocked["blocked"], ["failed"])

    def test_heavy_checks_respect_resource_capacity(self) -> None:
        active = 0
        peak = 0
        lock = threading.Lock()

        def runner(_item: dict[str, Any], _baseline: str | None):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.03)
            with lock:
                active -= 1
            return 0, "", "", ["check"]

        heavy = {**check("heavy-one"), "resource_class": "heavy"}
        other = {**check("heavy-two"), "resource_class": "heavy"}
        results, blocked = execute_checks([heavy, other], None, 2, runner=runner)

        self.assertEqual(set(results), {"heavy-one", "heavy-two"})
        self.assertEqual(blocked, {})
        self.assertEqual(peak, 1)

    def test_timeout_blocks_dependents_and_is_reported(self) -> None:
        telemetry: dict[str, dict[str, Any]] = {}

        def runner(item: dict[str, Any], _baseline: str | None):
            if item["id"] == "timed-out":
                return RunnerResult((124, "", "timed out\n", ["timed-out"]), timed_out=True)
            return 0, "", "", [item["id"]]

        selected = [check("timed-out"), check("dependent", "timed-out")]
        results, blocked = execute_checks(
            selected, None, 2, runner=runner, telemetry=telemetry
        )
        report = render_report(
            profile="full",
            selected=selected,
            results=results,
            blocked=blocked,
            source_changes=[],
            telemetry=telemetry,
        )

        self.assertEqual(blocked, {"dependent": ["timed-out"]})
        self.assertTrue(report["checks"][0]["timed_out"])
        self.assertEqual(report["checks"][0]["status"], "failed")
        self.assertEqual(report["checks"][1]["status"], "blocked")
        self.assertFalse(report["checks"][1]["timed_out"])
        self.assertIsInstance(report["checks"][0]["duration_seconds"], float)
        self.assertIn("queued_seconds", report["checks"][0])

    def test_dynamic_scheduler_backfills_ready_dependents(self) -> None:
        events: list[tuple[str, str, float]] = []
        lock = threading.Lock()
        dependent_started = threading.Event()

        def record(check_id: str, event: str) -> None:
            with lock:
                events.append((check_id, event, time.monotonic()))

        def runner(item: dict[str, Any], _baseline: str | None):
            check_id = item["id"]
            record(check_id, "start")
            if check_id == "first":
                time.sleep(0.03)
            elif check_id == "independent":
                dependent_started.wait(timeout=1.0)
            else:
                dependent_started.set()
                time.sleep(0.01)
            record(check_id, "end")
            return 0, "", "", [check_id]

        selected = [
            check("first"),
            check("dependent", "first"),
            check("independent"),
        ]
        execute_checks(selected, None, 2, runner=runner)

        timestamps = {(check_id, event): value for check_id, event, value in events}
        self.assertTrue(dependent_started.is_set())
        self.assertLess(
            timestamps[("dependent", "start")],
            timestamps[("independent", "end")],
        )

    def test_scheduler_prioritizes_checks_that_unlock_more_work(self) -> None:
        started: list[str] = []

        def runner(item: dict[str, Any], _baseline: str | None):
            started.append(item["id"])
            return 0, "", "", [item["id"]]

        selected = [
            check("independent"),
            check("root"),
            check("child", "root"),
            check("grandchild", "child"),
        ]
        execute_checks(selected, None, 1, runner=runner)

        self.assertEqual(started, ["root", "child", "grandchild", "independent"])

    def test_scheduler_uses_historical_critical_path_without_changing_coverage(self) -> None:
        started: list[str] = []

        def runner(item: dict[str, Any], _baseline: str | None):
            started.append(item["id"])
            return 0, "", "", [item["id"]]

        selected = [check("short"), check("long")]
        results, blocked = execute_checks(
            selected,
            None,
            1,
            runner=runner,
            duration_estimates={"short": 1.0, "long": 20.0},
        )

        self.assertEqual(started, ["long", "short"])
        self.assertEqual(set(results), {"short", "long"})
        self.assertEqual(blocked, {})

    def test_scheduler_assigns_only_reserved_child_capacity(self) -> None:
        observed: dict[str, int] = {}

        def runner(item: dict[str, Any], _baseline: str | None):
            observed[item["id"]] = item["_child_capacity"]
            return 0, "", "", [item["id"]]

        execute_checks(
            [
                {**check("heavy"), "resource_class": "heavy"},
                check("standard"),
            ],
            None,
            3,
            runner=runner,
        )

        self.assertEqual(observed, {"heavy": 2, "standard": 1})

    def test_runner_exception_is_recorded_as_a_failed_check(self) -> None:
        telemetry: dict[str, dict[str, Any]] = {}

        def runner(_item: dict[str, Any], _baseline: str | None):
            raise RuntimeError("runner unavailable")

        results, blocked = execute_checks(
            [check("unavailable")], None, 1, runner=runner, telemetry=telemetry
        )

        self.assertEqual(blocked, {})
        self.assertEqual(results["unavailable"][0], 1)
        self.assertIn("runner unavailable", results["unavailable"][2])
        self.assertGreaterEqual(telemetry["unavailable"]["duration_seconds"], 0.0)

    def test_reused_check_satisfies_dependencies_and_is_reported(self) -> None:
        telemetry: dict[str, dict[str, Any]] = {}
        initial = reusable_results(
            selected=[check("cached"), check("dependent", "cached")],
            decisions={
                "cached": {
                    "reusable": True,
                    "reason": "previous passed result is hash-bound to current inputs",
                }
            },
            commands_by_id={"cached": ["python", "cached.py"]},
        )

        results, blocked = execute_checks(
            [check("cached"), check("dependent", "cached")],
            None,
            1,
            telemetry=telemetry,
            initial_results=initial,
            runner=lambda item, _baseline: (0, "", "", [item["id"]]),
        )
        report = render_report(
            profile="micro",
            selected=[check("cached"), check("dependent", "cached")],
            results=results,
            blocked=blocked,
            source_changes=[],
            telemetry=telemetry,
        )

        self.assertEqual(blocked, {})
        self.assertEqual(report["checks"][0]["status"], "reused-pass")
        self.assertEqual(
            report["checks"][0]["result_provenance"]["kind"], "reused"
        )
        self.assertEqual(report["checks"][1]["status"], "passed")
        self.assertEqual(
            report["checks"][1]["result_provenance"]["kind"], "executed"
        )
        self.assertTrue(report["reuse_contract"]["successful"])
        self.assertFalse(report["acceptance_evidence"]["eligible"])
        self.assertEqual(
            report["acceptance_evidence"]["mode"], "local-result-reuse"
        )
        self.assertEqual(report["acceptance_evidence"]["reused_check_ids"], ["cached"])

    def test_process_timeout_is_a_typed_runner_failure(self) -> None:
        from unittest.mock import patch
        import subprocess

        item = check("timed-process")
        with patch(
            "check_all.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["python", "check"], 30, output="partial"),
        ):
            result = run_check(item, None)

        self.assertTrue(result.timed_out)
        self.assertEqual(result.result[0], 124)
        self.assertEqual(result.result[1], "partial")
        self.assertIn("timed out after 30 seconds", result.result[2])

    def test_source_snapshot_detects_changes_to_already_dirty_files(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            path = root / "tracked.txt"
            path.write_text("accepted\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
            path.write_text("dirty before checks\n", encoding="utf-8")
            before = source_snapshot(root)

            path.write_text("changed by checker\n", encoding="utf-8")
            changes = snapshot_changes(before, source_snapshot(root))

            self.assertEqual(changes, ["modified tracked.txt"])

    def test_source_snapshot_detects_non_ignored_created_files(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            before = source_snapshot(root)

            (root / "created.txt").write_text("unexpected\n", encoding="utf-8")

            self.assertEqual(
                snapshot_changes(before, source_snapshot(root)),
                ["created created.txt"],
            )

    def test_machine_report_preserves_exact_failure_evidence(self) -> None:
        selected = [{**check("failed"), "write_scope": "none"}]
        from unittest.mock import patch

        with patch(
            "check_all.source_identity",
            return_value={
                "source_commit": "abc123",
                "source_tree_dirty": True,
                "manifest_path": "tools/check_manifest.json",
                "manifest_sha256": "digest",
                "check_manifest_schema_version": 2,
            },
        ):
            report = render_report(
                profile="full",
                selected=selected,
                results={
                    "failed": (
                        7,
                        "partial output\n",
                        "failure detail\n",
                        ["python", "failed.py"],
                    )
                },
                blocked={},
                source_changes=["modified tracked.txt"],
            )

        self.assertEqual(report["checks"][0]["status"], "failed")
        self.assertEqual(report["checks"][0]["exit_code"], 7)
        self.assertEqual(report["checks"][0]["stderr"], "failure detail\n")
        self.assertEqual(report["schema_version"], 3)
        self.assertEqual(report["checks"][0]["resource_class"], "standard")
        self.assertFalse(report["source_write_scope"]["preserved"])
        self.assertTrue(report["reuse_contract"]["completed"])
        self.assertFalse(report["reuse_contract"]["successful"])
        self.assertFalse(report["acceptance_evidence"]["eligible"])
        self.assertEqual(report["acceptance_evidence"]["mode"], "cold-execution")
        self.assertFalse(report["selection"]["fell_back_to_full"])
        self.assertEqual(report["selection"]["selected_check_ids"], ["failed"])
        self.assertIn("timing", report)
        self.assertEqual(report["source"]["source_commit"], "abc123")
        self.assertEqual(report["source"]["manifest_path"], "tools/check_manifest.json")

    def test_report_catalog_keeps_distinct_entries_for_the_same_path(self) -> None:
        selected = [check("first"), check("second")]
        fingerprints = {
            "first": {
                "sha256": "first",
                "entries": [
                    {"path": "shared", "kind": "file", "mode": 33188, "digest": "a"}
                ],
            },
            "second": {
                "sha256": "second",
                "entries": [
                    {"path": "shared", "kind": "symlink", "mode": 40960, "digest": "b"}
                ],
            },
        }

        report = render_report(
            profile="full",
            selected=selected,
            results={item["id"]: (0, "", "", [item["id"]]) for item in selected},
            blocked={},
            source_changes=[],
            input_fingerprints=fingerprints,
        )

        self.assertEqual(len(report["input_catalog"]["entries"]), 2)
        self.assertNotEqual(
            report["checks"][0]["input_fingerprint"]["entry_ids"],
            report["checks"][1]["input_fingerprint"]["entry_ids"],
        )

    def test_selection_report_explains_changed_path_routing(self) -> None:
        item = {**check("matched"), "profiles": ["full"], "platforms": ["all"]}

        from unittest.mock import patch

        with patch("check_all.git_changed_paths", return_value=["area/matched/file.md"]):
            plan = select_check_plan([item], "fast", "HEAD~1", platform="linux")

        report = selection_report(profile="fast", changed_from="HEAD~1", plan=plan)

        self.assertEqual(report["changed_paths"], ["area/matched/file.md"])
        self.assertEqual(report["checks"][0]["selection_reasons"], ["changed-path-trigger"])
        self.assertEqual(report["checks"][0]["matched_changed_paths"], ["area/matched/file.md"])

    def test_live_manifest_declares_complete_trigger_inputs(self) -> None:
        for item in load_manifest():
            declared = set(item["contract_inputs"] + item["implementation_paths"])
            self.assertTrue(declared <= set(item["trigger_paths"]), item["id"])

    def test_report_order_follows_selected_manifest_order(self) -> None:
        first = check("first")
        second = check("second")
        report = render_report(
            profile="full",
            selected=[first, second],
            results={
                "second": (0, "", "", ["second"]),
                "first": (0, "", "", ["first"]),
            },
            blocked={},
            source_changes=[],
            telemetry={
                "second": {"duration_seconds": 0.2, "timed_out": False},
                "first": {"duration_seconds": 0.1, "timed_out": False},
            },
        )

        self.assertEqual([item["id"] for item in report["checks"]], ["first", "second"])
        self.assertEqual(
            [item["id"] for item in report["timing"]["slowest_checks"]],
            ["second", "first"],
        )

    def test_report_output_cannot_bypass_source_write_scope(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / ".gitignore").write_text("tmp/\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "outside the source tree"):
                resolve_report_path(root / "source-check-report.json", root=root)
            self.assertEqual(
                resolve_report_path(root / "tmp" / "source-check-report.json", root=root),
                (root / "tmp" / "source-check-report.json").resolve(),
            )

    def test_report_output_rejects_tracked_file_under_ignored_tmp(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / ".gitignore").write_text("tmp/\n", encoding="utf-8")
            report = root / "tmp" / "report.json"
            report.parent.mkdir()
            report.write_text("tracked\n", encoding="utf-8")
            subprocess.run(["git", "add", "-f", "tmp/report.json"], cwd=root, check=True)

            with self.assertRaisesRegex(ValueError, "tracked source file"):
                resolve_report_path(report, root=root)

    def test_report_output_rejects_unignored_tmp_path(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)

            with self.assertRaisesRegex(ValueError, "ignored by Git"):
                resolve_report_path(root / "tmp" / "report.json", root=root)


if __name__ == "__main__":
    unittest.main()
