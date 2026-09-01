from __future__ import annotations

import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_all import SelectionResult  # noqa: E402
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


class MinimumWorkPlanTests(unittest.TestCase):
    def test_build_plan_reports_micro_context_checks_and_reuse_boundary(self) -> None:
        item = check()
        selection = SelectionResult(
            selected=[item],
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
            effective_profile="micro",
        )

        with ExitStack() as stack:
            stack.enter_context(patch("plan_minimum_work.load_manifest", return_value=[item]))
            stack.enter_context(patch("plan_minimum_work.resolve_changed_from", return_value="HEAD"))
            stack.enter_context(patch("plan_minimum_work.select_check_plan", return_value=selection))
            stack.enter_context(patch(
                "plan_minimum_work.source_snapshot",
                return_value={
                    "docs/human/faq.md": SourceEntry("file", 0o644, "aaa"),
                    "tools/check_docs.py": SourceEntry("file", 0o755, "bbb"),
                },
            ))
            stack.enter_context(patch("plan_minimum_work.source_identity", return_value={"manifest_sha256": "m"}))
            stack.enter_context(patch("plan_minimum_work.environment_report", return_value={"platform": "linux", "python": "p"}))
            stack.enter_context(patch(
                "plan_minimum_work._load_source_tooling_context",
                return_value={"required_context": ["tools/README.md"]},
            ))
            plan = build_plan(
                requested_profile="auto",
                changed_from=None,
                from_ref=None,
                reuse_report_path=None,
            )

        self.assertEqual(plan["task_class"], "small-task")
        self.assertEqual(plan["effective_profile"], "micro")
        self.assertEqual(plan["check_plan"]["selected_check_ids"], ["docs"])
        self.assertEqual(plan["context_packet"]["required_context"], ["tools/README.md"])
        self.assertIn("logical integrity review", plan["quality_boundary"])
        self.assertEqual(plan["reuse"]["reusable_check_count"], 0)
        self.assertIn("--profile micro", render_summary(plan))


if __name__ == "__main__":
    unittest.main()
