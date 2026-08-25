from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from project_knowledge import select_project_knowledge  # noqa: E402


def entry(
    knowledge_id: str,
    *,
    authority: str = "accepted",
    freshness: str = "current",
    areas: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "knowledge_id": knowledge_id,
        "guidance_kind": "reviewed-knowledge",
        "summary": f"Knowledge {knowledge_id}",
        "fact_ids": [f"fact.{knowledge_id}"],
        "authority": {
            "state": authority,
            "canonical_owner": "docs/architecture.md",
        },
        "freshness": {"state": freshness},
        "precedence": {"kind": "base-rule"},
        "applicability": {
            "task_profiles": ["code-local"],
            "project_areas": areas or ["orders"],
            "subsystems": ["order-processing"],
            "architecture_item_ids": ["ARCH-ORDERS"],
            "dependencies": [],
            "path_globs": ["src/orders/**"],
            "symbols": ["Order"],
            "contract_ids": ["contract.orders"],
            "issue_lineage": ["issue-1"],
        },
    }


class ProjectKnowledgeSelectionTests(unittest.TestCase):
    def test_profile_only_does_not_select_knowledge(self) -> None:
        selected = select_project_knowledge(
            [entry("one")],
            {"task_profile": "code-local", "project_areas": []},
            stage="initial",
            limit=2,
        )
        self.assertEqual(selected["constraints"], [])

    def test_refined_fact_and_path_select_current_constraint(self) -> None:
        selected = select_project_knowledge(
            [entry("one", areas=["other"])],
            {
                "task_profile": "code-local",
                "project_areas": [],
                "fact_ids": ["fact.one"],
                "paths": ["src/orders/Order.php"],
            },
            stage="refined",
            limit=2,
        )
        self.assertEqual(
            [item["knowledge_id"] for item in selected["constraints"]],
            ["one"],
        )

    def test_non_authoritative_and_historical_matches_are_omitted(self) -> None:
        selected = select_project_knowledge(
            [
                entry("observed", authority="observed"),
                entry("historical", freshness="historical"),
            ],
            {"task_profile": "code-local", "project_areas": ["orders"]},
            stage="initial",
            limit=2,
        )
        self.assertEqual(selected["constraints"], [])
        self.assertEqual(selected["warnings"], [])
        self.assertEqual(
            {item["knowledge_id"] for item in selected["omitted"]},
            {"observed", "historical"},
        )

    def test_contradiction_is_not_hidden_by_packet_limit(self) -> None:
        conflict = entry("conflict", freshness="contradicted")
        conflict["applicability"]["issue_lineage"] = []
        selected = select_project_knowledge(
            [
                entry("current", areas=["orders", "billing"]),
                conflict,
            ],
            {
                "task_profile": "code-local",
                "project_areas": ["orders", "billing"],
                "issue_lineage": ["issue-1"],
            },
            stage="initial",
            limit=1,
        )
        self.assertEqual(
            [item["knowledge_id"] for item in selected["blockers"]],
            ["conflict"],
        )
        self.assertTrue(selected["packet_limit_exceeded_for_blockers"])

    def test_revalidation_required_is_a_warning(self) -> None:
        selected = select_project_knowledge(
            [entry("stale", freshness="revalidation-required")],
            {"task_profile": "code-local", "project_areas": ["orders"]},
            stage="initial",
            limit=1,
        )
        self.assertEqual(
            [item["knowledge_id"] for item in selected["warnings"]],
            ["stale"],
        )

    def test_delivery_preserves_guidance_kind_and_precedence(self) -> None:
        selected = select_project_knowledge(
            [entry("one")],
            {"task_profile": "code-local", "project_areas": ["orders"]},
            stage="initial",
            limit=1,
        )
        self.assertEqual(selected["constraints"][0]["guidance_kind"], "reviewed-knowledge")
        self.assertEqual(selected["constraints"][0]["precedence_kind"], "base-rule")


if __name__ == "__main__":
    unittest.main()
