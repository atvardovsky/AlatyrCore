from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_target_adapter import Finding, render_summary  # noqa: E402


def findings() -> list[Finding]:
    return [
        Finding("error", "SUPPORT_STATE_STALE", "support state differs", ".ai/support-state.json"),
        Finding("error", "ACTIVE_TASK_BINDING", "problem model path is unsafe", ".ai/assistant/active-tasks.json"),
        Finding("warning", "SUPPORT_STATE_STALE", "support state warning", ".ai/support-state.json"),
        Finding("warning", "APPROVAL_ARCHIVE_PRESSURE", "archive is large", ".ai/assistant/approvals/"),
        Finding("warning", "APPROVAL_ARCHIVE_PRESSURE", "archive is large again", ".ai/assistant/approvals/"),
        Finding("info", "ENGINEERING_EVIDENCE_CHECKED", "checked one record", "record.json"),
        Finding("info", "PACKAGE_CHECKED", "checked one package", "package.json"),
    ]


def render(*, summary: bool) -> str:
    stream = io.StringIO()
    with redirect_stdout(stream):
        code = render_summary(
            findings(),
            strict_warnings=False,
            validation_phase="acceptance",
            summary=summary,
        )
    return f"code={code}\n{stream.getvalue()}"


class TargetValidatorSummaryTests(unittest.TestCase):
    def test_summary_keeps_errors_blocking_warnings_and_grouped_counts(self) -> None:
        output = render(summary=True)
        self.assertIn("ERROR SUPPORT_STATE_STALE", output)
        self.assertIn("ERROR ACTIVE_TASK_BINDING", output)
        self.assertIn("WARNING SUPPORT_STATE_STALE", output)
        self.assertIn("WARNING APPROVAL_ARCHIVE_PRESSURE: 2 finding(s)", output)
        self.assertNotIn("INFO ENGINEERING_EVIDENCE_CHECKED", output)
        self.assertNotIn("INFO PACKAGE_CHECKED", output)
        self.assertIn("Summary: errors=2 warnings=3", output)
        self.assertLess(len(output.splitlines()), 20)

    def test_full_text_retains_every_finding_and_info(self) -> None:
        output = render(summary=False)
        self.assertIn("WARNING APPROVAL_ARCHIVE_PRESSURE .ai/assistant/approvals/: archive is large", output)
        self.assertIn("INFO ENGINEERING_EVIDENCE_CHECKED", output)
        self.assertIn("INFO PACKAGE_CHECKED", output)

    def test_summary_caps_error_list_without_changing_counts(self) -> None:
        many = [Finding("error", f"SYNTHETIC_{index}", "failure") for index in range(25)]
        stream = io.StringIO()
        with redirect_stdout(stream):
            render_summary(
                many,
                strict_warnings=False,
                validation_phase="acceptance",
                summary=True,
            )
        output = stream.getvalue()
        self.assertIn("... 5 more error(s)", output)
        self.assertIn("Summary: errors=25", output)


if __name__ == "__main__":
    unittest.main()
