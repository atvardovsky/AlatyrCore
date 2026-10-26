from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_context_planning import ROOT, TargetFixture, write_json, write_text
from context_planning import ContextPlanRequest, plan_target_context


ROUTER = ".ai/assistant/context-router.json"
PROFILE = ".ai/assistant/context/profiles/code-local.json"
OPERATION_INDEX = ".ai/assistant/operation-index.json"
OPERATION_CATALOG = ".ai/assistant/operation-catalog.json"
CAPABILITY_INDEX = ".ai/assistant/assistant-capabilities.json"
BAD_OBJECTS = (None, [], "object", 1, 1.5, True, False)
BAD_TEXT = (None, [], {}, 1, 1.5, True, False, "", " ")
BAD_LISTS = (None, {}, "item", 1, 1.5, True, False, [None], ["valid", {}], [""])


class MalformedContextPlanningTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.target = Path(directory.name).resolve() / "target"
        self.target.mkdir()
        self.fixture = TargetFixture(self.target)
        self.fixture.build()
        router = self.load(ROUTER)
        router["schema_version"] = 13
        router["context_budgets"]["profile_default"]["max_total_characters"] = 60000
        write_json(self.target / ROUTER, router)

    def load(self, artifact: str) -> dict:
        return json.loads((self.target / artifact).read_text(encoding="utf-8"))

    def request(self, **overrides: object) -> ContextPlanRequest:
        values = {
            "target": self.target,
            "profile": "code-local",
            "operation": "product change",
        }
        values.update(overrides)
        return ContextPlanRequest(**values)

    def assert_blocked(self, plan: dict, artifact: str, field: str) -> None:
        self.assertEqual(plan["status"], "blocked", plan)
        self.assertIsNone(plan["context_packet"])
        self.assertTrue(plan["read_only"])
        error = plan["errors"][0]
        self.assertEqual(error["details"]["artifact"], artifact, error)
        self.assertEqual(error["details"]["field"], field, error)

    def assert_api_and_cli_blocked(self, artifact: str, field: str) -> None:
        before = {path.relative_to(self.target).as_posix(): path.read_bytes()
                  for path in self.target.rglob("*") if path.is_file()}
        api = None
        with self.subTest(surface="API"):
            api = plan_target_context(self.request())
            self.assert_blocked(api, artifact, field)
        with self.subTest(surface="CLI"):
            result = subprocess.run(
                [
                    sys.executable, "-B", str(ROOT / "tools/plan_target_context.py"),
                    "--target", str(self.target), "--profile", "code-local",
                    "--operation", "product change",
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(result.stderr, "")
            cli = json.loads(result.stdout)
            self.assert_blocked(cli, artifact, field)
            if api is not None:
                self.assertEqual(cli, api)
        after = {path.relative_to(self.target).as_posix(): path.read_bytes()
                 for path in self.target.rglob("*") if path.is_file()}
        self.assertEqual(after, before)

    def check_reported_mutations(self, artifact: str, keys: tuple, field: str) -> None:
        original = self.load(artifact)
        malformed_list = [None] if keys[-1] == "allowed_actions" else []
        mutations = (
            ("null", None), ("bool-false", False), ("bool-true", True),
            ("number", 1), ("fractional-number", 1.5), ("list", malformed_list),
            ("object", {}), ("unknown-string", "unknown-operation"),
        )
        for shape, value in mutations:
            with self.subTest(shape=shape):
                data = json.loads(json.dumps(original))
                parent = data
                for key in keys[:-1]:
                    parent = parent[key]
                parent[keys[-1]] = value
                write_json(self.target / artifact, data)
                expected_field = field + "[0]" if shape == "list" and malformed_list else field
                if shape == "object" and field == "context_budgets":
                    expected_field += ".profile_default"
                self.assert_api_and_cli_blocked(artifact, expected_field)
        write_json(self.target / artifact, original)

    def check_shapes(self, artifact: str, keys: tuple, values: tuple) -> None:
        original = (self.target / artifact).read_bytes()
        field = ""
        for key in keys:
            field += f"[{key}]" if isinstance(key, int) else ("." if field else "") + key
        for value in values:
            with self.subTest(artifact=artifact, field=field, value=value):
                data = json.loads(original)
                parent = data
                for key in keys[:-1]:
                    parent = parent[key]
                parent[keys[-1]] = value
                write_json(self.target / artifact, data)
                self.fixture.refresh_catalogs()
                result = plan_target_context(self.request())
                expected_field = field
                string_list = keys[-1] in {
                    "allowed_actions", "context_profiles", "operation_candidates",
                    "required_context", "preload_terms", "product-change",
                }
                if isinstance(value, list) and value and string_list:
                    invalid = next((i for i, item in enumerate(value)
                                    if not isinstance(item, str) or not item.strip()), None)
                    if invalid is not None:
                        expected_field += f"[{invalid}]"
                self.assert_blocked(result, artifact, expected_field)
        write_json(self.target / artifact, json.loads(original))
        self.fixture.refresh_catalogs()

    def test_profile_index_scalar_is_blocked(self) -> None:
        self.check_reported_mutations(ROUTER, ("profile_index",), "profile_index")

    def test_operation_alias_list_is_blocked(self) -> None:
        self.check_reported_mutations(
            OPERATION_INDEX, ("aliases", "product change"), "aliases.product change"
        )

    def test_operation_actions_null_is_blocked(self) -> None:
        self.check_reported_mutations(
            OPERATION_CATALOG, ("operations", 0, "allowed_actions"),
            "operations[0].allowed_actions",
        )

    def test_context_budgets_null_is_blocked(self) -> None:
        self.check_reported_mutations(ROUTER, ("context_budgets",), "context_budgets")

    def test_valid_action_list_still_requires_fresh_index(self) -> None:
        catalog = self.load(OPERATION_CATALOG)
        catalog["operations"][0]["allowed_actions"] = []
        write_json(self.target / OPERATION_CATALOG, catalog)
        self.assert_api_and_cli_blocked(OPERATION_INDEX, "operations.product-change")

    def test_router_object_shapes(self) -> None:
        for keys in (
            ("profile_index",), ("profile_index", "code-local"),
            ("operation_routing",), ("recursive_context",),
            ("recursive_context", "contour_indexes"), ("context_budgets",),
            ("context_budgets", "profile_default"), ("semantic_codebook",),
            ("cache_aware_delivery",),
        ):
            self.check_shapes(ROUTER, keys, BAD_OBJECTS)

    def test_router_path_shapes_are_not_stringified(self) -> None:
        for keys in (
            ("profile_index", "code-local", "descriptor"),
            ("operation_routing", "index"), ("operation_routing", "catalog"),
            ("recursive_context", "contour_indexes", "framework"),
            ("semantic_codebook", "index"),
            ("cache_aware_delivery", "provider_capability_index"),
        ):
            self.check_shapes(ROUTER, keys, BAD_TEXT)

    def test_router_schema_shapes(self) -> None:
        self.check_shapes(ROUTER, ("schema_version",), (None, [], {}, "13", 13.0, True, False))

    def test_selected_artifact_identity_shapes(self) -> None:
        for artifact, field in (
            (ROUTER, "router_kind"), (PROFILE, "descriptor_kind"),
            (PROFILE, "profile"), (OPERATION_INDEX, "index_kind"),
            (OPERATION_INDEX, "catalog"), (OPERATION_CATALOG, "catalog_kind"),
        ):
            self.check_shapes(artifact, (field,), BAD_TEXT)

    def test_selected_alias_and_index_shapes(self) -> None:
        self.check_shapes(OPERATION_INDEX, ("aliases",), BAD_OBJECTS)
        self.check_shapes(OPERATION_INDEX, ("operations",), BAD_OBJECTS)
        self.check_shapes(OPERATION_INDEX, ("aliases", "product change"), BAD_TEXT)
        self.check_shapes(OPERATION_INDEX, ("operations", "product-change"), BAD_LISTS)

    def test_operation_catalog_does_not_drop_bad_records(self) -> None:
        self.check_shapes(OPERATION_CATALOG, ("operations",), (None, {}, "operation", 1, 1.5, True, False))
        self.check_shapes(OPERATION_CATALOG, ("operations", 0), BAD_OBJECTS)
        self.check_shapes(OPERATION_CATALOG, ("operations", 0, "id"), BAD_TEXT)

    def test_selected_operation_fields(self) -> None:
        for field in ("required_module", "flow"):
            self.check_shapes(OPERATION_CATALOG, ("operations", 0, field), BAD_TEXT)
        for field in ("allowed_actions", "context_profiles"):
            self.check_shapes(OPERATION_CATALOG, ("operations", 0, field), BAD_LISTS)

    def test_profile_list_shapes(self) -> None:
        for field in ("operation_candidates", "required_context"):
            self.check_shapes(PROFILE, (field,), BAD_LISTS)

    def test_configured_budget_shapes(self) -> None:
        for field in ("max_files", "max_total_words", "max_total_characters"):
            self.check_shapes(
                ROUTER, ("context_budgets", "profile_default", field),
                (None, [], {}, "5000", 5000.0, True, False, 0, -1),
            )

    def test_capability_index_shapes(self) -> None:
        self.check_shapes(CAPABILITY_INDEX, ("surfaces",), BAD_OBJECTS)
        self.check_shapes(CAPABILITY_INDEX, ("default_surface",), BAD_TEXT)
        surface = self.load(CAPABILITY_INDEX)["default_surface"]
        self.check_shapes(CAPABILITY_INDEX, ("surfaces", surface), BAD_TEXT)

    def test_absent_optional_provider_route_preserves_a_usable_plan(self) -> None:
        router = self.load(ROUTER)
        router["cache_aware_delivery"].pop("provider_capability_index")
        write_json(self.target / ROUTER, router)
        result = plan_target_context(self.request())
        self.assertEqual(result["status"], "ready", result)
        self.assertIsNotNone(result["context_packet"])
        # Absence is not malformed adoption; present null remains rejected above.
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/plan_target_context.py"),
            "--target", str(self.target), "--profile", "code-local", "--operation", "product change"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "ready")
        selected = plan_target_context(self.request(assistant_surface="codex"))
        self.assertNotEqual(selected["status"], "ready")
        self.assertIsNone(selected["context_packet"])

    def test_semantic_preload_shapes(self) -> None:
        self.check_shapes(ROUTER, ("semantic_codebook", "preload_terms"), BAD_LISTS)

    def test_conditional_dependency_shapes(self) -> None:
        self.check_shapes(PROFILE, ("conditional_context",), (None, {}, "path", 1, True))
        self.check_shapes(PROFILE, ("conditional_context", 0), BAD_OBJECTS)
        for field in ("path", "when"):
            self.check_shapes(PROFILE, ("conditional_context", 0, field), BAD_TEXT)

    def test_schema_one_artifacts_reject_boolean_and_numeric_aliases(self) -> None:
        for artifact in (PROFILE, OPERATION_INDEX, OPERATION_CATALOG):
            self.check_shapes(artifact, ("schema_version",), (None, [], {}, "1", 1.0, True, False))

    def test_artifact_paths_are_blocked_at_the_source_field(self) -> None:
        paths = ("../escape", "/absolute", "C:\\absolute", "nested/../../escape", "bad\x00path")
        self.check_shapes(ROUTER, ("operation_routing", "index"), paths)
        self.check_shapes(PROFILE, ("required_context", 0), paths)
        self.check_shapes(OPERATION_CATALOG, ("operations", 0, "flow"), paths)

    def test_top_level_non_object_artifacts_are_blocked_in_api_and_cli(self) -> None:
        for artifact in (ROUTER, PROFILE, OPERATION_INDEX, OPERATION_CATALOG):
            original = self.load(artifact)
            for value in (None, [], "object", 1, True):
                with self.subTest(artifact=artifact, value=value):
                    write_json(self.target / artifact, value)
                    self.assert_api_and_cli_blocked(artifact, "$")
            write_json(self.target / artifact, original)

    def test_alias_to_missing_operation_reports_stale_metadata(self) -> None:
        index = self.load(OPERATION_INDEX)
        index["aliases"]["product change"] = "absent"
        write_json(self.target / OPERATION_INDEX, index)
        self.assert_api_and_cli_blocked(OPERATION_INDEX, "aliases.product change")

    def test_request_shapes_are_structured_and_json_serializable(self) -> None:
        fields = {
            "profile": BAD_TEXT, "operation": BAD_TEXT,
            "changed_paths": (None, "src/a.py", {}, 1, True, [None], [[]]),
            "fact_ids": (None, "fact.id", {}, 1, True, [None], [[]]),
            "max_words": ([], {}, "10", 1.5, True, False, 0, -1),
            "max_characters": ([], {}, "10", 1.5, True, False, 0, -1),
            "assistant_surface": ([], {}, 1, 1.5, True, False, "", " "),
            "architecture_mode": ([], {}, 1, 1.5, True, False, "", " "),
            "document_warnings": (None, [], {}, 0, 1, "false"),
        }
        for field, values in fields.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    result = plan_target_context(self.request(**{field: value}))
                    self.assertEqual(result["status"], "invalid-request", result)
                    self.assertEqual(result["errors"][0]["details"]["artifact"], "request")
                    self.assertTrue(result["errors"][0]["details"]["field"].startswith(field))
                    json.dumps(result)

    def test_duplicate_operation_identity_is_blocked(self) -> None:
        catalog = self.load(OPERATION_CATALOG)
        catalog["operations"].append(dict(catalog["operations"][0]))
        write_json(self.target / OPERATION_CATALOG, catalog)
        self.assert_api_and_cli_blocked(OPERATION_CATALOG, "operations[1].id")

    def test_unselected_metadata_and_content_stay_lazy(self) -> None:
        router = self.load(ROUTER)
        router["profile_index"]["unselected"] = {"descriptor": "missing.json"}
        write_json(self.target / ROUTER, router)
        catalog = self.load(OPERATION_CATALOG)
        catalog["operations"].append({"id": "unselected", "allowed_actions": None})
        write_json(self.target / OPERATION_CATALOG, catalog)
        index = self.load(OPERATION_INDEX)
        index["aliases"]["unselected"] = []
        index["operations"]["unselected"] = None
        write_json(self.target / OPERATION_INDEX, index)
        write_text(self.fixture.project / "optional.md", "unselected stale content\n")
        with patch.object(Path, "read_bytes", autospec=True, side_effect=Path.read_bytes) as read:
            result = plan_target_context(self.request())
        self.assertEqual(result["status"], "ready", result)
        read_paths = {call.args[0].relative_to(self.target).as_posix() for call in read.call_args_list}
        self.assertNotIn(".ai/project/optional.md", read_paths)
        self.assertNotIn("missing.json", read_paths)
        self.assertEqual(read.call_count, 27)

    def test_valid_baseline_keeps_selected_paths_and_bounded_snapshot_reads(self) -> None:
        with patch.object(Path, "read_bytes", autospec=True, side_effect=Path.read_bytes) as read:
            result = plan_target_context(self.request())
        self.assertEqual(result["status"], "ready", result)
        # The old 23-byte-read count excluded five JSON text reads. Snapshot
        # binding uses byte reads throughout: 27 total, below the old 28 total.
        self.assertEqual(read.call_count, 27)
        self.assertEqual(
            {item["path"] for item in result["context_packet"]["selected_items"]},
            {
                ".ai/assistant/flows/product-change.flow.md", PROFILE,
                ".ai/framework/context.md", ".ai/framework/context-profiles.md",
                ".ai/project/billing.md",
            },
        )
        cli = subprocess.run(
            [sys.executable, "-B", str(ROOT / "tools/plan_target_context.py"),
             "--target", str(self.target), "--profile", "code-local",
             "--operation", "product change"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertEqual(cli.stderr, "")
        self.assertEqual(json.loads(cli.stdout), result)

    def test_selected_content_freshness_is_still_required(self) -> None:
        write_text(self.fixture.framework / "context.md", "stale selected content\n")
        result = plan_target_context(self.request())
        self.assertEqual(result["errors"][0]["code"], "CONTEXT_CATALOG_STALE")
        self.assertIsNone(result["context_packet"])

    def test_configured_budget_boundaries(self) -> None:
        ready = plan_target_context(self.request())
        self.assertEqual(ready["status"], "ready", ready)
        packet = ready["context_packet"]
        required = {
            "max_files": len(packet["selected_items"]),
            "max_total_words": packet["budget"]["total_words"],
            "max_total_characters": packet["budget"]["total_characters"],
        }
        original = self.load(ROUTER)
        for field, bound in required.items():
            for offset in (-1, 0, 1):
                with self.subTest(field=field, offset=offset):
                    router = json.loads(json.dumps(original))
                    router["context_budgets"]["profile_default"][field] = bound + offset
                    write_json(self.target / ROUTER, router)
                    result = plan_target_context(self.request())
                    self.assertEqual(result["status"], "blocked" if offset < 0 else "ready", result)
        write_json(self.target / ROUTER, original)

    def test_unexpected_errors_are_not_suppressed(self) -> None:
        with patch("context_planning._load_router", side_effect=RuntimeError("sentinel")):
            with self.assertRaisesRegex(RuntimeError, "sentinel"):
                plan_target_context(self.request())


if __name__ == "__main__":
    unittest.main()
