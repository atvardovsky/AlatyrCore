from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_lifecycle_conformance import (  # noqa: E402
    approval_record, mark_fixture_selected_assistant, refresh_context_and_bootstrap,
    resolve_adapter, run_git, transition_installation_state,
)
from render_installed_context_catalogs import expected_outputs  # noqa: E402
from scaffold_target_structure import plan as scaffold_plan  # noqa: E402
from target_adapter_validation.harness_scenarios.common import validator, write_json  # noqa: E402
from validate_target_adapter import parse_manifest  # noqa: E402
import yaml  # noqa: E402


MODULES = ["installed-operations", "project-vocabulary", "team-collaboration"]
TASKS = ".ai/assistant/team/tasks"
LINKS = ".ai/project/vocabulary/data-dictionary-links.json"


def read_json(target: Path, path: str) -> dict:
    return json.loads((target / path).read_bytes())


def configure_records(target: Path) -> None:
    """Install concrete, synthetic records on the real projected module layout."""
    template = ROOT / "templates/target"

    def resolved(path: str) -> dict:
        return json.loads(re.sub(r"\{[A-Z][A-Z0-9_]*\}", "fixture-value",
                                 (template / path).read_text(encoding="utf-8")))

    policy = resolved(".ai/project/team-policy.json")
    actor = policy["actors"][0]
    actor.update(id="owner", aliases=[], status="active")
    policy.update(actors=[actor], priorities=[{"id": "normal", "assigner_actor_ids": ["owner"]}],
                  state_transitions=[])
    write_json(target / ".ai/project/team-policy.json", policy)
    (target / ".ai/project/team-operating-model.md").write_text(
        "# Team\n\n### Actor `owner`\n\n### Priority `normal`\n", encoding="utf-8")
    registry = resolved(".ai/assistant/team/work-registry.json")
    registry.update(module_state="enabled", evidence_revision=run_git(target, "rev-parse", "HEAD"))
    write_json(target / ".ai/assistant/team/work-registry.json", registry)
    backend = resolved(".ai/assistant/team/backend-contract.json")
    backend.update(backend_mode="repository", capabilities=["read-tasks"])
    write_json(target / ".ai/assistant/team/backend-contract.json", backend)
    active = resolved(".ai/assistant/team/active-work-index.json")
    active["entries"] = []
    write_json(target / ".ai/assistant/team/active-work-index.json", active)
    task = resolved(".ai/assistant/team/task-record-template.json")
    task.update(id="TASK-1", status="complete", priority="normal",
                priority_decided_by="owner", owner_actor_id="owner",
                requested_by_actor_id="owner", last_updated_by_actor_id="owner",
                assistant_actor_id="none", reviewer_actor_ids=[], review_state="not-required",
                validation_state="passed", handoff_state="none", allowed_actions=["read-only"])
    task["claim"].update(state="released", mode="advisory", actor_id="owner")
    task["overlap"]["state"] = "none"
    task["transition"].update({"from": "none", "to": "complete", "changed_by_actor_id": "owner"})
    write_json(target / TASKS / "TASK-1.json", task)

    term_data = resolved(".ai/project/vocabulary/terms.json")
    term = term_data["terms"][0]
    term.update(id="TERM-1", state="accepted", replacement_term_id="none",
                aliases=[], acronyms=[], related_term_ids=[], data_dictionary_refs=["LINK-1"],
                canonical_sources=["README.md"])
    write_json(target / ".ai/project/vocabulary/terms.json", term_data)
    catalog = resolved(".ai/project/vocabulary/catalog.json")
    entry = catalog["entries"][0]
    for field in ("canonical_term", "normalized_term", "aliases", "acronyms", "domains",
                  "state", "replacement_term_id", "last_verified_revision"):
        entry[field] = term[field]
    entry.update(term_id=term["id"], record=".ai/project/vocabulary/terms.json#TERM-1")
    catalog["module_state"] = "enabled"
    write_json(target / ".ai/project/vocabulary/catalog.json", catalog)
    links = resolved(LINKS)
    links["links"][0].update(id="LINK-1", term_id="TERM-1", canonical_owner="README.md")
    write_json(target / LINKS, links)


class AdapterRecordIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed_directory = tempfile.TemporaryDirectory()
        cls.seed = Path(cls.seed_directory.name).resolve()
        run_git(cls.seed, "init", "-q")
        run_git(cls.seed, "config", "user.name", "Adapter Fixture")
        run_git(cls.seed, "config", "user.email", "fixture@example.invalid")
        run_git(cls.seed, "config", "core.autocrlf", "false")
        (cls.seed / "README.md").write_bytes(b"# Synthetic project\n")
        run_git(cls.seed, "add", ".")
        run_git(cls.seed, "commit", "-qm", "seed fixture")
        actions, blocked = scaffold_plan(SimpleNamespace(
            target=cls.seed, write=True, overwrite_existing=False, profile="full",
            framework_pack="matched", enable_module=MODULES, assistant_surface=[]))
        if blocked or not actions:
            raise AssertionError(blocked)
        resolve_adapter(cls.seed, "full")
        manifest_path = cls.seed / ".ai/alatyr.yaml"
        manifest = yaml.safe_load(manifest_path.read_bytes())
        manifest["modules"].update(selected=MODULES, enabled=MODULES, staged=[], deferred=[])
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        profile = cls.seed / ".ai/assistant/module-profile.md"
        text = profile.read_text(encoding="utf-8")
        for module in MODULES:
            text = re.sub(rf"(Module: `{module}`\s*\nState:) [^\n]+", r"\1 enabled", text)
        profile.write_text(text, encoding="utf-8")
        configure_records(cls.seed)
        mark_fixture_selected_assistant(cls.seed)

    @classmethod
    def tearDownClass(cls):
        cls.seed_directory.cleanup()

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.target = Path(directory.name).resolve() / "target"
        shutil.copytree(self.seed, self.target)

    def findings(self, module: str):
        check = validator(self.target)
        manifest = parse_manifest(self.target / ".ai/alatyr.yaml")
        getattr(check, "check_" + module)(manifest)
        return check.findings

    def generate(self):
        for path, text in expected_outputs(self.target).items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))

    def test_generated_task_catalog_is_not_a_task(self):
        self.assertFalse([f for f in self.findings("team_collaboration") if f.level == "error"])
        self.generate()
        self.assertTrue((self.target / TASKS / "context-index.json").is_file())
        self.assertFalse([f for f in self.findings("team_collaboration") if f.level == "error"])

    def test_unrelated_invalid_json_is_not_hidden_by_catalog_filter(self):
        self.generate()
        write_json(self.target / TASKS / "invalid.json", {"index_kind": "alatyr-context-index"})
        findings = self.findings("team_collaboration")
        self.assertTrue(any(f.code == "TEAM_TASK_SCHEMA" and f.path.endswith("invalid.json") for f in findings))
        (self.target / TASKS / "broken.json").write_bytes(b"{")
        self.assertTrue(any(f.level == "error" and f.path.endswith("broken.json")
                            for f in self.findings("team_collaboration")))

    def test_owner_reference_types_and_paths(self):
        links = read_json(self.target, LINKS)
        cases = [
            (None, "VOCABULARY_LINK_UNRESOLVED"),
            ({}, "VOCABULARY_LINK_UNRESOLVED"),
            ([], "VOCABULARY_LINK_UNRESOLVED"),
            (True, "VOCABULARY_LINK_UNRESOLVED"),
            (42, "VOCABULARY_LINK_UNRESOLVED"),
            ("{OWNER}", "VOCABULARY_LINK_UNRESOLVED"),
            ("unknown", "VOCABULARY_LINK_UNRESOLVED"),
            ("https://example.invalid/owner", "VOCABULARY_LINK_OWNER_REFERENCE_KIND"),
            ("provider:owner", "VOCABULARY_LINK_OWNER_REFERENCE_KIND"),
            ("file:///tmp/owner", "VOCABULARY_LINK_OWNER_REFERENCE_KIND"),
            ("C:/owner.md", "VOCABULARY_LINK_OWNER_REFERENCE_KIND"),
            ("../owner.md", "VOCABULARY_LINK_OWNER_PATH"),
            ("/owner.md", "VOCABULARY_LINK_OWNER_PATH"),
            ("docs\\owner.md", "VOCABULARY_LINK_OWNER_PATH"),
            ("docs/../README.md", "VOCABULARY_LINK_OWNER_PATH"),
            ("docs/*.md", "VOCABULARY_LINK_OWNER_PATH"),
            ("README.md#", "VOCABULARY_LINK_OWNER_PATH"),
            (".ai/project", "VOCABULARY_LINK_OWNER_MISSING"),
            ("DataOwner", "VOCABULARY_LINK_OWNER_MISSING"),
        ]
        for owner, code in cases:
            with self.subTest(owner=owner):
                links["links"][0]["canonical_owner"] = owner
                write_json(self.target / LINKS, links)
                self.assertIn(code, [f.code for f in self.findings("project_vocabulary")])
        for owner in ("README.md", "README.md#synthetic-project", "docs/Owner [id].md"):
            with self.subTest(owner=owner):
                path = self.target / owner.partition("#")[0]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
                links["links"][0]["canonical_owner"] = owner
                write_json(self.target / LINKS, links)
                self.assertFalse([f for f in self.findings("project_vocabulary") if f.level == "error"])

    def test_owner_symlink_escape_is_a_finding(self):
        path = self.target / "escape.md"
        outside = self.target.parent / "outside.md"
        outside.write_bytes(b"# Outside\n")
        try:
            path.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("host does not allow symlink creation")
        links = read_json(self.target, LINKS)
        links["links"][0]["canonical_owner"] = "escape.md"
        write_json(self.target / LINKS, links)
        self.assertIn("VOCABULARY_LINK_OWNER_PATH", [f.code for f in self.findings("project_vocabulary")])

    def test_owner_checks_do_not_read_owner_content(self):
        check = validator(self.target)
        original = check.context.read_bytes_result
        def measured(path, **kwargs):
            self.assertNotEqual(Path(path).resolve(), self.target / "README.md")
            return original(path, **kwargs)
        with patch.object(check.context, "read_bytes_result", side_effect=measured):
            check.check_project_vocabulary(parse_manifest(self.target / ".ai/alatyr.yaml"))
        self.assertFalse([f for f in check.findings if f.level == "error"])

    def test_malformed_task_fields_produce_findings(self):
        path = self.target / TASKS / "TASK-1.json"
        task = json.loads(path.read_bytes())
        for field in ("priority", "status", "review_state", "validation_state", "handoff_state"):
            for value in (None, {}, [], True, 1):
                with self.subTest(field=field, value=value):
                    changed = {**task, field: value}
                    write_json(path, changed)
                    self.assertTrue(any(f.level == "error" for f in self.findings("team_collaboration")))
        for field in ("state", "mode"):
            for value in ({}, []):
                with self.subTest(claim_field=field, value=value):
                    write_json(path, {**task, "claim": {**task["claim"], field: value}})
                    self.assertTrue(any(f.level == "error" for f in self.findings("team_collaboration")))
        for value in ({}, []):
            write_json(path, {**task, "status": "merge-ready", "review_state": value,
                              "overlap": {**task["overlap"], "state": value}})
            self.assertTrue(any(f.level == "error" for f in self.findings("team_collaboration")))

    def test_malformed_vocabulary_lists_and_link_identities_produce_findings(self):
        for field in ("id", "term_id"):
            for value in (None, {}, [], True, 1, "{ID}", "unknown"):
                with self.subTest(field=field, value=value):
                    links = read_json(self.target, LINKS)
                    links["links"][0][field] = value
                    write_json(self.target / LINKS, links)
                    self.assertIn("VOCABULARY_LINK_UNRESOLVED", [f.code for f in self.findings("project_vocabulary")])
                    configure_records(self.target)
        for source, key in (("catalog", "entries"), ("terms", "terms")):
            path = self.target / f".ai/project/vocabulary/{source}.json"
            original = read_json(self.target, str(path.relative_to(self.target)))
            for field in ("aliases", "acronyms", "domains"):
                for value in (["alias", 1], [{}], [None], {}, None):
                    with self.subTest(source=source, field=field, value=value):
                        changed = json.loads(json.dumps(original))
                        changed[key][0][field] = value
                        write_json(path, changed)
                        self.assertTrue(any(f.level == "error" for f in self.findings("project_vocabulary")))
            write_json(path, original)

    def test_missing_vocabulary_owner_is_rejected_and_restoration_passes(self):
        self.assertFalse([f for f in self.findings("project_vocabulary") if f.level == "error"])
        links = read_json(self.target, LINKS)
        links["links"][0]["canonical_owner"] = "docs/does-not-exist.md"
        write_json(self.target / LINKS, links)
        findings = self.findings("project_vocabulary")
        self.assertTrue(any(f.code == "VOCABULARY_LINK_OWNER_MISSING" and "LINK-1" in f.message
                            and "docs/does-not-exist.md" in f.message for f in findings))
        owner = self.target / "docs/does-not-exist.md"
        owner.parent.mkdir(parents=True, exist_ok=True)
        owner.write_bytes(b"# Owner\n")
        self.assertFalse([f for f in self.findings("project_vocabulary") if f.level == "error"])

    def command(self, *arguments: str):
        return subprocess.run([sys.executable, "-B", *arguments], cwd=ROOT,
                              capture_output=True, text=True, check=False)

    def test_scoped_finalization_and_full_acceptance_reject_missing_owner(self):
        base = run_git(self.target, "rev-parse", "HEAD")
        approval = ".ai/assistant/approvals/fixture-install.json"
        write_json(self.target / approval, approval_record(base, "full"))
        transition_installation_state(
            self.target, next_state="accepted", reason="strict-acceptance",
            operation_id="fixture-install", validation_status="passed",
            validation_evidence="synthetic fixture acceptance setup")
        bindings = ["--target", str(self.target), "--framework-source", str(ROOT),
                    "--diff-ref", base, "--approval-record", approval]
        delegate = str(self.target / ".ai/assistant/tools/alatyr_delegate.py")
        result = self.command(delegate, "finalize-support", *bindings, "--write", "--require-current-change")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.target / TASKS / "context-index.json").is_file())
        links = read_json(self.target, LINKS)
        links["links"][0]["canonical_owner"] = "docs/does-not-exist.md"
        write_json(self.target / LINKS, links)
        result = self.command(delegate, "finalize-support", *bindings, "--write", "--require-current-change")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("VOCABULARY_LINK_OWNER_MISSING", result.stdout + result.stderr)
        # Regenerate stale projections independently after the finalizer's rollback,
        # so the public acceptance probe does not depend on unrelated drift errors.
        refresh_context_and_bootstrap(self.target)
        report = self.target.parent / "validation.json"
        result = self.command(str(ROOT / "tools/validate_target_adapter.py"), *bindings,
                              "--enforce-approval-scope", "--validation-phase", "acceptance",
                              "--validation-scope", "full", "--approval-archive-mode", "full",
                              "--output", str(report))
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(report.read_bytes())
        self.assertTrue(any(f["code"] == "VOCABULARY_LINK_OWNER_MISSING" for f in payload["findings"]))
        self.assertEqual({f["code"] for f in payload["findings"] if f["level"] == "error"},
                         {"VOCABULARY_LINK_OWNER_MISSING"})
        self.assertFalse(payload["placeholder_validation"]["acceptance_eligible"])
        links["links"][0]["canonical_owner"] = "README.md"
        write_json(self.target / LINKS, links)
        result = self.command(delegate, "finalize-support", *bindings, "--write", "--require-current-change")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.command(str(ROOT / "tools/validate_target_adapter.py"), *bindings,
                              "--enforce-approval-scope", "--validation-phase", "acceptance",
                              "--validation-scope", "full", "--approval-archive-mode", "full",
                              "--output", str(report))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(report.read_bytes())["placeholder_validation"]["acceptance_eligible"])
        write_json(self.target / TASKS / "context-index.json", {})
        result = self.command(str(ROOT / "tools/validate_target_adapter.py"), *bindings,
                              "--validation-phase", "acceptance", "--validation-scope", "full",
                              "--approval-archive-mode", "full", "--output", str(report))
        self.assertNotEqual(result.returncode, 0)
        findings = json.loads(report.read_bytes())["findings"]
        self.assertTrue(any(f["code"] == "CONTEXT_CATALOG_INVALID" for f in findings))
        self.assertFalse(any(f["code"].startswith("TEAM_TASK") and f["path"].endswith("context-index.json")
                             for f in findings))


if __name__ == "__main__":
    unittest.main()
