from __future__ import annotations

import hashlib
import ast
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from code_relationships import inspect_relationships
from project_evidence import ProjectEvidence
from inspect_code_relationships import main


class CodeRelationshipTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name).resolve()
        self.write("app/service.py", "from .rules import Rule\n\nclass Service:\n    def run(self):\n        return Rule()\n")
        self.write("app/rules.py", "class Rule:\n    pass\n")
        self.nodes = [self.node("service", "app/service.py", "Service.run"),
                      self.node("rules", "app/rules.py", "Rule")]
        self.map()

    def write(self, path, content):
        destination = self.target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    def node(self, identifier, path, selector):
        return {"id": identifier, "level": "area", "canonical_owner": "docs/architecture.md",
                "coverage_state": "isolated-verified", "relationships": [],
                "bindings": [{"id": identifier, "surface_kind": "code", "path": path,
                              "selector_kind": "symbol", "selector": selector}]}

    def map(self):
        self.write(".ai/project/consistency-map.json", json.dumps({
            "schema_version": 2, "map_kind": "target-consistency-map", "nodes": self.nodes}))

    def inspect(self):
        return inspect_relationships(self.target, ["app/service.py", "app/rules.py"])

    def codes(self, result):
        return {row["code"] for row in result["findings"]}

    def test_observed_imports_are_review_hints_not_accepted_edges(self):
        before = (self.target / ".ai/project/consistency-map.json").read_bytes()
        result = self.inspect()
        self.assertEqual({"CODE_DEPENDENCY_REVIEW"}, self.codes(result))
        self.assertEqual("observed", result["observed_relationships"][0]["state"])
        self.assertEqual("not-assessed", result["architecture_review"])
        self.assertEqual(before, (self.target / ".ai/project/consistency-map.json").read_bytes())

    def test_only_accepted_declared_dependencies_corroborate_imports(self):
        for state in ("observed", "proposed", "rejected", "stale", "contradicted", "removed", "accepted"):
            with self.subTest(state=state):
                self.nodes[0]["relationships"] = [{"type": "depends-on", "target": "rules", "state": state}]
                self.map()
                self.assertEqual(state != "accepted", "CODE_DEPENDENCY_REVIEW" in self.codes(self.inspect()))

    def test_absence_of_import_does_not_disprove_declared_relationship(self):
        self.write("app/service.py", "class Service:\n    def run(self):\n        return 1\n")
        self.nodes[0]["relationships"] = [{"type": "depends-on", "target": "rules", "state": "accepted"}]
        self.map()
        result = self.inspect()
        self.assertEqual([], result["findings"])
        self.assertEqual([], result["observed_relationships"])

    def test_missing_symbol_and_ambiguous_ownership_are_visible(self):
        self.nodes[0]["bindings"][0]["selector"] = "Service.missing"
        self.nodes.append(self.node("other", "app/service.py", "Service"))
        self.map()
        self.assertEqual({"CODE_SYMBOL_MISSING", "CODE_OWNERSHIP_AMBIGUOUS"}, self.codes(self.inspect()))

    def test_aliases_conditional_local_and_star_imports(self):
        self.write("app/service.py", "import app.rules as rules\nclass Service:\n    def run(self):\n        if False:\n            from .rules import *\n        return 1\n")
        # AST parsing is intentionally syntactic; it never executes the source.
        self.assertEqual(2, len(self.inspect()["observed_relationships"]))

    def test_external_and_unselected_imports_remain_unresolved(self):
        self.write("app/service.py", "import os\nimport app.unselected\nclass Service:\n    def run(self):\n        pass\n")
        result = self.inspect()
        self.assertEqual(2, len(result["unresolved_imports"]))
        self.assertEqual([], result["observed_relationships"])

    def test_partial_multi_name_import_preserves_unresolved_sibling(self):
        self.write("app/service.py", "from app import rules, missing\nclass Service:\n    def run(self):\n        pass\n")
        result = self.inspect()
        self.assertEqual("app/rules.py", result["observed_relationships"][0]["dependency"])
        self.assertEqual(1, len(result["unresolved_imports"]))
        self.assertEqual(["app.missing", "app"], result["unresolved_imports"][0]["modules"])

    def test_duplicate_symbol_definition_is_not_a_unique_binding(self):
        self.write("app/rules.py", "class Rule:\n    pass\nclass Rule:\n    pass\n")
        self.assertIn("CODE_SYMBOL_AMBIGUOUS", self.codes(self.inspect()))

    def test_large_public_wire_representation_obeys_actual_byte_limit(self):
        self.write("app/service.py", ("import " + "u" * 120 + "\n") * 4000)
        self.nodes[0]["bindings"][0].update(selector_kind="file", selector="whole-file")
        self.map()
        result = self.cli(raw=True)
        payload = json.loads(result.stdout)
        self.assertLessEqual(len(result.stdout), 1024 * 1024)
        if payload["status"] == "blocked":
            self.assertEqual(1, result.returncode)
            self.assertIn("exceeds", payload["findings"][0]["message"])
        else:
            self.assertEqual(4000, len(payload["unresolved_imports"]))
            self.assertGreater(len(json.dumps(payload, indent=2).encode("utf-8")), 1024 * 1024)

    def test_wire_bytes_do_not_depend_on_host_newline_translation(self):
        stream = io.BytesIO()
        wrapper = io.TextIOWrapper(stream, encoding="utf-8", newline="\r\n")
        arguments = ["code-relationships", "--target", str(self.target),
                     "--source", "app/service.py", "--source", "app/rules.py"]
        with patch.object(sys, "stdout", wrapper), patch.object(sys, "argv", arguments):
            self.assertEqual(1, main())
        raw = stream.getvalue()
        self.assertTrue(raw.endswith(b"\n"))
        self.assertFalse(raw.endswith(b"\r\n"))
        self.assertEqual("review-required", json.loads(raw)["status"])

    def test_sharded_graph_and_source_root(self):
        self.write("app/service.py", "from rules import Rule\nclass Service:\n    def run(self):\n        return Rule()\n")
        self.write(".ai/project/area.json", json.dumps({"schema_version": 1,
                   "shard_kind": "target-consistency-map-shard", "id": "app", "nodes": self.nodes}))
        self.write(".ai/project/consistency-map.json", json.dumps({"schema_version": 3,
                   "map_kind": "target-consistency-map", "node_shards": [{"id": "app", "path": ".ai/project/area.json"}]}))
        result = inspect_relationships(self.target, ["app/service.py", "app/rules.py"], source_root="app")
        self.assertEqual(1, len(result["observed_relationships"]))
        self.assertEqual(4, len(result["input_bindings"]))

    def test_malformed_enum_and_selector_values_never_crash_cli(self):
        for value in ({}, [], None, True, 4):
            with self.subTest(value=value):
                self.nodes[0]["bindings"][0]["selector_kind"] = value
                self.map()
                result = self.cli()
                self.assertEqual(1, result.returncode, result.stderr)
                self.assertEqual("blocked", json.loads(result.stdout)["status"])
                self.assertNotIn("Traceback", result.stderr)

    def test_path_traversal_unsupported_source_and_invalid_python(self):
        for sources in (["../escape.py"], ["app/service.ts"], ["app/service.py", "app/service.py"], []):
            with self.subTest(sources=sources), self.assertRaises(ValueError):
                inspect_relationships(self.target, sources)
        self.write("app/service.py", "def broken(:\n")
        result = self.cli()
        self.assertEqual(1, result.returncode)
        self.assertEqual("blocked", json.loads(result.stdout)["status"])

    def test_source_symlink_is_rejected(self):
        self.write("outside.py", "pass\n")
        link = self.target / "app/link.py"
        try:
            link.symlink_to(self.target / "outside.py")
        except OSError:
            self.skipTest("host cannot create symlinks")
        with self.assertRaises(ValueError):
            inspect_relationships(self.target, ["app/link.py"])

    def test_graph_and_source_mutations_prevent_delivery(self):
        original = ProjectEvidence.bindings
        for path in ("app/rules.py", ".ai/project/consistency-map.json"):
            self.setUp()
            def mutate(evidence):
                result = original(evidence)
                with (self.target / path).open("a", encoding="utf-8") as stream:
                    stream.write(" ")
                return result
            with self.subTest(path=path), patch.object(ProjectEvidence, "bindings", mutate), self.assertRaises(ValueError):
                self.inspect()

    def test_explicit_source_and_result_boundaries(self):
        with patch("code_relationships.MAX_SOURCES", 2):
            inspect_relationships(self.target, ["app/service.py"])
            self.inspect()
            with self.assertRaises(ValueError):
                inspect_relationships(self.target, ["app/service.py", "app/rules.py", "app/third.py"])
        # An observation, unresolved imported symbol and review hint: three rows.
        for limit in (2, 3, 4):
            with self.subTest(limit=limit), patch("code_relationships.MAX_ROWS", limit):
                if limit == 2:
                    with self.assertRaises(ValueError):
                        self.inspect()
                else:
                    self.inspect()

    def test_node_ast_and_serialized_report_boundaries(self):
        for limit in (1, 2, 3):
            with self.subTest(nodes=limit), patch("code_relationships.MAX_NODES", limit):
                if limit == 1:
                    with self.assertRaises(ValueError):
                        self.inspect()
                else:
                    self.inspect()
        count = sum(1 for _ in ast.walk(ast.parse((self.target / "app/service.py").read_bytes())))
        for limit in (count - 1, count, count + 1):
            with self.subTest(ast=limit), patch("code_relationships.MAX_AST_NODES", limit):
                if limit < count:
                    with self.assertRaises(ValueError):
                        self.inspect()
                else:
                    self.inspect()
        size = len((json.dumps(self.inspect()) + "\n").encode("utf-8"))
        for limit in (size - 1, size, size + 1):
            with self.subTest(report=limit), patch("code_relationships.MAX_REPORT_BYTES", limit):
                if limit < size:
                    with self.assertRaises(ValueError):
                        self.inspect()
                else:
                    self.inspect()

    def test_unmapped_code_and_case_collisions_are_not_silently_accepted(self):
        self.nodes.pop()
        self.map()
        self.assertIn("CODE_OWNERSHIP_UNMAPPED", self.codes(self.inspect()))
        with self.assertRaises(ValueError):
            inspect_relationships(self.target, ["app/rules.py", "app/Rules.py"])

    def test_evidence_file_total_and_count_boundaries(self):
        self.write("one", "1234")
        self.write("two", "5678")
        for limit in (3, 4, 5):
            with self.subTest(limit=limit), patch("project_evidence.MAX_FILE_BYTES", limit):
                if limit < 4:
                    with ProjectEvidence(self.target) as evidence, self.assertRaises(ValueError):
                        evidence.exact("one")
                else:
                    with ProjectEvidence(self.target) as evidence:
                        self.assertEqual(b"1234", evidence.exact("one"))
        for limit in (7, 8, 9):
            with self.subTest(total=limit), patch("project_evidence.MAX_TOTAL_BYTES", limit):
                with ProjectEvidence(self.target) as evidence:
                    evidence.exact("one")
                    if limit == 7:
                        with self.assertRaises(ValueError):
                            evidence.exact("two")
                    else:
                        evidence.exact("two")
                        evidence.exact("one")
                        self.assertEqual(8, sum(evidence.measured.values()))
        with patch("project_evidence.MAX_FILES", 1), ProjectEvidence(self.target) as evidence:
            evidence.exact("one")
            evidence.exact("one")
            with self.assertRaises(ValueError):
                evidence.exact("two")

    def cli(self, *, raw=False):
        return subprocess.run([sys.executable, "-B", str(ROOT / "tools/alatyr.py"),
                               "code-relationships", "--target", str(self.target),
                               "--source", "app/service.py", "--source", "app/rules.py"],
                              capture_output=True, text=not raw, check=False)

    def test_public_dispatch_and_no_target_writes(self):
        before = {path.relative_to(self.target).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in self.target.rglob("*") if path.is_file()}
        self.assertEqual(1, self.cli().returncode)
        self.nodes[0]["relationships"] = [{"type": "depends-on", "target": "rules", "state": "accepted"}]
        self.map()
        result = self.cli()
        self.assertEqual(0, result.returncode, result.stderr)
        after = {path.relative_to(self.target).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in self.target.rglob("*") if path.is_file()}
        self.assertEqual(set(before), set(after))
        self.assertEqual(before["app/service.py"], after["app/service.py"])


if __name__ == "__main__":
    unittest.main()
