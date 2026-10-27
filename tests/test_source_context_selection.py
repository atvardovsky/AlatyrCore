import json
import hashlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from contextlib import contextmanager, redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from source_context_selection import bootstrap_outputs, project_file
import source_context_selection as selection
from plan_minimum_work import build_source_profile_context, measure_source_context, resolve_source_conditionals


@contextmanager
def isolated_source_git():
    """Use current source bytes with private refs, objects and index, never checkout."""
    with tempfile.TemporaryDirectory(prefix="alatyr-source-cli-") as directory:
        metadata = Path(directory) / "metadata"
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                   GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid",
                   PYTHONDONTWRITEBYTECODE="1")
        subprocess.run(["git", "init", "-q", str(metadata)], env=env, check=True, capture_output=True)
        env.update(GIT_DIR=str(metadata / ".git"), GIT_WORK_TREE=str(ROOT),
                   GIT_INDEX_FILE=str(metadata / ".git/index"))

        def git(*args, input=None):
            return subprocess.run(
                ["git", "-c", "core.autocrlf=false", "-c", "commit.gpgSign=false", *args],
                cwd=ROOT, env=env, input=input, check=True, capture_output=True,
            ).stdout.decode("utf-8").strip()

        # The remote is deliberately stale. Only the private baseline is authoritative.
        empty_tree = git("mktree", input=b"")
        stale = git("commit-tree", empty_tree, "-m", "stale fixture baseline")
        git("add", "--all", "--", ".")
        tree = git("write-tree")
        baseline = git("commit-tree", tree, "-p", stale, "-m", "current source bytes")
        git("update-ref", "HEAD", baseline)
        git("update-ref", "refs/remotes/origin/main", stale)
        yield env, git, baseline, stale, empty_tree


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

    def test_development_context_contract_is_not_read_by_routine_profiles(self):
        router = json.loads((ROOT / "tools/source_context_router.json").read_text())
        strategy_paths = {
            ROOT / "docs/source-architecture.md",
            ROOT / "docs/source-optimization-workflow.md",
        }
        opened = []
        original_open = Path.open

        def observed_open(path, *args, **kwargs):
            if path in strategy_paths:
                opened.append(path)
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", observed_open):
            for profile in router["profiles"]:
                with self.subTest(profile=profile):
                    context = build_source_profile_context(profile)
                    self.assertNotIn(
                        "docs/source-architecture.md",
                        context["context_budget"]["resolved"]["paths"],
                    )
                    self.assertNotIn(
                        "docs/source-optimization-workflow.md",
                        context["context_budget"]["resolved"]["paths"],
                    )
        self.assertEqual(opened, [])

    def test_development_context_contract_uses_existing_section_routes(self):
        path = "docs/source-architecture.md"
        for profile in ("source-tooling", "repository-audit"):
            with self.subTest(profile=profile):
                default = build_source_profile_context(profile)
                context = build_source_profile_context(
                    profile,
                    selector_values={"architecture_topics": ["development-context-contract"]},
                )
                view = context["context_projections"][path]
                self.assertEqual(context["readiness"]["status"], "ready")
                self.assertEqual(view, project_file(ROOT, path, ["development-context-contract"]))
                self.assertTrue(view["content"].startswith("## Development Context Contract\n"))
                self.assertNotIn("## Engineering Principles", view["content"])
                self.assertNotIn("## Extraction Rules", view["content"])
                self.assertIn("source-optimization-workflow.md#development-context-contract", view["content"])
                self.assertLessEqual(len(view["content"].split()), 100)
                self.assertLessEqual(len(view["content"]), 1000)
                self.assertTrue(
                    set(default["context_budget"]["resolved"]["paths"])
                    <= set(context["context_budget"]["resolved"]["paths"])
                )
                self.assertTrue(context["context_budget"]["reserved_capacity_preserved"])

    def test_development_context_selection_retains_required_whole_file_priority(self):
        path = "docs/source-architecture.md"
        context = build_source_profile_context(
            "source-tooling",
            selector_values={
                "architecture_topics": ["development-context-contract"],
                "contract_paths": [path],
            },
        )
        self.assertEqual(context["readiness"]["status"], "ready")
        self.assertNotIn(path, context["context_projections"])
        self.assertIn(path, context["context_budget"]["resolved"]["paths"])

    def test_development_context_guide_is_loaded_only_by_explicit_contract_routes(self):
        path = "docs/source-optimization-workflow.md"
        guide = (ROOT / path).read_text(encoding="utf-8")
        contract = project_file(ROOT, path, ["development-context-contract"])["content"]
        self.assertLessEqual(len(contract.split()), 850)
        self.assertLessEqual(len(contract), 7500)
        for profile, selector in (
            ("source-tooling", "contract_paths"),
            ("repository-audit", "audit_context_paths"),
        ):
            with self.subTest(profile=profile):
                context = build_source_profile_context(profile, selector_values={selector: [path]})
                self.assertEqual(context["readiness"]["status"], "ready")
                self.assertNotIn(path, context["context_projections"])
                self.assertIn(path, context["context_budget"]["resolved"]["paths"])
                self.assertIn("## Development Context Contract", guide)
                self.assertTrue(context["context_budget"]["reserved_capacity_preserved"])

    def test_public_cli_delivers_strategy_section_and_blocks_unknown_section(self):
        path = "docs/source-architecture.md"
        command = [
            sys.executable, str(ROOT / "tools/alatyr.py"), "plan-work",
            "--source-profile", "source-tooling", "--changed-from", "HEAD", "--compact",
            "--context-selector",
        ]
        with isolated_source_git() as (env, _, _, _, _):
            self.check_strategy_cli(command, env, path)

    def check_strategy_cli(self, command, env, path):
        for section, status in (
            ("development-context-contract", "ready"),
            ("development-context-contract-missing", "needs-expansion"),
        ):
            with self.subTest(section=section):
                result = subprocess.run(
                    [*command, "architecture_topics=" + section],
                    cwd=ROOT, env=env, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                view = json.loads(result.stdout)
                self.assertEqual(view["context_readiness"]["status"], status)
                if status == "ready":
                    self.assertEqual(
                        view["context_projections"][path]["content"],
                        project_file(ROOT, path, [section])["content"],
                    )
                else:
                    self.assertNotIn(path, view.get("context_projections", {}))
                    self.assertTrue(view["context_readiness"]["reasons"])
                self.assertNotIn("Traceback", result.stderr)

    def test_public_cli_preserves_dirty_context_and_real_budget_blockers(self):
        command = [sys.executable, str(ROOT / "tools/alatyr.py"), "plan-work",
                   "--source-profile", "source-tooling", "--changed-from", "HEAD", "--compact"]
        with isolated_source_git() as (env, git, baseline, stale, empty_tree):
            blob = git("hash-object", "-w", "--stdin", input=b"different fixture documentation\n")
            git("update-index", "--cacheinfo", "100644", blob, "tools/README.md")
            dirty = git("commit-tree", git("write-tree"), "-p", baseline, "-m", "different source baseline")
            git("update-ref", "HEAD", dirty)
            result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            view = json.loads(result.stdout)
            self.assertIn("tools/README.md", [item["path"] for item in view["selected_sources"]])
            self.assertNotIn("tools/README.md", view["context_projections"])

            # Leave real files untouched while exposing a genuinely broad dirty diff.
            git("update-ref", "HEAD", stale)
            git("read-tree", empty_tree)
            result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            view = json.loads(result.stdout)
            self.assertEqual(view["context_readiness"]["status"], "needs-expansion")
            self.assertTrue(any("budget" in reason for reason in view["context_readiness"]["reasons"]))

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
        command = [sys.executable, str(ROOT / "tools/alatyr.py"), "plan-work", "--source-profile", "framework-rule", "--changed-from", "HEAD", "--context-selector", "rule_ids=ALATYR-CONTEXT-001", "--compact"]
        with isolated_source_git() as (env, _, _, _, _):
            result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            view = json.loads(result.stdout)
            self.assertIn("framework/rule-registry.json", view["context_projections"])
            self.assertIn("not acceptance evidence", view["full_receipt"])
            self.assertNotIn("input_fingerprints", view)
            result = subprocess.run([*command, "--context-selector", "invalid"], cwd=ROOT, env=env, capture_output=True, text=True)
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
