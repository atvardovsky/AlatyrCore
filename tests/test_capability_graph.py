from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from capability_catalog import (  # noqa: E402
    dependency_closure,
    load_modules,
    removable_target_files,
    shared_surface_merge_requirement,
    target_files,
)
from target_adapter_validation.modules import (  # noqa: E402
    CAPABILITY_ROUTES,
    CapabilityRouteKind,
    registry_contract_errors,
)


class CapabilityGraphTests(unittest.TestCase):
    def test_validation_routes_cover_the_complete_capability_catalog(self) -> None:
        self.assertEqual(set(CAPABILITY_ROUTES), set(load_modules()))
        self.assertEqual(registry_contract_errors(), [])
        self.assertEqual(
            {route.kind for route in CAPABILITY_ROUTES.values()},
            set(CapabilityRouteKind),
        )

    def test_returns_transitive_dependency_closure(self) -> None:
        modules = {
            "base": {"requires": []},
            "middle": {"requires": ["base"]},
            "top": {"requires": ["middle"]},
        }

        self.assertEqual(dependency_closure(["top"], modules), {"base", "middle", "top"})

    def test_rejects_dependency_cycle(self) -> None:
        modules = {
            "first": {"requires": ["second"]},
            "second": {"requires": ["first"]},
        }

        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            dependency_closure(["first"], modules)

    def test_shared_target_file_remains_when_one_producer_is_disabled(self) -> None:
        modules = {
            "diagrams": {
                "requires": [],
                "target_files": [".ai/shared.json", ".ai/diagrams.md"],
            },
            "bridges": {
                "requires": [],
                "target_files": [".ai/shared.json", ".ai/bridges.md"],
            },
        }
        surfaces = {
            ".ai/shared.json": {
                "producers": ["diagrams", "bridges"],
                "preserve_on_disable": True,
            }
        }

        self.assertEqual(
            target_files({"bridges"}, modules),
            {Path(".ai/shared.json"), Path(".ai/bridges.md")},
        )
        self.assertEqual(
            removable_target_files(
                {"diagrams", "bridges"}, {"bridges"}, modules, surfaces
            ),
            {Path(".ai/diagrams.md")},
        )

    def test_preserved_shared_target_file_survives_final_disable(self) -> None:
        modules = {
            "first": {
                "requires": [],
                "target_files": [".ai/shared.json", ".ai/first.md"],
            },
            "second": {
                "requires": [],
                "target_files": [".ai/shared.json", ".ai/second.md"],
            },
        }
        surfaces = {
            ".ai/shared.json": {
                "producers": ["first", "second"],
                "preserve_on_disable": True,
            }
        }

        self.assertEqual(
            removable_target_files({"first", "second"}, set(), modules, surfaces),
            {Path(".ai/first.md"), Path(".ai/second.md")},
        )

    def test_generated_shared_target_file_can_be_pruned_after_final_disable(self) -> None:
        modules = {
            "first": {"requires": [], "target_files": [".ai/generated.json"]},
            "second": {"requires": [], "target_files": [".ai/generated.json"]},
        }
        surfaces = {
            ".ai/generated.json": {
                "producers": ["first", "second"],
                "preserve_on_disable": False,
            }
        }

        self.assertEqual(
            removable_target_files({"first", "second"}, set(), modules, surfaces),
            {Path(".ai/generated.json")},
        )

    def test_existing_shared_surface_requires_its_declared_merge_strategy(self) -> None:
        surfaces = {
            ".ai/shared.json": {
                "merge_strategy": "record-merge-by-assistant-id",
            }
        }

        self.assertEqual(
            shared_surface_merge_requirement(".ai/shared.json", surfaces),
            "record-merge-by-assistant-id",
        )
        self.assertIsNone(
            shared_surface_merge_requirement(".ai/not-shared.json", surfaces)
        )

    def test_load_modules_requires_module_kind(self) -> None:
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capabilities.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "capability_kind": "alatyr-optional-module-catalog",
                        "surfaces": {},
                        "modules": {"feature": {"requires": []}},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "invalid kinds"):
                load_modules(path)


if __name__ == "__main__":
    unittest.main()
