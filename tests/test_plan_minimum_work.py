from __future__ import annotations

import json
import subprocess
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_all import SelectionResult  # noqa: E402
import plan_minimum_work  # noqa: E402
from plan_minimum_work import build_plan, render_summary  # noqa: E402
from source_state import SourceEntry  # noqa: E402


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
        "schema_version": 1,
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
        "freshness": "current-session",
        "evidence": "fixture capability",
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
