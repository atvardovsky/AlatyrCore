from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.modules import (  # noqa: E402
    MODULE_IMPLEMENTATIONS,
    dispatch_capability_checks,
    registry_contract_errors,
)


class RecordingValidator:
    def __init__(self, calls: list[tuple[str, object | None]]) -> None:
        self.calls = calls

    def capability_validation_context(self) -> object:
        return "capability-context"

    def __getattr__(self, name: str):
        def record(manifest: object | None = None) -> None:
            self.calls.append((name, manifest))

        return record


class RecordingModule:
    def __init__(
        self,
        calls: list[tuple[str, object | None]],
        check_id: str = "check_ai_infrastructure_router",
    ) -> None:
        self.calls = calls
        self.check_id = check_id

    def validate(self, context: object, manifest: object | None) -> None:
        self.calls.append((self.check_id, (context, manifest)))


class ValidatorModuleDispatchTests(unittest.TestCase):
    def test_disabled_capabilities_run_no_optional_checks(self) -> None:
        calls: list[tuple[str, object | None]] = []
        validator = RecordingValidator(calls)

        dispatched = dispatch_capability_checks(validator, [], {"manifest": True})

        self.assertEqual(dispatched, ())
        self.assertEqual(calls, [])

    def test_shared_checks_run_once_for_dependency_closure(self) -> None:
        calls: list[tuple[str, object | None]] = []
        validator = RecordingValidator(calls)
        manifest = {"manifest": True}

        with patch.dict(
            MODULE_IMPLEMENTATIONS,
            {
                check_id: RecordingModule(calls, check_id)
                for check_id in {
                    "check_ai_infrastructure_router",
                    "check_development_evidence",
                    "check_extensions",
                }
            },
        ):
            dispatched = dispatch_capability_checks(
                validator,
                ["ai-infrastructure", "extensions"],
                manifest,
            )

        self.assertEqual(
            dispatched,
            ("check_ai_infrastructure_router", "check_development_evidence", "check_extensions"),
        )
        self.assertEqual(
            calls,
            [
                (
                    "check_ai_infrastructure_router",
                    ("capability-context", manifest),
                ),
                (
                    "check_development_evidence",
                    ("capability-context", manifest),
                ),
                ("check_extensions", ("capability-context", manifest)),
            ],
        )

    def test_extracted_registry_is_incrementally_extensible(self) -> None:
        self.assertEqual(
            set(MODULE_IMPLEMENTATIONS),
            {
                "check_ai_infrastructure_router",
                "check_architecture_knowledge",
                "check_code_documentation",
                "check_consistency_map",
                "check_dependency_knowledge",
                "check_development_evidence",
                "check_extensions",
                "check_project_vocabulary",
                "check_support_generation",
                "check_team_collaboration",
                "check_test_first_development",
            },
        )
        self.assertEqual(
            MODULE_IMPLEMENTATIONS["check_consistency_map"].check_id,
            "check_consistency_map",
        )
        self.assertEqual(registry_contract_errors(), [])

    def test_registry_contract_rejects_an_undeclared_check(self) -> None:
        from target_adapter_validation.modules import CAPABILITY_CHECKS

        with patch.dict(
            CAPABILITY_CHECKS,
            {"fixture": ("check_typo",)},
            clear=True,
        ):
            self.assertEqual(
                registry_contract_errors(),
                [
                    "capability check has no implementation or compatibility fallback: check_typo",
                    *[
                        f"module implementation is not declared by a capability: {check_id}"
                        for check_id in sorted(MODULE_IMPLEMENTATIONS)
                    ],
                    *[
                        f"compatibility fallback is not declared by a capability: {check_id}"
                        for check_id in sorted(
                            {
                                "check_debug_mode",
                                "check_discussion_diagrams",
                                "check_subagent_delegation",
                                "check_workspace_modes",
                            }
                        )
                    ],
                ],
            )


if __name__ == "__main__":
    unittest.main()
