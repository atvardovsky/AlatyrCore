from __future__ import annotations

import unittest

from tools.verify_target_upgrade import acceptance_failures


def accepted_payload() -> dict[str, object]:
    return {
        "tool": "validate_target_adapter",
        "status": "passed",
        "validation_phase": "acceptance",
        "validation_scope": "full",
        "installation_state": "accepted",
        "placeholder_validation": {
            "acceptance_eligible": True,
            "unresolved_active": 0,
        },
        "approval_archive": {"mode": "full"},
        "health_layers": {
            "current_change": {
                "state": "structurally-checked",
                "approval_scope_enforced": True,
                "approval_records_selected": 1,
                "change_package_enforced": True,
                "change_package_required": True,
                "change_packages_selected": 1,
                "change_set": {
                    "hash_contract": "canonical-git-change-set-v1",
                    "content_sha256": "c" * 64,
                    "base_revision": "a" * 40,
                    "head_revision": "b" * 40,
                    "selected_revision": "a" * 40,
                    "changed_path_count": 3,
                },
            }
        },
        "counts": {"errors": 0, "blocking_warnings": 0},
        "evidence": {
            "observed_revision": "a" * 40,
            "observed_branch": "main",
        },
    }


class UpgradeAcceptanceTest(unittest.TestCase):
    def test_accepts_only_complete_strict_evidence(self) -> None:
        self.assertEqual(acceptance_failures(accepted_payload()), [])

    def test_rejects_staged_update_even_when_validation_passed(self) -> None:
        payload = accepted_payload()
        payload["installation_state"] = "staged"
        payload["placeholder_validation"] = {
            "acceptance_eligible": False,
            "unresolved_active": 0,
        }

        failures = acceptance_failures(payload)

        self.assertIn("installation state is not accepted", failures)
        self.assertIn("validator report is not acceptance eligible", failures)

    def test_rejects_reduced_scope_and_unresolved_placeholders(self) -> None:
        payload = accepted_payload()
        payload["validation_scope"] = "changed"
        payload["approval_archive"] = {"mode": "changed"}
        payload["placeholder_validation"] = {
            "acceptance_eligible": True,
            "unresolved_active": 2,
        }

        failures = acceptance_failures(payload)

        self.assertIn("validation scope is not full", failures)
        self.assertIn("approval archive was not fully validated", failures)
        self.assertIn("active target placeholders remain", failures)

    def test_rejects_upgrade_without_enforced_current_change(self) -> None:
        payload = accepted_payload()
        payload["health_layers"] = {
            "current_change": {
                "state": "partial",
                "approval_scope_enforced": True,
                "approval_records_selected": 1,
                "change_package_enforced": False,
                "change_packages_selected": 0,
            }
        }

        failures = acceptance_failures(payload)

        self.assertIn("upgrade change scope was not structurally checked", failures)

    def test_optional_package_is_not_required_when_module_is_disabled(self) -> None:
        payload = accepted_payload()
        current = payload["health_layers"]["current_change"]
        current["change_package_required"] = False
        current["change_package_enforced"] = False
        current["change_packages_selected"] = 0

        self.assertEqual(acceptance_failures(payload), [])


if __name__ == "__main__":
    unittest.main()
