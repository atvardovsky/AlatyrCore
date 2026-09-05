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
    projection_generator_id,
    target_projection_nodes,
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
        for profile in ("kernel", "core", "standard"):
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

    def test_full_separates_target_and_conformance_materialization(self) -> None:
        target = resolve_composition(CompositionRequest("full"))
        conformance = resolve_composition(
            CompositionRequest("full", projection_purpose="conformance")
        )

        self.assertEqual(target.projection_purpose, "target")
        self.assertEqual(conformance.projection_purpose, "conformance")
        self.assertLess(
            len(target.selected_target_paths), len(conformance.selected_target_paths)
        )
        self.assertEqual(
            set(conformance.selected_target_paths),
            {
                path.relative_to(ROOT / "templates/target").as_posix()
                for path in (ROOT / "templates/target").rglob("*")
                if path.is_file()
            },
        )
        self.assertEqual(
            set(target.available_capabilities),
            set(resolve_composition(CompositionRequest("kernel")).available_capabilities),
        )
        self.assertTrue(
            set(target.enabled_capabilities) <= set(target.installed_capabilities)
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

    def test_target_projection_graph_assigns_every_output_once(self) -> None:
        paths = (
            ".ai/alatyr.yaml",
            ".ai/assistant/operation-catalog.json",
            ".ai/assistant/operation-index.json",
            ".ai/support-state.json",
        )
        nodes = target_projection_nodes(paths)

        self.assertEqual(validate_projection_graph(nodes)[-1], "target:.ai/support-state.json")
        self.assertEqual(
            {output.path for node in nodes for output in node.outputs}, set(paths)
        )
        self.assertEqual(
            projection_generator_id(".ai/assistant/operation-index.json"),
            "project-operation-index",
        )
        manifest_node = next(
            node for node in nodes if node.node_id == "target:.ai/alatyr.yaml"
        )
        self.assertEqual(manifest_node.owner, "tools/scaffold_projection.py")
        index_node = next(
            node
            for node in nodes
            if node.node_id == "target:.ai/assistant/operation-index.json"
        )
        self.assertIn(
            ProjectionInput(
                "projection-output", ".ai/assistant/operation-catalog.json"
            ),
            index_node.inputs,
        )


if __name__ == "__main__":
    unittest.main()
