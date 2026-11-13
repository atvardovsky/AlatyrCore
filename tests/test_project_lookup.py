from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import project_lookup as lookup
from project_lookup import project_lookup
from project_evidence import ProjectEvidence


def registry(*, authority="accepted", node="deferred", coverage="deferred"):
    return f"""# Registry
### Fact Type: `behavior`
Fact type: `behavior`
Authority: ap=`applicable`; st=`{authority}`; ds=`docs/decision.md`; er=`old-revision`; at=`2026-09-01`; gs=`none`
Canonical owner: `docs/decision.md`
Routing: cl=`fact`; pa=`core`; cn=`{node}`; rc=`{coverage}`
"""


class ProjectLookupTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name).resolve()
        self.target = self.base / "target"
        self.target.mkdir()
        self.write("src/core.py", "def field_count(fields):\n    return len(fields)\n")
        self.write("docs/decision.md", "# Accepted Decision\n\nOnly the owner mutates state.\n")
        self.write(".ai/project/source-of-truth-registry.md", registry())
        self.navigation = self.base / "navigation.json"

    def write(self, name, content):
        path = self.target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def cli(self, *extra, delegate=False):
        command = ([sys.executable, "-B", str(ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"),
                    "project-lookup", "--target", str(self.target), "--framework-source", str(ROOT), "--"]
                   if delegate else [sys.executable, "-B", str(ROOT / "tools/alatyr.py"),
                                     "project-lookup", "--target", str(self.target)])
        return subprocess.run([*command, "--question", "What does field_count do?", *extra],
                              capture_output=True, text=True, check=False)

    def navigation_data(self):
        return {"schema_version": 1, "report_kind": "code-navigation-evidence",
                "query": "What does field_count do?", "backend": "test-captured-host-tool",
                "match_kind": "symbol-reference", "coverage": "selected-files",
                "source_bindings": [{"path": "src/core.py", "sha256": hashlib.sha256((self.target / "src/core.py").read_bytes()).hexdigest()}],
                "matches": [{"path": "src/core.py", "line": 1}], "limitations": []}

    def run_navigation(self, data):
        self.navigation.write_text(json.dumps(data), encoding="utf-8")
        return self.cli("--source", "src/core.py", "--navigation-report", str(self.navigation))

    def test_direct_lookup_ignores_unrelated_broken_adapter_and_does_not_write(self):
        self.write(".ai/project/source-of-truth-registry.md", "broken unrelated registry")
        self.write(".ai/assistant/context-router.json", "not JSON")
        before = {path.relative_to(self.target): path.read_bytes() for path in self.target.rglob("*") if path.is_file()}
        result = self.cli("--source", "src/core.py")
        self.assertEqual(0, result.returncode, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual("ready-for-inspection", data["status"])
        self.assertEqual(["src/core.py"], [row["path"] for row in data["input_bindings"]])
        self.assertEqual(1, data["measurement"]["input_files"])
        self.assertFalse(data["authorization_granted"])
        self.assertFalse(data["acceptance_granted"])
        self.assertFalse(data["code_executed"])
        self.assertEqual(before, {path.relative_to(self.target): path.read_bytes() for path in self.target.rglob("*") if path.is_file()})

    def test_installed_delegate_uses_the_same_bounded_inspection(self):
        direct = self.cli("--source", "src/core.py")
        installed = self.cli("--source", "src/core.py", delegate=True)
        self.assertEqual(0, installed.returncode, installed.stderr)
        self.assertEqual(json.loads(direct.stdout), json.loads(installed.stdout))

    def test_local_lookup_does_not_import_optional_adapter_dependencies(self):
        result = subprocess.run([sys.executable, "-B", "-S", str(ROOT / "tools/inspect_project_lookup.py"),
            "--target", str(self.target), "--question", "Explain", "--source", "src/core.py"],
            capture_output=True, text=True, check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("ready-for-inspection", json.loads(result.stdout)["status"])

    def test_line_selection_is_exact_and_does_not_claim_whole_file_delivery(self):
        data = json.loads(self.cli("--source", "src/core.py", "--start-line", "2", "--end-line", "2").stdout)
        self.assertEqual("    return len(fields)\n", data["content"][0]["text"])
        self.assertEqual(2, data["content"][0]["start_line"])
        self.assertEqual(hashlib.sha256((self.target / "src/core.py").read_bytes()).hexdigest(), data["content"][0]["sha256"])
        self.assertGreater(data["measurement"]["input_bytes"], data["measurement"]["selected_content_bytes"])

    def test_invalid_or_incomplete_ranges_fail_without_truncating(self):
        for extra in (("--start-line", "1"), ("--start-line", "2", "--end-line", "1"),
                      ("--start-line", "0", "--end-line", "1"), ("--start-line", "1", "--end-line", "3")):
            with self.subTest(extra=extra):
                result = self.cli("--source", "src/core.py", *extra)
                self.assertEqual(1, result.returncode)
                self.assertEqual("blocked", json.loads(result.stdout)["status"])

    def test_intent_loads_only_selected_fact_and_canonical_owner(self):
        self.write(".ai/project/source-of-truth-registry.md", registry(node="fact.behavior", coverage="mapped") +
                   "\n### Fact Type: `unrelated`\nCanonical owner: `missing.md`\n")
        result = self.cli("--purpose", "project-intent", "--fact-type", "behavior")
        self.assertEqual(0, result.returncode, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual("expansion-required", data["status"])
        self.assertEqual(["docs/decision.md"], [row["path"] for row in data["content"]])
        self.assertNotIn("unrelated", data["registry"]["declaration"])
        self.assertEqual("not-established-by-registry-metadata", data["registry"]["health"]["source_freshness"])
        self.assertEqual("declared-not-verified", data["registry"]["health"]["mapping"])

    def test_deferred_coverage_is_not_factual_non_applicability(self):
        data = json.loads(self.cli("--purpose", "change-impact", "--fact-type", "behavior").stdout)
        health = data["registry"]["health"]
        self.assertEqual("applicable", health["applicability"])
        self.assertEqual("accepted", health["authority"])
        self.assertEqual("unavailable", health["mapping"])
        self.assertIn("LOOKUP_COVERAGE_UNAVAILABLE", [row["code"] for row in data["findings"]])
        self.assertTrue(any("existing context profile and impact" in message for message in data["required_expansion"]))

    def test_status_like_node_identity_does_not_invent_a_coverage_gap(self):
        self.write(".ai/project/source-of-truth-registry.md", registry(node="deferred", coverage="mapped"))
        result = self.cli("--purpose", "project-intent", "--fact-type", "behavior")
        self.assertEqual(0, result.returncode, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual("declared-not-verified", data["registry"]["health"]["mapping"])
        self.assertNotIn("LOOKUP_COVERAGE_UNAVAILABLE", [row["code"] for row in data["findings"]])

    def test_current_observed_bytes_preserve_contradicted_authority(self):
        self.write(".ai/project/source-of-truth-registry.md", registry(authority="contradicted"))
        data = json.loads(self.cli("--source", "src/core.py", "--fact-type", "behavior").stdout)
        self.assertEqual("contradicted", data["registry"]["health"]["authority"])
        self.assertIn("LOOKUP_AUTHORITY_REVIEW", [row["code"] for row in data["findings"]])
        self.assertEqual("expansion-required", data["status"])

    def test_decision_owner_and_broad_owner_are_not_auto_selected_canonical_files(self):
        for line in ("Decision owner: `maintainers`", "Canonical owner: `docs/**`", "Canonical owner: `docs/`"):
            self.write(".ai/project/source-of-truth-registry.md", registry().replace("Canonical owner: `docs/decision.md`", line))
            with self.subTest(line=line):
                result = self.cli("--purpose", "project-intent", "--fact-type", "behavior")
                self.assertEqual(0, result.returncode, result.stderr)
                data = json.loads(result.stdout)
                self.assertEqual([], data["content"])
                self.assertIn("LOOKUP_OWNER_MISSING", [row["code"] for row in data["findings"]])

    def test_missing_duplicate_or_conflicting_fact_is_rejected(self):
        for text in ("# Empty", registry() + registry(), registry() + "Authority state: `observed`\n"):
            self.write(".ai/project/source-of-truth-registry.md", text)
            with self.subTest(text=text):
                result = self.cli("--purpose", "project-intent", "--fact-type", "behavior")
                self.assertEqual(1, result.returncode)
                self.assertNotIn("Traceback", result.stderr)

    def test_source_selection_shape_and_path_matrix(self):
        for sources in ({}, None, [None], [True], ["../secret"], ["/outside"], ["src/core.py", "SRC/core.py"]):
            with self.subTest(sources=sources), self.assertRaises(ValueError):
                project_lookup(self.target, "Explain", sources)
        for value in ({}, [], None, True, 3, ""):
            with self.subTest(question=value), self.assertRaises(ValueError):
                project_lookup(self.target, value, ["src/core.py"])

    def test_source_closure_count_boundary(self):
        for number in range(lookup.MAX_SOURCES + 1):
            self.write(f"src/{number}.py", "pass\n")
        for count in (lookup.MAX_SOURCES - 1, lookup.MAX_SOURCES, lookup.MAX_SOURCES + 1):
            sources = [f"src/{number}.py" for number in range(count)]
            with self.subTest(count=count):
                if count <= lookup.MAX_SOURCES:
                    self.assertEqual(count, len(project_lookup(self.target, "Explain", sources)["content"]))
                else:
                    with self.assertRaises(ValueError):
                        project_lookup(self.target, "Explain", sources)

    def test_content_word_and_byte_boundaries(self):
        for count in (lookup.MAX_CONTENT_WORDS - 1, lookup.MAX_CONTENT_WORDS, lookup.MAX_CONTENT_WORDS + 1):
            self.write("words.txt", "x " * count)
            with self.subTest(words=count):
                if count <= lookup.MAX_CONTENT_WORDS:
                    self.assertEqual(count, project_lookup(self.target, "Explain", ["words.txt"])["measurement"]["selected_content_words"])
                else:
                    with self.assertRaises(ValueError):
                        project_lookup(self.target, "Explain", ["words.txt"])
        for count in (lookup.MAX_CONTENT_BYTES - 1, lookup.MAX_CONTENT_BYTES, lookup.MAX_CONTENT_BYTES + 1):
            self.write("bytes.txt", "x" * count)
            with self.subTest(bytes=count):
                if count <= lookup.MAX_CONTENT_BYTES:
                    project_lookup(self.target, "Explain", ["bytes.txt"])
                else:
                    with self.assertRaises(ValueError):
                        project_lookup(self.target, "Explain", ["bytes.txt"])

    def test_question_word_and_character_boundaries(self):
        for count in (199, 200, 201):
            with self.subTest(words=count):
                if count <= 200:
                    project_lookup(self.target, "x " * count, ["src/core.py"])
                else:
                    with self.assertRaises(ValueError):
                        project_lookup(self.target, "x " * count, ["src/core.py"])
        for count in (1999, 2000, 2001):
            with self.subTest(characters=count):
                if count <= 2000:
                    project_lookup(self.target, "x" * count, ["src/core.py"])
                else:
                    with self.assertRaises(ValueError):
                        project_lookup(self.target, "x" * count, ["src/core.py"])

    def test_source_byte_ceiling_applies_even_to_a_tiny_excerpt(self):
        from project_evidence import MAX_FILE_BYTES
        for count in (MAX_FILE_BYTES - 1, MAX_FILE_BYTES, MAX_FILE_BYTES + 1):
            self.write("large.txt", "x\n" + "z" * (count - 2))
            with self.subTest(input_bytes=count):
                if count <= MAX_FILE_BYTES:
                    result = project_lookup(self.target, "Explain", ["large.txt"], start_line=1, end_line=1)
                    self.assertEqual(2, result["measurement"]["selected_content_bytes"])
                else:
                    with self.assertRaises(ValueError):
                        project_lookup(self.target, "Explain", ["large.txt"], start_line=1, end_line=1)

    def test_exact_serialized_report_boundary(self):
        result = project_lookup(self.target, "Explain", ["src/core.py"])
        size = len(lookup.render_lookup(result).encode())
        for maximum in (size - 1, size, size + 1):
            with self.subTest(maximum=maximum), patch.object(lookup, "MAX_REPORT_BYTES", maximum):
                if maximum < size:
                    with self.assertRaises(ValueError):
                        lookup.render_lookup(result)
                else:
                    self.assertEqual(size, len(lookup.render_lookup(result).encode()))

    def test_context_changes_during_delivery_block(self):
        original = ProjectEvidence.bindings
        def mutate(evidence):
            result = original(evidence)
            (self.target / "src/core.py").write_text("changed\n", encoding="utf-8")
            return result
        with patch.object(ProjectEvidence, "bindings", mutate), self.assertRaises(ValueError):
            project_lookup(self.target, "Explain", ["src/core.py"])

    def test_navigation_preserves_provenance_and_incomplete_coverage(self):
        for kind in ("symbol-reference", "text-match"):
            data = self.navigation_data()
            data["match_kind"] = kind
            with self.subTest(kind=kind):
                result = self.run_navigation(data)
                self.assertEqual(0, result.returncode, result.stderr)
                nav = json.loads(result.stdout)["navigation"]
                self.assertEqual("captured-not-authenticated", nav["provenance"])
                self.assertFalse(nav["complete_call_graph"])
                self.assertFalse(nav["absence_proven"])
                self.assertEqual("textual-candidates" if kind == "text-match" else "tool-reported-symbol-references", nav["resolution"])
        data["matches"] = []
        self.assertFalse(json.loads(self.run_navigation(data).stdout)["navigation"]["absence_proven"])

    def test_navigation_stale_and_unselected_sources_fail(self):
        data = self.navigation_data()
        for change in ("stale", "unselected", "query", "coverage", "line", "duplicate", "unbound"):
            candidate = copy.deepcopy(data)
            if change == "stale":
                candidate["source_bindings"][0]["sha256"] = "0" * 64
            elif change == "unselected":
                candidate["source_bindings"][0]["path"] = "docs/decision.md"
            elif change == "query":
                candidate["query"] = "Different question"
            elif change == "coverage":
                candidate["coverage"] = "repository-complete"
            elif change == "line":
                candidate["matches"][0]["line"] = 3
            elif change == "duplicate":
                candidate["matches"].append(candidate["matches"][0])
            else:
                candidate["matches"][0]["path"] = "docs/decision.md"
            with self.subTest(change=change):
                result = self.run_navigation(candidate)
                self.assertEqual(1, result.returncode, result.stderr)
                self.assertEqual("blocked", json.loads(result.stdout)["status"])

    def test_navigation_malformed_field_matrix_through_public_cli(self):
        original = self.navigation_data()
        for field in ("schema_version", "query", "backend", "match_kind", "coverage", "source_bindings", "matches", "limitations"):
            for value in ({}, None, True, 7, "unknown"):
                candidate = copy.deepcopy(original)
                candidate[field] = value
                with self.subTest(field=field, value=value):
                    result = self.run_navigation(candidate)
                    self.assertEqual(1, result.returncode, result.stderr)
                    self.assertEqual("blocked", json.loads(result.stdout)["status"])
                    self.assertNotIn("Traceback", result.stderr)
        for field in ("path", "line"):
            for value in ({}, [], None, True):
                candidate = copy.deepcopy(original)
                candidate["matches"][0][field] = value
                with self.subTest(match_field=field, value=value):
                    self.assertEqual(1, self.run_navigation(candidate).returncode)

    def test_navigation_match_count_boundary_and_unhashable_enums(self):
        from code_navigation import MAX_MATCHES
        self.write("src/core.py", "pass\n" * (MAX_MATCHES + 1))
        for count in (MAX_MATCHES - 1, MAX_MATCHES, MAX_MATCHES + 1):
            data = self.navigation_data()
            data["matches"] = [{"path": "src/core.py", "line": number + 1} for number in range(count)]
            with self.subTest(matches=count):
                self.assertEqual(0 if count <= MAX_MATCHES else 1, self.run_navigation(data).returncode)
        for value in ({}, [], None, False, 0, "unsupported"):
            data = self.navigation_data()
            data["match_kind"] = value
            with self.subTest(enum=value):
                result = self.run_navigation(data)
                self.assertEqual(1, result.returncode)
                self.assertNotIn("Traceback", result.stderr)

    def test_duplicate_json_members_and_option_abbreviations_are_rejected(self):
        raw = json.dumps(self.navigation_data()).replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')
        self.navigation.write_text(raw, encoding="utf-8")
        self.assertEqual(1, self.cli("--source", "src/core.py", "--navigation-report", str(self.navigation)).returncode)
        for args in (("--purp", "observed-code"), ("--purpose", "observed-code", "--purpose", "observed-code")):
            self.assertEqual(2, self.cli("--source", "src/core.py", *args).returncode)

    def test_installed_lookup_cannot_rebind_target_through_remainder(self):
        result = self.cli("--source", "src/core.py", "--target", str(self.base), delegate=True)
        self.assertEqual(2, result.returncode)
        self.assertIn("may be supplied only once", result.stderr)

    def test_external_navigation_report_stays_bound_until_delivery(self):
        self.navigation.write_text(json.dumps(self.navigation_data()), encoding="utf-8")
        original = ProjectEvidence.bindings
        def mutate(evidence):
            result = original(evidence)
            if evidence.root == self.target:
                self.navigation.write_text("{}", encoding="utf-8")
            return result
        with patch.object(ProjectEvidence, "bindings", mutate), self.assertRaises(ValueError):
            project_lookup(self.target, "What does field_count do?", ["src/core.py"], navigation_report=self.navigation)

    def test_nested_snapshot_context_is_restored_with_optional_capture(self):
        from context_input_snapshot import _ACTIVE
        self.navigation.write_text(json.dumps(self.navigation_data()), encoding="utf-8")
        before = _ACTIVE.get()
        with ProjectEvidence(self.target) as outer:
            project_lookup(self.target, "What does field_count do?", ["src/core.py"], navigation_report=self.navigation)
            self.assertIs(outer, _ACTIVE.get())
        self.assertIs(before, _ACTIVE.get())

    def test_projection_review_reuses_source_bound_architecture_review(self):
        def save_review(digest):
            self.write(lookup.ARCHITECTURE_PATH, json.dumps({"schema_version": 2,
                "catalog_kind": "target-architecture-knowledge-catalog", "module_state": "enabled", "areas": [{
                "id": "core", "status": "accepted", "source_review": {
                    "state": "reviewed", "reason": "Owner review", "reviewer": "maintainer",
                    "reviewed_at": "2026-01-01T00:00:00Z", "changed_fact_ids": ["behavior"],
                    "inputs": [{"path": "docs/decision.md", "sha256": digest}]}}], "patterns": []}))
        digest = hashlib.sha256((self.target / "docs/decision.md").read_bytes()).hexdigest()
        save_review(digest)
        first = json.loads(self.cli("--source", "src/core.py", "--architecture-item", "core").stdout)
        self.assertEqual("current-bindings-only", first["projection"]["source_review"])
        self.write("docs/decision.md", "# Changed decision\n")
        stale = json.loads(self.cli("--source", "src/core.py", "--architecture-item", "core").stdout)
        self.assertEqual("revalidation-required", stale["projection"]["source_review"])
        self.assertEqual("expansion-required", stale["status"])
        self.assertEqual("canonical-owners-not-replaced", stale["projection"]["authority"])


if __name__ == "__main__":
    unittest.main()
