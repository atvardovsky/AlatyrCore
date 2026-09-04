from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.modules import (  # noqa: E402
    CAPABILITY_CHECKS,
    CAPABILITY_ROUTES,
    CapabilityRoute,
    CapabilityRouteKind,
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

    def test_unknown_target_capability_does_not_truncate_other_findings(self) -> None:
        calls: list[tuple[str, object | None]] = []

        dispatched = dispatch_capability_checks(
            RecordingValidator(calls), ["target-only-unknown"], {"manifest": True}
        )

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
                "check_discussion_diagrams",
                "check_extensions",
                "check_project_vocabulary",
                "check_support_generation",
                "check_subagent_delegation",
                "check_team_collaboration",
                "check_test_first_development",
                "check_workspace_modes",
            },
        )
        self.assertEqual(
            set(CAPABILITY_CHECKS),
            {
                capability_id
                for capability_id, route in CAPABILITY_ROUTES.items()
                if route.checks
            },
        )
        self.assertEqual(
            MODULE_IMPLEMENTATIONS["check_consistency_map"].check_id,
            "check_consistency_map",
        )
        self.assertEqual(registry_contract_errors(), [])

    def test_registry_contract_rejects_a_catalog_capability_without_route(self) -> None:
        with patch(
            "target_adapter_validation.modules.load_modules",
            return_value={**{key: {} for key in CAPABILITY_ROUTES}, "new-capability": {}},
        ):
            self.assertEqual(
                registry_contract_errors(),
                ["catalog capability has no validation route: new-capability"],
            )

    def test_registry_contract_rejects_a_route_without_catalog_capability(self) -> None:
        with patch(
            "target_adapter_validation.modules.load_modules",
            return_value={key: {} for key in CAPABILITY_ROUTES if key != "diagrams"},
        ):
            self.assertEqual(
                registry_contract_errors(),
                ["validation route has no catalog capability: diagrams"],
            )

    def test_registry_contract_rejects_mismatched_route_semantics(self) -> None:
        replacement = CapabilityRoute(
            "consistency-map",
            CapabilityRouteKind.UNIVERSAL,
            ("check_consistency_map",),
        )
        with patch.dict(
            CAPABILITY_ROUTES,
            {"consistency-map": replacement},
        ):
            self.assertEqual(
                registry_contract_errors(),
                [
                    "universal capability must not declare dispatch checks: consistency-map",
                    "module implementation is not declared by a modular capability: check_consistency_map",
                ],
            )


if __name__ == "__main__":
    unittest.main()
