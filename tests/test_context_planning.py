from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from context_catalog import file_digest, word_count  # noqa: E402
from context_planning import ContextPlanRequest, plan_target_context  # noqa: E402
from impact_graph import build_reverse_index, load_impact_graph  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n").encode(
            "utf-8"
        )
    )


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value.encode("utf-8"))


def catalog_entry(
    root: Path,
    item_id: str,
    relpath: str,
    *,
    semantic_refs: list[str] | None = None,
    owner_refs: list[str] | None = None,
    rule_ids: list[str] | None = None,
) -> dict[str, object]:
    path = root / relpath
    return {
        "id": item_id,
        "kind": "content",
        "path": relpath,
        "summary": item_id,
        "selectors": {
            "path_terms": sorted(set(Path(relpath).stem.replace("_", "-").split("-"))),
            "rule_ids": rule_ids or [],
        },
        "load_when": ["selected by an exact test signal"],
        "semantic_refs": semantic_refs or [],
        "owner_refs": owner_refs or [],
        "estimated_words": word_count(path),
        "content_digest": file_digest(path),
    }


def write_catalog(
    root: Path, contour: str, entries: list[dict[str, object]]
) -> None:
    write_json(
        root / "context-index.json",
        {
            "schema_version": 1,
            "index_kind": "alatyr-context-index",
            "index_id": f"{contour}.root",
            "contour": contour,
            "title": f"{contour.title()} context",
            "summary": f"{contour.title()} test context",
            "max_depth": 4,
            "entries": entries,
        },
    )


class TargetFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.framework = root / ".ai/framework"
        self.project = root / ".ai/project"
        self.assistant = root / ".ai/assistant"

    def build(self) -> None:
        write_text(self.framework / "context.md", "bounded context policy\n")
        write_text(self.framework / "context-profiles.md", "canonical context owner\n")
        write_text(self.project / "billing.md", "billing adapter knowledge\n")
        write_text(self.project / "source-of-truth-registry.md", "billing facts registry\n")
        write_text(self.assistant / "flows/product-change.flow.md", "product change flow\n")
        write_text(self.root / "docs/billing.md", "SECRET-BILLING-OWNER accepted billing rule\n")
        write_text(self.root / "src/payment/retry.py", "SECRET-SOURCE retry = True\n")

        write_json(
            self.assistant / "context/profiles/code-local.json",
            {
                "schema_version": 1,
                "descriptor_kind": "target-context-profile",
                "profile": "code-local",
                "use_when": ["local code repair"],
                "operation_candidates": ["product-change"],
                "required_context": [
                    ".ai/framework/context.md",
                    ".ai/project/billing.md",
                ],
                "conditional_context": [],
                "expand_when": ["relationship changes"],
                "approval_gates": [],
                "validation": ["python -m unittest"],
                "final_evidence": ["validation"],
            },
        )
        write_json(
            self.assistant / "context/consistency-routing.json",
            {
                "schema_version": 1,
                "descriptor_kind": "target-consistency-routing",
                "required_context": [
                    ".ai/project/source-of-truth-registry.md",
                    ".ai/project/consistency-map.json",
                    ".ai/assistant/consistency-reverse-index.json",
                ],
                "lookup_order": ["changed paths", "accepted relationships"],
            },
        )
        write_json(
            self.assistant / "operation-catalog.json",
            {
                "schema_version": 1,
                "catalog_kind": "target-operation-catalog",
                "operations": [
                    {
                        "id": "product-change",
                        "title": "Product change",
                        "summary": "Change product behavior",
                        "use_when": ["product change"],
                        "context_profiles": ["code-local"],
                        "required_module": "core-profile",
                        "flow": ".ai/assistant/flows/product-change.flow.md",
                        "minimum_inputs": ["goal"],
                        "allowed_actions": ["read-only", "code-and-tests"],
                        "preview": "risk-gated",
                        "aliases": ["product change"],
                        "final_evidence": ["validation"],
                    }
                ],
            },
        )
        write_json(
            self.assistant / "operation-index.json",
            {
                "schema_version": 1,
                "index_kind": "target-operation-index",
                "catalog": ".ai/assistant/operation-catalog.json",
                "aliases": {"product change": "product-change"},
                "operations": {
                    "product-change": [
                        "core-profile",
                        ".ai/assistant/flows/product-change.flow.md",
                        "read-only",
                        "code-and-tests",
                    ]
                },
            },
        )
        write_json(
            self.assistant / "assistant-capabilities.json",
            {
                "schema_version": 3,
                "capability_kind": "target-assistant-capability-index",
                "default_surface": "generic",
                "surfaces": {
                    "generic": ".ai/assistant/assistant-capabilities/generic.json"
                },
            },
        )
        write_json(
            self.assistant / "assistant-capabilities/generic.json",
            {
                "schema_version": 4,
                "capability_kind": "target-assistant-surface-capabilities",
                "assistant_surface": "generic",
                "context_caching": {
                    "route": "unknown",
                    "stable_prefix_ordering": True,
                    "context_window_reduction": False,
                },
            },
        )
        self._write_semantics()
        self._write_graph()
        self._write_router()
        self.refresh_catalogs()

    def _write_semantics(self) -> None:
        term = {
            "id": "alatyr:bounded-context-expansion@1",
            "version": 1,
            "definition": "Load required owners and expand only for named boundaries.",
            "owner_rule_id": "ALATYR-CONTEXT-001",
            "canonical_owner": "context-profiles.md",
            "scope": "context routing",
            "non_meanings": ["omit required context"],
            "depends_on": [],
            "replaced_by": None,
        }
        write_json(
            self.framework / "semantics/core.json",
            {
                "schema_version": 1,
                "record_kind": "alatyr-semantic-codebook-shard",
                "shard_id": "core",
                "preload": True,
                "selectors": {"task_profiles": ["code-local"]},
                "terms": [term],
            },
        )
        write_json(
            self.framework / "semantics/index.json",
            {
                "schema_version": 1,
                "index_kind": "alatyr-semantic-codebook-index",
                "codebook_id": "test",
                "shards": [
                    {
                        "id": "core",
                        "path": "core.json",
                        "preload": True,
                        "selectors": {"task_profiles": ["code-local"]},
                        "term_ids": ["alatyr:bounded-context-expansion@1"],
                        "content_digest": file_digest(
                            self.framework / "semantics/core.json"
                        ),
                    }
                ],
            },
        )

    def _write_graph(self) -> None:
        write_json(
            self.project / "consistency/areas/billing.json",
            {
                "schema_version": 1,
                "shard_kind": "target-consistency-map-shard",
                "id": "billing",
                "project_area": "billing",
                "nodes": [
                    {
                        "id": "fact.payment-retry",
                        "fact_type": "business-rule",
                        "level": "fact",
                        "project_area": "billing",
                        "canonical_owner": "docs/billing.md",
                        "coverage_state": "isolated-verified",
                        "bindings": [
                            {
                                "id": "binding.payment-source",
                                "surface_kind": "code",
                                "path": "src/payment/**",
                                "selector_kind": "glob",
                                "selector": "whole-file",
                                "authority": "derived",
                                "context_ids": ["project.billing"],
                            }
                        ],
                        "relationships": [],
                    }
                ],
            },
        )
        write_json(
            self.project / "consistency-map.json",
            {
                "schema_version": 3,
                "map_kind": "target-consistency-map",
                "impact_policy": {"max_depth": 4, "max_nodes": 20},
                "node_shards": [
                    {
                        "id": "billing",
                        "path": ".ai/project/consistency/areas/billing.json",
                    }
                ],
                "reverse_index": ".ai/assistant/consistency-reverse-index.json",
            },
        )
        graph = load_impact_graph(self.root)
        write_json(
            self.assistant / "consistency-reverse-index.json",
            build_reverse_index(graph),
        )

    def _write_router(self) -> None:
        write_json(
            self.assistant / "context-router.json",
            {
                "schema_version": 10,
                "router_kind": "target-context-router",
                "context_budgets": {
                    "profile_default": {"max_files": 20, "max_total_words": 5000}
                },
                "recursive_context": {
                    "contour_indexes": {
                        "framework": ".ai/framework/context-index.json",
                        "project": ".ai/project/context-index.json",
                        "assistant": ".ai/assistant/context-index.json",
                    }
                },
                "semantic_codebook": {
                    "index": ".ai/framework/semantics/index.json",
                    "preload_terms": ["alatyr:bounded-context-expansion@1"],
                },
                "cache_aware_delivery": {
                    "provider_capability_index": ".ai/assistant/assistant-capabilities.json"
                },
                "profile_index": {
                    "code-local": {
                        "use_when": ["local code repair"],
                        "descriptor": ".ai/assistant/context/profiles/code-local.json",
                    }
                },
                "operation_routing": {
                    "index": ".ai/assistant/operation-index.json",
                    "catalog": ".ai/assistant/operation-catalog.json",
                },
                "consistency_routing": {
                    "descriptor": ".ai/assistant/context/consistency-routing.json"
                },
            },
        )

    def refresh_catalogs(self) -> None:
        term = ["alatyr:bounded-context-expansion@1"]
        write_catalog(
            self.framework,
            "framework",
            [
                catalog_entry(
                    self.framework,
                    "framework.context",
                    "context.md",
                    semantic_refs=term,
                    owner_refs=["ALATYR-CONTEXT-001"],
                ),
                catalog_entry(
                    self.framework,
                    "framework.context-owner",
                    "context-profiles.md",
                    semantic_refs=term,
                    rule_ids=["ALATYR-CONTEXT-001"],
                ),
            ],
        )
        write_catalog(
            self.project,
            "project",
            [
                catalog_entry(
                    self.project,
                    "project.billing",
                    "billing.md",
                    semantic_refs=term,
                    owner_refs=["ALATYR-CONTEXT-001"],
                ),
                catalog_entry(
                    self.project,
                    "project.registry",
                    "source-of-truth-registry.md",
                    semantic_refs=term,
                ),
                catalog_entry(
                    self.project,
                    "project.consistency-map",
                    "consistency-map.json",
                    semantic_refs=term,
                ),
                catalog_entry(
                    self.project,
                    "project.consistency-billing",
                    "consistency/areas/billing.json",
                    semantic_refs=term,
                ),
            ],
        )
        write_catalog(
            self.assistant,
            "assistant",
            [
                catalog_entry(
                    self.assistant,
                    "assistant.profile.code-local",
                    "context/profiles/code-local.json",
                    semantic_refs=term,
                ),
                catalog_entry(
                    self.assistant,
                    "assistant.consistency-routing",
                    "context/consistency-routing.json",
                    semantic_refs=term,
                ),
                catalog_entry(
                    self.assistant,
                    "assistant.flow.product-change",
                    "flows/product-change.flow.md",
                    semantic_refs=term,
                ),
                catalog_entry(
                    self.assistant,
                    "assistant.consistency-reverse-index",
                    "consistency-reverse-index.json",
                    semantic_refs=term,
                ),
            ],
        )


class ContextPlanningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name) / "target"
        self.target.mkdir()
        self.fixture = TargetFixture(self.target)
        self.fixture.build()

    def request(self, **overrides: object) -> ContextPlanRequest:
        values: dict[str, object] = {
            "target": self.target,
            "profile": "code-local",
            "operation": "product change",
            "changed_paths": ("src/payment/retry.py",),
            "fact_ids": (),
        }
        values.update(overrides)
        return ContextPlanRequest(**values)  # type: ignore[arg-type]

    def test_ready_plan_is_deterministic_and_contains_no_file_contents(self) -> None:
        before = {
            path.relative_to(self.target).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in self.target.rglob("*")
            if path.is_file()
        }
        first = plan_target_context(self.request())
        second = plan_target_context(self.request())
        after = {
            path.relative_to(self.target).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in self.target.rglob("*")
            if path.is_file()
        }

        self.assertEqual(first, second)
        self.assertEqual(before, after)
        self.assertEqual(first["status"], "ready")
        self.assertEqual(first["request"]["operation"], "product-change")
        self.assertEqual(
            first["impact"]["selected_node_ids"], ["fact.payment-retry"]
        )
        paths = {
            item["path"] for item in first["context_packet"]["selected_items"]
        }
        self.assertIn("docs/billing.md", paths)
        self.assertIn("src/payment/retry.py", paths)
        projection = dict(first["context_packet"])
        projection_digest = projection.pop("projection_digest")
        expected_projection_digest = "sha256:" + hashlib.sha256(
            json.dumps(
                projection,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(projection_digest, expected_projection_digest)
        self.assertRegex(
            first["context_packet"]["source_packet"]["content_bound_digest"],
            r"^sha256:[0-9a-f]{64}$",
        )
        rendered = json.dumps(first, sort_keys=True)
        self.assertNotIn("SECRET-BILLING-OWNER", rendered)
        self.assertNotIn("SECRET-SOURCE", rendered)
        self.assertNotIn("definition\"", rendered)

    def test_windows_style_changed_path_normalizes_deterministically(self) -> None:
        result = plan_target_context(
            self.request(changed_paths=(r"src\payment\retry.py",))
        )

        self.assertEqual(result["status"], "ready")
        self.assertEqual(
            result["request"]["changed_paths"], ["src/payment/retry.py"]
        )

    def test_unknown_path_blocks_instead_of_omitting_context(self) -> None:
        result = plan_target_context(
            self.request(changed_paths=("src/new/unmapped.py",))
        )

        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["upgrade_required"])
        self.assertEqual(result["errors"][0]["code"], "CHANGED_PATH_UNMAPPED")
        self.assertIsNone(result["context_packet"])

    def test_unknown_profile_and_operation_are_structured_invalid_requests(self) -> None:
        profile = plan_target_context(self.request(profile="missing"))
        operation = plan_target_context(self.request(operation="missing"))

        self.assertEqual(profile["status"], "invalid-request")
        self.assertEqual(profile["errors"][0]["code"], "UNKNOWN_CONTEXT_PROFILE")
        self.assertEqual(operation["status"], "invalid-request")
        self.assertEqual(operation["errors"][0]["code"], "UNKNOWN_OPERATION")

    def test_stale_catalog_returns_upgrade_evidence(self) -> None:
        write_text(self.fixture.project / "billing.md", "changed without reindex\n")

        result = plan_target_context(self.request())

        self.assertEqual(result["status"], "unavailable")
        self.assertTrue(result["upgrade_required"])
        self.assertEqual(result["errors"][0]["code"], "CONTEXT_CATALOG_STALE")

    def test_selected_profile_placeholder_returns_upgrade_evidence(self) -> None:
        profile = self.fixture.assistant / "context/profiles/code-local.json"
        value = json.loads(profile.read_text(encoding="utf-8"))
        value["validation"] = ["{TARGET_VALIDATION}"]
        write_json(profile, value)

        result = plan_target_context(self.request())

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(
            result["errors"][0]["code"], "ADAPTER_PLACEHOLDERS_UNRESOLVED"
        )

    def test_budget_overflow_blocks_without_truncating_required_context(self) -> None:
        result = plan_target_context(self.request(max_words=1))

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(
            result["errors"][0]["code"], "CONTEXT_WORD_BUDGET_EXCEEDED"
        )
        self.assertIsNone(result["context_packet"])

    def test_stale_reverse_index_is_rejected(self) -> None:
        reverse_path = self.fixture.assistant / "consistency-reverse-index.json"
        reverse = json.loads(reverse_path.read_text(encoding="utf-8"))
        reverse["exact_paths"] = {"unexpected.py": ["fact.payment-retry"]}
        write_json(reverse_path, reverse)
        self.fixture.refresh_catalogs()

        result = plan_target_context(self.request())

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(
            result["errors"][0]["code"], "CONSISTENCY_REVERSE_INDEX_STALE"
        )

    def test_incomplete_adapter_is_unavailable_and_unchanged(self) -> None:
        empty = Path(self.directory.name) / "empty"
        empty.mkdir()
        before = list(empty.iterdir())

        result = plan_target_context(
            ContextPlanRequest(empty, "code-local", "product-change")
        )

        self.assertEqual(result["status"], "unavailable")
        self.assertTrue(result["upgrade_required"])
        self.assertEqual(before, list(empty.iterdir()))

    def test_cli_writes_only_outside_target_and_rejects_target_output(self) -> None:
        command = [
            sys.executable,
            str(ROOT / "tools/alatyr.py"),
            "context-plan",
            "--target",
            str(self.target),
            "--profile",
            "code-local",
            "--operation",
            "product-change",
            "--changed-path",
            "src/payment/retry.py",
        ]
        output = Path(self.directory.name) / "plan.json"
        success = subprocess.run(
            [*command, "--output", str(output)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        blocked_path = self.target / "plan.json"
        blocked = subprocess.run(
            [*command, "--output", str(blocked_path)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertEqual(json.loads(output.read_text())["status"], "ready")
        self.assertEqual(blocked.returncode, 2)
        self.assertFalse(blocked_path.exists())
        self.assertEqual(json.loads(blocked.stdout)["errors"][0]["code"], "OUTPUT_INSIDE_TARGET")

    def test_absolute_and_parent_paths_are_rejected_cross_platform(self) -> None:
        for changed_path in ["../outside.py", r"C:\outside.py", "/outside.py"]:
            with self.subTest(changed_path=changed_path):
                result = plan_target_context(
                    self.request(changed_paths=(changed_path,))
                )
                self.assertEqual(result["status"], "invalid-request")
                self.assertEqual(
                    result["errors"][0]["code"], "INVALID_RELATIVE_PATH"
                )


if __name__ == "__main__":
    unittest.main()
