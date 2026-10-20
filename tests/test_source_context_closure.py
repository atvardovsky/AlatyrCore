import copy
import io
import json
import math
import sys
import tempfile
import unittest
import shutil
import subprocess
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import source_context_selection as selection
import plan_minimum_work as planner
import check_source_context_routing as checker


class SourceContextClosureTests(unittest.TestCase):
    def test_malformed_route_lists_are_contract_errors_not_type_crashes(self):
        for field in ("preloaded_context", "bootstrap_context", "required_context"):
            for bad in (None, True, {}, "AGENTS.md", [{}]):
                router = selection.read_source_object(ROOT, "tools/source_context_router.json")
                owner = router["profiles"]["source-tooling"] if field == "required_context" else router
                owner[field] = bad
                with self.subTest(field=field, bad=bad), patch.object(planner, "_load_source_router", return_value=router):
                    with self.assertRaisesRegex(ValueError, field):
                        planner.build_source_profile_context("source-tooling")

    def test_public_generator_noop_and_parent_symlink_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            shutil.copytree(ROOT / "tools", root / "tools", ignore=shutil.ignore_patterns("__pycache__"))
            args = [sys.executable, str(root / "tools/source_context_selection.py")]
            written = subprocess.run([*args, "--write"], capture_output=True, text=True)
            self.assertEqual(written.returncode, 0, written.stderr)
            checked = subprocess.run([*args, "--check"], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            parent = root / "tools/source-context/profiles"
            outside = Path(directory) / "profiles"
            parent.rename(outside)
            try:
                parent.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(str(exc))
            for mode in ("--check", "--write"):
                bad = subprocess.run([*args, mode], capture_output=True, text=True)
                self.assertEqual(bad.returncode, 2, bad.stderr)
                self.assertIn("symlink", bad.stderr)
                self.assertNotIn("Traceback", bad.stderr)
            self.assertTrue(parent.is_symlink())

    def test_planner_and_checker_enforce_required_limits_from_same_profile(self):
        router = selection.read_source_object(ROOT, "tools/source_context_router.json")
        profile = router["profiles"]["framework-rule"]
        profile["context_budget"].update(max_required_files=1, max_required_words=1)
        with patch.object(planner, "_load_source_router", return_value=router):
            context = planner.build_source_profile_context("framework-rule")
        self.assertEqual(context["readiness"]["status"], "needs-expansion")
        for dimension in ("required-file", "required-word"):
            self.assertTrue(any(dimension in reason for reason in context["readiness"]["reasons"]))
        failures = []
        checker.validate_source_profile_budget("framework-rule", profile,
            [*router["preloaded_context"], *router["bootstrap_context"]], failures)
        for dimension in ("required-file", "required-word"):
            self.assertTrue(any(dimension in reason for reason in failures))

    def test_nonfinite_decoding_and_encoding_reject_without_changing_finite_bytes(self):
        for token in ("1e400", "-1e400", "NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token), self.assertRaises(ValueError):
                selection.source_json('{"checks":[{"id":"a","cost":' + token + '}]}')
        for value in (math.inf, -math.inf, math.nan):
            with self.subTest(value=value), self.assertRaises(ValueError):
                selection.encoded({"nested": [value]})
        value = {"checks": [{"id": "a", "cost": 1e308, "count": 12345678901234567890}]}
        self.assertEqual(selection.source_json(selection.encoded(value)), value)
        self.assertEqual(selection.encoded(value), json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n")

    def test_duplicate_authority_keys_leave_owners_unresolved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "framework").mkdir()
            (root / "framework/good.md").write_text("valid owner")
            for fields in ('"canonical_source":"framework/missing.md","canonical_source":"framework/good.md"',
                           '"canonical_source":"framework/good.md","canonical_source":"framework/good.md"'):
                (root / "framework/rule-registry.json").write_text('{"rules":[{"id":"ALATYR-TEST-001",' + fields + '}]}')
                self.assertEqual(planner._canonical_owner_paths("ALATYR-TEST-001", [], root=root), ([], ["ALATYR-TEST-001"]))

    def test_equal_byte_symlink_rejected_before_any_output_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            (root / "tools").mkdir(parents=True)
            (root / "tools/source_context_router.json").write_bytes((ROOT / "tools/source_context_router.json").read_bytes())
            outputs = selection.bootstrap_outputs(root)
            for name, content in outputs.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            link = root / "tools/source-context/profiles/docs-local.json"
            outside = Path(directory) / "outside.json"
            outside.write_bytes(link.read_bytes())
            original = outside.read_bytes()
            link.unlink()
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(str(exc))
            other = root / "tools/source-context/profiles/source-tooling.json"
            other.write_text("stale output")
            for mode in ("--check", "--write"):
                with self.subTest(mode=mode), patch.object(selection, "ROOT", root), patch.object(sys, "argv", ["source-context", mode]), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        selection.main()
                    self.assertEqual(error.exception.code, 2)
                self.assertTrue(link.is_symlink())
                self.assertEqual(outside.read_bytes(), original)
                self.assertEqual(other.read_text(), "stale output")

    def test_shared_budget_boundary_and_zero_required_context(self):
        budget = {"max_required_files": 2, "max_required_words": 10, "max_initial_words": 20,
            "max_resolved_files": 5, "max_resolved_words": 30, "max_resolved_characters": 300,
            "reserved_files": 1, "reserved_words": 5, "reserved_characters": 30}
        resolved = {"resolved_files": 4, "resolved_words": 25, "resolved_characters": 270}
        kwargs = dict(required_files=2, required_words=10, initial_words=20, resolved=resolved)
        self.assertEqual(selection.evaluate_source_budget(budget, **kwargs)["failures"], [])
        for field in ("required_files", "required_words", "initial_words"):
            for delta in (-1, 0, 1):
                mutant = dict(kwargs)
                mutant[field] += delta
                with self.subTest(field=field, delta=delta):
                    self.assertEqual(bool(selection.evaluate_source_budget(budget, **mutant)["failures"]), delta > 0)
        for dimension in ("files", "words", "characters"):
            for delta in (-1, 0, 1):
                mutant = dict(resolved)
                mutant["resolved_" + dimension] += delta
                with self.subTest(dimension=dimension, delta=delta):
                    self.assertEqual(bool(selection.evaluate_source_budget(budget, **dict(kwargs, resolved=mutant))["failures"]), delta > 0)
        for bad in (None, True, {}, "unknown", -1):
            mutant = dict(budget, max_required_files=bad)
            self.assertTrue(selection.evaluate_source_budget(mutant, **kwargs)["failures"])
        empty = dict(budget, max_required_files=0, max_required_words=0)
        self.assertEqual(selection.evaluate_source_budget(empty, **dict(kwargs, required_files=0, required_words=0))["failures"], [])

    def test_compact_view_keeps_required_path_and_does_not_mutate_full_plan(self):
        context = planner.build_source_profile_context("source-tooling")
        path = "conformance/runs/assistant-surfaces.json"
        context["context_budget"]["resolved"]["unresolved_paths"] = [path]
        context["readiness"] = {"status": "needs-expansion", "reasons": ["required path missing"]}
        plan = {"context_packet": context, "source_profile": "source-tooling", "task_classification": {},
            "check_plan": [], "validation_profiles": [], "selection": {}, "delegation_assessment": {},
            "reuse": {"reusable_check_ids": []}, "quality_boundary": "planning only"}
        original = copy.deepcopy(plan)
        view = selection.compact_plan(plan)
        self.assertEqual(view["unresolved_paths"], [path])
        self.assertEqual(view["context_readiness"]["status"], "needs-expansion")
        self.assertEqual(plan, original)
        paths = [f"missing/{number}.md" for number in range(40)]
        plan["context_packet"]["context_budget"]["resolved"]["unresolved_paths"] = paths
        view = selection.compact_plan(plan)
        self.assertEqual(view["unresolved_paths"], paths[:32])
        self.assertEqual(view["unresolved_path_count"], 40)
        self.assertEqual(view["omitted_unresolved_path_count"], 8)
        self.assertIn("without --compact", view["full_receipt"])
        self.assertEqual(plan["context_packet"]["context_budget"]["resolved"]["unresolved_paths"], paths)
