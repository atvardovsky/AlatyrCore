from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from bootstrap_index import (  # noqa: E402
    build_bootstrap_index,
    build_bootstrap_integrity,
    build_bundle_from_target,
    context_root_sha256,
)


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

    def test_integrity_binds_each_recursive_context_root(self) -> None:
        manifest = "schema_version: 1\n"
        router = json.dumps({"routing_order": []})
        bootstrap = build_bootstrap_index(manifest, "# Project\n", router)
        roots = {
            "framework_context_root": '{"index_id":"framework"}\n',
            "project_context_root": '{"index_id":"project"}\n',
            "assistant_context_root": '{"index_id":"assistant"}\n',
        }

        integrity = build_bootstrap_integrity(
            manifest,
            "# Project\n",
            router,
            bootstrap=bootstrap,
            context_root_texts=roots,
        )

        self.assertEqual(integrity["schema_version"], 2)
        for name, text in roots.items():
            self.assertEqual(
                integrity["derived_from"][name]["sha256"],
                hashlib.sha256(text.encode("utf-8")).hexdigest(),
            )

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

    def test_source_template_resolves_framework_context_root_from_source(self) -> None:
        _bootstrap, integrity = build_bundle_from_target(ROOT / "templates/target")

        self.assertEqual(
            integrity["derived_from"]["framework_context_root"]["path"],
            ".ai/framework/context-index.json",
        )

    def test_assistant_root_digest_excludes_only_integrity_self_digest(self) -> None:
        before = json.dumps(
            {
                "entries": [
                    {
                        "path": "bootstrap-integrity.json",
                        "content_digest": "sha256:before",
                    },
                    {"path": "help.md", "content_digest": "sha256:help"},
                ]
            }
        )
        self_changed = before.replace("sha256:before", "sha256:after")
        other_changed = before.replace("sha256:help", "sha256:changed")

        self.assertEqual(
            context_root_sha256("assistant_context_root", before),
            context_root_sha256("assistant_context_root", self_changed),
        )
        self.assertNotEqual(
            context_root_sha256("assistant_context_root", before),
            context_root_sha256("assistant_context_root", other_changed),
        )


if __name__ == "__main__":
    unittest.main()
