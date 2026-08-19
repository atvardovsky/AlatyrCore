from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_validation_support import parse_manifest  # noqa: E402


class ManifestParserTests(unittest.TestCase):
    def parse(self, text: str):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "alatyr.yaml"
        path.write_text(text, encoding="utf-8")
        return parse_manifest(path)

    def test_preserves_nested_mapping_list_paths_and_lines(self) -> None:
        parsed = self.parse(
            "framework:\n"
            "  name: Alatyr Core\n"
            "validation:\n"
            "  commands:\n"
            "    - name: tests\n"
            "      required_for:\n"
            "        - code-local\n"
        )

        self.assertEqual(parsed.parse_failures, [])
        self.assertIn(("framework",), parsed.containers)
        self.assertEqual(parsed.scalars[("framework", "name")].line, 2)
        self.assertEqual(
            parsed.scalars[("validation", "commands", "[]", "name")].value,
            "tests",
        )
        self.assertEqual(
            parsed.lists[("validation", "commands", "[]", "required_for")][0].value,
            "code-local",
        )

    def test_rejects_duplicate_mapping_keys(self) -> None:
        parsed = self.parse("framework:\n  name: first\n  name: second\n")

        self.assertTrue(any("duplicate key name" in item for item in parsed.parse_failures))

    def test_reports_yaml_syntax_with_line_context(self) -> None:
        parsed = self.parse("framework: [unterminated\n")

        self.assertTrue(parsed.parse_failures)
        self.assertIn("line 1", parsed.parse_failures[0])


if __name__ == "__main__":
    unittest.main()
