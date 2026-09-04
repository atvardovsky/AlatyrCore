from __future__ import annotations

import json
import subprocess
import sys
import unittest
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_all import SelectionResult  # noqa: E402
import plan_minimum_work  # noqa: E402
from plan_minimum_work import build_plan, render_summary  # noqa: E402
from source_state import SourceEntry  # noqa: E402


NOW = datetime(2026, 9, 3, 12, 5, tzinfo=timezone.utc)
SESSION_ID = "test-session-opaque-id"


def check() -> dict[str, object]:
    return {
        "id": "docs",
        "command": ["tools/check_docs.py"],
        "profiles": ["micro", "full"],
        "platforms": ["all"],
        "depends_on": [],
        "contract_inputs": ["docs/human/**"],
        "implementation_paths": ["tools/check_docs.py"],
        "trigger_paths": ["docs/human/**", "tools/check_docs.py"],
        "micro_trigger_paths": ["docs/human/**"],
        "timeout_seconds": 30,
        "resource_class": "light",
    }


def capability_record(max_parallelism: int = 2) -> dict[str, object]:
    return {
        "schema_version": 2,
        "status": "available",
        "surface_id": "test-surface",
        "runtime_id": "test-runtime",
        "backend_kind": "native-worker",
        "role_ids": ["read-only-auditor"],
        "max_parallelism": max_parallelism,
        "write_isolation": "read-only",
        "result_delivery": True,
        "model_binding": "client-default",
        "verified_at": "2026-09-03T12:00:00Z",
        "expires_at": "2026-09-03T12:20:00Z",
        "freshness": "current-session",
        "session_id": SESSION_ID,
        "evidence": "fixture capability",
    }


def worker_packet(workstream_id: str, context: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "packet_kind": "source-read-only-workstream",
        "workstream_id": workstream_id,
        "role_id": "read-only-auditor",
        "objective": f"Inspect {workstream_id}",
        "bounded_context": [context],
        "conditional_context": [],
        "non_goals": ["modify repository state"],
        "allowed_actions": ["inspect"],
        "write_scope": "none",
        "independent": True,
        "independence_key": f"area-{workstream_id}",
        "expected_evidence": "Path-specific findings",
    }


class MinimumWorkPlanTests(unittest.TestCase):
    def build_test_plan(
        self,
        *,
        selection: SelectionResult,
        expected_validation_profile: str,
        requested_profile: str = "auto",
        source_profile: str | None = None,
        runtime_capability: str = "unknown",
        delegation_decision: str | None = None,
        delegation_skip_reason: str | None = None,
        delegation_reason: str | None = None,
        runtime_capability_record: dict[str, object] | None = None,
        task_worker_packets: list[dict[str, object]] | None = None,
        worker_workstream_ids: list[str] | None = None,
        worker_session_id: str | None = None,
        now: datetime = NOW,
    ) -> dict[str, object]:
        item = check()
        with ExitStack() as stack:
            stack.enter_context(patch("plan_minimum_work.load_manifest", return_value=[item]))
            stack.enter_context(
                patch(
                    "plan_minimum_work.resolve_changed_from",
                    return_value="HEAD",
                )
            )
            baseline = stack.enter_context(
                patch(
                    "plan_minimum_work.effective_baseline",
                    wraps=plan_minimum_work.effective_baseline,
                )
            )
            select_plan = stack.enter_context(
                patch("plan_minimum_work.select_check_plan", return_value=selection)
            )
            stack.enter_context(patch(
                "plan_minimum_work.source_snapshot",
                return_value={
                    "docs/human/faq.md": SourceEntry("file", 0o644, "aaa"),
                    "tools/check_docs.py": SourceEntry("file", 0o755, "bbb"),
                },
            ))
            stack.enter_context(patch("plan_minimum_work.source_identity", return_value={"manifest_sha256": "m"}))
            stack.enter_context(patch("plan_minimum_work.environment_report", return_value={"platform": "linux", "python": "p"}))
            plan = build_plan(
                requested_profile=requested_profile,
                source_profile=source_profile,
                changed_from=None,
                from_ref=None,
                reuse_report_path=None,
                runtime_capability=runtime_capability,
                delegation_decision=delegation_decision,
                delegation_skip_reason=delegation_skip_reason,
                delegation_reason=delegation_reason,
                runtime_capability_record=runtime_capability_record,
                task_worker_packets=task_worker_packets,
                worker_workstream_ids=worker_workstream_ids,
                worker_session_id=(
                    worker_session_id
                    if worker_session_id is not None
                    else SESSION_ID if runtime_capability_record is not None else None
                ),
                now=now,
            )
        self.assertEqual(select_plan.call_args.args[1], expected_validation_profile)
        self.assertEqual(baseline.call_args.args[0], selection.effective_profile)
        return plan

    def test_build_plan_reports_bounded_docs_context_and_reuse_boundary(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=["docs/human/faq.md"],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={
                "docs": {
                    "reasons": ["micro-changed-path-trigger"],
                    "matched_changed_paths": ["docs/human/faq.md"],
                }
            },
            effective_profile="fast",
        )
        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="fast",
            source_profile="docs-local",
        )

        self.assertEqual(plan["source_profile"], "docs-local")
        self.assertEqual(plan["task_class"], "small-task")
        self.assertEqual(plan["effective_profile"], "fast")
        self.assertEqual(plan["check_plan"]["selected_check_ids"], ["docs"])
        self.assertIn(
            "docs/framework-maintenance.md",
            plan["context_packet"]["required_context"],
        )
        self.assertEqual(
            plan["context_packet"]["selectors"]["changed_paths"],
            ["docs/human/faq.md"],
        )
        self.assertEqual(plan["context_packet"]["selectors"]["check_ids"], ["docs"])
        self.assertTrue(plan["context_packet"]["omitted_candidates"])
        self.assertIn("logical integrity review", plan["quality_boundary"])
        self.assertEqual(plan["reuse"]["reusable_check_count"], 0)
        self.assertIn("--profile fast", render_summary(plan))

    def test_explicit_repository_audit_overrides_clean_tree_auto_profile(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=[],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={"docs": {"reasons": ["full-profile"]}},
            effective_profile="full",
        )

        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="full",
            source_profile="repository-audit",
        )

        self.assertEqual(plan["source_profile"], "repository-audit")
        self.assertEqual(plan["effective_profile"], "full")
        self.assertEqual(plan["task_class"], "large-or-resumable")
        self.assertTrue(plan["decomposition"]["required"])
        self.assertGreaterEqual(
            len(plan["decomposition"]["candidate_workstreams"]),
            2,
        )
        policy = json.loads(
            (ROOT / "tools" / "source_worker_policy.json").read_text(
                encoding="utf-8"
            )
        )
        for workstream in plan["decomposition"]["candidate_workstreams"]:
            expected = policy["workstreams"][workstream["workstream_id"]]
            self.assertEqual(workstream["objective"], expected["objective"])
            self.assertEqual(
                workstream["bounded_context"], expected["required_context"]
            )
            self.assertEqual(workstream["allowed_actions"], ["inspect"])
            self.assertEqual(workstream["write_scope"], "none")

    def test_auto_plan_without_changed_paths_is_not_a_small_task(self) -> None:
        selection = SelectionResult(
            selected=[],
            fell_back_to_full=False,
            changed_paths=[],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={},
            effective_profile="micro",
        )

        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="micro",
        )

        self.assertNotEqual(plan["task_class"], "small-task")
        self.assertIn(plan["task_class"], {"scope-unknown", "standard-task"})

    def test_repository_audit_records_runtime_delegation_fallback(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=[],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={"docs": {"reasons": ["full-profile"]}},
            effective_profile="full",
        )

        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="full",
            source_profile="repository-audit",
        )
        assessment = plan["delegation_assessment"]

        self.assertTrue(assessment["evaluation_required"])
        self.assertTrue(assessment["candidate"])
        self.assertEqual(assessment["evaluation_status"], "required")
        self.assertEqual(
            assessment["candidate_workstream_ids"],
            plan["decomposition"]["independent_worker_candidates"],
        )
        self.assertEqual(assessment["selected_workstream_ids"], [])
        self.assertEqual(assessment["runtime_capability_status"], "unknown")
        self.assertEqual(assessment["runtime_capability"], "unknown")
        self.assertEqual(assessment["decision"], "runtime-verification-required")
        self.assertIsNone(assessment["skip_reason_id"])
        self.assertEqual(assessment["fallback"], "primary-assistant")
        self.assertTrue(assessment["reasons"])

    def test_available_workers_are_recommended_for_repository_audit(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=[],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={"docs": {"reasons": ["full-profile"]}},
            effective_profile="full",
        )

        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="full",
            source_profile="repository-audit",
            runtime_capability="available",
            runtime_capability_record=capability_record(),
        )
        assessment = plan["delegation_assessment"]

        self.assertEqual(assessment["decision"], "delegation-recommended")
        self.assertEqual(len(assessment["selected_workstream_ids"]), 2)
        self.assertIsNone(assessment["skip_reason_id"])

    def test_unavailable_workers_fall_back_with_reason(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=[],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={"docs": {"reasons": ["full-profile"]}},
            effective_profile="full",
        )

        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="full",
            source_profile="repository-audit",
            runtime_capability="unavailable",
        )
        assessment = plan["delegation_assessment"]

        self.assertEqual(assessment["decision"], "kept-local")
        self.assertEqual(assessment["skip_reason_id"], "capability-unavailable")
        self.assertTrue(assessment["reason"])

    def test_available_workers_kept_local_require_concrete_evidence(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=[],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={"docs": {"reasons": ["full-profile"]}},
            effective_profile="full",
        )

        with self.assertRaisesRegex(ValueError, "concrete reason"):
            self.build_test_plan(
                selection=selection,
                expected_validation_profile="full",
                source_profile="repository-audit",
                runtime_capability="available",
                runtime_capability_record=capability_record(),
                delegation_decision="kept-local",
                delegation_skip_reason="coordination-cost-exceeds-benefit",
            )

        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="full",
            source_profile="repository-audit",
            runtime_capability="available",
            runtime_capability_record=capability_record(),
            delegation_decision="kept-local",
            delegation_skip_reason="coordination-cost-exceeds-benefit",
            delegation_reason="two packets would repeat the same canonical-owner review",
        )
        self.assertEqual(plan["delegation_assessment"]["decision"], "kept-local")

    def test_bare_available_capability_cannot_recommend_delegation(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=[],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={"docs": {"reasons": ["full-profile"]}},
            effective_profile="full",
        )

        with self.assertRaisesRegex(ValueError, "requires a capability record"):
            self.build_test_plan(
                selection=selection,
                expected_validation_profile="full",
                source_profile="repository-audit",
                runtime_capability="available",
            )

    def test_planner_enforces_capability_time_and_session_binding(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=[],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={"docs": {"reasons": ["full-profile"]}},
            effective_profile="full",
        )
        cases = [
            ({"verified_at": "2026-09-03T11:00:00Z"}, SESSION_ID, "stale"),
            ({"session_id": "other-session"}, SESSION_ID, "session_id"),
            ({}, "", "session_id"),
        ]
        for updates, session_id, error in cases:
            with self.subTest(error=error):
                record = capability_record()
                record.update(updates)
                with self.assertRaisesRegex(ValueError, error):
                    self.build_test_plan(
                        selection=selection,
                        expected_validation_profile="full",
                        source_profile="repository-audit",
                        runtime_capability="available",
                        runtime_capability_record=record,
                        worker_session_id=session_id,
                    )

    def test_preflight_cannot_claim_workers_were_delegated(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=[],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={"docs": {"reasons": ["full-profile"]}},
            effective_profile="full",
        )

        with self.assertRaisesRegex(ValueError, "invalid delegation decision"):
            self.build_test_plan(
                selection=selection,
                expected_validation_profile="full",
                source_profile="repository-audit",
                runtime_capability="available",
                runtime_capability_record=capability_record(),
                delegation_decision="delegated",
            )

    def test_release_source_profile_preserves_supplemental_release_gate(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=[],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={"docs": {"reasons": ["full-profile"]}},
            effective_profile="full",
        )

        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="full",
            source_profile="release-versioning",
        )

        self.assertEqual(plan["validation_profiles"], ["full", "release"])
        self.assertEqual(len(plan["check_plan"]["additional_commands"]), 1)
        self.assertIn(
            "--from-ref",
            plan["check_plan"]["additional_commands"][0],
        )
        self.assertIn(
            "--profile release",
            render_summary(plan),
        )

    def test_windows_summary_uses_platform_command_rendering(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=["docs/human/faq.md"],
            unmatched_changed_paths=[],
            platform="windows",
            selection_details={"docs": {"reasons": ["changed-path-trigger"]}},
            effective_profile="fast",
        )

        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="fast",
            source_profile="docs-local",
        )
        rendered_command = subprocess.list2cmdline(plan["check_plan"]["command"])

        self.assertIn(rendered_command, render_summary(plan))

    def test_small_task_requires_one_covered_profile_path(self) -> None:
        cases = [
            (
                ["docs/human/faq.md", "docs/human/quick-demo.md"],
                [],
                False,
                {
                    "docs": {
                        "reasons": ["changed-path-trigger"],
                        "matched_changed_paths": [
                            "docs/human/faq.md",
                            "docs/human/quick-demo.md",
                        ],
                    }
                },
            ),
            (
                ["unrouted.file"],
                ["unrouted.file"],
                True,
                {"docs": {"reasons": ["full-fallback-unmatched"], "matched_changed_paths": []}},
            ),
            (
                ["tools/check_docs.py"],
                [],
                False,
                {
                    "docs": {
                        "reasons": ["changed-path-trigger"],
                        "matched_changed_paths": ["tools/check_docs.py"],
                    }
                },
            ),
            (
                ["docs/human/faq.md"],
                [],
                False,
                {"docs": {"reasons": ["always-for-changed"], "matched_changed_paths": []}},
            ),
        ]
        for changed, unmatched, fallback, details in cases:
            with self.subTest(changed=changed, unmatched=unmatched, fallback=fallback):
                selection = SelectionResult(
                    selected=[check()],
                    fell_back_to_full=fallback,
                    changed_paths=changed,
                    unmatched_changed_paths=unmatched,
                    platform="linux",
                    selection_details=details,
                    effective_profile="fast",
                )
                plan = self.build_test_plan(
                    selection=selection,
                    expected_validation_profile="fast",
                    source_profile="docs-local",
                )
                self.assertEqual(plan["task_class"], "standard-task")
                self.assertFalse(plan["task_classification"]["small_task_eligible"])

    def test_boundary_path_is_large_even_on_fast_route(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=["framework/action-authorization.md"],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={
                "docs": {
                    "reasons": ["changed-path-trigger"],
                    "matched_changed_paths": ["framework/action-authorization.md"],
                }
            },
            effective_profile="fast",
        )
        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="fast",
            source_profile="docs-local",
        )
        self.assertEqual(plan["task_class"], "large-or-resumable")
        self.assertEqual(
            plan["delegation_assessment"]["decision"],
            "workstream-identification-required",
        )

    def test_one_covered_source_tool_path_remains_small(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=["tools/check_docs.py"],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={
                "docs": {
                    "reasons": ["changed-path-trigger"],
                    "matched_changed_paths": ["tools/check_docs.py"],
                }
            },
            effective_profile="fast",
        )
        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="fast",
            source_profile="source-tooling",
        )
        self.assertEqual(plan["task_class"], "small-task")

    def test_micro_escalation_cannot_remain_a_small_task(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=["docs/human/faq.md"],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={
                "docs": {
                    "reasons": ["changed-path-trigger"],
                    "matched_changed_paths": ["docs/human/faq.md"],
                }
            },
            effective_profile="fast",
            escalated_from_micro=True,
            micro_escalation_reasons=["path requires non-micro checks"],
        )
        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="fast",
            source_profile="docs-local",
        )
        self.assertEqual(plan["task_class"], "standard-task")
        self.assertTrue(
            any(
                "micro escalation" in reason
                for reason in plan["task_classification"]["reasons"]
            )
        )

    def test_large_non_audit_task_requires_explicit_workstream_identification(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=[],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={"docs": {"reasons": ["full-profile"]}},
            effective_profile="full",
        )
        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="full",
            source_profile="ai-infrastructure-bridge",
        )
        self.assertEqual(
            plan["delegation_assessment"]["decision"],
            "workstream-identification-required",
        )
        self.assertEqual(plan["decomposition"]["candidate_workstreams"], [])
        self.assertTrue(plan["delegation_assessment"]["evaluation_required"])
        self.assertEqual(
            plan["delegation_assessment"]["skip_reason_id"],
            "insufficient-independent-work",
        )

    def test_one_large_task_packet_still_requires_workstream_identification(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=[],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={"docs": {"reasons": ["full-profile"]}},
            effective_profile="full",
        )
        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="full",
            source_profile="ai-infrastructure-bridge",
            task_worker_packets=[
                worker_packet("router", "tools/source_context_router.json")
            ],
        )
        self.assertEqual(
            plan["delegation_assessment"]["decision"],
            "workstream-identification-required",
        )
        self.assertTrue(plan["decomposition"]["workstream_identification_required"])

    def test_large_non_audit_task_can_recommend_two_explicit_packets(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=[],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={"docs": {"reasons": ["full-profile"]}},
            effective_profile="full",
        )
        packets = [
            worker_packet("router", "tools/source_context_router.json"),
            worker_packet("policy", "tools/source_worker_policy.json"),
        ]
        plan = self.build_test_plan(
            selection=selection,
            expected_validation_profile="full",
            source_profile="ai-infrastructure-bridge",
            task_worker_packets=packets,
            runtime_capability="available",
            runtime_capability_record=capability_record(),
        )
        assessment = plan["delegation_assessment"]
        self.assertEqual(assessment["decision"], "delegation-recommended")
        self.assertEqual(assessment["selected_workstream_ids"], ["router", "policy"])

    def test_large_task_rejects_non_independent_packets(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=[],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={"docs": {"reasons": ["full-profile"]}},
            effective_profile="full",
        )
        packets = [
            worker_packet("router", "tools/source_context_router.json"),
            worker_packet("policy", "tools/source_worker_policy.json"),
        ]
        packets[1]["independence_key"] = packets[0]["independence_key"]
        with self.assertRaisesRegex(ValueError, "independence keys must be unique"):
            self.build_test_plan(
                selection=selection,
                expected_validation_profile="full",
                source_profile="ai-infrastructure-bridge",
                task_worker_packets=packets,
            )

    def test_small_task_planning_does_not_load_optional_worker_policy(self) -> None:
        selection = SelectionResult(
            selected=[check()],
            fell_back_to_full=False,
            changed_paths=["docs/human/faq.md"],
            unmatched_changed_paths=[],
            platform="linux",
            selection_details={"docs": {"reasons": ["changed-path-trigger"]}},
            effective_profile="fast",
        )

        with patch(
            "plan_minimum_work._load_source_worker_policy",
            side_effect=AssertionError("worker policy should remain lazy"),
        ):
            plan = self.build_test_plan(
                selection=selection,
                expected_validation_profile="fast",
                source_profile="docs-local",
            )

        self.assertEqual(plan["delegation_assessment"]["decision"], "primary-assistant")


if __name__ == "__main__":
    unittest.main()
