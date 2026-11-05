from __future__ import annotations

import sys
import unittest
import tempfile
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


class KnowledgeAdoptionTests(unittest.TestCase):
    def fixture(self, target):
        from check_project_knowledge import fixture
        return fixture(target)

    def findings(self, target, index):
        from check_project_knowledge import write_json
        from project_knowledge import validate_project_knowledge
        write_json(target / ".ai/project/knowledge/index.json", index)
        return [row for row in validate_project_knowledge(target, ROOT / "schemas") if row.level == "error"]

    def test_intake_and_known_gaps_do_not_require_reviewed_routes(self):
        from check_project_knowledge import write_json
        for retained in ("known-gap", "rejected-intake", "empty-shard"):
            with self.subTest(retained=retained), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)
                index, shard, promotion = self.fixture(target)
                self.assertEqual(self.findings(target, index), [])
                index["promotion_records"] = []
                index["shards"] = []
                index["coverage"] = {"areas": [], "fact_types": []}
                index["adoption"] = {"state": "enabled-empty", "reuse_evidence": []}
                if retained == "known-gap":
                    index["coverage"]["areas"] = [{"subject": "hydration", "status": "known-gap", "guidance_ids": [], "evidence": "Owner review", "gap": "Accepted guidance is not yet established"}]
                elif retained == "rejected-intake":
                    promotion["human_review"]["disposition"] = "rejected"
                    promotion["human_review"]["route_entry_ids"] = []
                    path = ".ai/project/knowledge/promotions/PROMO-RESULT-TRANSFORM-001.json"
                    write_json(target / path, promotion)
                    index["promotion_records"] = [{"promotion_id": promotion["promotion_id"], "status": "rejected", "path": path}]
                else:
                    shard["entries"] = []
                    path = ".ai/project/knowledge/routes/hydration.json"
                    write_json(target / path, shard)
                    index["shards"] = [{key: value for key, value in shard.items() if key not in {"schema_version", "shard_kind", "entries"}}]
                    index["shards"][0]["path"] = path
                self.assertEqual(self.findings(target, index), [])

    def test_empty_label_cannot_hide_reviewed_routes_or_claim_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            index, _, _ = self.fixture(target)
            index["adoption"] = {"state": "enabled-empty", "reuse_evidence": []}
            self.assertIn("PROJECT_KNOWLEDGE_ADOPTION_STATE", {row.code for row in self.findings(target, index)})
            index["promotion_records"], index["shards"] = [], []
            index["coverage"] = {"areas": [], "fact_types": []}
            index["adoption"]["reuse_evidence"] = ["operation:later-task"]
            self.assertIn("PROJECT_KNOWLEDGE_ADOPTION_STATE", {row.code for row in self.findings(target, index)})

    def test_retained_coverage_is_still_validated_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            index, _, _ = self.fixture(target)
            index["promotion_records"], index["shards"] = [], []
            index["adoption"] = {"state": "enabled-empty", "reuse_evidence": []}
            failures = self.findings(target, index)
            self.assertIn("PROJECT_GUIDANCE_COVERAGE_REFERENCE", {row.code for row in failures})


if __name__ == "__main__":
    unittest.main()
