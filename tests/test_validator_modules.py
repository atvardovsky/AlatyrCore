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
    check_id = "check_ai_infrastructure_router"

    def __init__(self, calls: list[tuple[str, object | None]]) -> None:
        self.calls = calls

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
            {"check_ai_infrastructure_router": RecordingModule(calls)},
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
                ("check_development_evidence", manifest),
                ("check_extensions", manifest),
            ],
        )

    def test_extracted_registry_is_incrementally_extensible(self) -> None:
        self.assertEqual(
            set(MODULE_IMPLEMENTATIONS),
            {
                "check_ai_infrastructure_router",
                "check_consistency_map",
                "check_support_generation",
            },
        )
        self.assertEqual(
            MODULE_IMPLEMENTATIONS["check_consistency_map"].check_id,
            "check_consistency_map",
        )


if __name__ == "__main__":
    unittest.main()
