from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import context_slice  # noqa: E402


GUIDE = """# Guide

Intro text.

## Alpha

Alpha text.

### Alpha detail

Detail text.

```sh
# not a heading
```

## Beta

Beta text.

## Gamma

Gamma text.
"""

SAMPLE = '''def top(value):
    return value


@decorator
def decorated(value):
    return value


class Widget:
    def render(self):
        return "ok"

    class Inner:
        def nested(self):
            return "nested"
'''

DUPLICATE = """def same():
    return 1


def same():
    return 2
"""


class ContextSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name) / "target"
        (self.target / "docs").mkdir(parents=True)
        (self.target / "src").mkdir()
        (self.target / "docs/guide.md").write_text(GUIDE, encoding="utf-8")
        (self.target / "src/sample.py").write_text(SAMPLE, encoding="utf-8")
        (self.target / "src/duplicate.py").write_text(DUPLICATE, encoding="utf-8")

    def cli(self, *arguments: str):
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/context_slice.py"),
                "--target",
                str(self.target),
                *arguments,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_list_ignores_fenced_headings(self) -> None:
        result = self.cli("list", "--path", "docs/guide.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("alpha", result.stdout)
        self.assertIn("alpha-detail", result.stdout)
        self.assertIn("beta", result.stdout)
        self.assertNotIn("not a heading", result.stdout)
        self.assertIn("total_words:", result.stdout)

    def test_heading_slice_includes_subheadings_and_stops_at_siblings(self) -> None:
        result = self.cli("read", "--path", "docs/guide.md", "--heading", "alpha", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["selection"], "heading alpha")
        self.assertIn("## Alpha", payload["content"])
        self.assertIn("### Alpha detail", payload["content"])
        self.assertIn("Detail text.", payload["content"])
        self.assertNotIn("## Beta", payload["content"])
        self.assertLess(payload["words"], payload["total_words"])
        self.assertTrue(payload["sha256"].startswith("sha256:"))

    def test_heading_matches_title_case_insensitively(self) -> None:
        result = self.cli(
            "read", "--path", "docs/guide.md", "--heading", "Alpha Detail", "--json"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["selection"], "heading alpha-detail")

    def test_symbol_slice_includes_decorator(self) -> None:
        result = self.cli(
            "read", "--path", "src/sample.py", "--symbol", "decorated", "--json"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["content"].startswith("@decorator"))
        self.assertIn("def decorated", payload["content"])
        self.assertNotIn("def top", payload["content"])

    def test_nested_symbol_is_bounded(self) -> None:
        result = self.cli("read", "--path", "src/sample.py", "--symbol", "nested", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("def nested", payload["content"])
        self.assertNotIn("class Widget", payload["content"])
        self.assertLess(payload["words"], payload["total_words"])

    def test_line_range_is_inclusive(self) -> None:
        result = self.cli("read", "--path", "docs/guide.md", "--lines", "3:5", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["start_line"], 3)
        self.assertEqual(payload["end_line"], 5)
        self.assertEqual(payload["content"], "Intro text.\n\n## Alpha\n")

    def test_over_budget_slice_fails_without_emitting_content(self) -> None:
        result = self.cli(
            "read",
            "--path",
            "docs/guide.md",
            "--heading",
            "alpha",
            "--max-words",
            "1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("limit 1", result.stderr)
        self.assertNotIn("Alpha text.", result.stdout)

    def test_ambiguous_symbol_fails(self) -> None:
        result = self.cli(
            "read", "--path", "src/duplicate.py", "--symbol", "same", "--json"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ambiguous", result.stderr)

    def test_unknown_heading_and_symbol_fail(self) -> None:
        heading = self.cli(
            "read", "--path", "docs/guide.md", "--heading", "missing"
        )
        self.assertNotEqual(heading.returncode, 0)
        self.assertIn("unknown heading", heading.stderr)
        symbol = self.cli("read", "--path", "src/sample.py", "--symbol", "missing")
        self.assertNotEqual(symbol.returncode, 0)
        self.assertIn("unknown Python symbol", symbol.stderr)

    def test_path_escape_and_symlink_are_refused(self) -> None:
        outside = Path(self.temporary.name) / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        escaped = self.cli("read", "--path", "../outside.txt", "--lines", "1:1")
        self.assertNotEqual(escaped.returncode, 0)
        self.assertIn("target-relative", escaped.stderr)

        linked = self.target / "linked.md"
        linked.symlink_to(outside)
        symlinked = self.cli("read", "--path", "linked.md", "--lines", "1:1")
        self.assertNotEqual(symlinked.returncode, 0)
        self.assertIn("symlink", symlinked.stderr)

    def test_invalid_lines_and_max_words_are_bounded(self) -> None:
        bad_range = self.cli("read", "--path", "docs/guide.md", "--lines", "3:2")
        self.assertNotEqual(bad_range.returncode, 0)
        self.assertIn("1 <= START <= END", bad_range.stderr)

        bad_limit = self.cli(
            "read", "--path", "docs/guide.md", "--lines", "1:1", "--max-words", "0"
        )
        self.assertNotEqual(bad_limit.returncode, 0)
        self.assertIn("--max-words", bad_limit.stderr)

    def test_library_helpers_are_deterministic(self) -> None:
        sections = context_slice.markdown_sections(GUIDE)
        self.assertEqual(
            [section["id"] for section in sections],
            ["guide", "alpha", "alpha-detail", "beta", "gamma"],
        )
        symbols = context_slice.python_symbols(SAMPLE)
        self.assertEqual(
            [symbol["name"] for symbol in symbols],
            ["top", "decorated", "Widget", "render", "Inner", "nested"],
        )
        self.assertEqual(context_slice.words("one two  three\n"), 3)


if __name__ == "__main__":
    unittest.main()
