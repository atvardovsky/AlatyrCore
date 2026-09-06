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
class CompositionModelTests(unittest.TestCase):
    def test_profile_resolution_is_monotonic_and_pack_matched(self) -> None:
        resolved = {
            profile: resolve_composition(CompositionRequest(profile))
            for profile in ("kernel", "core", "standard", "full")
        }
        self.assertLess(
            set(resolved["kernel"].selected_target_paths),
            set(resolved["core"].selected_target_paths),
        )
        self.assertLess(
            set(resolved["core"].selected_target_paths),
            set(resolved["standard"].selected_target_paths),
        )
        self.assertEqual(
            set(resolved["standard"].selected_target_paths),
            set(resolved["full"].selected_target_paths),
        )
        self.assertEqual(
            {profile: value.framework_pack for profile, value in resolved.items()},
            {
                "kernel": "kernel",
                "core": "core",
                "standard": "standard",
                "full": "complete",
            },
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

    def test_resolution_preserves_capability_and_alias_facts(self) -> None:
        request = CompositionRequest(
            "standard",
            requested_capabilities=("extensions",),
            requested_assistant_surfaces=("openai-codex",),
        )
        resolved = resolve_composition(request)
        self.assertIn(("openai-codex", "codex"), resolved.alias_resolutions)
        self.assertEqual(set(resolved.assistant_surfaces), {"codex"})
        self.assertIn("AI_ASSISTANTS.md", resolved.selected_target_paths)
        self.assertNotIn("CLAUDE.md", resolved.selected_target_paths)
        self.assertIn("multi-assistant-bridges", resolved.enabled_capabilities)
        self.assertIn("installed-operations", resolved.enabled_capabilities)

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

    def test_projection_graph_rejects_dangling_and_undeclared_inputs(self) -> None:
        dangling = ProjectionNode(
            "dangling",
            "owner",
            "phase",
            (),
            (ProjectionInput("projection-output", "missing.json"),),
            (ProjectionOutput("result.json", "derived", "replace", "none", False),),
            "generator",
            ("check",),
        )
        with self.assertRaisesRegex(ValueError, "unknown output"):
            validate_projection_graph((dangling,))

        source = ProjectionNode(
            "source",
            "owner",
            "phase",
            (),
            (),
            (ProjectionOutput("source.json", "derived", "replace", "none", False),),
            "generator",
            ("check",),
        )
        consumer = ProjectionNode(
            "consumer",
            "owner",
            "phase",
            (),
            (ProjectionInput("projection-output", "source.json"),),
            (ProjectionOutput("result.json", "derived", "replace", "none", False),),
            "generator",
            ("check",),
        )
        with self.assertRaisesRegex(ValueError, "without declaring dependency"):
            validate_projection_graph((source, consumer))

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
