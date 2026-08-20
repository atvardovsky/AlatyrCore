from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from capability_catalog import dependency_closure  # noqa: E402


class CapabilityGraphTests(unittest.TestCase):
    def test_returns_transitive_dependency_closure(self) -> None:
        modules = {
            "base": {"requires": []},
            "middle": {"requires": ["base"]},
            "top": {"requires": ["middle"]},
        }

        self.assertEqual(dependency_closure(["top"], modules), {"base", "middle", "top"})

    def test_rejects_dependency_cycle(self) -> None:
        modules = {
            "first": {"requires": ["second"]},
            "second": {"requires": ["first"]},
        }

        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            dependency_closure(["first"], modules)


if __name__ == "__main__":
    unittest.main()
