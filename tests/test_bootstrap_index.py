from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from bootstrap_index import build_bootstrap_index  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
