from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from source_architecture import (FOUNDATION, architecture_failures, branch_points,
                                 cycle_failures, entrypoint_failures,
                                 strongly_connected_components)
from source_change_impact import source_change_impact
from source_check_manifest import load_manifest


class SourceMaintenanceTests(unittest.TestCase):
    def test_checker_claims_keep_diagnostics_and_read_each_surface_once(self):
        from types import SimpleNamespace
        from validate_target_adapter import Validator
        for exists in (True, False):
            for placeholders in (True, False):
                paths = [Path(".ai/assistant/contour.md"), Path(".ai/framework/contour.md")]
                texts = {paths[0]: "Alatyr checker missing; check-alatyr.sh", paths[1]: "ignored"}
                checker = Path("scripts/check-alatyr.sh")
                texts[checker] = "MANIFEST"
                reads, rows = [], []
                def read(path):
                    reads.append(path)
                    return texts[path]
                sink = SimpleNamespace(scan_live_text_files=lambda: paths, rel=str, read_text=read,
                    allow_placeholders=placeholders,
                    config=SimpleNamespace(checker_coverage=lambda: {"manifest": "manifest", "router": "router"}))
                for level in ("info", "warn", "error"):
                    setattr(sink, level, lambda *args, level=level: rows.append((level, *args)))
                Validator.check_checker_claims(sink, [checker] if exists else [], [])
                self.assertEqual(reads, [paths[0], checker] if exists else [paths[0]])
                codes = [row[1] for row in rows]
                self.assertIn("TARGET_CHECKER_FOUND" if exists else "TARGET_CHECKER_MISSING", codes)
                if exists:
                    self.assertEqual(codes.count("TARGET_CHECKER_COVERAGE_GAP"), 1)
                else:
                    self.assertIn("STALE_CHECKER_REFERENCE", codes)

    def test_impact_rejects_unsafe_paths_and_groups_shared_review_once(self):
        for paths in (["../secret"], ["/absolute"], ["tools//x.py"], ["C:\\x.py"], [None], "tools/x.py"):
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                source_change_impact(ROOT, paths, [])
        paths = ["schemas/alatyr-task-closure.schema.json", "templates/target/.ai/assistant/templates/task-closure.json"]
        report = source_change_impact(ROOT, paths, load_manifest())
        self.assertEqual(list(report["review_groups"]), ["contract:analysis-strategies"])
        self.assertTrue(all(row["review_groups"] == ["contract:analysis-strategies"] for row in report["rows"]))

    def test_foundation_has_no_back_imports_or_cycles(self):
        policy = json.loads((ROOT / "tools/tool_complexity_allowlist.json").read_text())
        self.assertEqual(architecture_failures(ROOT, allowed_cycles=policy["dependency_cycles"]), [])

    def test_cycle_ratchet_rejects_growth_and_new_edges_but_allows_removal(self):
        allowed = [{"members": ["a", "b"], "edges": [["a", "b"], ["b", "a"]], "reason": "legacy"}]
        self.assertEqual(cycle_failures({"a": {"b"}, "b": {"a"}}, allowed), [])
        self.assertEqual(cycle_failures({"a": {"b"}, "b": set()}, allowed), [])
        for graph in ({"a": {"b"}, "b": {"c"}, "c": {"a"}},
                      {"a": {"a", "b"}, "b": {"a"}}, {"new": {"new"}}):
            self.assertTrue(cycle_failures(graph, allowed))

    def test_entrypoint_signatures_reject_untyped_wrong_arity_and_async(self):
        from types import SimpleNamespace
        def valid(context: "CapabilityValidationContext", manifest: object) -> None:
            pass
        def untyped(context, manifest):
            pass
        def wrong(context: object) -> None:
            pass
        async def asynchronous(context: object, manifest: object) -> None:
            pass
        def run(function):
            return entrypoint_failures({"test": SimpleNamespace(validate=function)}, [])
        self.assertEqual(run(valid), [])
        from target_adapter_validation.capability import CapabilityValidationContext
        concrete = {}
        exec(compile("def concrete(context: Host, manifest: object) -> None: pass", "<fixture>", "exec", dont_inherit=True),
             {"Host": CapabilityValidationContext}, concrete)
        self.assertEqual(run(concrete["concrete"]), [])
        for function in (untyped, wrong, asynchronous):
            self.assertTrue(run(function))

    def test_qualified_and_dynamic_imports_have_canonical_dependency_coverage(self):
        from local_python_import_graph import LocalPythonImportGraph
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools/pkg").mkdir(parents=True)
            (root / "tools/leaf.py").write_text("", encoding="utf-8")
            source = root / "tools/main.py"
            source.write_text("import tools.leaf\nimport importlib as loader\nfrom importlib import import_module as load\nloader.import_module('tools.leaf')\nload('leaf')\n", encoding="utf-8")
            init = root / "tools/pkg/__init__.py"
            init.write_text("from . import child\n", encoding="utf-8")
            (root / "tools/pkg/child.py").write_text("", encoding="utf-8")
            graph = LocalPythonImportGraph(root)
            self.assertIn((root / "tools/leaf.py").resolve(), graph.scan(source).dependencies)
            self.assertNotIn(init.resolve(), graph.scan(init).dependencies)
            source.write_text("from importlib import import_module as load\nload(variable)\n", encoding="utf-8")
            self.assertFalse(LocalPythonImportGraph(root).scan(source).complete)
            source.write_text("import importlib\nimportlib.import_module('.child', package='pkg')\n", encoding="utf-8")
            scan = LocalPythonImportGraph(root).scan(source)
            self.assertTrue(scan.complete)
            self.assertIn((root / "tools/pkg/child.py").resolve(), scan.dependencies)
            source.write_text("import importlib\nimportlib.import_module('.child', package=unknown)\n", encoding="utf-8")
            self.assertFalse(LocalPythonImportGraph(root).scan(source).complete)

    def test_debug_privacy_extraction_keeps_order_and_strict_false_flags(self):
        from target_adapter_validation.debug_mode import _validate_record_privacy
        class Findings:
            def __init__(self): self.rows = []
            def error(self, *args): self.rows.append(args)
        sink = Findings()
        _validate_record_privacy(sink, {"nested": [{"SECRETS": "synthetic"}], "privacy": {"raw_ai_conversation_stored": 0}}, "record.json")
        self.assertEqual(sink.rows[0][0], "DEBUG_MODE_PROHIBITED_CONTENT_FIELD")
        self.assertIn("nested[0].SECRETS", sink.rows[0][1])
        self.assertTrue(any("raw_ai_conversation_stored" in row[1] for row in sink.rows[1:]))
        for record in ({}, {"ordinary": "secrets"}, {"privacy": None}):
            sink = Findings()
            _validate_record_privacy(sink, record, "record.json")
            self.assertEqual(sink.rows, [])

    def test_runtime_cycles_self_cycles_and_acyclic_graphs(self):
        self.assertEqual(strongly_connected_components({"a": {"b"}, "b": set()}), [])
        self.assertEqual(strongly_connected_components({"a": {"b"}, "b": {"a"}, "c": {"c"}}),
                         [["a", "b"], ["c"]])

    def test_injected_back_import_cycle_and_missing_foundation_are_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            for name in FOUNDATION:
                (root / "tools" / (name + ".py")).write_text("", encoding="utf-8")
            (root / "tools/cli.py").write_text("", encoding="utf-8")
            (root / "tools/path_spec.py").write_text("from tools import cli\nimport source_state\n", encoding="utf-8")
            (root / "tools/source_state.py").write_text("import path_spec\n", encoding="utf-8")
            failures = architecture_failures(root)
            self.assertTrue(any("back-import" in f for f in failures))
            self.assertTrue(any("cycle" in f for f in failures))
            (root / "tools/source_state.py").unlink()
            self.assertTrue(any("missing" in f for f in architecture_failures(root)))

    def test_branch_screening_is_not_line_count(self):
        self.assertEqual(branch_points(ast.parse("x = 1\n" * 20)), 0)
        self.assertGreater(branch_points(ast.parse("if x and y:\n pass\n")), 1)

    def test_impact_joins_existing_contracts_and_keeps_unknowns_explicit(self):
        report = source_change_impact(ROOT, ["schemas/alatyr-task-closure.schema.json", "tools/new.py"], load_manifest())
        by_path = {row["path"]: row for row in report["rows"]}
        self.assertEqual(by_path["schemas/alatyr-task-closure.schema.json"]["contracts"], ["analysis-strategies"])
        self.assertIn("tools/new.py", report["unmapped_semantic_paths"])
        self.assertIn("not mandatory edits", report["claim_boundary"])
        self.assertTrue(source_change_impact(ROOT, ["tools/render_target_contract_compatibility.py"], [])['projection_review'])

    def test_public_impact_view_is_opt_in_and_compact_compatible(self):
        from tests.test_source_context_selection import isolated_source_git
        command = [sys.executable, "-B", str(ROOT / "tools/plan_minimum_work.py"), "--changed-from", "HEAD", "--compact"]
        with isolated_source_git() as (env, *_):
            for impact in (False, True):
                result = subprocess.run(command + (["--impact"] if impact else []), env=env,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual("source_change_impact" in json.loads(result.stdout), impact)


if __name__ == "__main__":
    unittest.main()
