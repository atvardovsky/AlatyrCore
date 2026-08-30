from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_target_adapter import (  # noqa: E402
    AdapterValidatorConfig,
    Finding,
    Validator,
    findings_payload,
)
from target_adapter_validation.installation_state import validate_installation_state  # noqa: E402


def validator(target: Path, *, validation_phase: str = "acceptance") -> Validator:
    return Validator(
        target,
        framework_source=None,
        diff_ref=None,
        approval_records=[],
        enforce_approval_scope=False,
        change_packages=[],
        enforce_change_package=False,
        migration_diff=None,
        allow_placeholders=validation_phase == "migration-staging",
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
        validation_phase=validation_phase,
    )


def write_state(target: Path, state: str) -> None:
    manifest = target / ".ai/alatyr.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        f"installation:\n"
        f"  state: {state}\n"
        f"  state_record: .ai/assistant/installation-state.json\n",
        encoding="utf-8",
    )


def write_accepted_record(target: Path, *, validation_status: str = "passed") -> None:
    path = target / ".ai/assistant/installation-state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "record_kind": "alatyr-installation-state",
                "current_state": "accepted",
                "transitions": [
                    {
                        "sequence": 1,
                        "previous_state": None,
                        "next_state": "scaffolded",
                        "reason": "initial-scaffold",
                        "operation_id": "scaffold",
                        "repository_revision": "revision-1",
                        "current_user_authorization": "modify scaffold",
                        "approval_evidence": None,
                        "validation": {
                            "status": "not-run",
                            "evidence": "initial scaffold",
                        },
                        "recorded_at": "2026-08-25T00:00:00Z",
                    },
                    {
                        "sequence": 2,
                        "previous_state": "scaffolded",
                        "next_state": "staged",
                        "reason": "adaptation-started",
                        "operation_id": "install",
                        "repository_revision": "revision-1",
                        "current_user_authorization": "modify adapter",
                        "approval_evidence": "approval-install",
                        "validation": {
                            "status": "not-run",
                            "evidence": "adaptation started",
                        },
                        "recorded_at": "2026-08-25T00:01:00Z",
                    },
                    {
                        "sequence": 3,
                        "previous_state": "staged",
                        "next_state": "accepted",
                        "reason": "strict-acceptance",
                        "operation_id": "install",
                        "repository_revision": "revision-2",
                        "current_user_authorization": "modify adapter",
                        "approval_evidence": "approval-install",
                        "validation": {
                            "status": validation_status,
                            "evidence": "strict validation report",
                        },
                        "recorded_at": "2026-08-25T00:02:00Z",
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )


class TargetValidatorInstallationStateTests(unittest.TestCase):
    def test_nonaccepted_states_are_unverified_and_ineligible(self) -> None:
        for state in ["scaffolded", "staged", "degraded"]:
            with self.subTest(state=state), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)
                write_state(target, state)

                payload = findings_payload(
                    [],
                    target=target,
                    strict_warnings=False,
                    installation_state=state,
                )

                self.assertEqual(payload["installation_state"], state)
                self.assertEqual(payload["evidence"]["installation_state"], state)
                self.assertEqual(payload["adapter_health"]["state"], "unverified")
                self.assertFalse(
                    payload["placeholder_validation"]["acceptance_eligible"]
                )

    def test_accepted_state_can_be_ready_and_acceptance_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            write_state(target, "accepted")
            write_accepted_record(target)

            payload = findings_payload([], target=target, strict_warnings=False)

            self.assertEqual(payload["adapter_health"]["state"], "ready")
            self.assertTrue(
                payload["placeholder_validation"]["acceptance_eligible"]
            )

    def test_accepted_state_remains_unverified_in_migration_staging(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            write_state(target, "accepted")
            write_accepted_record(target)

            payload = findings_payload(
                [],
                target=target,
                strict_warnings=False,
                validation_phase="migration-staging",
            )

            self.assertEqual(payload["adapter_health"]["state"], "unverified")
            self.assertFalse(
                payload["placeholder_validation"]["acceptance_eligible"]
            )

    def test_direct_evidence_does_not_trust_accepted_scalar_without_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            write_state(target, "accepted")

            payload = findings_payload([], target=target, strict_warnings=False)

            self.assertEqual(payload["installation_state"], "unverified")
            self.assertEqual(payload["adapter_health"]["state"], "unverified")

    def test_run_payload_uses_validated_installation_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            write_state(target, "accepted")
            checked = validator(target)

            findings = checked.run()
            payload = findings_payload(
                findings,
                target=target,
                strict_warnings=False,
                installation_state=checked.installation_state,
            )

            self.assertEqual(payload["installation_state"], "unverified")
            self.assertEqual(payload["evidence"]["installation_state"], "unverified")
            self.assertEqual(payload["adapter_health"]["state"], "blocked")
            self.assertTrue(
                any(
                    finding.code == "INSTALLATION_STATE_RECORD_MISSING"
                    for finding in findings
                )
            )

    def test_blocking_findings_take_precedence_over_installation_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            write_state(target, "staged")

            payload = findings_payload(
                [Finding("error", "MANIFEST_SCHEMA", "invalid manifest")],
                target=target,
                strict_warnings=False,
            )

            self.assertEqual(payload["adapter_health"]["state"], "blocked")
            self.assertFalse(
                payload["placeholder_validation"]["acceptance_eligible"]
            )

    def test_manifest_parser_requires_and_captures_installation_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            write_state(target, "accepted")
            accepted = validator(target)

            accepted.check_manifest()

            self.assertEqual(accepted.installation_state, "accepted")

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            manifest = target / ".ai/alatyr.yaml"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text("installation:\n  mode: new\n", encoding="utf-8")
            missing = validator(target)

            missing.check_manifest()

            self.assertEqual(missing.installation_state, "unverified")
            self.assertTrue(
                any(
                    finding.code == "MANIFEST_FIELD_MISSING"
                    and "installation.state" in finding.message
                    for finding in missing.findings
                )
            )

    def test_transition_record_is_required_for_accepted_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            write_state(target, "accepted")
            accepted = validator(target)
            manifest = accepted.check_manifest()

            validate_installation_state(
                accepted.capability_validation_context(), manifest
            )

            self.assertTrue(
                any(
                    finding.code == "INSTALLATION_STATE_RECORD_MISSING"
                    for finding in accepted.findings
                )
            )

    def test_transition_record_rejects_unvalidated_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            write_state(target, "accepted")
            write_accepted_record(target, validation_status="not-run")
            accepted = validator(target)
            manifest = accepted.check_manifest()

            validate_installation_state(
                accepted.capability_validation_context(), manifest
            )

            self.assertTrue(
                any(
                    finding.code == "INSTALLATION_STATE_TRANSITION"
                    and "requires passed strict validation" in finding.message
                    for finding in accepted.findings
                )
            )


if __name__ == "__main__":
    unittest.main()
