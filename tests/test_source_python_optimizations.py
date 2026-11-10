from __future__ import annotations

import ast
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from local_python_import_graph import LocalPythonImportGraph
from check_source_unit_tests import adaptive_test_shards, test_shards, test_weights
from source_check_reuse import SourceSnapshotIndex, canonical_digest, environment_fingerprint, reuse_decisions
from check_all import DEFAULT_JOBS, SelectionResult, build_run_identity, resolve_job_count
import check_all as runner
from tests import test_plan_minimum_work as planner_tests
import plan_minimum_work as planner


class ImportScanOptimizationTests(unittest.TestCase):
    def test_single_walk_preserves_alias_order_and_incomplete_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "tools/pkg").mkdir(parents=True)
            for name in ("leaf.py", "pkg/__init__.py", "pkg/child.py"):
                (root / "tools" / name).write_text("VALUE = 1\n", encoding="utf-8")
            cases = [
                ("load('leaf')\nfrom importlib import import_module as load\n", {"leaf.py"}, True),
                ("lib.import_module('leaf')\nimport importlib as lib\n", {"leaf.py"}, True),
                ("from importlib import import_module\nimport_module('.child', package='pkg')\n", {"pkg/child.py"}, True),
                ("import importlib\nimportlib.import_module(name)\n", set(), False),
                ("from importlib import import_module\nimport_module('.child', package=name)\n", set(), False),
                ("def f():\n import leaf\n", {"leaf.py"}, True),
                ("this is not valid Python!\n", set(), False),
            ]
            path = root / "tools/example.py"
            for source, names, complete in cases:
                with self.subTest(source=source):
                    path.write_text(source, encoding="utf-8")
                    graph = LocalPythonImportGraph(root)
                    with patch("local_python_import_graph.ast.walk", wraps=ast.walk) as walk:
                        result = graph.scan(path)
                        self.assertEqual(graph.scan(path), result)
                    self.assertLessEqual(walk.call_count, 1)
                    self.assertEqual(result.complete, complete)
                    self.assertEqual(result.dependencies, {root / "tools" / name for name in names})


class AdaptiveShardTests(unittest.TestCase):
    def test_selection_matches_independent_queue_oracle_and_preserves_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / f"test_{i:02d}.py" for i in range(31)]
            for path in paths:
                path.write_bytes(b"x")
            for capacity in (1, 2, 3, 4, 1000000000):
                for count in (0, 1, 7, 8, 9, 15, 16, 17, 31):
                    selected = paths[:count]
                    hints = {path.as_posix(): float(1 + (i * 13) % 89) for i, path in enumerate(selected)}
                    weights, _ = test_weights(selected, hints)
                    def score(shards):
                        lanes = [0.0] * min(max(1, capacity), max(1, len(shards)))
                        for shard in shards:
                            index = min(range(len(lanes)), key=lambda i: (lanes[i], i))
                            lanes[index] += sum(weights[path] for path in shard)
                        return max(lanes), len(shards)
                    candidates = [test_shards(selected, capacity, duration_hints=hints, shard_multiplier=m) for m in (2, 3, 4)]
                    actual = adaptive_test_shards(selected, capacity, hints)
                    self.assertEqual(score(actual), min(map(score, candidates)))
                    self.assertCountEqual([path for shard in actual for path in shard], selected)
                    self.assertEqual(actual, adaptive_test_shards(list(reversed(selected)), capacity, hints))

    def test_missing_invalid_and_unrelated_hints_do_not_change_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / f"test_{i}.py" for i in range(9)]
            for i, path in enumerate(paths):
                path.write_bytes(b"x" * (i + 1))
            expected = test_shards(paths, 2)
            self.assertEqual(adaptive_test_shards(paths, 2, {}), expected)
            invalid = {paths[0].as_posix(): float("nan"), "unrelated.py": 1e300}
            self.assertEqual(adaptive_test_shards(paths, 2, invalid), expected)
            hints = {paths[0].as_posix(): 1e308, paths[1].as_posix(): 1e308}
            weights, _ = test_weights(paths, hints)
            self.assertTrue(all(math.isfinite(value) and value > 0 for value in weights.values()))
            self.assertEqual(adaptive_test_shards(paths, 2, hints),
                             adaptive_test_shards(paths, 2, {**hints, "unrelated.py": 1e-300}))


class PlannerReuseIdentityTests(unittest.TestCase):
    def test_emitted_command_parser_identity_matches_escalation_and_fallback(self):
        item = {**planner_tests.check(), "trigger_paths": ["docs/human/**", "tools/change.py"]}
        for requested, changed, effective, fallback in (("micro", "tools/change.py", "fast", False),
                                                        ("fast", "unmatched.txt", "fast", True)):
            with self.subTest(requested=requested), \
                    patch.object(planner, "load_manifest", return_value=[item]), \
                    patch.object(runner, "git_changed_paths", return_value=[changed]), \
                    patch.object(planner, "source_snapshot", return_value={}), \
                    patch.object(planner, "reuse_decisions", wraps=reuse_decisions) as reuse:
                plan = planner.build_plan(requested_profile=requested, changed_from="HEAD",
                                          from_ref=None, reuse_report_path=None)
                args = runner.argument_parser().parse_args(plan["check_plan"]["command"][2:])
                self.assertEqual(args.profile, effective)
                self.assertEqual(args.changed_from, "HEAD")
                self.assertEqual(plan["selection"]["fell_back_to_full"], fallback)
                selected = runner.select_check_plan([item], args.profile, args.changed_from)
                selection = runner.selection_report(profile=args.profile, changed_from=args.changed_from,
                                                     plan=selected, manifest_checks=[item])
                kwargs = reuse.call_args.kwargs
                identity = runner.build_run_identity(requested_profile=args.profile, selection=selection,
                    changed_from=args.changed_from, baseline=runner.effective_baseline(args.profile, args.changed_from, args.from_ref),
                    source=kwargs["current_source"], jobs=runner.resolve_job_count(args.jobs))
                self.assertEqual(kwargs["current_run_identity"], identity)

    def test_plan_shares_index_and_supplies_canonical_execution_identity(self):
        selection = SelectionResult(selected=[planner_tests.check()], fell_back_to_full=False,
            changed_paths=["docs/human/faq.md"], unmatched_changed_paths=[], platform="linux",
            selection_details={"docs": {"reasons": ["changed-path-trigger"], "matched_changed_paths": ["docs/human/faq.md"]}},
            effective_profile="fast")
        with patch.object(planner, "SourceSnapshotIndex", wraps=SourceSnapshotIndex) as index, \
                patch.object(planner, "reuse_decisions", wraps=reuse_decisions) as reuse:
            plan = planner_tests.MinimumWorkPlanTests().build_test_plan(selection=selection,
                expected_validation_profile="fast", requested_profile="fast", source_profile="docs-local")
        self.assertEqual(index.call_count, 1)
        kwargs = reuse.call_args.kwargs
        expected = build_run_identity(requested_profile="fast", selection=plan["selection"],
            changed_from="HEAD", baseline="HEAD", source=kwargs["current_source"], jobs=resolve_job_count(DEFAULT_JOBS))
        self.assertEqual(kwargs["current_run_identity"], expected)
        self.assertTrue(expected["source_snapshot_sha256"].startswith("sha256:"))
        digest = canonical_digest(expected)
        previous = {"schema_version": 3, "report_kind": "alatyr-source-check-run", "source": kwargs["current_source"],
            "environment": kwargs["current_environment"], "source_write_scope": {"declared": "none", "preserved": True, "changes": []},
            "reuse_contract": {"contract": "alatyr-source-check-reuse-v1", "completed": True, "successful": True,
                "run_identity": expected, "run_identity_sha256": digest,
                "environment_sha256": environment_fingerprint(kwargs["current_environment"])["sha256"]},
            "checks": [{"id": "docs", "status": "passed", "timed_out": False,
                "command": kwargs["commands_by_id"]["docs"], "input_fingerprint": kwargs["input_fingerprints"]["docs"],
                "result_provenance": {"kind": "executed", "run_identity_sha256": digest}}]}
        self.assertTrue(reuse_decisions(**{**kwargs, "previous_report": previous})["docs"]["reusable"])
        changed = {**expected, "jobs": expected["jobs"] + 1}
        self.assertFalse(reuse_decisions(**{**kwargs, "previous_report": previous, "current_run_identity": changed})["docs"]["reusable"])


class ConformanceScenarioTests(unittest.TestCase):
    def test_selected_scenarios_match_full_enumeration_without_reloading_catalog(self):
        import run_conformance_scaffold as scaffold
        import capability_catalog
        with patch.object(capability_catalog, "load_catalog", wraps=capability_catalog.load_catalog) as load:
            all_scenarios = scaffold.support_profile_scenarios()
        self.assertEqual(load.call_count, 1)
        for row in all_scenarios:
            with patch.object(scaffold, "minimum_pack", wraps=scaffold.minimum_pack) as resolve:
                self.assertEqual(scaffold.support_profile_scenarios(row[0]), [row])
            self.assertLessEqual(resolve.call_count, 1)
        with self.assertRaisesRegex(ValueError, "unknown support profile"):
            scaffold.support_profile_scenarios("unknown-scenario")


if __name__ == "__main__":
    unittest.main()
