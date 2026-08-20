from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.modules import dispatch_capability_checks  # noqa: E402


class RecordingValidator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object | None]] = []

    def __getattr__(self, name: str):
        def record(manifest: object | None = None) -> None:
            self.calls.append((name, manifest))

        return record


class ValidatorModuleDispatchTests(unittest.TestCase):
    def test_disabled_capabilities_run_no_optional_checks(self) -> None:
        validator = RecordingValidator()

        dispatched = dispatch_capability_checks(validator, [], {"manifest": True})

        self.assertEqual(dispatched, ())
        self.assertEqual(validator.calls, [])

    def test_shared_checks_run_once_for_dependency_closure(self) -> None:
        validator = RecordingValidator()
        manifest = {"manifest": True}

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
            validator.calls,
            [
                ("check_ai_infrastructure_router", None),
                ("check_development_evidence", manifest),
                ("check_extensions", manifest),
            ],
        )


if __name__ == "__main__":
    unittest.main()
