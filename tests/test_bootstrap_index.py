from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from bootstrap_index import build_bootstrap_index, build_bootstrap_integrity  # noqa: E402


class BootstrapIndexTests(unittest.TestCase):
    def test_preserves_numeric_installed_versions_as_strings(self) -> None:
        manifest = """\
schema_version: 12
framework:
  version: 0.1.0-alpha.13
  template_version: 13
  pack: core
installation:
  support_profile: core
modules:
  enabled: []
known_gaps: []
"""
        router = json.dumps(
            {
                "routing_order": ["docs-local"],
                "profile_index": {},
                "context_budgets": {"on_exceed": "record expansion"},
            }
        )

        result = build_bootstrap_index(manifest, "# Project map\n", router)

        self.assertEqual(result["installation"]["adapter_schema_version"], "12")
        self.assertEqual(result["installation"]["template_version"], "13")

    def test_integrity_metadata_stays_out_of_compact_bootstrap(self) -> None:
        manifest = """\
schema_version: 12
framework:
  version: 0.1.0-alpha.13
  template_version: 13
  pack: core
installation:
  support_profile: core
modules:
  enabled: []
known_gaps: []
"""
        router = json.dumps(
            {
                "routing_order": ["docs-local"],
                "profile_index": {},
                "context_budgets": {"on_exceed": "record expansion"},
            }
        )

        bootstrap = build_bootstrap_index(manifest, "# Project map\n", router)
        integrity = build_bootstrap_integrity(
            manifest,
            "# Project map\n",
            router,
            bootstrap=bootstrap,
            rule_registry_text=json.dumps({"category_owners": []}),
            semantic_index_text=json.dumps({"schema_version": 2}),
            generated_by={"tool": "test"},
        )

        self.assertNotIn("generated_by", bootstrap)
        self.assertNotIn("derived_from", bootstrap)
        self.assertIsInstance(bootstrap["rule_selector"], str)
        self.assertEqual(integrity["generated_by"], {"tool": "test"})
        self.assertIn("derived_from", integrity)
        self.assertIsInstance(integrity["rule_selector"], dict)
        self.assertRegex(integrity["bootstrap_digest"], r"^sha256:[0-9a-f]{64}$")

    def test_semantic_preload_includes_compact_rule_owner(self) -> None:
        manifest = """\
schema_version: 12
framework:
  version: 0.1.0-alpha.13
  template_version: 13
  pack: core
installation:
  support_profile: core
modules:
  enabled: []
known_gaps: []
"""
        router = json.dumps(
            {
                "routing_order": ["docs-local"],
                "profile_index": {},
                "semantic_codebook": {
                    "preload_terms": ["alatyr:logical-integrity@1"],
                },
                "context_budgets": {"on_exceed": "record expansion"},
            }
        )

        result = build_bootstrap_index(
            manifest,
            "# Project map\n",
            router,
            semantic_terms={
                "alatyr:logical-integrity@1": {
                    "version": 1,
                    "definition": "Review semantic facts against owners.",
                    "owner_rule_id": "ALATYR-INTEGRITY-001",
                    "canonical_owner": "logical-integrity.md",
                }
            },
        )

        self.assertEqual(
            result["semantic_preload"]["terms"][0]["owner_rule_id"],
            "ALATYR-INTEGRITY-001",
        )


if __name__ == "__main__":
    unittest.main()
