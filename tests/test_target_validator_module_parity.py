from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.ai_infrastructure import (  # noqa: E402
    AI_INFRASTRUCTURE_ITEM_TYPES,
    AI_INFRASTRUCTURE_ROUTES_V1,
)
from target_adapter_validation.team_collaboration import (  # noqa: E402
    TEAM_COLLABORATION_MODULE,
)
from target_adapter_validation.modules import (  # noqa: E402
    CAPABILITY_ROUTES,
    dispatch_capability_checks,
)
from target_validation_support import parse_manifest  # noqa: E402
from validate_target_adapter import AdapterValidatorConfig, Validator  # noqa: E402


def validator(target: Path) -> Validator:
    return Validator(
        target,
        framework_source=None,
        diff_ref=None,
        approval_records=[],
        enforce_approval_scope=False,
        change_packages=[],
        enforce_change_package=False,
        migration_diff=None,
        allow_placeholders=True,
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
        validation_phase="migration-staging",
    )


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def finding_snapshot(instance: Validator) -> list[tuple[str, str, str | None, str]]:
    return [
        (finding.level, finding.code, finding.path, finding.message)
        for finding in instance.findings
    ]


class TargetValidatorModuleParityTests(unittest.TestCase):
    def test_every_capability_route_dispatches_its_registered_checks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for module_id, route in CAPABILITY_ROUTES.items():
                instance = validator(target)

                dispatched = dispatch_capability_checks(
                    instance,
                    [module_id],
                    None,
                )

                self.assertEqual(dispatched, tuple(dict.fromkeys(route.checks)))

    def test_team_collaboration_real_module_dispatches_with_locked_finding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            write_json(target / ".ai/project/team-policy.json", {})
            instance = validator(target)

            TEAM_COLLABORATION_MODULE.validate(
                instance.capability_validation_context(), None
            )

            self.assertEqual(
                finding_snapshot(instance),
                [
                    (
                        "error",
                        "TEAM_OPERATING_MODEL_MISSING",
                        ".ai/project/team-operating-model.md",
                        "team work registry exists without its target-owned operating model",
                    )
                ],
            )

    def test_changed_scope_routes_module_and_declared_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            instance = validator(Path(directory))
            instance.validation_scope = "changed"
            instance.diff_ref = "HEAD"
            instance.capability_modules = {
                "project-vocabulary": {
                    "module_kind": "project-facing",
                    "target_files": [".ai/project/vocabulary/terms.json"],
                    "requires": ["support-generation"],
                },
                "support-generation": {
                    "module_kind": "assistant-infrastructure",
                    "target_files": [".ai/support-state.json"],
                    "requires": [],
                },
                "debug-mode": {
                    "module_kind": "assistant-infrastructure",
                    "target_files": [".ai/assistant/debug/session.json"],
                    "requires": [],
                },
            }
            with patch(
                "validate_target_adapter.git_changed_files",
                return_value=[".ai/project/vocabulary/terms.json"],
            ):
                selected = instance.changed_scope_modules(set(instance.capability_modules))

        self.assertEqual(selected, {"project-vocabulary", "support-generation"})

    def test_adapter_schema_31_requires_sharded_consistency_map(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            manifest_path = target / ".ai/alatyr.yaml"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text("schema_version: 31\n", encoding="utf-8")
            write_json(
                target / ".ai/project/consistency-map.json",
                {
                    "schema_version": 2,
                    "map_kind": "target-consistency-map",
                    "levels": ["fact", "contract", "area", "system", "adapter"],
                    "relationship_types": [
                        "implements",
                        "verifies",
                        "documents",
                        "visualizes",
                        "generates",
                        "constrains",
                        "depends-on",
                        "routes",
                    ],
                    "nodes": [],
                },
            )

            instance = validator(target)
            instance.check_consistency_map(parse_manifest(manifest_path))

            self.assertIn(
                "CONSISTENCY_MAP_SCHEMA_MIGRATION_REQUIRED",
                {finding.code for finding in instance.findings},
            )

    def test_consistency_map_preserves_locked_finding_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            write_json(
                target / ".ai/project/consistency-map.json",
                {
                    "schema_version": 1,
                    "map_kind": "target-consistency-map",
                    "levels": ["fact"],
                    "relationship_types": ["implements"],
                    "nodes": [],
                },
            )

            instance = validator(target)
            instance.check_consistency_map()

            self.assertEqual(
                finding_snapshot(instance),
                [
                    (
                        "warning",
                        "CONSISTENCY_MAP_SCHEMA_LEGACY",
                        ".ai/project/consistency-map.json",
                        "schema_version 1 should migrate to schema 2 registry-sync policy",
                    ),
                    (
                        "error",
                        "CONSISTENCY_MAP_REGISTRY",
                        ".ai/project/consistency-map.json",
                        "human_registry should point to the target source-of-truth registry",
                    ),
                    (
                        "error",
                        "CONSISTENCY_MAP_LEVELS",
                        ".ai/project/consistency-map.json",
                        "levels must match the portable consistency level order",
                    ),
                    (
                        "error",
                        "CONSISTENCY_MAP_RELATIONSHIPS",
                        ".ai/project/consistency-map.json",
                        "relationship_types must match the portable relationship set",
                    ),
                    (
                        "error",
                        "CONSISTENCY_MAP_IMPACT_POLICY",
                        ".ai/project/consistency-map.json",
                        "impact_policy must be an object",
                    ),
                    (
                        "error",
                        "CONSISTENCY_MAP_NODES",
                        ".ai/project/consistency-map.json",
                        "nodes must be a non-empty list",
                    ),
                ],
            )

    def test_ai_router_preserves_locked_finding_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            route = {
                field: ["read-only"] if field == "allowed_actions" else ["fixture"]
                for field in [
                    "use_when",
                    "required_context",
                    "expand_when",
                    "allowed_actions",
                    "approval_gates",
                    "validation",
                    "final_evidence",
                ]
            }
            write_json(
                target / ".ai/assistant/ai-infrastructure-router.json",
                {
                    "schema_version": 3,
                    "router_kind": "target-ai-infrastructure-router",
                    "routing_order": sorted(AI_INFRASTRUCTURE_ROUTES_V1),
                    "item_types": sorted(AI_INFRASTRUCTURE_ITEM_TYPES),
                    "routes": {
                        route_name: route
                        for route_name in AI_INFRASTRUCTURE_ROUTES_V1
                    },
                    "items": ["invalid-item"],
                },
            )

            instance = validator(target)
            instance.check_ai_infrastructure_router()

            self.assertEqual(
                finding_snapshot(instance),
                [
                    (
                        "error",
                        "AI_ROUTER_SCHEMA",
                        ".ai/assistant/ai-infrastructure-router.json",
                        "schema_version should be 1 or 2",
                    ),
                    (
                        "error",
                        "AI_ROUTER_ITEM_SHAPE",
                        ".ai/assistant/ai-infrastructure-router.json",
                        "items[0] must be an object",
                    ),
                ],
            )


if __name__ == "__main__":
    unittest.main()
