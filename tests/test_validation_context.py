from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.context import (  # noqa: E402
    TargetFileState,
    TargetPathEscapeError,
    ValidationContext,
)
from validate_target_adapter import AdapterValidatorConfig, Validator  # noqa: E402
import validate_target_adapter  # noqa: E402


class ValidationContextTests(unittest.TestCase):
    def test_exposes_coherent_bytes_text_json_and_digest_apis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            path = target / "example.json"
            path.write_text('{"value": "before"}\n', encoding="utf-8")
            context = ValidationContext(target)

            byte_result = context.read_bytes_result(path)
            text_result = context.read_text_result(path)
            json_result = context.read_json_result(path)
            path.write_text('{"value": "after"}\n', encoding="utf-8")

            self.assertEqual(byte_result.value, b'{"value": "before"}\n')
            self.assertEqual(text_result.value, '{"value": "before"}\n')
            self.assertEqual(json_result.value, {"value": "before"})
            self.assertEqual(context.read_bytes(path), byte_result.value)
            self.assertEqual(context.read_text(path), text_result.value)
            self.assertEqual(context.content_digest(path), byte_result.digest)
            self.assertEqual(byte_result.status.state, TargetFileState.FILE)

    def test_typed_results_distinguish_missing_invalid_text_and_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            context = ValidationContext(target)

            missing = context.read_text_result(target / "missing.txt")
            invalid_text_path = target / "invalid.txt"
            invalid_text_path.write_bytes(b"\xff")
            invalid_text = context.read_text_result(invalid_text_path)
            invalid_json_path = target / "invalid.json"
            invalid_json_path.write_text("{", encoding="utf-8")
            invalid_json = context.read_json_result(invalid_json_path)

            self.assertEqual(missing.status.state, TargetFileState.MISSING)
            self.assertIsNone(missing.value)
            self.assertEqual(invalid_text.status.state, TargetFileState.INVALID_TEXT)
            self.assertIsNone(invalid_text.value)
            self.assertEqual(invalid_json.status.state, TargetFileState.INVALID_JSON)
            self.assertIsNone(invalid_json.value)

    def test_finalize_detects_relevant_content_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            path = target / "example.txt"
            path.write_text("before\n", encoding="utf-8")
            context = ValidationContext(target)

            self.assertEqual(context.read_text(path), "before\n")
            path.write_text("after\n", encoding="utf-8")
            mutations = context.finalize()

            self.assertEqual(len(mutations), 1)
            self.assertEqual(mutations[0].path, path)
            self.assertTrue(mutations[0].content_changed)

    def test_finalize_accepts_stable_relevant_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            path = target / "example.txt"
            path.write_text("stable\n", encoding="utf-8")
            context = ValidationContext(target)

            context.read_text(path)

            self.assertEqual(context.finalize(), ())

    def test_validator_parses_manifest_once_per_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            manifest = target / ".ai/alatyr.yaml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("schema_version: 44\n", encoding="utf-8")
            validator = Validator(
                target,
                framework_source=None,
                diff_ref=None,
                approval_records=[],
                enforce_approval_scope=False,
                change_packages=[],
                enforce_change_package=False,
                migration_diff=None,
                allow_placeholders=True,
                allow_local_paths=[],
                config=AdapterValidatorConfig(),
            )

            with patch.object(
                validate_target_adapter,
                "parse_manifest",
                wraps=validate_target_adapter.parse_manifest,
            ) as parser:
                validator.run()

            self.assertEqual(parser.call_count, 1)

    def test_validator_finalizes_relevant_target_input_observations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            manifest = target / ".ai/alatyr.yaml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("schema_version: 44\n", encoding="utf-8")
            validator = Validator(
                target,
                framework_source=None,
                diff_ref=None,
                approval_records=[],
                enforce_approval_scope=False,
                change_packages=[],
                enforce_change_package=False,
                migration_diff=None,
                allow_placeholders=True,
                allow_local_paths=[],
                config=AdapterValidatorConfig(),
            )

            def mutate_last_observed_input() -> None:
                manifest.write_text("schema_version: 45\n", encoding="utf-8")

            with patch.object(
                validator,
                "check_migration_diff_evidence",
                side_effect=mutate_last_observed_input,
            ):
                validator.run()

            self.assertEqual(len(validator.target_mutations), 1)
            self.assertEqual(validator.target_mutations[0].path, manifest)
            self.assertTrue(validator.target_mutations[0].content_changed)
            self.assertTrue(
                any(
                    finding.code == "TARGET_INPUT_MUTATED"
                    and finding.level == "error"
                    and finding.path == ".ai/alatyr.yaml"
                    for finding in validator.findings
                )
            )

    def test_combined_local_path_scan_preserves_unix_and_windows_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            document = target / ".ai/project/paths.md"
            document.parent.mkdir(parents=True)
            document.write_text(
                "Unix: /home/example/project/file.txt\n"
                "Windows: C:\\Users\\Example\\project\\file.txt\n",
                encoding="utf-8",
            )
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

            validator.check_local_paths()

            self.assertEqual(
                [finding.code for finding in validator.findings],
                ["LOCAL_PATH_LEAKAGE", "LOCAL_PATH_LEAKAGE"],
            )

    def test_cached_content_is_stable_without_reopening_the_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            context = ValidationContext(target)
            path = target / "example.json"
            path.write_text('{"value": "before"}\n', encoding="utf-8")

            first = context.read_text(path)
            path.write_text('{"value": "after"}\n', encoding="utf-8")
            second = context.read_text(path)

            self.assertEqual(first, second)

    def test_missing_path_replaced_by_external_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "target"
            target.mkdir()
            outside = parent / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            path = target / "later.txt"
            context = ValidationContext(target)

            self.assertEqual(context.read_text(path), "")
            path.symlink_to(outside)

            with self.assertRaises(TargetPathEscapeError):
                context.read_text(path)

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

    def test_cached_internal_symlink_cannot_be_retargeted_outside(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "target"
            target.mkdir()
            inside = target / "inside.txt"
            inside.write_text("inside\n", encoding="utf-8")
            outside = parent / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            link = target / "linked.txt"
            try:
                link.symlink_to(inside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            context = ValidationContext(target)

            self.assertEqual(context.read_text(link), "inside\n")
            link.unlink()
            link.symlink_to(outside)

            with self.assertRaises(TargetPathEscapeError):
                context.read_text(link)

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

    def test_capability_module_cannot_follow_external_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "target"
            map_path = target / ".ai/project/consistency-map.json"
            map_path.parent.mkdir(parents=True)
            outside = parent / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            try:
                map_path.symlink_to(outside)
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

            validator.check_consistency_map()

            self.assertEqual(
                [item.code for item in validator.findings], ["TARGET_PATH_ESCAPE"]
            )
