import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from architecture_context import architecture_context, MODES
from context_planning import ContextPlanRequest, plan_target_context
from tests.test_context_planning import TargetFixture, write_json, write_text, catalog_entry


class ArchitectureContextTests(unittest.TestCase):
    def descriptor(self):
        return json.loads((ROOT / "templates/target/.ai/assistant/context/intents/architecture-request.json").read_text())

    def test_mode_union_and_shared_guards(self):
        descriptor = self.descriptor()
        for mode in MODES:
            selected = architecture_context(descriptor, mode)
            self.assertTrue(set(descriptor["required_context"]).issubset(selected))
        self.assertEqual(set(architecture_context(descriptor)), set().union(*(architecture_context(descriptor, mode) for mode in MODES)))
        for bad in ({}, [], None, True, "unknown"):
            if bad is not None:
                with self.assertRaises(ValueError): architecture_context(descriptor, bad)
        mutant = copy.deepcopy(descriptor)
        mutant["required_context"] = []
        with self.assertRaises(ValueError): architecture_context(mutant, "explain")

    def test_all_modes_use_public_planner_and_stale_evidence_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            fixture = TargetFixture(target)
            fixture.build()
            descriptor = self.descriptor()
            intent = ".ai/assistant/context/intents/architecture-request.json"
            write_json(target / intent, descriptor)
            paths = [*architecture_context(descriptor), intent]
            for path in paths:
                if path != intent:
                    write_text(target / path, "selected architecture evidence\n")
            for contour in ("framework", "project", "assistant"):
                root = target / ".ai" / contour
                index = json.loads((root / "context-index.json").read_text())
                for number, path in enumerate(paths):
                    prefix = ".ai/" + contour + "/"
                    if path.startswith(prefix):
                        index["entries"].append(catalog_entry(root, f"{contour}.architecture-{number}", path[len(prefix):]))
                write_json(root / "context-index.json", index)
            router_path = target / ".ai/assistant/context-router.json"
            router = json.loads(router_path.read_text())
            router["intent_overlays"] = {"architecture-request": {"descriptor": intent}}
            write_json(router_path, router)
            catalog_path = target / ".ai/assistant/operation-catalog.json"
            catalog = json.loads(catalog_path.read_text())
            operation = catalog["operations"][0]
            operation.update(id="architecture-assistance", aliases=[], flow=".ai/assistant/flows/architecture-assistance.flow.md")
            write_json(catalog_path, catalog)
            write_json(target / ".ai/assistant/operation-index.json", {
                "schema_version": 1, "index_kind": "target-operation-index", "catalog": ".ai/assistant/operation-catalog.json",
                "aliases": {}, "operations": {operation["id"]: ["core-profile", operation["flow"], "read-only", "code-and-tests"]}})
            for mode in (*MODES, None):
                result = plan_target_context(ContextPlanRequest(target, "code-local", operation["id"], architecture_mode=mode))
                self.assertEqual(result["status"], "ready", result)
                self.assertIs(result["read_only"], True)
                self.assertEqual(result["request"]["architecture_mode"], mode)
                selected = {item["path"] for item in result["context_packet"]["selected_items"]}
                result_path = ".ai/assistant/templates/architecture-discussion-result.md"
                self.assertEqual(result_path in selected, mode in {None, "discuss", "compare", "document"})
                self.assertTrue(set(descriptor["required_context"]).issubset(selected))
            for malformed in ([], None, True, "wrong"):
                router["intent_overlays"] = malformed
                write_json(router_path, router)
                result = plan_target_context(ContextPlanRequest(target, "code-local", operation["id"], architecture_mode="explain"))
                self.assertNotEqual(result["status"], "ready")
                self.assertIsNone(result["context_packet"])
            router["intent_overlays"] = {"architecture-request": {"descriptor": intent}}
            write_json(router_path, router)
            write_text(target / ".ai/project/architecture/catalog.json", "stale changed evidence")
            result = plan_target_context(ContextPlanRequest(target, "code-local", operation["id"], architecture_mode="explain"))
            self.assertNotEqual(result["status"], "ready")
