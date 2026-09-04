from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from scaffold_projection import (  # noqa: E402
    path_available,
    project_assistant_capability_index,
    project_manifest,
    project_markdown_fragments,
    project_module_profile,
    project_router,
    selected_path_index,
)
from scaffold_target_structure import plan  # noqa: E402


class ScaffoldProjectionTests(unittest.TestCase):
    def test_markdown_fragments_require_installed_paths_and_modules(self) -> None:
        source = (
            "base\n"
            '<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/optional.json"]} -->\n'
            "path claim\n"
            "<!-- /alatyr:scaffold-fragment -->\n"
            '<!-- alatyr:scaffold-fragment {"requires_modules":["optional"]} -->\n'
            "module claim\n"
            "<!-- /alatyr:scaffold-fragment -->\n"
        )

        absent = project_markdown_fragments(source, set())
        present = project_markdown_fragments(
            source,
            {Path(".ai/optional.json")},
            {"optional"},
        )

        self.assertEqual(absent, "base\n")
        self.assertEqual(present, "base\npath claim\nmodule claim\n")
        self.assertNotIn("alatyr:scaffold-fragment", present)

    def test_markdown_fragments_reject_unclosed_markers(self) -> None:
        source = (
            '<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/optional.json"]} -->\n'
            "claim\n"
        )

        with self.assertRaisesRegex(ValueError, "unclosed scaffold Markdown fragment"):
            project_markdown_fragments(source, set())

    def test_selected_path_index_preserves_path_availability_semantics(self) -> None:
        selected = {
            Path(".ai/assistant/context/profiles/docs-local.json"),
            Path(".ai/project/contour.md"),
        }
        indexed = selected_path_index(selected)

        self.assertTrue(
            path_available(".ai/assistant/context/profiles/docs-local.json", indexed)
        )
        self.assertTrue(path_available(".ai/assistant/context/profiles", indexed))
        self.assertFalse(path_available(".ai/assistant/operation-catalog.json", indexed))

    def test_selected_path_index_normalizes_windows_separators_once(self) -> None:
        indexed = selected_path_index(
            {Path(".ai/project/contour.md"), ".ai\\assistant\\help.md"}
        )

        self.assertTrue(path_available(".ai/assistant/help.md", indexed))
        self.assertTrue(path_available(".ai/assistant", indexed))
        self.assertFalse(path_available(".ai/assistant/help-reference.md", indexed))

    def test_assistant_capability_index_keeps_only_installed_records_and_bridges(self) -> None:
        source = {
            "default_surface": "generic",
            "surfaces": {
                "generic": ".ai/assistant/assistant-capabilities/generic.json",
                "codex": ".ai/assistant/assistant-capabilities/codex.json",
            },
            "bridge_paths": {
                "generic": ["AI_ASSISTANTS.md"],
                "codex": ["AGENTS.md", "AI_ASSISTANTS.md"],
            },
        }
        selected = {
            Path(".ai/assistant/assistant-capabilities/generic.json"),
            Path("AGENTS.md"),
        }

        projected = project_assistant_capability_index(source, selected)

        self.assertEqual(
            projected["surfaces"],
            {"generic": ".ai/assistant/assistant-capabilities/generic.json"},
        )
        self.assertEqual(projected["bridge_paths"], {"generic": []})

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

    def test_missing_profile_defaults_to_kernel(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)

            actions, blocked = plan(
                SimpleNamespace(
                    target=target,
                    write=True,
                    overwrite_existing=False,
                    framework_pack="matched",
                    enable_module=[],
                )
            )

            self.assertFalse(blocked)
            self.assertTrue(actions)
            self.assertTrue((target / ".ai/assistant/entry-packet.json").is_file())
            self.assertFalse((target / ".ai/assistant/operation-catalog.json").exists())
            self.assertFalse(
                (target / ".ai/assistant/assistant-capabilities.json").exists()
            )
            agents_text = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertNotIn(".ai/assistant/operation-index.json", agents_text)
            self.assertNotIn(".ai/assistant/ai-infrastructure-router.json", agents_text)
            self.assertNotIn(".ai/assistant/assistant-capabilities.json", agents_text)

    def test_kernel_scaffold_generates_profile_specific_support_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)

            _actions, blocked = plan(
                SimpleNamespace(
                    target=target,
                    write=True,
                    overwrite_existing=False,
                    profile="kernel",
                    framework_pack="matched",
                    enable_module=[],
                    assistant_surface=[],
                )
            )

            self.assertFalse(blocked)
            state = json.loads(
                (target / ".ai/support-state.json").read_text(encoding="utf-8")
            )
            paths = {item["path"] for item in state["files"]}
            self.assertIn(".ai/assistant/bootstrap-index.json", paths)
            self.assertNotIn(".ai/assistant/operation-catalog.json", paths)
            self.assertNotIn(".agents/skills/README.md", paths)
            readme = (target / ".ai/README.md").read_text(encoding="utf-8")
            bootstrap = json.loads(
                (target / ".ai/assistant/bootstrap-index.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                bootstrap["derived_from"]["project_map"]["sha256"],
                hashlib.sha256(readme.encode("utf-8")).hexdigest(),
            )

    def test_partial_profile_capability_module_installs_closed_generic_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            _actions, blocked = plan(
                SimpleNamespace(
                    target=target,
                    write=True,
                    overwrite_existing=False,
                    profile="core",
                    framework_pack="matched",
                    enable_module=["multi-assistant-bridges"],
                    assistant_surface=[],
                )
            )

            self.assertFalse(blocked)
            index = json.loads(
                (target / ".ai/assistant/assistant-capabilities.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                index["surfaces"],
                {"generic": ".ai/assistant/assistant-capabilities/generic.json"},
            )
            self.assertTrue(
                (target / ".ai/assistant/assistant-capabilities/generic.json").is_file()
            )
            self.assertFalse(
                (target / ".ai/assistant/assistant-capabilities/codex.json").exists()
            )

    def test_kernel_agents_surface_projects_optional_agents_skill_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)

            actions, blocked = plan(
                SimpleNamespace(
                    target=target,
                    write=True,
                    overwrite_existing=False,
                    profile="full",
                    framework_pack="matched",
                    enable_module=[],
                    assistant_surface=["agents"],
                )
            )

            self.assertFalse(blocked)
            self.assertTrue(
                any(".agents/skills/README.md" in action for action in actions)
            )
            state = json.loads(
                (target / ".ai/support-state.json").read_text(encoding="utf-8")
            )
            paths = {item["path"] for item in state["files"]}
            self.assertIn(".agents/skills/README.md", paths)

    def test_support_profile_markdown_projection_removes_absent_claims(self) -> None:
        expected = {
            "kernel": {
                ".ai/README.md": [
                    "engineering-evidence capture",
                    "canonical operation catalog",
                    "AI infrastructure router entries",
                ],
            },
            "core": {
                ".ai/README.md": [
                    "canonical operation catalog",
                    "AI infrastructure router entries",
                ],
            },
            "standard": {
                "AI_ASSISTANTS.md": [
                    ".ai/assistant/ai-infrastructure-router.json",
                    ".ai/assistant/prompts/worker-orchestration.md",
                    "selected capability record",
                ],
                ".ai/assistant/templates/post-install-message.md": [
                    ".ai/assistant/assistant-capabilities.json",
                    "`architecture-assistance`",
                    "`debug-mode`",
                ],
            },
        }
        for profile, file_claims in expected.items():
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)
                _actions, blocked = plan(
                    SimpleNamespace(
                        target=target,
                        write=True,
                        overwrite_existing=False,
                        profile=profile,
                        framework_pack="matched",
                        enable_module=[],
                        assistant_surface=[],
                    )
                )
                self.assertFalse(blocked)
                for relpath, absent_claims in file_claims.items():
                    text = (target / relpath).read_text(encoding="utf-8")
                    self.assertNotIn("alatyr:scaffold-fragment", text)
                    for claim in absent_claims:
                        self.assertNotIn(claim, text)
                readme = (target / ".ai/README.md").read_text(encoding="utf-8")
                if profile == "kernel":
                    self.assertNotIn("durable engineering evidence", readme)
                    self.assertNotIn("target-authorized project guidance", readme)
                    self.assertNotIn("documentation-sync rules", readme)
                    self.assertNotIn("human and machine-readable approval", readme)
                    self.assertNotIn("- prompts", readme)
                if profile in {"core", "standard"}:
                    self.assertIn("durable engineering evidence", readme)
                    self.assertIn("target-authorized project guidance", readme)
                    self.assertIn("documentation-sync rules", readme)
                    self.assertNotIn("human and machine-readable approval", readme)
                    self.assertNotIn("- prompts", readme)

    def test_full_profile_markdown_projection_is_marker_free_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            _actions, blocked = plan(
                SimpleNamespace(
                    target=target,
                    write=True,
                    overwrite_existing=False,
                    profile="full",
                    framework_pack="matched",
                    enable_module=[],
                    assistant_surface=[],
                )
            )

            self.assertFalse(blocked)
            selected = {
                path.relative_to(ROOT / "templates/target")
                for path in (ROOT / "templates/target").rglob("*")
                if path.is_file()
            }
            projected_paths = [
                Path(".ai/README.md"),
                Path("AI_ASSISTANTS.md"),
                Path(".ai/assistant/templates/post-install-message.md"),
                Path(".ai/assistant/templates/post-update-message.md"),
            ]
            for relpath in projected_paths:
                with self.subTest(relpath=relpath):
                    source = (ROOT / "templates/target" / relpath).read_text(
                        encoding="utf-8"
                    )
                    rendered = (target / relpath).read_text(encoding="utf-8")
                    expected = project_markdown_fragments(source, selected)
                    self.assertEqual(rendered, expected)
                    self.assertNotIn("alatyr:scaffold-fragment", rendered)
            assistants = (target / "AI_ASSISTANTS.md").read_text(encoding="utf-8")
            self.assertIn(".ai/assistant/ai-infrastructure-router.json", assistants)
            self.assertIn(".ai/assistant/prompts/worker-orchestration.md", assistants)


if __name__ == "__main__":
    unittest.main()
