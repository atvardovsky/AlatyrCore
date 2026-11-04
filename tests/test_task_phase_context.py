from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from context_planning import ContextPlanRequest, plan_target_context
from task_phase_context import select_phase_context
from tests.test_context_planning import TargetFixture, catalog_entry, write_json, write_text


class TaskPhaseContextTests(unittest.TestCase):
    def test_phase_metadata_cannot_weaken_or_redefine_prerequisites(self):
        from task_phase_context import PHASE_REQUIREMENTS
        for overlay, phases in PHASE_REQUIREMENTS.items():
            path = self.root / f".ai/assistant/context/task-scales/{overlay}.json"
            original = json.loads(path.read_text())
            for phase in phases:
                for field in ("requires_instance", "requires_role"):
                    mutant = copy.deepcopy(original)
                    mutant["phase_context"][phase][field] = not mutant["phase_context"][phase][field]
                    write_json(path, mutant)
                    self.refresh()
                    request = replace(self.request, overlay_phases=(overlay + ":" + phase,),
                        phase_instances=(".ai/assistant/operations/current.md",),
                        worker_role="explorer" if overlay == "delegated-execution" and phase == "dispatch" else None)
                    result = plan_target_context(request)
                    self.assertNotEqual(result["status"], "ready", (overlay, phase, field))
                    self.assertIn("prerequisites", result["errors"][0]["message"])
            mutant = copy.deepcopy(original)
            mutant["phase_context"]["unsupported"] = next(iter(original["phase_context"].values()))
            write_json(path, mutant)
            self.refresh()
            result = plan_target_context(replace(self.request, overlay_phases=(overlay + ":unsupported",)))
            self.assertNotEqual(result["status"], "ready")
            write_json(path, original)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.fixture = TargetFixture(self.root)
        self.fixture.build()
        self.router_path = self.root / ".ai/assistant/context-router.json"
        router = json.loads(self.router_path.read_text())
        router["task_scale_overlays"] = {}
        self.extra = []
        for name in ("large-or-resumable", "delegated-execution"):
            path = f".ai/assistant/context/task-scales/{name}.json"
            router["task_scale_overlays"][name] = {"descriptor": path}
            document = json.loads((ROOT / "templates/target" / path).read_text())
            for variant in document["phase_context"].values():
                variant["required_context"] = [".ai/framework/context.md"]
            document["phase_context"].get("create", {})["required_context"] = [".ai/framework/context.md", ".ai/assistant/templates/create.md"]
            write_json(self.root / path, document)
            self.extra.append(path)
        for path in (".ai/assistant/templates/create.md", ".ai/assistant/operations/current.md",
                     ".ai/assistant/workers/roles/explorer.md", ".ai/assistant/workers/roles/other.md"):
            write_text(self.root / path, "bounded fixture source " + path)
            self.extra.append(path)
        write_json(self.router_path, router)
        self.roles = {"schema_version": 2, "catalog_kind": "target-worker-role-catalog", "roles": [{"id": "explorer", "state": "enabled", "prompt": ".ai/assistant/workers/roles/explorer.md",
            "action_ceiling": "read-only", "write_mode": "none", "max_files": 5, "max_context_words": 1000},
            {"id": "other", "state": "unresolved", "prompt": ".ai/assistant/workers/roles/other.md"}]}
        self.role_path = self.root / ".ai/assistant/workers/role-catalog.json"
        write_json(self.role_path, self.roles)
        self.refresh()
        self.request = ContextPlanRequest(self.root, "code-local", "product-change")

    def refresh(self):
        self.fixture.refresh_catalogs()
        path = self.root / ".ai/assistant/context-index.json"
        catalog = json.loads(path.read_text())
        catalog["entries"].extend(catalog_entry(self.root / ".ai/assistant", "phase." + str(i),
            path.removeprefix(".ai/assistant/")) for i, path in enumerate(self.extra))
        write_json(path, catalog)

    def paths(self, result):
        self.assertEqual(result["status"], "ready", result)
        return {item["path"] for item in result["context_packet"]["selected_items"]}

    def test_legacy_request_does_not_call_new_resolver_or_change_shape(self):
        with patch("task_phase_context.select_phase_context", side_effect=AssertionError("must stay lazy")):
            one = plan_target_context(self.request)
            two = plan_target_context(replace(self.request, overlay_phases=(), phase_instances=(), worker_role=None))
        self.assertEqual(one, two)
        self.assertNotIn("phase_context", one)

    def test_create_and_resume_retain_base_owners_but_only_create_loads_template(self):
        create = plan_target_context(replace(self.request, overlay_phases=("large-or-resumable:create",)))
        resume = plan_target_context(replace(self.request, overlay_phases=("large-or-resumable:resume",),
            phase_instances=(".ai/assistant/operations/current.md",)))
        self.assertIn(".ai/assistant/templates/create.md", self.paths(create))
        paths = self.paths(resume)
        self.assertNotIn(".ai/assistant/templates/create.md", paths)
        self.assertIn(".ai/framework/context-profiles.md", paths)
        self.assertIn(".ai/assistant/operations/current.md", paths)

    def test_combined_dispatch_selects_one_enabled_role_and_binds_machine_catalog(self):
        request = replace(self.request, overlay_phases=("large-or-resumable:resume", "delegated-execution:dispatch"),
            phase_instances=(".ai/assistant/operations/current.md",), worker_role="explorer")
        result = plan_target_context(request)
        paths = self.paths(result)
        self.assertIn(".ai/assistant/workers/roles/explorer.md", paths)
        self.assertNotIn(".ai/assistant/workers/roles/other.md", paths)
        self.assertNotIn(".ai/assistant/workers/role-catalog.json", paths)
        bindings = result["routing_sources"]["phase_inputs"]
        self.assertIn(".ai/assistant/workers/role-catalog.json", bindings)
        from session_knowledge import bind_plans
        plan_path = self.root / "plan.json"
        write_json(plan_path, result)
        read = lambda path: (self.root / path).read_bytes()
        load = lambda path: json.loads(read(path))
        binding = bind_plans(["plan.json"], load, read)
        self.assertIn(".ai/assistant/workers/role-catalog.json", binding["plans"][0]["routing_paths"])
        for missing in bindings:
            mutated = copy.deepcopy(result)
            del mutated["routing_sources"]["phase_inputs"][missing]
            write_json(plan_path, mutated)
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, "phase routing"):
                bind_plans(["plan.json"], load, read)
        write_json(plan_path, result)
        for value in (None, [], True, 2, "invalid"):
            mutant = copy.deepcopy(result)
            mutant["routing_sources"] = value
            write_json(plan_path, mutant)
            with self.subTest(routing_sources=value), self.assertRaisesRegex(ValueError, "phase routing"):
                bind_plans(["plan.json"], load, read)
        write_json(plan_path, result)
        write_json(self.role_path, {**self.roles, "revision": 2})
        with self.assertRaisesRegex(ValueError, "phase routing"):
            bind_plans(["plan.json"], load, read)

    def test_combined_projection_is_immutable_and_repeatable(self):
        from session_knowledge import knowledge_projection
        result = plan_target_context(replace(self.request, overlay_phases=("large-or-resumable:create",)))
        self.paths(result)
        result["request"]["knowledge_request"] = "query.json"
        result["knowledge"] = {"routing_paths": ["query.json"], "selection": {"constraints": [], "warnings": []}}
        result["routing_sources"]["knowledge_inputs"] = {"query.json": "sha256:" + "a" * 64}
        before = copy.deepcopy(result)
        first = knowledge_projection("plan.json", result)
        self.assertEqual(result, before)
        self.assertEqual(first, knowledge_projection("plan.json", result))

    def test_role_catalog_envelope_is_required(self):
        for field, value in (("schema_version", False), ("schema_version", None), ("catalog_kind", "unrelated-document")):
            catalog = copy.deepcopy(self.roles)
            catalog[field] = value
            write_json(self.role_path, catalog)
            result = plan_target_context(replace(self.request, overlay_phases=("delegated-execution:dispatch",),
                phase_instances=(".ai/assistant/operations/current.md",), worker_role="explorer"))
            self.assertNotEqual(result["status"], "ready")
            self.assertIn("catalog envelope", result["errors"][0]["message"])

    def test_invalid_phases_instances_roles_and_json_types_fail_without_packet(self):
        cases = [dict(overlay_phases=("large-or-resumable:resume",)),
            dict(overlay_phases=("unknown:create",)), dict(overlay_phases=("large-or-resumable:unknown",)),
            dict(overlay_phases=("large-or-resumable:create", "large-or-resumable:resume")),
            dict(overlay_phases=({},)), dict(phase_instances=("missing",)), dict(worker_role={})]
        for values in cases:
            with self.subTest(values=values):
                result = plan_target_context(replace(self.request, **values))
                self.assertNotEqual(result["status"], "ready")
                self.assertIsNone(result["context_packet"])
        for field in ("action_ceiling", "write_mode", "max_files", "max_context_words", "state"):
            for value in ({}, [], None, True, "unknown"):
                roles = copy.deepcopy(self.roles)
                roles["roles"][0][field] = value
                write_json(self.role_path, roles)
                result = plan_target_context(replace(self.request, overlay_phases=("delegated-execution:dispatch",),
                    phase_instances=(".ai/assistant/operations/current.md",), worker_role="explorer"))
                self.assertNotEqual(result["status"], "ready", (field, value))

    def test_phase_context_uses_canonical_budget_boundaries(self):
        request = replace(self.request, overlay_phases=("large-or-resumable:create",))
        ready = plan_target_context(request)
        words = ready["context_packet"]["budget"]["total_words"]
        for delta in (-1, 0, 1):
            result = plan_target_context(replace(request, max_words=words + delta))
            self.assertEqual(result["status"] == "ready", delta >= 0, result)

    def test_combined_context_character_and_file_boundaries(self):
        request = replace(self.request, overlay_phases=("large-or-resumable:resume", "delegated-execution:dispatch"),
            phase_instances=(".ai/assistant/operations/current.md",), worker_role="explorer")
        ready = plan_target_context(request)
        paths = self.paths(ready)
        characters = ready["context_packet"]["budget"]["total_characters"]
        for delta in (-1, 0, 1):
            result = plan_target_context(replace(request, max_characters=characters + delta))
            self.assertEqual(result["status"] == "ready", delta >= 0, result)
        for delta in (-1, 0, 1):
            router = json.loads(self.router_path.read_text())
            router["context_budgets"]["profile_default"]["max_files"] = len(paths) + delta
            write_json(self.router_path, router)
            result = plan_target_context(request)
            self.assertEqual(result["status"] == "ready", delta >= 0, result)

    def test_shipped_resume_requirements_are_indexed_and_creation_template_is_omitted(self):
        path = ".ai/assistant/context/task-scales/large-or-resumable.json"
        descriptor = json.loads((ROOT / "templates/target" / path).read_text())
        write_json(self.root / path, descriptor)
        required = descriptor["phase_context"]["resume"]["required_context"]
        for relpath in required:
            write_text(self.root / relpath, "canonical fixture evidence " + relpath)
        self.refresh()
        for contour in ("framework", "assistant"):
            base = self.root / ".ai" / contour
            catalog_path = base / "context-index.json"
            catalog = json.loads(catalog_path.read_text())
            existing = {entry["path"] for entry in catalog["entries"]}
            for index, relpath in enumerate(required):
                prefix = ".ai/" + contour + "/"
                if relpath.startswith(prefix) and relpath.removeprefix(prefix) not in existing:
                    catalog["entries"].append(catalog_entry(base, "real." + str(index), relpath.removeprefix(prefix)))
            write_json(catalog_path, catalog)
        result = plan_target_context(replace(self.request, overlay_phases=("large-or-resumable:resume",),
            phase_instances=(".ai/assistant/operations/current.md",)))
        paths = self.paths(result)
        self.assertTrue(set(required) <= paths)
        self.assertNotIn(".ai/assistant/templates/large-task-operation-packet.md", paths)

    def test_unindexed_phase_source_keeps_canonical_recovery_error(self):
        descriptor_path = self.root / ".ai/assistant/context/task-scales/large-or-resumable.json"
        descriptor = json.loads(descriptor_path.read_text())
        descriptor["phase_context"]["create"]["required_context"] = [".ai/assistant/not-indexed.md"]
        write_text(self.root / ".ai/assistant/not-indexed.md", "not indexed")
        write_json(descriptor_path, descriptor)
        self.refresh()
        result = plan_target_context(replace(self.request, overlay_phases=("large-or-resumable:create",)))
        self.assertNotEqual(result["errors"][0]["code"], "TASK_PHASE_CONTEXT_INVALID")
        self.assertNotEqual(result["status"], "ready")

    def test_public_cli_routes_resume_and_rejects_missing_instance(self):
        command = [sys.executable, "-B", str(ROOT / "tools/plan_target_context.py"), "--target", str(self.root),
            "--profile", "code-local", "--operation", "product-change", "--overlay-phase", "large-or-resumable:resume"]
        missing = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2, missing.stderr)
        valid = subprocess.run([*command, "--phase-instance", ".ai/assistant/operations/current.md"], capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)


if __name__ == "__main__":
    unittest.main()
