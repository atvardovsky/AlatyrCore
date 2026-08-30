from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from impact_graph import (
    ImpactGraphError,
    build_reverse_index,
    load_impact_graph,
    matching_node_ids,
    traverse_impact,
    validate_graph,
)
from plan_support_impact import main as impact_main


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2) + "\n").encode("utf-8"))


class ImpactGraphTests(unittest.TestCase):
    def make_graph(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name)
        root = {
            "schema_version": 3,
            "map_kind": "target-consistency-map",
            "impact_policy": {"max_depth": 4, "max_nodes": 20},
            "node_shards": [
                {"id": "billing", "path": ".ai/project/consistency/areas/billing.json"}
            ],
        }
        shard = {
            "schema_version": 1,
            "shard_kind": "target-consistency-map-shard",
            "id": "billing",
            "project_area": "billing",
            "nodes": [
                {
                    "id": "fact.payment-retry",
                    "fact_type": "business rule",
                    "level": "fact",
                    "project_area": "billing",
                    "canonical_owner": "docs/billing.md",
                    "coverage_state": "mapped",
                    "bindings": [
                        {
                            "id": "binding.payment-service",
                            "surface_kind": "code",
                            "path": "src/payment/**",
                            "selector_kind": "glob",
                            "selector": "whole-file",
                            "authority": "derived",
                            "context_ids": ["project.content.billing"],
                        }
                    ],
                    "relationships": [
                        {
                            "id": "edge.retry-tests",
                            "type": "verifies",
                            "target": "surface.payment-tests",
                            "state": "accepted",
                        }
                    ],
                },
                {
                    "id": "surface.payment-tests",
                    "fact_type": "test surface",
                    "level": "surface",
                    "project_area": "billing",
                    "canonical_owner": "tests/payment",
                    "coverage_state": "isolated-verified",
                    "bindings": [
                        {
                            "id": "binding.payment-tests",
                            "surface_kind": "test",
                            "path": "tests/payment/**",
                            "selector_kind": "glob",
                            "selector": "whole-file",
                            "authority": "evidence",
                            "context_ids": [],
                        }
                    ],
                    "relationships": [],
                },
            ],
        }
        write_json(target / ".ai/project/consistency-map.json", root)
        write_json(target / ".ai/project/consistency/areas/billing.json", shard)
        return directory, target

    def test_reverse_index_routes_changed_code_to_fact(self) -> None:
        _directory, target = self.make_graph()
        graph = load_impact_graph(target)
        reverse = build_reverse_index(graph)
        self.assertEqual(
            matching_node_ids(reverse, "src/payment/retry.py"),
            {"fact.payment-retry"},
        )

    def test_traversal_selects_only_accepted_relationships(self) -> None:
        _directory, target = self.make_graph()
        graph = load_impact_graph(target)
        selected, edges, skipped = traverse_impact(graph, ["fact.payment-retry"])
        self.assertEqual(selected, ["fact.payment-retry", "surface.payment-tests"])
        self.assertEqual([edge["id"] for edge in edges], ["edge.retry-tests"])
        self.assertEqual(skipped, [])

    def test_accepted_missing_target_fails_validation(self) -> None:
        _directory, target = self.make_graph()
        shard_path = target / ".ai/project/consistency/areas/billing.json"
        shard = json.loads(shard_path.read_text(encoding="utf-8"))
        shard["nodes"][0]["relationships"][0]["target"] = "missing"
        write_json(shard_path, shard)
        graph = load_impact_graph(target)
        self.assertTrue(
            any("targets missing node" in failure for failure in validate_graph(graph))
        )

    def test_node_limit_fails_closed(self) -> None:
        _directory, target = self.make_graph()
        graph = load_impact_graph(target)
        with self.assertRaisesRegex(ImpactGraphError, "max_nodes"):
            traverse_impact(graph, ["fact.payment-retry"], max_nodes=1)

    def test_impact_plan_reports_stable_digest_and_path_summary(self) -> None:
        _directory, target = self.make_graph()
        (target / "src/payment").mkdir(parents=True)
        (target / "src/payment/retry.py").write_text("retry = True\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=target, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=target, check=True)
        subprocess.run(["git", "add", "."], cwd=target, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=target, check=True)
        (target / "src/payment/retry.py").write_text("retry = False\n", encoding="utf-8")

        output = target / "impact.json"
        original_argv = sys.argv
        try:
            sys.argv = [
                "plan_support_impact.py",
                "--target",
                str(target),
                "--diff-ref",
                "HEAD",
                "--output",
                str(output),
            ]
            self.assertEqual(impact_main(), 0)
        finally:
            sys.argv = original_argv

        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertRegex(report["impact_plan_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(report["changed_path_summary"]["changed_path_count"], 1)
        self.assertEqual(report["changed_path_summary"]["mapped_path_count"], 1)


if __name__ == "__main__":
    unittest.main()
