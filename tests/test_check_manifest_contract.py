from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_all  # noqa: E402
from check_check_manifest import (  # noqa: E402
    SourcePathIndex,
    declaration_matches_source,
    direct_local_tool_dependencies,
    evidence_contract_routing_failures,
    tool_command_routing_failures,
)


def manifest_entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "id": "example",
        "command": ["tools/check_all.py"],
        "contract_inputs": ["tools/check_manifest.json"],
        "implementation_paths": ["tools/check_all.py"],
        "trigger_paths": ["tools/check_manifest.json", "tools/check_all.py"],
    }
    entry.update(overrides)
    return entry


class CheckManifestContractTests(unittest.TestCase):
    def load(self, entry: dict[str, object]) -> list[dict[str, object]]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "manifest_kind": "alatyr-source-checks",
                        "defaults": {
                            "profiles": ["full"],
                            "platforms": ["all"],
                            "write_scope": "none",
                            "depends_on": [],
                            "timeout_seconds": 30,
                            "resource_class": "standard",
                        },
                        "checks": [entry],
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(check_all, "MANIFEST", path):
                return check_all.load_manifest()

    def test_loads_complete_declarations(self) -> None:
        checks = self.load(manifest_entry())

        self.assertEqual(checks[0]["contract_inputs"], ["tools/check_manifest.json"])
        self.assertEqual(checks[0]["implementation_paths"], ["tools/check_all.py"])

    def test_rejects_legacy_owned_paths(self) -> None:
        with self.assertRaisesRegex(ValueError, "owned_paths is obsolete"):
            self.load(manifest_entry(owned_paths=["tools/check_all.py"]))

    def test_rejects_trigger_omitting_a_declared_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "trigger_paths must include"):
            self.load(manifest_entry(trigger_paths=["tools/check_all.py"]))

    def test_rejects_unsafe_input_declaration(self) -> None:
        with self.assertRaisesRegex(ValueError, "contract_inputs is invalid"):
            self.load(manifest_entry(contract_inputs=["../outside"]))

    def test_rejects_contract_implementation_overlap(self) -> None:
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.load(
                manifest_entry(
                    contract_inputs=["tools/check_all.py"],
                    trigger_paths=["tools/check_all.py"],
                )
            )

    def test_detects_direct_local_tool_imports(self) -> None:
        dependencies = direct_local_tool_dependencies("tools/check_check_manifest.py")

        self.assertEqual(
            dependencies,
            {
                "tools/check_all.py",
                "tools/evidence_contract.py",
                "tools/source_check_manifest.py",
            },
        )

    def test_declaration_matching_uses_source_path_index(self) -> None:
        index = SourcePathIndex.from_paths(
            [
                "framework/context-router.md",
                "framework/catalog/core/context-index.json",
                "tools/check_all.py",
            ]
        )

        self.assertTrue(declaration_matches_source("framework", index))
        self.assertTrue(declaration_matches_source("framework/**", index))
        self.assertTrue(
            declaration_matches_source("framework/catalog/**", index)
        )
        self.assertTrue(declaration_matches_source("tools/check_all.py", index))
        self.assertFalse(declaration_matches_source("docs/**", index))
        self.assertFalse(declaration_matches_source("tools/missing.py", index))

    def test_live_manifest_routes_every_evidence_contract_path(self) -> None:
        checks = check_all.load_manifest()

        self.assertEqual(evidence_contract_routing_failures(checks), [])

    def test_tool_command_scripts_require_source_check_routes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            command_manifest = Path(directory) / "tools" / "tool_commands.json"
            command_manifest.parent.mkdir()
            command_manifest.write_text(
                json.dumps(
                    {
                        "commands": [
                            {
                                "name": "example",
                                "script": "unrouted_tool.py",
                                "purpose": "fixture",
                                "write_scope": "none",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "check_check_manifest.ROOT",
                Path(directory),
            ):
                failures = tool_command_routing_failures(
                    [manifest_entry(implementation_paths=["tools/check_all.py"])]
                )

        self.assertEqual(
            failures,
            [
                "tool command script lacks implementation owner: tools/unrouted_tool.py",
                "tool command script lacks trigger route: tools/unrouted_tool.py",
            ],
        )


if __name__ == "__main__":
    unittest.main()
