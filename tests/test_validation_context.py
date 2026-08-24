from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.context import (  # noqa: E402
    TargetPathEscapeError,
    ValidationContext,
)
from validate_target_adapter import AdapterValidatorConfig, Validator  # noqa: E402


class ValidationContextTests(unittest.TestCase):
    def test_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "target"
            target.mkdir()
            outside = parent / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")

            with self.assertRaises(TargetPathEscapeError):
                ValidationContext(target).read_text(target / ".." / "outside.txt")

            data, error = ValidationContext(target).read_json(
                target / ".." / "outside.txt"
            )
            self.assertIsNone(data)
            self.assertIn("resolves outside", error or "")

    def test_rejects_symlink_that_resolves_outside_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "target"
            target.mkdir()
            outside = parent / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            link = target / "linked.txt"
            try:
                link.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaises(TargetPathEscapeError):
                ValidationContext(target).read_text(link)

    def test_allows_symlink_that_stays_inside_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            source = target / "source.txt"
            source.write_text("inside\n", encoding="utf-8")
            link = target / "linked.txt"
            try:
                link.symlink_to(source)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            self.assertEqual(ValidationContext(target).read_text(link), "inside\n")

    def test_validator_records_target_path_escape_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "target"
            target.mkdir()
            outside = parent / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            link = target / "linked.txt"
            try:
                link.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            validator = Validator(
                target,
                framework_source=None,
                diff_ref=None,
                approval_records=[],
                enforce_approval_scope=False,
                change_packages=[],
                enforce_change_package=False,
                migration_diff=None,
                allow_placeholders=False,
                allow_local_paths=[],
                config=AdapterValidatorConfig(),
            )

            first = validator.target_path("linked.txt")
            second = validator.target_path("linked.txt")

            self.assertFalse(first.exists())
            self.assertEqual(first, second)
            self.assertEqual(
                [item.code for item in validator.findings], ["TARGET_PATH_ESCAPE"]
            )

    def test_selected_records_must_stay_inside_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "target"
            target.mkdir()
            outside = parent / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")

            validator = Validator(
                target,
                framework_source=None,
                diff_ref=None,
                approval_records=[outside],
                enforce_approval_scope=False,
                change_packages=[Path("../outside.json")],
                enforce_change_package=False,
                migration_diff=None,
                allow_placeholders=False,
                allow_local_paths=[],
                config=AdapterValidatorConfig(),
            )

            self.assertEqual(validator.approval_records, [])
            self.assertEqual(validator.change_packages, [])
            self.assertEqual(
                [item.code for item in validator.findings],
                ["TARGET_PATH_ESCAPE", "TARGET_PATH_ESCAPE"],
            )
