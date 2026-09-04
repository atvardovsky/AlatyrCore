from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from composition_model import CompositionRequest, resolve_composition  # noqa: E402
from projection_graph import (  # noqa: E402
    ProjectionInput,
    ProjectionNode,
    ProjectionOutput,
    operation_projection_nodes,
    validate_projection_graph,
)
from scaffold_target_structure import (  # noqa: E402
    project_assistant_bridges,
    resolve_assistant_surfaces,
    resolve_profile_paths,
    resolved_framework_pack,
)


class CompositionModelTests(unittest.TestCase):
    def test_shadow_resolution_matches_legacy_profiles(self) -> None:
        for profile in ("kernel", "core", "standard", "full"):
            with self.subTest(profile=profile):
                resolved = resolve_composition(CompositionRequest(profile))
                legacy_paths = project_assistant_bridges(
                    resolve_profile_paths(profile, set()), set()
                )
                self.assertEqual(
                    set(resolved.selected_target_paths),
                    {path.as_posix() for path in legacy_paths},
                )
                self.assertEqual(
                    resolved.framework_pack,
                    resolved_framework_pack(profile, "matched", set()),
                )

    def test_shadow_resolution_preserves_capability_and_alias_facts(self) -> None:
        request = CompositionRequest(
            "standard",
            requested_capabilities=("extensions",),
            requested_assistant_surfaces=("openai-codex",),
        )
        resolved = resolve_composition(request)
        legacy_surfaces = resolve_assistant_surfaces(["openai-codex"])
        legacy_paths = project_assistant_bridges(
            resolve_profile_paths("standard", set(resolved.enabled_capabilities)),
            legacy_surfaces,
        )
        self.assertIn(("openai-codex", "codex"), resolved.alias_resolutions)
        self.assertEqual(set(resolved.assistant_surfaces), legacy_surfaces)
        self.assertEqual(
            set(resolved.selected_target_paths),
            {path.as_posix() for path in legacy_paths},
        )

    def test_projection_graph_orders_operation_outputs(self) -> None:
        self.assertEqual(
            validate_projection_graph(operation_projection_nodes()),
            ("project.operation-catalog", "project.operation-index"),
        )

    def test_projection_graph_rejects_cycles_and_duplicate_outputs(self) -> None:
        output = ProjectionOutput("generated.json", "derived", "replace", "none", False)
        first = ProjectionNode(
            "first", "owner", "phase", ("second",), (), (output,), "generator", ("check",)
        )
        second = ProjectionNode(
            "second", "owner", "phase", ("first",), (), (), "generator", ("check",)
        )
        with self.assertRaisesRegex(ValueError, "cycle"):
            validate_projection_graph((first, second))
        duplicate = ProjectionNode(
            "duplicate", "owner", "phase", (), (ProjectionInput("canonical-file", "source"),), (output,), "generator", ("check",)
        )
        with self.assertRaisesRegex(ValueError, "multiple owners"):
            validate_projection_graph((first, duplicate))


if __name__ == "__main__":
    unittest.main()
