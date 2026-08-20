from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from scaffold_projection import project_manifest, project_router  # noqa: E402


class ScaffoldProjectionTests(unittest.TestCase):
    def test_optional_approval_mapping_is_omitted_without_surfaces(self) -> None:
        source = "framework:\n  version: x\napprovals:\n  index: .ai/assistant/approvals/index.json\n"

        rendered = project_manifest(
            source,
            "core",
            "core",
            {Path(".ai/alatyr.yaml")},
        )

        self.assertNotIn("approvals:", rendered)

    def test_router_omits_profiles_without_installed_descriptors(self) -> None:
        router = {
            "routing_order": ["docs-local", "ai-infrastructure"],
            "profile_index": {
                "docs-local": {
                    "descriptor": ".ai/assistant/context/profiles/docs-local.json"
                },
                "ai-infrastructure": {
                    "descriptor": ".ai/assistant/context/profiles/ai-infrastructure.json"
                },
            },
        }
        selected = {
            Path(".ai/assistant/context/profiles/docs-local.json"),
        }

        projected = project_router(router, selected, set())

        self.assertEqual(list(projected["profile_index"]), ["docs-local"])
        self.assertEqual(projected["routing_order"], ["docs-local"])


if __name__ == "__main__":
    unittest.main()
