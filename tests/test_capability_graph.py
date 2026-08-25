from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from capability_catalog import (  # noqa: E402
    dependency_closure,
    removable_target_files,
    shared_surface_merge_requirement,
    target_files,
)


class CapabilityGraphTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
