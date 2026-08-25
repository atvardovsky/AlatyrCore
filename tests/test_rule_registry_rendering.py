from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from render_rule_registry_docs import (  # noqa: E402
    installed_owner,
    render_ownership,
    render_registry,
)


REGISTRY_FIXTURE = {
    "category_owners": [
        {
            "category": "CONTEXT",
            "owner": "framework/context-profiles.md",
            "rule_ids": ["ALATYR-CONTEXT-001"],
            "derived_surfaces": ["target context router"],
        }
    ],
    "rules": [
        {
            "id": "ALATYR-CONTEXT-001",
            "canonical_source": "framework/context-profiles.md",
            "summary": "Load bounded task context.",
            "applies_to": ["all work"],
            "enforcement": "required",
        }
    ],
}


class RuleRegistryRenderingTests(unittest.TestCase):
    def test_registry_distinguishes_source_and_installed_owners(self) -> None:
        rendered = render_registry(REGISTRY_FIXTURE)

        self.assertIn("Source owner: `framework/context-profiles.md`", rendered)
        self.assertIn(
            "Installed owner: `.ai/framework/context-profiles.md`", rendered
        )
        self.assertNotIn(
            "Canonical source: `.ai/framework/context-profiles.md`", rendered
        )

    def test_ownership_distinguishes_both_owner_identities(self) -> None:
        rendered = render_ownership(REGISTRY_FIXTURE)

        self.assertIn(
            "Source routing owner: `framework/context-profiles.md`", rendered
        )
        self.assertIn(
            "Installed routing owner: `.ai/framework/context-profiles.md`", rendered
        )
        self.assertIn(
            "Source canonical owner: `framework/context-profiles.md`", rendered
        )
        self.assertIn(
            "Installed canonical owner: `.ai/framework/context-profiles.md`", rendered
        )
        self.assertNotIn(
            "Canonical owner: `.ai/framework/context-profiles.md`", rendered
        )

    def test_installed_owner_rejects_non_framework_sources(self) -> None:
        for source in (".ai/framework/context-profiles.md", "../framework/rule.md"):
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    installed_owner(source)


if __name__ == "__main__":
    unittest.main()
