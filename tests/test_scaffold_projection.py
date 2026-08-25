from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from scaffold_projection import (  # noqa: E402
    project_manifest,
    project_module_profile,
    project_router,
)
from scaffold_target_structure import plan  # noqa: E402


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

    def test_disabled_debug_contract_metadata_is_omitted_with_its_surfaces(self) -> None:
        source = (
            "framework:\n  version: x\n"
            "debug_mode:\n"
            "  contract_version: 3\n"
            "  flow: .ai/assistant/flows/debug-mode.flow.md\n"
            "engineering_evidence:\n"
            "  contract_version: 2\n"
            "  flow: .ai/assistant/flows/engineering-evidence-capture.flow.md\n"
        )

        rendered = project_manifest(
            source,
            "core",
            "core",
            {
                Path(".ai/alatyr.yaml"),
                Path(".ai/assistant/flows/engineering-evidence-capture.flow.md"),
            },
        )

        self.assertNotIn("debug_mode:", rendered)
        self.assertIn("engineering_evidence:\n  contract_version: 2", rendered)

    def test_manifest_projection_forces_non_accepted_scaffold_state(self) -> None:
        source = (
            "installation:\n"
            "  support_profile: \"{CORE_STANDARD_OR_FULL}\"\n"
            "  state: \"accepted\"\n"
            "framework:\n"
            "  pack: \"{CORE_STANDARD_OR_COMPLETE}\"\n"
        )

        rendered = project_manifest(source, "standard", "standard", set())

        self.assertIn('state: "scaffolded"', rendered)
        self.assertNotIn('state: "accepted"', rendered)

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

    def test_enabled_modules_are_projected_into_human_profile(self) -> None:
        source = (
            "Module: `ai-infrastructure`\n"
            "State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`\n\n"
            "Module: `debug-mode`\n"
            "State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`\n"
        )

        rendered = project_module_profile(source, {"ai-infrastructure"})

        self.assertIn("Module: `ai-infrastructure`\nState: `enabled`", rendered)
        self.assertIn(
            "Module: `debug-mode`\n"
            "State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`",
            rendered,
        )

    def test_overwrite_preserves_existing_catalog_shared_surface(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            shared = target / ".ai/assistant/assistant-capabilities.json"
            shared.parent.mkdir(parents=True)
            shared.write_text('{"target_authored": true}\n', encoding="utf-8")

            _actions, blocked = plan(
                SimpleNamespace(
                    target=target,
                    write=True,
                    overwrite_existing=True,
                    profile="full",
                    framework_pack="matched",
                    enable_module=[],
                )
            )

            self.assertEqual(
                shared.read_text(encoding="utf-8"),
                '{"target_authored": true}\n',
            )
            self.assertTrue(
                any(
                    "record-merge-by-assistant-id" in item
                    and "preserved existing file" in item
                    for item in blocked
                )
            )


if __name__ == "__main__":
    unittest.main()
