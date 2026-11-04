from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.contract_compatibility import (  # noqa: E402
    artifact_compatibility,
    contract_compatibility,
    minimum_index_version,
)


class ContractCompatibilityTests(unittest.TestCase):
    def test_every_catalog_artifact_has_freshness_and_routing_coverage(self):
        from render_target_contract_compatibility import input_coverage_failures
        from source_check_manifest import load_manifest
        from target_adapter_validation.contract_compatibility import load_contract_compatibility
        catalog = load_contract_compatibility()
        check = next(c for c in load_manifest() if c["id"] == "target-contract-compatibility")
        self.assertEqual(input_coverage_failures(catalog, check), [])
        broken = {**check, "contract_inputs": [], "trigger_paths": [], "dependency_trigger_mode": "none"}
        failures = input_coverage_failures(catalog, broken)
        self.assertTrue(any("input coverage" in value for value in failures))
        self.assertTrue(any("routing coverage" in value for value in failures))

    def test_current_versions_are_supported(self) -> None:
        for contract_id in [
            "debug-mode",
            "engineering-evidence",
            "project-knowledge",
        ]:
            contract = contract_compatibility(contract_id)
            for artifact_id in contract["artifacts"]:
                artifact = artifact_compatibility(contract_id, artifact_id)
                self.assertIn(artifact["current"], artifact["supported"])

    def test_record_index_compatibility_is_centralized(self) -> None:
        self.assertEqual(minimum_index_version("engineering-evidence", 3), 4)
        self.assertEqual(minimum_index_version("debug-mode", 5), 5)
        self.assertIsNone(minimum_index_version("debug-mode", 99))


if __name__ == "__main__":
    unittest.main()
