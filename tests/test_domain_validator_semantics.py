from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.code_documentation import (  # noqa: E402
    documentation_selectors_overlap,
)
from target_adapter_validation.project_vocabulary import (  # noqa: E402
    vocabulary_scopes_overlap,
)


class DocumentationSelectorTests(unittest.TestCase):
    def test_nested_source_globs_overlap(self) -> None:
        broad = {
            "include": ["src/**"],
            "exclude": ["vendor/**"],
            "languages": ["php"],
            "frameworks": [],
        }
        narrow = {
            "include": ["src/Domain/**"],
            "exclude": ["vendor/**"],
            "languages": ["php"],
            "frameworks": ["framework-a"],
        }
        self.assertTrue(documentation_selectors_overlap(broad, narrow))

    def test_language_partitions_but_exclusions_do_not_prove_disjointness(self) -> None:
        base = {
            "include": ["src/**"],
            "exclude": ["vendor/**"],
            "languages": ["php"],
            "frameworks": [],
        }
        different_language = {**base, "languages": ["typescript"]}
        different_exclusion = {**base, "exclude": ["generated/**"]}
        self.assertFalse(documentation_selectors_overlap(base, different_language))
        self.assertTrue(documentation_selectors_overlap(base, different_exclusion))

    def test_malformed_include_is_ignored_without_crashing(self) -> None:
        left = {"include": [1, "src/**"], "languages": [], "frameworks": []}
        right = {"include": ["src/App/**"], "languages": [], "frameworks": []}
        self.assertTrue(documentation_selectors_overlap(left, right))


class VocabularyScopeTests(unittest.TestCase):
    def test_intersecting_domain_and_usage_scope_is_ambiguous(self) -> None:
        self.assertTrue(
            vocabulary_scopes_overlap(
                {"billing", "orders"},
                {"api"},
                {"billing"},
                {"api", "docs"},
            )
        )

    def test_disjoint_domain_or_usage_scope_is_not_ambiguous(self) -> None:
        self.assertFalse(
            vocabulary_scopes_overlap({"billing"}, {"api"}, {"orders"}, {"api"})
        )
        self.assertFalse(
            vocabulary_scopes_overlap({"billing"}, {"api"}, {"billing"}, {"docs"})
        )


if __name__ == "__main__":
    unittest.main()
