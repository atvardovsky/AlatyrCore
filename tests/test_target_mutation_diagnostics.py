from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.context import ValidationContext  # noqa: E402
import target_adapter_validation.context as context_module  # noqa: E402
from target_adapter_validation.harness_scenarios.common import validator  # noqa: E402
from validate_target_adapter import Finding  # noqa: E402


@contextmanager
def entries_without_file_ids(path, *, scandir=os.scandir):
    """Model the zero identity fields exposed by Windows DirEntry.stat()."""
    with scandir(path) as children:
        entries = []
        for child in children:
            info = child.stat(follow_symlinks=False)
            metadata = SimpleNamespace(st_dev=0, st_ino=0, st_mode=info.st_mode,
                                       st_size=info.st_size, st_mtime_ns=info.st_mtime_ns)
            entries.append(SimpleNamespace(name=child.name,
                                           stat=lambda follow_symlinks=False, info=metadata: info))
        yield entries


class TargetMutationDiagnosticsTests(unittest.TestCase):
    def test_directory_metadata_diagnostics_do_not_claim_content_was_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            observed = target / "observed"
            observed.mkdir()
            (observed / "owner.md").write_bytes(b"stable\n")
            context = ValidationContext(target)
            before = context.status(observed)
            info = observed.stat()
            os.utime(observed, ns=(info.st_atime_ns, info.st_mtime_ns + 2_000_000_000))

            mutation, = context.finalize()
            details = mutation.diagnostics(target)
            self.assertFalse(mutation.content_changed)
            self.assertEqual(details["before_state"], "directory")
            self.assertEqual(details["after_state"], "directory")
            self.assertEqual(details["content"], {
                "comparison": "not-measured", "before_sha256": None, "after_sha256": None,
            })
            self.assertEqual(details["directory_entries"]["comparison"], "unchanged")
            self.assertEqual(details["directory_entries"]["before"]["entry_count"], 1)
            for field in ("mtime_ns", "link_mtime_ns"):
                self.assertEqual(details["metadata_changes"][field], {
                    "before": getattr(before, field), "after": observed.stat().st_mtime_ns,
                })
            self.assertEqual((observed / "owner.md").read_bytes(), b"stable\n")
            self.assertNotIn(str(target), json.dumps(details))

    def test_backward_directory_timestamp_stays_blocking_without_claiming_a_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            observed = target / "approvals"
            observed.mkdir()
            (observed / "approval.json").write_bytes(b"{}")
            context = ValidationContext(target)
            context.status(observed)
            info = observed.stat()
            os.utime(observed, ns=(info.st_atime_ns, info.st_mtime_ns - 2_000_000_000))

            mutation, = context.finalize()
            details = mutation.diagnostics(target)
            delta = details["metadata_changes"]["mtime_ns"]
            self.assertLess(delta["after"], delta["before"])
            self.assertEqual(details["directory_entries"]["comparison"], "unchanged")
            self.assertEqual(details["content"]["comparison"], "not-measured")
            self.assertNotIn("writer", details)

    def test_directory_membership_and_entry_identity_changes_are_distinguished(self):
        for change in ("create", "delete", "rename", "replace"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                target = Path(directory).resolve()
                observed = target / "approvals"
                observed.mkdir()
                path = observed / "approval.json"
                path.write_bytes(b"{}")
                context = ValidationContext(target)
                context.status(observed)
                info = observed.stat()
                if change == "create":
                    (observed / "extra.json").write_bytes(b"{}")
                elif change == "delete":
                    path.unlink()
                elif change == "rename":
                    path.rename(observed / "renamed.json")
                else:
                    replacement = target / "replacement.json"
                    replacement.write_bytes(b"{}")
                    original = path.stat()
                    replacement.replace(path)
                    os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns - 4_000_000_000))
                # Make the metadata mismatch deterministic on every host.
                os.utime(observed, ns=(info.st_atime_ns, info.st_mtime_ns - 2_000_000_000))
                mutation, = context.finalize()
                details = mutation.diagnostics(target)
                self.assertEqual(details["directory_entries"]["comparison"], "changed")
                self.assertNotEqual(details["directory_entries"]["before"]["sha256"],
                                    details["directory_entries"]["after"]["sha256"])
                self.assertNotIn("approval.json", json.dumps(details))
                self.assertNotIn(str(target), json.dumps(details))

    def test_replacement_diagnostics_with_unavailable_entry_file_ids(self):
        for timestamp_delta in (0, -4_000_000_000):
            with self.subTest(timestamp_delta=timestamp_delta), tempfile.TemporaryDirectory() as directory:
                target = Path(directory).resolve()
                observed = target / "observed"
                observed.mkdir()
                path = observed / "entry.json"
                path.write_bytes(b"{}")
                timestamp = 1_700_000_000_000_000_000
                os.utime(path, ns=(timestamp, timestamp))
                context = ValidationContext(target)
                with patch.object(context_module.os, "scandir", side_effect=entries_without_file_ids):
                    context.status(observed)
                    before = observed.stat()
                    replacement = target / "replacement.json"
                    replacement.write_bytes(b"[]")
                    replacement.replace(path)
                    os.utime(path, ns=(timestamp, timestamp + timestamp_delta))
                    os.utime(observed, ns=(before.st_atime_ns, before.st_mtime_ns - 2_000_000_000))
                    mutation, = context.finalize()
                details = mutation.diagnostics(target)
                self.assertEqual(details["directory_entries"]["comparison"],
                                 "unchanged" if timestamp_delta == 0 else "changed")
                self.assertEqual(details["content"]["comparison"], "not-measured")
                self.assertNotEqual(mutation.before.mtime_ns, mutation.after.mtime_ns)

    def test_incomplete_directory_capture_never_claims_unchanged_entries(self):
        for phase in ("before", "after"):
            for failure in ("entry-limit", "name-limit", "permission", "unstable"):
                with self.subTest(phase=phase, failure=failure), tempfile.TemporaryDirectory() as directory:
                    target = Path(directory).resolve()
                    observed = target / "approvals"
                    observed.mkdir()
                    (observed / "approval.json").write_bytes(b"{}")
                    context = ValidationContext(target)

                    def capture():
                        if phase == "before":
                            context.status(observed)
                        else:
                            return context.finalize()

                    if phase == "after":
                        context.status(observed)
                    info = observed.stat()
                    if failure == "entry-limit":
                        boundary = patch.object(context_module, "MAX_DIRECTORY_ENTRIES", 0)
                    elif failure == "name-limit":
                        boundary = patch.object(context_module, "MAX_DIRECTORY_NAME_BYTES", 0)
                    elif failure == "permission":
                        boundary = patch.object(context_module.os, "scandir", side_effect=PermissionError("private"))
                    else:
                        original = context._status
                        calls = 0

                        def changed_status(path):
                            nonlocal calls
                            calls += 1
                            os.utime(observed, ns=(info.st_atime_ns, info.st_mtime_ns + calls * 2_000_000_000))
                            return original(path)

                        boundary = patch.object(context, "_status", side_effect=changed_status)
                    if phase == "after":
                        os.utime(observed, ns=(info.st_atime_ns, info.st_mtime_ns - 2_000_000_000))
                    with boundary:
                        mutations = capture()
                    if phase == "before":
                        os.utime(observed, ns=(info.st_atime_ns, info.st_mtime_ns - 2_000_000_000))
                        mutations = context.finalize()
                    mutation, = mutations
                    details = mutation.diagnostics(target)
                    entries = details["directory_entries"]
                    self.assertEqual(entries[phase]["state"], {
                        "entry-limit": "limit-exceeded", "name-limit": "limit-exceeded",
                        "permission": "unavailable", "unstable": "unstable",
                    }[failure])
                    self.assertIsNone(entries[phase]["sha256"])
                    self.assertEqual(entries["comparison"], "not-measured" if phase == "before" else "unavailable")
                    self.assertNotIn("private", json.dumps(details))

    def test_stable_finalize_does_not_rescan_directory_or_read_children(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            observed = target / "approvals"
            observed.mkdir()
            (observed / "approval.json").write_bytes(b"{}")
            context = ValidationContext(target)
            with patch.object(Path, "read_bytes", side_effect=AssertionError("unexpected content read")), \
                    patch.object(context_module.os, "scandir", wraps=os.scandir) as scan:
                context.status(observed)
                context.status(observed)
                self.assertEqual(context.finalize(), ())
                self.assertEqual(scan.call_count, 1)

    def test_directory_capture_limits_include_the_boundary(self):
        for limit_kind in ("entries", "name-bytes"):
            for count in (1, 2, 3):
                with self.subTest(limit=limit_kind, count=count), tempfile.TemporaryDirectory() as directory:
                    target = Path(directory).resolve()
                    observed = target / "observed"
                    observed.mkdir()
                    for number in range(count):
                        (observed / str(number)).write_bytes(b"unread")
                    limit = "MAX_DIRECTORY_ENTRIES" if limit_kind == "entries" else "MAX_DIRECTORY_NAME_BYTES"
                    context = ValidationContext(target)
                    with patch.object(context_module, limit, 2):
                        context.status(observed)
                        info = observed.stat()
                        os.utime(observed, ns=(info.st_atime_ns, info.st_mtime_ns - 2_000_000_000))
                        mutation, = context.finalize()
                    entries = mutation.diagnostics(target)["directory_entries"]
                    self.assertEqual(entries["comparison"], "unchanged" if count <= 2 else "not-measured")
                    self.assertEqual(entries["before"]["state"], "complete" if count <= 2 else "limit-exceeded")
                    self.assertLessEqual(entries["before"]["entries_measured"], 2)

    def test_incomplete_diagnostics_do_not_change_existing_stability_decisions(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            observed = target / "observed"
            observed.mkdir()
            (observed / "owner.json").write_bytes(b"{}")
            context = ValidationContext(target)
            with patch.object(context_module.os, "scandir", side_effect=PermissionError("private")):
                context.status(observed)
                self.assertEqual(context.finalize(), ())

    def test_directory_removal_and_containment_change_keep_blocking_evidence(self):
        for change in ("delete", "outside-link"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                parent = Path(directory).resolve()
                target = parent / "target"
                target.mkdir()
                observed = target / "approvals"
                observed.mkdir()
                context = ValidationContext(target)
                context.status(observed)
                observed.rmdir()
                if change == "outside-link":
                    outside = parent / "private"
                    outside.mkdir()
                    try:
                        observed.symlink_to(outside, target_is_directory=True)
                    except (OSError, NotImplementedError):
                        self.skipTest("host does not allow symlink creation")
                mutation, = context.finalize()
                details = mutation.diagnostics(target)
                self.assertEqual(details["after_state"], "missing" if change == "delete" else "outside-target")
                self.assertEqual(details["directory_entries"]["comparison"], "unavailable")
                self.assertNotIn("private", json.dumps(details))
                self.assertNotIn(str(parent), json.dumps(details))

    def test_directory_snapshot_never_follows_child_symlinks_or_recurses(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            target = parent / "target"
            target.mkdir()
            observed = target / "observed"
            observed.mkdir()
            outside = parent / "private"
            outside.mkdir()
            (outside / "private.txt").write_bytes(b"not target evidence")
            try:
                (observed / "link").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("host does not allow symlink creation")
            context = ValidationContext(target)
            with patch.object(Path, "read_bytes", side_effect=AssertionError("unexpected content read")), \
                    patch.object(context_module.os, "scandir", wraps=os.scandir) as scan:
                context.status(observed)
                info = observed.stat()
                os.utime(observed, ns=(info.st_atime_ns, info.st_mtime_ns - 2_000_000_000))
                mutation, = context.finalize()
            self.assertEqual(scan.call_count, 2)
            self.assertTrue(all(call.args == (observed,) for call in scan.call_args_list))
            details = mutation.diagnostics(target)
            self.assertEqual(details["directory_entries"]["comparison"], "unchanged")
            self.assertEqual(details["directory_entries"]["before"]["entry_count"], 1)
            self.assertNotIn("private", json.dumps(details))

    def test_metadata_only_file_change_preserves_measured_content_status(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            path = target / "example.txt"
            path.write_bytes(b"stable")
            context = ValidationContext(target)
            context.read_bytes(path)
            info = path.stat()
            os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 2_000_000_000))

            mutation, = context.finalize()
            details = mutation.diagnostics(target)
            self.assertEqual(details["content"]["comparison"], "unchanged")
            self.assertEqual(details["content"]["before_sha256"],
                             details["content"]["after_sha256"])
            self.assertIn("mtime_ns", details["metadata_changes"])

    def test_content_only_diagnostics_reuse_captured_digests(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            path = target / "example.txt"
            path.write_bytes(b"before")
            info = path.stat()
            context = ValidationContext(target)
            context.read_bytes(path)
            path.write_bytes(b"after!")
            os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))

            mutation, = context.finalize()
            with patch.object(Path, "read_bytes", side_effect=AssertionError("unexpected read")), \
                    patch.object(Path, "stat", side_effect=AssertionError("unexpected stat")):
                details = mutation.diagnostics(target)
                mutation.summary(details)
            self.assertEqual(details["metadata_changes"], {})
            self.assertEqual(details["content"], {
                "comparison": "changed",
                "before_sha256": hashlib.sha256(b"before").hexdigest(),
                "after_sha256": hashlib.sha256(b"after!").hexdigest(),
            })

    def test_diagnostics_distinguish_creation_deletion_and_type_changes(self):
        for change in ("create", "delete", "replace-with-directory"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                target = Path(directory).resolve()
                path = target / "input"
                context = ValidationContext(target)
                if change == "create":
                    context.status(path)
                    path.write_bytes(b"new")
                    states = ("missing", "file", "not-measured")
                else:
                    path.write_bytes(b"before")
                    context.read_bytes(path)
                    path.unlink()
                    if change == "replace-with-directory":
                        path.mkdir()
                    states = ("file", "missing" if change == "delete" else "directory", "unavailable")
                mutation, = context.finalize()
                details = mutation.diagnostics(target)
                self.assertEqual((details["before_state"], details["after_state"],
                                  details["content"]["comparison"]), states)
                self.assertIn("state", details["metadata_changes"])
                self.assertNotIn(str(target), json.dumps(details))

    def test_symlink_changes_report_relative_paths_without_exposing_external_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            target = parent / "target"
            target.mkdir()
            first, second, outside = target / "first", target / "second", parent / "outside"
            for path in (first, second, outside):
                path.write_bytes(path.name.encode())
            link = target / "link"
            try:
                link.symlink_to(first)
            except (OSError, NotImplementedError):
                self.skipTest("host does not allow symlink creation")
            context = ValidationContext(target)
            context.read_bytes(link)
            link.unlink()
            link.symlink_to(second)
            mutation, = context.finalize()
            details = mutation.diagnostics(target)
            self.assertEqual(details["metadata_changes"]["resolved_path"],
                             {"before": "first", "after": "second"})
            self.assertEqual(details["content"]["comparison"], "changed")

            context = ValidationContext(target)
            context.read_bytes(link)
            link.unlink()
            link.symlink_to(outside)
            mutation, = context.finalize()
            details = mutation.diagnostics(target)
            self.assertEqual(details["after_state"], "outside-target")
            self.assertEqual(details["content"]["comparison"], "unavailable")
            self.assertNotIn(str(parent), json.dumps(details))
            self.assertNotIn(str(outside), json.dumps(details))

    def test_schema_mutations_use_the_same_diagnostics_and_stay_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target, schemas = root / "target", root / "schemas"
            target.mkdir()
            schemas.mkdir()
            path = schemas / "example.json"
            path.write_bytes(b"{}")
            check = validator(target)
            check.schema_context = ValidationContext(schemas)
            check.schema_context.read_json(path)
            path.write_bytes(b"[]")
            check.validation_phases(None, "full", set())[-1].run()
            finding, = [f for f in check.findings if f.code == "VALIDATOR_SCHEMA_MUTATED"]
            self.assertTrue(finding.to_json()["blocking"])
            self.assertEqual(finding.path, "schemas/example.json")
            self.assertEqual(finding.to_json()["details"]["content"]["comparison"], "changed")

    def test_other_findings_keep_the_existing_json_shape(self):
        self.assertNotIn("details", Finding("error", "MANIFEST_SCHEMA", "invalid").to_json())


if __name__ == "__main__":
    unittest.main()
