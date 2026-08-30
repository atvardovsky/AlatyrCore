from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from report_adapter_health import render_text  # noqa: E402
from validate_target_adapter import Finding, findings_payload  # noqa: E402


class AdapterHealthReportTests(unittest.TestCase):
    def test_staging_health_is_unverified_and_not_acceptance_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [],
                target=Path(directory),
                strict_warnings=False,
                validation_phase="migration-staging",
                installation_state="staged",
            )

        text = render_text(payload)

        self.assertIn("Alatyr adapter health: unverified", text)
        self.assertIn("Installation state: staged", text)
        self.assertIn("Acceptance eligible: no", text)
        self.assertIn("Observed revision: unavailable", text)
        self.assertNotIn("None", text)
        self.assertIn("Repair operations: none", text)

    def test_blocking_findings_are_visible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [Finding("error", "MANIFEST_SCHEMA", "invalid manifest", ".ai/alatyr.yaml")],
                target=Path(directory),
                strict_warnings=False,
                installation_state="accepted",
            )

        text = render_text(payload)

        self.assertIn("Alatyr adapter health: blocked", text)
        self.assertIn("Blocking findings:", text)
        self.assertIn("MANIFEST_SCHEMA: invalid manifest [.ai/alatyr.yaml]", text)


if __name__ == "__main__":
    unittest.main()
