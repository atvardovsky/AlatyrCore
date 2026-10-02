from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from suggest_project_knowledge import suggestions  # noqa: E402


class ProjectKnowledgeSuggestionTests(unittest.TestCase):
    def test_helper_supports_package_style_import(self) -> None:
        result = subprocess.run(
            [sys.executable, "-c", "from tools.suggest_project_knowledge import suggestions"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def write_target(
        self, target: Path, records: list[dict[str, Any]]
    ) -> tuple[Path, Path]:
        package_index = target / ".ai/assistant/change-packages/index.json"
        knowledge_index = target / ".ai/project/knowledge/index.json"
        package_index.parent.mkdir(parents=True)
        knowledge_index.parent.mkdir(parents=True)
        compact_records: list[dict[str, Any]] = []
        for index, source in enumerate(records):
            package_id = source["package_id"]
            owners = source.get("canonical_owners", ["docs/billing.md"])
            fact_ids = source.get("changed_fact_ids", [f"FACT-{index}"])
            record_relpath = f".ai/assistant/change-packages/{package_id}.json"
            compact = {
                "package_id": package_id,
                "status": source["status"],
                "record": record_relpath,
                "changed_fact_ids": fact_ids,
                "canonical_owners": owners,
                "project_areas": source.get("project_areas", ["billing"]),
                "evidence_quality": "git-range",
                "approval_records": [".ai/assistant/approvals/A.json"],
                "active_workstream": "not active",
                "residual_risk": "none",
            }
            compact.update(source.get("compact_overrides", {}))
            compact_records.append(compact)
            facts = [
                {
                    "id": fact_id,
                    "canonical_owner": owners[min(position, len(owners) - 1)],
                }
                for position, fact_id in enumerate(fact_ids)
            ]
            package_record = {
                "package_id": package_id,
                "status": source.get("record_status", source["status"]),
                "changed_facts": facts,
                "routing": {"project_areas": source.get("project_areas", ["billing"])},
                "provenance": {"evidence_quality": "git-range"},
                "approved_scope": {
                    "approval_records": [".ai/assistant/approvals/A.json"]
                },
                "operation": {"active_workstream": "not active"},
            }
            record_path = target / record_relpath
            record_path.parent.mkdir(parents=True, exist_ok=True)
            record_path.write_text(json.dumps(package_record), encoding="utf-8")
        package_index.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "index_kind": "target-change-package-index",
                    "records": compact_records,
                    "shards": [],
                }
            ),
            encoding="utf-8",
        )
        knowledge_index.write_text(
            json.dumps({"promotion_records": []}), encoding="utf-8"
        )
        return package_index, knowledge_index

    def test_repeated_area_and_owner_produce_one_verified_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.write_target(
                target,
                [
                    {"package_id": "A", "status": "validated"},
                    {"package_id": "B", "status": "complete"},
                ],
            )
            report = suggestions(target)

        self.assertEqual(report["schema_version"], 3)
        self.assertEqual(report["validated_or_completed_packages_considered"], 2)
        self.assertEqual(report["candidate_projection_verified_packages"], 2)
        self.assertEqual(len(report["source_sha256"]), 64)
        self.assertEqual(len(report["knowledge_index_sha256"]), 64)
        self.assertEqual(len(report["candidates"]), 1)
        candidate = report["candidates"][0]
        self.assertEqual(candidate["candidate_kind"], "project-area-canonical-owner")
        self.assertEqual(
            candidate["selector"],
            {"project_area": "billing", "canonical_owner": "docs/billing.md"},
        )
        self.assertEqual(candidate["verified_evidence_samples"], 2)
        self.assertEqual(candidate["verified_occurrences"], 2)
        self.assertFalse(candidate["review_recommended"])
        self.assertFalse(report["automatic_promotion_performed"])

    def test_nonterminal_and_substring_statuses_are_not_candidates(self) -> None:
        rejected_statuses = [
            "proposed",
            "approved",
            "implementing",
            "blocked",
            "incomplete",
            "unvalidated",
            "not completed",
            "published",
            "deployed",
        ]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.write_target(
                target,
                [
                    {"package_id": f"P{index}", "status": status}
                    for index, status in enumerate(rejected_statuses)
                ],
            )
            report = suggestions(target)

        self.assertEqual(report["validated_or_completed_packages_considered"], 0)
        self.assertEqual(report["candidates"], [])

    def test_stale_compact_projection_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.write_target(
                target,
                [
                    {"package_id": "A", "status": "complete"},
                    {
                        "package_id": "B",
                        "status": "complete",
                        "record_status": "implementing",
                    },
                ],
            )
            report = suggestions(target)

        self.assertEqual(report["candidate_projection_verified_packages"], 1)
        self.assertEqual(report["candidate_projection_rejected_packages"], 1)
        self.assertEqual(report["candidates"], [])

    def test_existing_candidate_snapshot_is_suppressed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            _, knowledge_index = self.write_target(
                target,
                [
                    {"package_id": "A", "status": "validated"},
                    {"package_id": "B", "status": "complete"},
                ],
            )
            first = suggestions(target)
            candidate_id = first["candidates"][0]["candidate_id"]
            promotion_relpath = ".ai/project/knowledge/promotions/candidate.json"
            promotion_path = target / promotion_relpath
            promotion_path.parent.mkdir(parents=True)
            promotion_path.write_text(
                json.dumps({"candidate": {"candidate_id": candidate_id}}),
                encoding="utf-8",
            )
            knowledge_index.write_text(
                json.dumps(
                    {
                        "promotion_records": [
                            {
                                "promotion_id": "promotion-1",
                                "status": "deferred",
                                "path": promotion_relpath,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            second = suggestions(target)

        self.assertEqual(second["candidates"], [])
        self.assertEqual(second["suppressed_existing_candidates"], 1)
        self.assertEqual(second["suppressed_candidate_ids"], [candidate_id])

    def test_candidate_evidence_samples_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.write_target(
                target,
                [
                    {"package_id": f"P{index}", "status": "complete"}
                    for index in range(20)
                ],
            )
            report = suggestions(target)

        candidate = report["candidates"][0]
        self.assertEqual(candidate["occurrences"], 20)
        self.assertEqual(len(candidate["package_ids"]), 8)
        self.assertEqual(len(candidate["changed_fact_ids"]), 8)
        self.assertEqual(len(candidate["evidence_sha256"]), 64)
        self.assertEqual(candidate["verified_evidence_samples"], 8)
        self.assertEqual(candidate["verified_occurrences"], 20)
        self.assertTrue(candidate["review_recommended"])
        self.assertTrue(candidate["evidence_truncated"])

    def test_sharded_package_index_is_processed_with_digest_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            package_index, _ = self.write_target(
                target,
                [
                    {"package_id": "A", "status": "validated"},
                    {"package_id": "B", "status": "complete"},
                ],
            )
            root = json.loads(package_index.read_text(encoding="utf-8"))
            shard_records = [root["records"].pop()]
            shard_relpath = ".ai/assistant/change-packages/archive/2026-09/index.json"
            shard_path = target / shard_relpath
            shard_path.parent.mkdir(parents=True)
            shard = {
                "schema_version": 1,
                "index_kind": "target-change-package-index-shard",
                "shard_id": "2026-09",
                "records": shard_records,
            }
            shard_path.write_text(json.dumps(shard), encoding="utf-8")
            root["shards"] = [
                {
                    "shard_id": "2026-09",
                    "path": shard_relpath,
                    "sha256": hashlib.sha256(shard_path.read_bytes()).hexdigest(),
                    "record_count": 1,
                }
            ]
            package_index.write_text(json.dumps(root), encoding="utf-8")
            report = suggestions(target)

        self.assertEqual(len(report["source_files"]), 2)
        self.assertEqual(len(report["candidates"]), 1)

    def test_multi_area_package_does_not_invent_cartesian_relationships(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.write_target(
                target,
                [
                    {
                        "package_id": package_id,
                        "status": "complete",
                        "project_areas": ["billing", "orders"],
                        "canonical_owners": ["docs/billing.md", "docs/orders.md"],
                        "changed_fact_ids": [f"{package_id}-BILL", f"{package_id}-ORDER"],
                    }
                    for package_id in ["A", "B"]
                ],
            )

            report = suggestions(target)

        self.assertEqual(report["candidates"], [])
        self.assertEqual(report["ambiguous_package_count"], 2)
        self.assertEqual(report["ambiguous_package_ids"], ["A", "B"])

    def test_single_area_multiple_owners_keep_owner_specific_fact_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.write_target(
                target,
                [
                    {
                        "package_id": package_id,
                        "status": "complete",
                        "canonical_owners": ["docs/a.md", "docs/b.md"],
                        "changed_fact_ids": [f"{package_id}-A", f"{package_id}-B"],
                    }
                    for package_id in ["A", "B"]
                ],
            )

            report = suggestions(target)

        by_owner = {
            candidate["selector"]["canonical_owner"]: candidate
            for candidate in report["candidates"]
        }
        self.assertEqual(set(by_owner), {"docs/a.md", "docs/b.md"})
        self.assertEqual(by_owner["docs/a.md"]["changed_fact_ids"], ["A-A", "B-A"])
        self.assertEqual(by_owner["docs/b.md"]["changed_fact_ids"], ["A-B", "B-B"])

    def test_stale_record_outside_display_sample_cannot_raise_occurrences(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            records = [
                {"package_id": f"P{index}", "status": "complete"}
                for index in range(8)
            ]
            records.append(
                {
                    "package_id": "STALE",
                    "status": "complete",
                    "record_status": "implementing",
                }
            )
            self.write_target(target, records)

            report = suggestions(target, minimum_occurrences=9, recommend_at_occurrences=9)

        self.assertEqual(report["candidates"], [])
        self.assertEqual(report["candidate_projection_verified_packages"], 8)
        self.assertEqual(report["candidate_projection_rejected_packages"], 1)

    def test_recommendation_threshold_is_separate_from_candidate_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.write_target(
                target,
                [
                    {"package_id": package_id, "status": "complete"}
                    for package_id in ["A", "B", "C"]
                ],
            )

            report = suggestions(target, minimum_occurrences=2, recommend_at_occurrences=3)

        self.assertTrue(report["candidates"][0]["review_recommended"])
        self.assertFalse(report["automatic_promotion_performed"])

    def test_recommendation_threshold_cannot_be_lower_than_candidate_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.write_target(target, [])

            with self.assertRaisesRegex(ValueError, "recommend_at_occurrences"):
                suggestions(target, minimum_occurrences=3, recommend_at_occurrences=2)


if __name__ == "__main__":
    unittest.main()
