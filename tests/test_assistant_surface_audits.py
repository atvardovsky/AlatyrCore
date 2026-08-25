from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_assistant_surface_audits import validate_contracts  # noqa: E402


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


class AssistantSurfaceAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.surfaces = load("conformance/runs/assistant-surfaces.json")
        self.audits = load("conformance/assistant-surface-integration-audits.json")
        self.executors = load("conformance/executors/executor-capabilities.json")

    def validate(
        self, surfaces=None, audits=None, executors=None, capability_overrides=None
    ) -> list[str]:
        return validate_contracts(
            surfaces or self.surfaces,
            audits or self.audits,
            executors or self.executors,
            capability_overrides,
        )

    def test_live_contract_is_consistent(self) -> None:
        self.assertEqual([], self.validate())

    def test_runtime_execution_claim_is_rejected(self) -> None:
        audits = copy.deepcopy(self.audits)
        next(item for item in audits["audits"] if item["id"] == "cline")[
            "runtime_execution_claimed"
        ] = True
        self.assertTrue(
            any("must not claim runtime execution" in failure for failure in self.validate(audits=audits))
        )

    def test_archived_surface_cannot_claim_active_status(self) -> None:
        audits = copy.deepcopy(self.audits)
        next(item for item in audits["audits"] if item["id"] == "roo-code")[
            "status"
        ] = "static-contract-ready-runtime-unverified"
        self.assertTrue(
            any("wrong lifecycle status" in failure for failure in self.validate(audits=audits))
        )

    def test_opencode_variants_are_required(self) -> None:
        audits = copy.deepcopy(self.audits)
        next(item for item in audits["audits"] if item["id"] == "opencode").pop(
            "variant_loading"
        )
        self.assertTrue(
            any("both loading contracts" in failure for failure in self.validate(audits=audits))
        )

    def test_client_permissions_cannot_grant_alatyr_authorization(self) -> None:
        record = load(
            "templates/target/.ai/assistant/assistant-capabilities/junie.json"
        )
        record["tool_permissions"]["alatyr_authorization_separate"] = False
        self.assertTrue(
            any(
                "can grant Alatyr authorization" in failure
                for failure in self.validate(capability_overrides={"junie": record})
            )
        )


if __name__ == "__main__":
    unittest.main()
