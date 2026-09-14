from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from framework_packaging import (  # noqa: E402
    projected_framework_contents,
    resolve_framework_files,
    validate_pack_catalog,
)


class FrameworkPackagingTests(unittest.TestCase):
    def test_direct_semantic_shard_declarations_are_rejected(self) -> None:
        catalog = {
            "schema_version": 1,
            "pack_kind": "alatyr-framework-pack-catalog",
            "semantic_projection": {
                "mode": "rule-owner-closure",
                "index": "semantics/index.json",
            },
            "packs": {
                "kernel": {"additional_files": ["semantics/core.json"]},
            },
        }

        with self.assertRaisesRegex(ValueError, "semantic shards directly"):
            validate_pack_catalog(catalog)

    def test_kernel_semantic_projection_follows_installed_rule_owners(self) -> None:
        selected = resolve_framework_files("kernel")

        self.assertIn("semantics/index.json", selected)
        self.assertIn("semantics/core.json", selected)
        self.assertIn("semantics/change.json", selected)
        self.assertIn("semantics/infrastructure.json", selected)
        self.assertIn("semantics/support.json", selected)
        self.assertNotIn("semantics/collaboration.json", selected)

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
