from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.values import (  # noqa: E402
    is_resolved_string,
    is_string_list,
    string_list_value,
)


class TargetAdapterValueTests(unittest.TestCase):
    def test_resolved_string_rejects_empty_placeholders_and_unresolved(self) -> None:
        self.assertTrue(is_resolved_string("accepted-owner"))
        self.assertFalse(is_resolved_string(""))
        self.assertFalse(is_resolved_string("   "))
        self.assertFalse(is_resolved_string("{TARGET_OWNER}"))
        self.assertFalse(is_resolved_string("unknown"))

    def test_resolved_string_can_reject_or_marker(self) -> None:
        self.assertTrue(is_resolved_string("codex"))
        self.assertTrue(is_resolved_string("CODEX_OR_GENERIC"))
        self.assertFalse(
            is_resolved_string("CODEX_OR_GENERIC", reject_or_marker=True)
        )

    def test_string_list_value_preserves_valid_lists(self) -> None:
        value = ["one", "two"]

        self.assertIs(string_list_value(value), value)
        self.assertEqual(string_list_value([], non_empty=False), [])
        self.assertIsNone(string_list_value([]))
        self.assertIsNone(string_list_value(["one", ""]))
        self.assertIsNone(string_list_value(["{TARGET_OWNER}"], resolved=True))

    def test_is_string_list_uses_same_contract(self) -> None:
        self.assertTrue(is_string_list(["one"]))
        self.assertTrue(is_string_list([], non_empty=False))
        self.assertFalse(is_string_list([]))
        self.assertFalse(is_string_list(["unknown"], resolved=True))


if __name__ == "__main__":
    unittest.main()
