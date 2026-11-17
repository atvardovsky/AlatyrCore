from __future__ import annotations

import ntpath
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from path_spec import PathDialect, PathSpec, logical_path, matches_any, select_paths


class PathSpecTests(unittest.TestCase):
    def test_portable_fnmatch_preserves_separator_crossing(self) -> None:
        spec = PathSpec("tools/*.py")
        self.assertTrue(spec.matches("tools/check.py"))
        self.assertTrue(spec.matches("tools/package/check.py"))
        self.assertFalse(spec.matches("TOOLS/check.py"))
        self.assertFalse(PathSpec("**/*.md").matches("README.md"))

    def test_support_tree_includes_root_and_descendants(self) -> None:
        spec = PathSpec(".ai/local/**", PathDialect.SUPPORT_TREE_V1)
        self.assertTrue(spec.matches(".ai/local"))
        self.assertTrue(spec.matches(".ai/local/cache/result.json"))
        self.assertFalse(spec.matches(".ai/locality/result.json"))

    def test_source_host_dialect_retains_host_normalization(self) -> None:
        with patch("fnmatch.os.path.normcase", side_effect=ntpath.normcase):
            spec = PathSpec("src/*.py", PathDialect.SOURCE_HOST_V1)
            self.assertTrue(spec.matches("SRC\\nested\\FILE.PY"))

    def test_approval_scope_normalizes_separators_but_not_case(self) -> None:
        spec = PathSpec("src/**/*.py", PathDialect.APPROVAL_SCOPE_V1)
        self.assertTrue(spec.matches("src\\domain\\model.py"))
        self.assertFalse(spec.matches("SRC/domain/model.py"))

    def test_strict_logical_path_rejects_ambiguous_and_escaping_values(self) -> None:
        for value in ("", ".", "./a", "a//b", "a/../b", "/root", "C:/root", "a\\b", "a\x00b"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                logical_path(value)
        self.assertEqual(logical_path("docs/guide.md"), "docs/guide.md")
        self.assertEqual(logical_path("docs/**", pattern=True), "docs/**")
        with self.assertRaisesRegex(ValueError, "repository-relative"):
            PathSpec("../docs/**")

    def test_collection_helpers_are_deterministic(self) -> None:
        paths = ["docs/b.md", "src/a.py", "docs/a.md"]
        self.assertTrue(matches_any("docs/a.md", ["docs/**"]))
        self.assertEqual(select_paths(paths, ["docs/**"]), ("docs/a.md", "docs/b.md"))

    def test_memoized_matching_preserves_dialects_boundaries_and_errors(self) -> None:
        import path_spec as source

        source._compiled_spec.cache_clear()
        cases = [
            (PathDialect.PORTABLE_FNMATCH_V1, "tools/*.py", "tools/package/check.py", True),
            (PathDialect.PORTABLE_FNMATCH_V1, "**/*.md", "README.md", False),
            (PathDialect.SUPPORT_TREE_V1, ".ai/local/**", ".ai/local", True),
            (PathDialect.SUPPORT_TREE_V1, ".ai/local/**", ".ai/locality/x", False),
            (PathDialect.APPROVAL_SCOPE_V1, "src/**/*.py", "src\\domain\\model.py", True),
            (PathDialect.APPROVAL_SCOPE_V1, "src/**/*.py", "SRC/domain/model.py", False),
        ]
        for dialect, pattern, path, expected in cases:
            with self.subTest(dialect=dialect, pattern=pattern, path=path):
                self.assertEqual(matches_any(path, [pattern], dialect=dialect), expected)
                self.assertEqual(
                    matches_any(path, [pattern], dialect=dialect),
                    PathSpec(pattern, dialect).matches(path),
                )

        for _ in range(2):
            with self.assertRaisesRegex(ValueError, "repository-relative"):
                matches_any("docs/a.md", ["../docs/**"])

        self.assertEqual(source._compiled_spec.cache_info().maxsize, 4096)
        self.assertIs(
            source._compiled_spec("src/*.py", PathDialect.SOURCE_HOST_V1),
            source._compiled_spec("src/*.py", PathDialect.SOURCE_HOST_V1),
        )
        self.assertIsNot(
            source._compiled_spec("src/*.py", PathDialect.SOURCE_HOST_V1),
            source._compiled_spec("src/*.py", PathDialect.PORTABLE_FNMATCH_V1),
        )

        for index in range(4100):
            self.assertFalse(matches_any("docs/a.md", [f"patterns/{index}/*.md"]))
        self.assertLessEqual(source._compiled_spec.cache_info().currsize, 4096)

    def test_memoized_source_host_matching_keeps_runtime_normcase_semantics(self) -> None:
        import path_spec as source

        source._compiled_spec.cache_clear()
        with patch("fnmatch.os.path.normcase", side_effect=ntpath.normcase):
            self.assertTrue(
                matches_any(
                    "SRC\\nested\\FILE.PY",
                    ["src/*.py"],
                    dialect=PathDialect.SOURCE_HOST_V1,
                )
            )
        self.assertFalse(
            matches_any(
                "SRC\\nested\\FILE.PY",
                ["src/*.py"],
                dialect=PathDialect.SOURCE_HOST_V1,
            )
        )


if __name__ == "__main__":
    unittest.main()
