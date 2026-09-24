from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from impact_graph import ImpactGraph, build_reverse_index, load_impact_graph
from target_adapter_validation.consistency_map import _validate_graph_bindings
from target_adapter_validation.context import TargetPathEscapeError
from target_adapter_validation.harness_scenarios.common import validator


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class ConsistencyMapValidationTests(unittest.TestCase):
    def make_target(self, binding_path: str = "src/service.py") -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name)
        for relpath in ["src/service.py", "docs/business.md"]:
            path = target / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n", encoding="utf-8")
        (target / ".ai/project/source-of-truth-registry.md").parent.mkdir(
            parents=True, exist_ok=True
        )
        (target / ".ai/project/source-of-truth-registry.md").write_text(
            "# Registry\n\n"
            "### Fact Type: `business rule`\n\n"
            "Fact type: `business rule`\n"
            "Canonical owner: `docs/business.md`\n"
            "Consistency map node: `fact.business`\n",
            encoding="utf-8",
        )
        root = {
            "schema_version": 3,
            "map_kind": "target-consistency-map",
            "human_registry": ".ai/project/source-of-truth-registry.md",
            "registry_sync_policy": {
                "coverage": "every-live-registry-fact-type",
                "node_reference": "registry-consistency-map-node-id",
                "fact_type_match": "exact",
                "extra_nodes": "allowed-for-derived-contract-area-system-adapter-and-surface-nodes",
            },
            "levels": ["fact", "contract", "area", "system", "adapter", "surface"],
            "relationship_types": [
                "implements", "verifies", "documents", "visualizes", "generates",
                "constrains", "depends-on", "routes",
            ],
            "relationship_states": [
                "observed", "proposed", "accepted", "rejected", "stale",
                "contradicted", "removed",
            ],
            "impact_policy": {
                "default_mode": "owner-and-applicable-accepted-relationships",
                "max_depth": 4,
                "max_nodes": 20,
                "transitive_expand_when": ["dependent contract changes"],
                "required_evidence": ["selected relationships"],
            },
            "node_shards": [
                {"id": "core", "path": ".ai/project/consistency/areas/core.json"}
            ],
            "reverse_index": ".ai/assistant/consistency-reverse-index.json",
            "relationship_candidates": ".ai/project/consistency/relationship-candidates.json",
        }
        shard = {
            "schema_version": 1,
            "shard_kind": "target-consistency-map-shard",
            "id": "core",
            "project_area": "core",
            "nodes": [
                {
                    "id": "fact.business",
                    "fact_type": "business rule",
                    "level": "fact",
                    "project_area": "core",
                    "canonical_owner": "docs/business.md",
                    "coverage_state": "mapped",
                    "coverage_evidence": ["reviewed mapping"],
                    "bindings": [
                        {
                            "id": "binding.service",
                            "surface_kind": "code",
                            "path": binding_path,
                            "selector_kind": "file",
                            "selector": "whole-file",
                            "authority": "derived",
                            "context_ids": [],
                        }
                    ],
                    "relationships": [
                        {
                            "id": "edge.self",
                            "type": "depends-on",
                            "target": "fact.business",
                            "state": "accepted",
                        }
                    ],
                }
            ],
        }
        write_json(target / ".ai/project/consistency-map.json", root)
        write_json(target / ".ai/project/consistency/areas/core.json", shard)
        write_json(
            target / ".ai/project/consistency/relationship-candidates.json",
            {
                "schema_version": 1,
                "record_kind": "target-consistency-relationship-candidates",
                "records": [],
            },
        )
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)
        subprocess.run(["git", "add", "."], cwd=target, check=True)
        reverse = build_reverse_index(load_impact_graph(target))
        write_json(target / ".ai/assistant/consistency-reverse-index.json", reverse)
        return target

    def test_mapped_binding_must_match_repository_inventory(self) -> None:
        target = self.make_target("src/missing.py")
        check = validator(target)

        check.check_consistency_map()

        self.assertIn(
            "CONSISTENCY_MAP_BINDING_UNMATCHED",
            {finding.code for finding in check.findings},
        )

    def test_relationship_candidate_records_are_schema_validated(self) -> None:
        target = self.make_target()
        write_json(
            target / ".ai/project/consistency/relationship-candidates.json",
            {
                "schema_version": 1,
                "record_kind": "target-consistency-relationship-candidates",
                "records": [{}],
            },
        )
        check = validator(target)

        check.check_consistency_map()

        self.assertIn(
            "CONSISTENCY_RELATIONSHIP_CANDIDATES",
            {finding.code for finding in check.findings},
        )

    def test_binding_escape_is_reported_instead_of_crashing(self) -> None:
        findings: list[tuple[str, str]] = []

        class Context:
            target = Path("fixture")

            @staticmethod
            def target_exists(path: str) -> bool:
                raise TargetPathEscapeError(path)

            @staticmethod
            def error(code: str, message: str, path: str) -> None:
                findings.append((code, message))

        graph = ImpactGraph(
            root={},
            nodes={
                "fact.business": {
                    "coverage_state": "mapped",
                    "bindings": [
                        {
                            "path": "outside-link",
                            "selector_kind": "file",
                        }
                    ],
                }
            },
            graph_digest="fixture",
            source_paths=(),
        )
        with patch(
            "target_adapter_validation.consistency_map.RepositoryInventory.load",
            return_value=SimpleNamespace(paths=("outside-link",)),
        ):
            _validate_graph_bindings(Context(), graph, "consistency-map.json")

        self.assertEqual(findings[0][0], "CONSISTENCY_MAP_BINDING_UNSAFE")
        self.assertEqual(len(findings), 1)


if __name__ == "__main__":
    unittest.main()
