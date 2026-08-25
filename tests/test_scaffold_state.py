from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from scaffold_state import (  # noqa: E402
    installation_transition_allowed,
    validate_installation_state_record,
)


class ScaffoldStateTests(unittest.TestCase):
    def record(self) -> dict[str, object]:
        return {
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
                    "validation": {"status": "not-run", "evidence": "initial"},
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
                    "validation": {"status": "not-run", "evidence": "in progress"},
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
                    "validation": {"status": "passed", "evidence": "strict report"},
                    "recorded_at": "2026-08-25T00:02:00Z",
                },
            ],
        }

    def test_acceptance_requires_strict_evidence(self) -> None:
        self.assertFalse(installation_transition_allowed("staged", "accepted"))
        self.assertTrue(
            installation_transition_allowed(
                "staged", "accepted", strict_acceptance=True
            )
        )

    def test_accepted_adapter_only_reopens_for_controlled_update(self) -> None:
        self.assertFalse(installation_transition_allowed("accepted", "staged"))
        self.assertTrue(
            installation_transition_allowed(
                "accepted", "staged", controlled_update=True
            )
        )

    def test_degradation_requires_blocking_drift(self) -> None:
        self.assertFalse(installation_transition_allowed("accepted", "degraded"))
        self.assertTrue(
            installation_transition_allowed(
                "accepted", "degraded", blocking_drift=True
            )
        )

    def test_repair_cannot_skip_staging(self) -> None:
        self.assertTrue(installation_transition_allowed("degraded", "staged"))
        self.assertFalse(
            installation_transition_allowed(
                "degraded", "accepted", strict_acceptance=True
            )
        )

    def test_scaffold_cannot_claim_acceptance(self) -> None:
        self.assertTrue(installation_transition_allowed("scaffolded", "staged"))
        self.assertFalse(
            installation_transition_allowed(
                "scaffolded", "accepted", strict_acceptance=True
            )
        )

    def test_unknown_state_is_rejected(self) -> None:
        self.assertFalse(installation_transition_allowed("unknown", "staged"))

    def test_transition_record_accepts_ordered_strict_evidence(self) -> None:
        self.assertEqual(
            validate_installation_state_record(
                self.record(), manifest_state="accepted"
            ),
            [],
        )

    def test_transition_record_rejects_acceptance_without_validation(self) -> None:
        record = self.record()
        record["transitions"][-1]["validation"]["status"] = "not-run"  # type: ignore[index]

        failures = validate_installation_state_record(record, manifest_state="accepted")

        self.assertTrue(any("requires passed strict validation" in item for item in failures))

    def test_transition_record_rejects_state_and_history_drift(self) -> None:
        record = self.record()
        record["transitions"][-1]["previous_state"] = "degraded"  # type: ignore[index]

        failures = validate_installation_state_record(record, manifest_state="staged")

        self.assertTrue(any("differs from manifest" in item for item in failures))
        self.assertTrue(any("breaks transition continuity" in item for item in failures))

    def test_legacy_adapter_can_start_truthfully_at_migration_staging(self) -> None:
        record = {
            "schema_version": 1,
            "record_kind": "alatyr-installation-state",
            "current_state": "staged",
            "transitions": [
                {
                    "sequence": 1,
                    "previous_state": None,
                    "next_state": "staged",
                    "reason": "legacy-migration-baseline",
                    "operation_id": "framework-update",
                    "repository_revision": "revision-1",
                    "current_user_authorization": "modify adapter",
                    "approval_evidence": "approval-update",
                    "validation": {
                        "status": "not-run",
                        "evidence": "prior transition history is unavailable",
                    },
                    "recorded_at": "2026-08-25T00:00:00Z",
                }
            ],
        }

        self.assertEqual(
            validate_installation_state_record(record, manifest_state="staged"),
            [],
        )


if __name__ == "__main__":
    unittest.main()
