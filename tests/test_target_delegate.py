from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
DELEGATE_PATH = (
    ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"
)
SPEC = importlib.util.spec_from_file_location("alatyr_delegate_template", DELEGATE_PATH)
assert SPEC is not None and SPEC.loader is not None
delegate = importlib.util.module_from_spec(SPEC)
_previous_dont_write_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    SPEC.loader.exec_module(delegate)
finally:
    sys.dont_write_bytecode = _previous_dont_write_bytecode


class TargetDelegateTests(unittest.TestCase):
    def test_validation_contract_commands_map_to_declared_canonical_operations(self) -> None:
        contract = json.loads(
            (
                ROOT / "templates/target/.ai/assistant/validation-contract.json"
            ).read_text(encoding="utf-8")
        )
        parser = delegate.build_parser()
        for entrypoint, entry in contract["entrypoints"].items():
            tokens = shlex.split(entry["command"])
            self.assertEqual(tokens[1], ".ai/assistant/tools/alatyr_delegate.py")
            delegate_arguments = tokens[2:]
            if delegate_arguments[0] == "validate-current":
                delegate_arguments.extend(
                    [
                        "--diff-ref",
                        "HEAD~1",
                        "--approval-record",
                        "approval.json",
                        "--change-package",
                        "package.json",
                    ]
                )
            parsed = parser.parse_args(delegate_arguments)
            canonical = delegate.canonical_arguments(
                parsed,
                Path("/target"),
                Path("/source"),
            )
            metadata = entry["canonical_delegate"]

            def option_value(option: str, fallback: str) -> str:
                return (
                    canonical[canonical.index(option) + 1]
                    if option in canonical
                    else fallback
                )

            with self.subTest(entrypoint=entrypoint):
                self.assertEqual(metadata["operation"], canonical[0])
                self.assertEqual(
                    metadata["validation_phase"],
                    option_value("--validation-phase", "not-applicable"),
                )
                self.assertEqual(
                    metadata["validation_scope"],
                    option_value("--validation-scope", "not-applicable"),
                )
                self.assertEqual(
                    metadata["approval_archive_mode"],
                    option_value("--approval-archive-mode", "not-applicable"),
                )
                self.assertEqual(
                    metadata["requires_diff_ref"],
                    "--diff-ref" in canonical,
                )
                self.assertEqual(
                    metadata["requires_approval_records"],
                    "--approval-record" in canonical,
                )
                self.assertEqual(
                    metadata["requires_change_packages"],
                    "--change-package" in canonical,
                )

    def test_source_resolution_fails_closed_without_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {}, clear=True
        ):
            with self.assertRaisesRegex(ValueError, "source is unresolved"):
                delegate.resolve_source(Path(directory), None)

    def test_local_source_resolution_accepts_only_a_source_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            source = Path(directory) / "source"
            (source / "tools").mkdir(parents=True)
            (source / "tools/alatyr.py").write_text("", encoding="utf-8")
            config = target / ".ai/local/framework-source"
            config.parent.mkdir(parents=True)
            config.write_text("../source", encoding="utf-8")

            resolved = delegate.resolve_source(target, None)

        self.assertEqual(resolved, source.resolve())

    def test_finalize_delegate_forwards_migration_staging(self) -> None:
        args = argparse.Namespace(
            operation="finalize-support",
            write=True,
            migration_staging=True,
            diff_ref=None,
            approval_record=[],
            change_package=[],
            require_current_change=False,
        )

        command = delegate.canonical_arguments(
            args, Path("/target"), Path("/source")
        )

        self.assertEqual(command[:3], ["finalize-support", "--target", "/target"])
        self.assertIn("--write", command)
        self.assertIn("--migration-staging", command)
        self.assertNotIn("--framework-source", command)

    def test_current_change_delegate_enforces_full_canonical_arguments(self) -> None:
        args = argparse.Namespace(
            operation="validate-current",
            diff_ref="HEAD~1",
            approval_record=["approval.json"],
            change_package=["package.json"],
        )
        command = delegate.canonical_arguments(
            args, Path("/target"), Path("/source")
        )

        self.assertEqual(command[0], "validate-adapter")
        self.assertIn("--validation-scope", command)
        self.assertEqual(command[command.index("--validation-scope") + 1], "full")
        self.assertEqual(
            command[command.index("--approval-archive-mode") + 1], "full"
        )
        self.assertIn("--enforce-approval-scope", command)
        self.assertIn("--enforce-change-package", command)

    def test_current_change_parser_requires_all_bindings(self) -> None:
        parser = delegate.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["validate-current", "--diff-ref", "HEAD~1"])


if __name__ == "__main__":
    unittest.main()
