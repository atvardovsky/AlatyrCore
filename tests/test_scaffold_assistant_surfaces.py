from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from scaffold_target_structure import plan, resolve_assistant_surfaces  # noqa: E402
from scaffold_projection import path_available, portable_relative_path  # noqa: E402


def scaffold_args(target: Path, *surfaces: str, profile: str = "full") -> SimpleNamespace:
    return SimpleNamespace(
        target=target,
        write=False,
        overwrite_existing=False,
        profile=profile,
        framework_pack="matched",
        enable_module=[],
        assistant_surface=list(surfaces),
    )


def action_paths(actions: list[str]) -> set[str]:
    return {
        action.split(" -> ", 1)[0].split(": ", 1)[1]
        for action in actions
        if action.startswith("template: ")
    }


class ScaffoldAssistantSurfaceTests(unittest.TestCase):
    def test_repository_paths_are_portable_across_windows_and_posix(self) -> None:
        windows_path = PureWindowsPath(
            ".ai\\assistant\\context\\profiles\\code-local.json"
        )
        self.assertEqual(
            portable_relative_path(windows_path).as_posix(),
            ".ai/assistant/context/profiles/code-local.json",
        )
        self.assertTrue(
            path_available(
                ".ai/assistant/context/profiles/code-local.json", {windows_path}
            )
        )

    def test_native_bridges_are_omitted_without_explicit_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            actions, _blocked = plan(scaffold_args(Path(directory)))

        paths = action_paths(actions)
        self.assertIn("AGENTS.md", paths)
        self.assertIn("AI_ASSISTANTS.md", paths)
        self.assertNotIn(".rules", paths)
        self.assertNotIn("CLAUDE.md", paths)
        self.assertNotIn(".roo/rules/alatyr-core.md", paths)

    def test_alias_selects_only_the_matching_native_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            actions, _blocked = plan(scaffold_args(Path(directory), "zed"))

        paths = action_paths(actions)
        self.assertIn(".rules", paths)
        self.assertNotIn("CLAUDE.md", paths)
        self.assertNotIn(".roo/rules/alatyr-core.md", paths)

    def test_multiple_explicit_surfaces_select_their_native_bridges(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            actions, _blocked = plan(
                scaffold_args(Path(directory), "anthropic-claude", "roo-code")
            )

        paths = action_paths(actions)
        self.assertIn("CLAUDE.md", paths)
        self.assertIn(".roo/rules/alatyr-core.md", paths)
        self.assertNotIn(".rules", paths)

    def test_explicit_surface_expands_a_partial_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            actions, _blocked = plan(
                scaffold_args(Path(directory), "claude", profile="standard")
            )

        paths = action_paths(actions)
        self.assertIn("CLAUDE.md", paths)
        self.assertIn(".ai/assistant/assistant-capabilities.json", paths)
        self.assertIn(
            ".ai/assistant/assistant-capabilities/generic.json", paths
        )
        self.assertIn(
            ".ai/assistant/assistant-capabilities/claude.json", paths
        )

    def test_unknown_surface_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown assistant surface"):
            resolve_assistant_surfaces(["not-a-real-client"])


if __name__ == "__main__":
    unittest.main()
