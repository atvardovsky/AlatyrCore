from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.context import ValidationContext  # noqa: E402
from target_adapter_validation.harness_scenarios.common import validator  # noqa: E402
from validate_target_adapter import Finding  # noqa: E402


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
            for field in ("mtime_ns", "link_mtime_ns"):
                self.assertEqual(details["metadata_changes"][field], {
                    "before": getattr(before, field), "after": observed.stat().st_mtime_ns,
                })
            self.assertEqual((observed / "owner.md").read_bytes(), b"stable\n")
            self.assertNotIn(str(target), json.dumps(details))

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
