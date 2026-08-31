from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from framework_packaging import (  # noqa: E402
    projected_framework_contents,
    resolve_framework_files,
)


class FrameworkPackagingTests(unittest.TestCase):
    def test_resolved_files_cache_returns_fresh_sets(self) -> None:
        first = resolve_framework_files("kernel")
        first.add("mutated-by-caller.md")

        self.assertNotIn("mutated-by-caller.md", resolve_framework_files("kernel"))

    def test_projected_contents_cache_returns_fresh_dicts(self) -> None:
        first = projected_framework_contents("kernel")
        original = first["README.md"]
        first["README.md"] = "mutated by caller\n"

        self.assertEqual(projected_framework_contents("kernel")["README.md"], original)


if __name__ == "__main__":
    unittest.main()
