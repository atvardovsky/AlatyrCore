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
    def test_changed_scope_never_produces_acceptance_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [],
                target=Path(directory),
                strict_warnings=False,
                installation_state="accepted",
                validation_scope="changed",
            )

        self.assertFalse(payload["placeholder_validation"]["acceptance_eligible"])
        self.assertEqual(payload["adapter_health"]["state"], "unverified")
        self.assertEqual(
            payload["health_layers"]["current_change"]["state"], "not-evaluated"
        )

    def test_partial_archive_mode_never_produces_acceptance_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [],
                target=Path(directory),
                strict_warnings=False,
                installation_state="accepted",
                approval_archive_summary={"mode": "changed"},
            )

        self.assertFalse(payload["placeholder_validation"]["acceptance_eligible"])

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
        self.assertIn(
            "Health layers: installation=staged support=unverified "
            "current_change=not-evaluated",
            text,
        )
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
        self.assertEqual(payload["health_layers"]["installation"]["state"], "degraded")

    def test_stale_support_does_not_change_accepted_installation_layer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [
                    Finding(
                        "error",
                        "SUPPORT_STATE_STALE",
                        "support state differs",
                        ".ai/support-state.json",
                    )
                ],
                target=Path(directory),
                strict_warnings=False,
                installation_state="accepted",
            )

        self.assertEqual(payload["health_layers"]["installation"]["state"], "accepted")
        self.assertEqual(payload["health_layers"]["support"]["state"], "blocked")
        self.assertEqual(
            payload["health_layers"]["current_change"]["state"], "not-evaluated"
        )

    def test_missing_required_contract_blocks_support_layer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [
                    Finding(
                        "error",
                        "REQUIRED_FILE_MISSING",
                        "required adapter file is missing",
                        ".ai/assistant/validation-contract.json",
                    )
                ],
                target=Path(directory),
                strict_warnings=False,
                installation_state="accepted",
            )

        self.assertEqual(payload["health_layers"]["installation"]["state"], "accepted")
        self.assertEqual(payload["health_layers"]["support"]["state"], "blocked")

    def test_selected_change_evidence_is_reported_separately(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [],
                target=Path(directory),
                strict_warnings=False,
                installation_state="accepted",
                diff_ref="HEAD~1",
                approval_records_selected=1,
                change_packages_selected=1,
                approval_scope_enforced=True,
                change_package_enforced=True,
            )

        current = payload["health_layers"]["current_change"]
        self.assertEqual(current["state"], "structurally-checked")
        self.assertFalse(current["semantic_correctness_proven"])

    def test_status_mode_omits_detailed_repair_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [Finding("error", "MANIFEST_SCHEMA", "invalid manifest", ".ai/alatyr.yaml")],
                target=Path(directory),
                strict_warnings=False,
                installation_state="accepted",
            )

        text = render_text(payload, mode="status")

        self.assertIn("Alatyr adapter health: blocked", text)
        self.assertIn("Repair operations: run doctor for prioritized repair routes", text)
        self.assertIn("Finding details: run doctor for prioritized findings", text)
        self.assertNotIn("Blocking findings:", text)


if __name__ == "__main__":
    unittest.main()
