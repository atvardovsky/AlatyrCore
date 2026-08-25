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
    direct_local_tool_dependencies,
    evidence_contract_routing_failures,
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
            {"tools/check_all.py", "tools/evidence_contract.py"},
        )

    def test_live_manifest_routes_every_evidence_contract_path(self) -> None:
        checks = check_all.load_manifest()

        self.assertEqual(evidence_contract_routing_failures(checks), [])


if __name__ == "__main__":
    unittest.main()
