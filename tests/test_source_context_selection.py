import json
import hashlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from source_context_selection import bootstrap_outputs, project_file
import source_context_selection as selection
from plan_minimum_work import build_source_profile_context, measure_source_context, resolve_source_conditionals


class SourceContextSelectionTests(unittest.TestCase):
    def test_exact_json_record_and_unknown_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "index.json"
            path.write_text(json.dumps({"checks": [{"id": "a", "depends_on": ["b"]}, {"id": "b"}]}))
            view = project_file(root, "index.json", ["a"])
            self.assertEqual(json.loads(view["content"])["checks"], [{"id": "a", "depends_on": ["b"]}])
            self.assertEqual(len(view["source_sha256"]), 64)
            for value in ("missing", "a-suffix"):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    project_file(root, "index.json", [value])
            path.write_text('{"checks":[{"id":"a"},{"id":"a"}]}')
            with self.assertRaisesRegex(ValueError, "ambiguous"):
                project_file(root, "index.json", ["a"])

    def test_markdown_sections_exclude_fenced_headings_and_reject_ambiguity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "guide.md"
            path.write_text("# Guide\n## Selected\nKeep this.\n```md\n## Fake\n```\n### Child\nKeep child.\n## Other\nExclude this.\n")
            view = project_file(root, "guide.md", ["selected"])
            self.assertIn("Keep child", view["content"])
            self.assertNotIn("Exclude this", view["content"])
            with self.assertRaises(ValueError):
                project_file(root, "guide.md", ["fake"])
            path.write_text("## Same\none\n## Same\ntwo\n")
            with self.assertRaisesRegex(ValueError, "ambiguous"):
                project_file(root, "guide.md", ["same"])

    def test_explicit_unknown_route_retains_a_blocker(self):
        context = build_source_profile_context("framework-rule", selector_values={"rule_ids": ["ALATYR-NONEXISTENT-001"]})
        self.assertEqual(context["readiness"]["status"], "needs-expansion")
        self.assertTrue(any(item.get("unresolved_selectors") for item in context["omitted_candidates"]))
        self.assertTrue(context["owner_fallbacks"])
        for selectors in ({"contract_paths": ["/etc/passwd"]}, {"requested_paths": ["framework/context-profiles.md"]}):
            with self.subTest(selectors=selectors):
                context = build_source_profile_context("source-tooling", selector_values=selectors)
                self.assertEqual(context["readiness"]["status"], "needs-expansion")
                self.assertNotIn("/etc/passwd", context["context_budget"]["resolved"]["paths"])

    def test_rule_projection_keeps_canonical_owner_and_reduces_registry_payload(self):
        context = build_source_profile_context("framework-rule", selector_values={"rule_ids": ["ALATYR-CONTEXT-001"]})
        view = context["context_projections"]["framework/rule-registry.json"]
        self.assertEqual([item["id"] for item in json.loads(view["content"])["rules"]], ["ALATYR-CONTEXT-001"])
        self.assertLess(len(view["content"]), (ROOT / view["path"]).stat().st_size)
        self.assertIn("framework/context-profiles.md", context["context_budget"]["resolved"]["paths"])
        self.assertNotIn("framework/context-profiles.md", context["context_projections"])

    def test_changed_whole_file_is_not_replaced_by_a_section(self):
        context = build_source_profile_context("source-tooling", changed_paths=["tools/README.md"], selector_values={"cli_topics": ["worker-context-preparation"]})
        self.assertNotIn("tools/README.md", context["context_projections"])

    def test_generated_descriptors_are_exact_and_do_not_widen_limits(self):
        router = json.loads((ROOT / "tools/source_context_router.json").read_text())
        for name, text in bootstrap_outputs().items():
            with self.subTest(name=name):
                self.assertEqual((ROOT / name).read_text(), text)
                if "/profiles/" in name:
                    data = json.loads(text)
                    self.assertEqual(data["context_budget"], router["profiles"][data["source_profile"]]["context_budget"])
        index = json.loads((ROOT / selection.BOOTSTRAP).read_text())
        for entry in index["profiles"].values():
            self.assertEqual(hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest(), entry["content_sha256"])

    def test_generator_preserves_exact_lf_bytes_and_detects_crlf_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "tools/source_context_router.json").write_bytes((ROOT / "tools/source_context_router.json").read_bytes())
            with patch.object(selection, "ROOT", root), patch.object(sys, "argv", ["render-source-context", "--write"]), redirect_stdout(io.StringIO()):
                self.assertEqual(selection.main(), 0)
            path = root / "tools/source-context/profiles/docs-local.json"
            canonical = path.read_bytes()
            self.assertNotIn(b"\r\n", canonical)
            path.write_bytes(canonical.replace(b"\n", b"\r\n"))
            with patch.object(selection, "ROOT", root), patch.object(sys, "argv", ["render-source-context", "--check"]), redirect_stdout(io.StringIO()):
                self.assertEqual(selection.main(), 1)
            with patch.object(selection, "ROOT", root), patch.object(sys, "argv", ["render-source-context", "--write"]), redirect_stdout(io.StringIO()):
                self.assertEqual(selection.main(), 0)
            self.assertEqual(path.read_bytes(), canonical)

    def test_malformed_router_and_profile_path_injection_fail_before_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            router = json.loads((ROOT / "tools/source_context_router.json").read_text())
            for profiles in (None, [], True, {"../../escape": {"check_profile": "fast"}}, {"docs-local": []}):
                with self.subTest(profiles=profiles):
                    mutated = dict(router, profiles=profiles)
                    (root / "tools/source_context_router.json").write_text(json.dumps(mutated))
                    with self.assertRaises(ValueError):
                        bootstrap_outputs(root)
            self.assertFalse((root / "tools/source-context").exists())

    def test_public_cli_materializes_exact_selector_and_rejects_invalid_shape(self):
        command = [sys.executable, str(ROOT / "tools/alatyr.py"), "plan-work", "--source-profile", "framework-rule", "--context-selector", "rule_ids=ALATYR-CONTEXT-001", "--compact"]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        view = json.loads(result.stdout)
        self.assertIn("framework/rule-registry.json", view["context_projections"])
        self.assertIn("not acceptance evidence", view["full_receipt"])
        self.assertNotIn("input_fingerprints", view)
        result = subprocess.run([*command, "--context-selector", "invalid"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_unsafe_or_missing_projection_fails_closed(self):
        for path in ("../outside.json", "/etc/passwd", "missing.json"):
            with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                project_file(ROOT, path, ["id"])
        result = measure_source_context(["../outside.json", "/etc/passwd"])
        self.assertEqual(result["resolved_paths"], [])
        self.assertEqual(len(result["unresolved_paths"]), 2)

    def test_symlink_loop_returns_a_source_path_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            try:
                (root / "loop.json").symlink_to("loop.json")
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            with self.assertRaisesRegex(ValueError, "symlink"):
                project_file(root, "loop.json", ["id"])

    def test_indexed_owner_failure_cannot_be_hidden_by_a_valid_projection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "framework").mkdir()
            (root / "framework/rule-registry.json").write_text(json.dumps({"rules": [{"id": "ALATYR-TEST-001", "canonical_source": "framework/missing.md"}]}))
            (root / "index.json").write_text(json.dumps({"entries": [{"id": "entry", "owner_refs": ["ALATYR-TEST-001"]}]}))
            selected, omitted = resolve_source_conditionals([{"id": "owner", "resolver": "indexed-query", "path_or_registry_query": "index.json#selector=rule_ids", "when": "test", "owner_rule_id": "$rule_id"}], {"rule_ids": ["ALATYR-TEST-001"]}, root=root)
            self.assertEqual(selected, [])
            self.assertEqual(omitted[0]["unresolved_owner_rule_ids"], ["ALATYR-TEST-001"])

    def test_validation_only_checks_do_not_expand_context_metadata(self):
        context = build_source_profile_context("source-tooling", selection_details={"check-manifest": {"reasons": ["full-profile"]}})
        self.assertEqual(context["selectors"]["check_ids"], [])
        self.assertNotIn("tools/check_manifest.json", context["context_projections"])

    def test_duplicate_fields_malformed_owners_and_bad_selectors_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for text in ('{"checks":[],"checks":[{"id":"a"}]}', '{"entries":[{"id":"a","owner_refs":[{}]}]}',
                         '{"checks":[{"id":"a","cost":NaN}]}', '{"checks":[{"id":"a"}],"rules":[{"id":"a"}]}',
                         '{"checks":{"a":{}}}', '{"stages":[{"id":"a"}]}'):
                (root / "index.json").write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    project_file(root, "index.json", ["a"])
        for value in (None, True, {}, "id", [None], [{}]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                project_file(ROOT, "tools/check_manifest.json", value)
