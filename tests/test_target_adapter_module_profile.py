from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.module_profile import (  # noqa: E402
    parse_module_profile,
    parse_module_profile_state,
)


class TargetAdapterModuleProfileTests(unittest.TestCase):
    def test_parse_all_preserves_duplicate_declarations(self) -> None:
        states = parse_module_profile(
            "Module: `diagrams`\nState: enabled\n\n"
            "Module: `diagrams`\nState: deferred\n\n"
            "Module: `code-documentation`\n"
        )

        self.assertEqual(
            [state.state for state in states["diagrams"]],
            ["enabled", "deferred"],
        )
        self.assertIsNone(states["code-documentation"][0].state)

    def test_parse_enabled_module_state(self) -> None:
        text = """
Module: `code-documentation`
State: `enabled`

Module: `project-vocabulary`
State: disabled
"""

        state = parse_module_profile_state(text, "code-documentation")

        self.assertTrue(state.declared)
        self.assertTrue(state.has_parseable_state)
        self.assertEqual(state.state, "enabled")
        self.assertTrue(state.validation_enabled)

    def test_disabled_module_is_declared_but_not_validation_enabled(self) -> None:
        state = parse_module_profile_state(
            "Module: `project-vocabulary`\nState: disabled\n",
            "project-vocabulary",
        )

        self.assertTrue(state.declared)
        self.assertEqual(state.state, "disabled")
        self.assertFalse(state.validation_enabled)

    def test_missing_module_and_missing_state_are_distinct(self) -> None:
        missing = parse_module_profile_state("", "diagrams")
        missing_state = parse_module_profile_state("Module: `diagrams`\n", "diagrams")

        self.assertFalse(missing.declared)
        self.assertFalse(missing.has_parseable_state)
        self.assertTrue(missing_state.declared)
        self.assertFalse(missing_state.has_parseable_state)

    def test_module_id_is_matched_literally(self) -> None:
        text = "Module: `test-first-development+extra`\nState: enabled\n"

        self.assertFalse(
            parse_module_profile_state(text, "test-first-development").declared
        )
        self.assertTrue(
            parse_module_profile_state(
                text, "test-first-development+extra"
            ).validation_enabled
        )


if __name__ == "__main__":
    unittest.main()
