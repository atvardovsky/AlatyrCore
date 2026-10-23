"""Reviewed historical witnesses must never become current authority."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from target_adapter_validation.harness_scenarios.common import validator


INDEX = ".ai/assistant/historical-evidence-index.json"
RECORD = ".ai/assistant/approvals/old.json"
PLAN = ".ai/assistant/change-packages/rejected-plan.md"


class HistoricalEvidenceClassificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.write(RECORD, {"schema_version": 2, "scope": {"allowed_files_or_surfaces": ["/tmp/past/**"]}})
        self.write(PLAN, "Rejected experiment. Original failure remains unresolved.\n")
        self.write("docs/owner.md", "Original incident remains blocked.\n")
        self.write("docs/decision.md", "Human review: retain historical evidence; no current authority.\n")
        self.index = {
            "schema_version": 1, "record_kind": "alatyr-historical-evidence-index",
            "authority": "none", "reviewed_by": "human-user", "reviewed_at": "2026-10-20T18:30:00Z",
            "decision": self.ref("docs/decision.md"),
            "entries": [self.entry(RECORD, "approval-record", "historical-incomplete"),
                        self.entry(PLAN, "retained-plan", "rejected-experiment")],
        }
        self.save()

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) if not isinstance(value, str) else value, encoding="utf-8")

    def ref(self, name):
        return {"path": name, "sha256": hashlib.sha256((self.root / name).read_bytes()).hexdigest()}

    def entry(self, name, kind, status):
        return {**self.ref(name), "kind": kind, "status": status,
                "reason": "Retained unchanged, not an authorization or completion claim.",
                "owner": self.ref("docs/owner.md"), "evidence": [self.ref("docs/decision.md")]}

    def save(self):
        self.write(INDEX, self.index)

    def current(self, *, opt_in=True):
        current = validator(self.root)
        current.enforce_approval_scope = True
        current.compact_archive_findings = False
        # Explicit selection; discovery never silently adopts a classification.
        current.historical_evidence_index = self.root / INDEX if opt_in else None
        return current

    def shape(self, current, name=RECORD):
        current.check_approval_record_shape([self.root / name], historical=True)
        return current.findings

    def errors(self, current):
        return [f for f in current.findings if f.level == "error"]

    def plans(self, current):
        current.diff_ref = "HEAD"
        with patch.object(current.git, "changed_files", return_value=[PLAN]):
            current.check_change_packages()

    def test_reviewed_historical_gaps_remain_visible_without_current_authority(self):
        before = (self.root / RECORD).read_bytes()
        current = self.current()
        self.shape(current)
        self.assertFalse(self.errors(current))
        self.assertIn("APPROVAL_RECORD_FIELD_MISSING", {f.code for f in current.findings})
        self.assertIn("APPROVAL_RECORD_SCOPE_INVALID", {f.code for f in current.findings})
        self.assertIn("HISTORICAL_EVIDENCE_NON_AUTHORITATIVE", {f.code for f in current.findings})
        self.assertEqual((self.root / RECORD).read_bytes(), before)

    def test_opt_in_is_required(self):
        current = self.current(opt_in=False)
        self.shape(current)
        self.assertTrue(self.errors(current))

    def test_unlisted_archive_record_remains_strict(self):
        self.write(".ai/assistant/approvals/unreviewed.json", {})
        current = self.current()
        self.shape(current, ".ai/assistant/approvals/unreviewed.json")
        self.assertTrue(self.errors(current))

    def test_selected_current_approval_cannot_use_archival_classification(self):
        current = self.current()
        current.approval_records = [self.root / RECORD]
        self.shape(current)
        self.assertTrue(self.errors(current))

    def test_direct_current_shape_check_remains_strict(self):
        current = self.current()
        current.check_approval_record_shape([self.root / RECORD])
        self.assertTrue(self.errors(current))

    def test_full_archive_entrypoint_preserves_current_enforcement(self):
        current = self.current()
        current.enforce_approval_scope = False
        current.check_approval_scope()
        self.assertIn("HISTORICAL_EVIDENCE_NON_AUTHORITATIVE", {f.code for f in current.findings})
        self.assertEqual(current.approval_archive_summary["records_checked"], 1)

    def test_selected_current_record_remains_blocking_through_scope_entrypoint(self):
        current = self.current()
        current.approval_records = [self.root / RECORD]
        current.diff_ref = "HEAD"
        with patch.object(current.git, "changed_files", return_value=[]):
            current.check_approval_scope()
        self.assertIn("APPROVAL_RECORD_SCOPE_INVALID", {f.code for f in self.errors(current)})

    def test_invalid_index_still_fails_when_every_approval_is_selected(self):
        self.write(INDEX, "{")
        current = self.current()
        current.approval_records = [self.root / RECORD]
        current.check_approval_scope()
        self.assertIn("HISTORICAL_EVIDENCE_INVALID", {f.code for f in self.errors(current)})

    def test_retained_plan_cannot_be_an_active_packages_plan(self):
        current = self.current()
        current.check_changed_plan_registration({PLAN}, {PLAN}, {PLAN: self.index["entries"][1]})
        self.assertIn("HISTORICAL_PLAN_ACTIVE_CONFLICT", {f.code for f in self.errors(current)})

    def test_rejected_plan_is_retained_not_fabricated_as_active_or_complete(self):
        current = self.current()
        self.plans(current)
        self.assertNotIn("PACKAGE_ACTIVE_PLAN_UNINDEXED", {f.code for f in current.findings})
        self.assertIn("HISTORICAL_PLAN_RETAINED", {f.code for f in current.findings})
        self.assertFalse(self.errors(current))

    def test_unregistered_active_plan_still_fails(self):
        self.index["entries"] = self.index["entries"][:1]
        self.save()
        current = self.current()
        self.plans(current)
        self.assertIn("PACKAGE_ACTIVE_PLAN_UNINDEXED", {f.code for f in self.errors(current)})

    def test_unresolved_lineage_is_not_relabelled_completed(self):
        self.index["entries"][1]["status"] = "retained-unresolved-lineage"
        self.save()
        current = self.current()
        self.plans(current)
        self.assertIn("retained-unresolved-lineage", " ".join(f.message for f in current.findings))

    def test_malformed_json_is_still_blocking_even_when_hash_matches(self):
        self.write(RECORD, "{not json")
        self.index["entries"][0].update(self.ref(RECORD))
        self.save()
        current = self.current()
        self.shape(current)
        self.assertIn("APPROVAL_RECORD_INVALID_JSON", {f.code for f in self.errors(current)})

    def test_non_object_record_is_still_blocking(self):
        self.write(RECORD, [])
        self.index["entries"][0].update(self.ref(RECORD))
        self.save()
        current = self.current()
        self.shape(current)
        self.assertIn("APPROVAL_RECORD_INVALID_SHAPE", {f.code for f in self.errors(current)})

    def test_stale_and_unsafe_or_unreviewed_indexes_fail_closed(self):
        cases = [
            lambda x: x["entries"][0].update(sha256="0" * 64),
            lambda x: x["entries"].append(copy.deepcopy(x["entries"][0])),
            lambda x: x.update(authority="current-authorization"),
            lambda x: x.update(reviewed_by=""),
            lambda x: x.update(reviewed_at="not a timestamp"),
            lambda x: x["decision"].update(sha256="0" * 64),
            lambda x: x["entries"][1]["owner"].update(sha256="0" * 64),
            lambda x: x["entries"][0].update(path="../outside.json"),
            lambda x: x["entries"][0].update(path="/tmp/outside.json"),
            lambda x: x["entries"][1].update(status="active"),
            lambda x: x["entries"][1].update(status="completed"),
            lambda x: x["entries"][0].update(evidence=[]),
        ]
        original = copy.deepcopy(self.index)
        for mutate in cases:
            with self.subTest(mutate=cases.index(mutate)):
                self.index = copy.deepcopy(original)
                mutate(self.index)
                self.save()
                current = self.current()
                self.shape(current)
                self.plans(current)
                codes = {f.code for f in self.errors(current)}
                self.assertIn("HISTORICAL_EVIDENCE_INVALID", codes)
                self.assertIn("PACKAGE_ACTIVE_PLAN_UNINDEXED", codes)

    def test_symlink_classification_input_is_rejected(self):
        record = self.root / RECORD
        real = self.root / "real.json"
        record.rename(real)
        try:
            record.symlink_to(real)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"fixture symlinks unavailable: {type(exc).__name__}")
        current = self.current()
        self.shape(current)
        self.assertIn("HISTORICAL_EVIDENCE_INVALID", {f.code for f in self.errors(current)})

    def test_invalid_json_index_is_blocking(self):
        self.write(INDEX, "{")
        current = self.current()
        self.shape(current)
        self.assertIn("HISTORICAL_EVIDENCE_INVALID", {f.code for f in self.errors(current)})

    def test_duplicate_json_fields_cannot_hide_a_conflicting_authority(self):
        self.write(INDEX, json.dumps(self.index).replace(
            '"authority": "none"', '"authority": "current-authorization", "authority": "none"'))
        current = self.current()
        self.shape(current)
        self.assertIn("HISTORICAL_EVIDENCE_INVALID", {f.code for f in self.errors(current)})

    def test_index_parent_symlink_is_rejected(self):
        (self.root / "witnesses").mkdir()
        self.write("witnesses/index.json", self.index)
        try:
            (self.root / "link").symlink_to(self.root / "witnesses", target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"fixture symlinks unavailable: {type(exc).__name__}")
        current = self.current()
        current.historical_evidence_index = self.root / "link/index.json"
        self.shape(current)
        self.assertIn("HISTORICAL_EVIDENCE_INVALID", {f.code for f in self.errors(current)})

    def test_json_type_mutations_fail_closed_without_exceptions(self):
        original = copy.deepcopy(self.index)
        paths = [("authority",), ("reviewed_by",), ("reviewed_at",), ("decision",), ("entries",),
                 ("entries", 0), ("entries", 0, "kind"), ("entries", 0, "status"),
                 ("entries", 0, "reason"), ("entries", 0, "owner"), ("entries", 0, "evidence")]
        for path in paths:
            for bad in (None, True, 1, [], {}, [{}], "unknown"):
                with self.subTest(path=path, bad=bad):
                    self.index = copy.deepcopy(original)
                    parent = self.index
                    for part in path[:-1]:
                        parent = parent[part]
                    parent[path[-1]] = bad
                    self.save()
                    current = self.current()
                    self.assertEqual(current.reviewed_historical_evidence(), {})
                    self.assertIn("HISTORICAL_EVIDENCE_INVALID", {f.code for f in self.errors(current)})

    def test_future_and_placeholder_reviews_cannot_relax_current_validation(self):
        for field, bad in (("reviewed_at", "2999-01-01T00:00:00Z"), ("reviewed_by", "{TARGET_REVIEWER}")):
            original = copy.deepcopy(self.index)
            self.index[field] = bad
            self.save()
            current = self.current()
            self.assertEqual(current.reviewed_historical_evidence(), {})
            self.assertIn("HISTORICAL_EVIDENCE_INVALID", {f.code for f in self.errors(current)})
            self.index = original

    def test_index_size_boundary_is_enforced_without_dropping_evidence(self):
        from target_adapter_validation.historical_evidence import MAX_INDEX_BYTES
        raw = json.dumps(self.index).encode()
        for size in (MAX_INDEX_BYTES - 1, MAX_INDEX_BYTES, MAX_INDEX_BYTES + 1):
            (self.root / INDEX).write_bytes(raw + b" " * (size - len(raw)))
            current = self.current()
            value = current.reviewed_historical_evidence()
            self.assertEqual(bool(value), size <= MAX_INDEX_BYTES)

    def test_opt_in_is_lazy_and_a_selected_snapshot_is_read_once(self):
        from target_adapter_validation import historical_evidence
        with patch.object(historical_evidence, "load_historical_evidence", wraps=historical_evidence.load_historical_evidence) as load:
            self.assertEqual(self.current(opt_in=False).reviewed_historical_evidence(), {})
            self.assertEqual(load.call_count, 0)
            current = self.current()
            self.assertEqual(current.reviewed_historical_evidence(), current.reviewed_historical_evidence())
            self.assertEqual(load.call_count, 1)

    def root_alias(self, directory):
        alias = Path(directory) / "root-alias"
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"fixture symlinks unavailable: {type(exc).__name__}")
        return alias

    def test_absolute_index_accepts_only_the_same_physical_project_root_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            alias = self.root_alias(directory)
            current = self.current()
            current.historical_evidence_index = alias / INDEX
            self.assertEqual(set(current.reviewed_historical_evidence()), {RECORD, PLAN})
            self.assertFalse(self.errors(current))

    def test_root_alias_cannot_hide_a_nested_symlink_to_the_root(self):
        with tempfile.TemporaryDirectory() as directory:
            alias = self.root_alias(directory)
            (self.root / "nested").symlink_to(self.root, target_is_directory=True)
            for selected in (self.root / "nested" / INDEX, alias / "nested" / INDEX):
                current = self.current()
                current.historical_evidence_index = selected
                self.assertEqual(current.reviewed_historical_evidence(), {})
                self.assertIn("HISTORICAL_EVIDENCE_INVALID", {f.code for f in self.errors(current)})

    def test_external_file_symlink_is_not_an_allowed_project_root_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            self.root_alias(directory)  # Establish symlink capability before the file case.
            link = Path(directory) / "index.json"
            link.symlink_to(self.root / INDEX)
            current = self.current()
            current.historical_evidence_index = link
            self.assertEqual(current.reviewed_historical_evidence(), {})
            self.assertIn("HISTORICAL_EVIDENCE_INVALID", {f.code for f in self.errors(current)})

    def test_absolute_cyclic_root_alias_returns_a_finding_not_an_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            self.root_alias(directory)
            first, second = Path(directory) / "first", Path(directory) / "second"
            first.symlink_to(second, target_is_directory=True)
            second.symlink_to(first, target_is_directory=True)
            current = self.current()
            current.historical_evidence_index = first / INDEX
            self.assertEqual(current.reviewed_historical_evidence(), {})
            self.assertIn("HISTORICAL_EVIDENCE_INVALID", {f.code for f in self.errors(current)})

    def prepare_dirty_history(self):
        for args in (("init", "-q"), ("config", "user.name", "Fixture"),
                     ("config", "user.email", "fixture@example.invalid"),
                     ("add", "."), ("commit", "-qm", "retain historical witnesses")):
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
        # Real Git reports a newly retained plan; classification must route it.
        subprocess.run(["git", "rm", "--cached", PLAN], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "leave inherited plan outside tracked baseline"], cwd=self.root, check=True, capture_output=True)

    def test_public_cli_classifies_real_git_dirty_history_but_never_current_authority(self):
        self.prepare_dirty_history()
        before = (self.root / RECORD).read_bytes()
        command = [sys.executable, "-B", str(ROOT / "tools/validate_target_adapter.py"),
                   "--target", str(self.root), "--diff-ref", "HEAD", "--enforce-approval-scope",
                   "--historical-evidence-index", INDEX, "--json"]
        result = subprocess.run(command, capture_output=True, text=True)
        payload = json.loads(result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("HISTORICAL_PLAN_RETAINED", {f["code"] for f in payload["findings"]})
        self.assertFalse(any(f["level"] == "error" and f.get("path") == RECORD for f in payload["findings"]))
        self.assertFalse(any(f["code"] == "PACKAGE_ACTIVE_PLAN_UNINDEXED" and f.get("path") == PLAN for f in payload["findings"]))
        # Selecting that same incomplete approval as current remains blocking.
        result = subprocess.run([*command, "--approval-record", RECORD], capture_output=True, text=True)
        payload = json.loads(result.stdout)
        self.assertTrue(any(f["level"] == "error" and f.get("path") == RECORD for f in payload["findings"]))
        self.assertEqual((self.root / RECORD).read_bytes(), before)

    def test_public_cli_accepts_absolute_index_through_project_root_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            alias = self.root_alias(directory)
            self.prepare_dirty_history()
            for target in (self.root, alias):
                with self.subTest(target=target):
                    command = [sys.executable, "-B", str(ROOT / "tools/validate_target_adapter.py"),
                               "--target", str(target), "--diff-ref", "HEAD", "--enforce-approval-scope",
                               "--historical-evidence-index", str(alias / INDEX), "--json"]
                    result = subprocess.run(command, capture_output=True, text=True)
                    payload = json.loads(result.stdout)
                    self.assertNotIn("Traceback", result.stderr)
                    codes = {finding["code"] for finding in payload["findings"]}
                    self.assertIn("HISTORICAL_PLAN_RETAINED", codes)
                    self.assertNotIn("HISTORICAL_EVIDENCE_INVALID", codes)
                    self.assertNotIn("PACKAGE_ACTIVE_PLAN_UNINDEXED", codes)


if __name__ == "__main__":
    unittest.main()
