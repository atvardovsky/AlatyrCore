from __future__ import annotations

import copy
import contextlib
import importlib.util
import io
import json
import shlex
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.harness_scenarios.common import (  # noqa: E402
    parse_manifest,
    validator,
    write_json,
)
from target_adapter_validation.validation_contract import (  # noqa: E402
    CONTRACT_PATH,
    DELEGATE_PATH,
    validate_validation_contract,
)


DELEGATE_SOURCE = ROOT / "templates/target" / DELEGATE_PATH
DELEGATE_SPEC = importlib.util.spec_from_file_location(
    "alatyr_delegate_differential_test",
    DELEGATE_SOURCE,
)
assert DELEGATE_SPEC is not None and DELEGATE_SPEC.loader is not None
delegate = importlib.util.module_from_spec(DELEGATE_SPEC)
_previous_dont_write_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    DELEGATE_SPEC.loader.exec_module(delegate)
finally:
    sys.dont_write_bytecode = _previous_dont_write_bytecode
REQUIRED_BINDINGS = {
    "validate-current": (
        ("--diff-ref", "HEAD"),
        ("--approval-record", "approval.json"),
        ("--change-package", "package.json"),
    )
}


class ValidationContractInvocationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.target = Path(self.temporary.name)
        self.contract_path = self.target / CONTRACT_PATH
        self.delegate_path = self.target / DELEGATE_PATH
        self.delegate_path.parent.mkdir(parents=True)
        self.delegate_path.write_text(
            (ROOT / "templates/target" / DELEGATE_PATH).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        self.contract = json.loads(
            (ROOT / "templates/target" / CONTRACT_PATH).read_text(encoding="utf-8")
        )
        manifest_path = self.target / ".ai/alatyr.yaml"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            "validation:\n  contract: .ai/assistant/validation-contract.json\n",
            encoding="utf-8",
        )
        self.manifest = parse_manifest(manifest_path)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate(self, contract: dict | None = None) -> set[str]:
        write_json(self.contract_path, contract or self.contract)
        checked = validator(self.target)
        validate_validation_contract(checked, self.manifest)
        return {
            finding.code
            for finding in checked.findings
            if finding.level == "error"
        }

    def current_change_contract(self, command: str) -> dict:
        contract = copy.deepcopy(self.contract)
        contract["entrypoints"]["current-change"]["command"] = command
        return contract

    def parser_accepts(self, command: str) -> bool:
        arguments = shlex.split(command)[2:]
        operation = arguments[0]
        for option, placeholder in REQUIRED_BINDINGS.get(operation, ()):
            if not any(
                token == option or token.startswith(f"{option}=")
                for token in arguments
            ):
                arguments.extend([option, placeholder])
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                io.StringIO()
            ):
                delegate.build_parser().parse_args(arguments)
        except SystemExit:
            return False
        return True

    def test_shipped_contract_passes(self) -> None:
        self.assertEqual(self.validate(), set())

    def test_portable_python_launchers_preserve_direct_invocation(self) -> None:
        commands = [
            "python .ai/assistant/tools/alatyr_delegate.py validate-current --target .",
            "python3.13 .ai/assistant/tools/alatyr_delegate.py validate-current --target=.",
            "py -3 .ai/assistant/tools/alatyr_delegate.py validate-current --target .",
            "py.exe -3.13 .ai/assistant/tools/alatyr_delegate.py validate-current --target .",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(
                    self.validate(self.current_change_contract(command)),
                    set(),
                )

    def test_reported_wrong_operation_and_echo_mutations_fail(self) -> None:
        cases = [
            (
                "python3 .ai/assistant/tools/alatyr_delegate.py status --target .",
                "VALIDATION_CONTRACT_DELEGATE_OPERATION",
            ),
            (
                "echo .ai/assistant/tools/alatyr_delegate.py",
                "VALIDATION_CONTRACT_DELEGATE_COMMAND",
            ),
        ]
        for command, expected in cases:
            with self.subTest(command=command):
                self.assertIn(
                    expected,
                    self.validate(self.current_change_contract(command)),
                )

    def test_non_direct_launchers_and_script_positions_fail(self) -> None:
        commands = [
            "env python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target .",
            "python3 -B .ai/assistant/tools/alatyr_delegate.py validate-current --target .",
            "python3 -c '.ai/assistant/tools/alatyr_delegate.py' validate-current --target .",
            "python3 .ai/assistant/tools/alatyr_delegate.py-invalid validate-current --target .",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertIn(
                    "VALIDATION_CONTRACT_DELEGATE_COMMAND",
                    self.validate(self.current_change_contract(command)),
                )

    def test_unsupported_or_ambiguous_arguments_fail(self) -> None:
        cases = [
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target other",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . --target .",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . --help",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . trailing",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . && echo done",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . & echo done",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . # ignored",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . --diff-ref $REF",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . --approval-record *.json",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . --diff-ref %REF%",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . --diff-ref -h --approval-record approval.json --change-package package.json",
        ]
        for command in cases:
            with self.subTest(command=command):
                self.assertIn(
                    "VALIDATION_CONTRACT_DELEGATE_ARGUMENTS",
                    self.validate(self.current_change_contract(command)),
                )

    def test_contract_acceptance_implies_shipped_parser_acceptance(self) -> None:
        commands = [
            "python3 .ai/assistant/tools/alatyr_delegate.py status --target .",
            "python3 .ai/assistant/tools/alatyr_delegate.py archive-audit --target .",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target .",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . --diff-ref HEAD",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . --approval-record approval.json",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . --change-package package.json",
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . --diff-ref HEAD --approval-record approval.json --change-package package.json",
        ]
        bases_and_options = [
            (
                "adapter-health",
                "python3 .ai/assistant/tools/alatyr_delegate.py status --target .",
                ["--framework-source"],
            ),
            (
                "archive-audit",
                "python3 .ai/assistant/tools/alatyr_delegate.py archive-audit --target .",
                ["--framework-source"],
            ),
            (
                "current-change",
                "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . --diff-ref HEAD --approval-record approval.json --change-package package.json",
                [
                    "--framework-source",
                    "--diff-ref",
                    "--approval-record",
                    "--change-package",
                ],
            ),
        ]
        candidates: list[tuple[str, str]] = []
        for entrypoint, base, options in bases_and_options:
            for option in options:
                for value in ("-h", "-x", "-v"):
                    tokens = shlex.split(base)
                    if option in tokens:
                        tokens[tokens.index(option) + 1] = value
                        command = shlex.join(tokens)
                    else:
                        command = f"{base} {option} {value}"
                    candidates.append((entrypoint, command))
                candidates.append((entrypoint, f"{base} {option}"))

        entrypoint_for_operation = {
            "status": "adapter-health",
            "archive-audit": "archive-audit",
            "validate-current": "current-change",
        }
        candidates.extend(
            (
                entrypoint_for_operation[shlex.split(command)[2]],
                command,
            )
            for command in commands
        )
        for entrypoint, command in candidates:
            with self.subTest(entrypoint=entrypoint, command=command):
                contract = copy.deepcopy(self.contract)
                contract["entrypoints"][entrypoint]["command"] = command
                contract_accepts = not self.validate(contract)
                parser_accepts = self.parser_accepts(command)
                self.assertFalse(
                    contract_accepts and not parser_accepts,
                    "contract accepted a command rejected by the shipped delegate parser",
                )

    def test_complete_current_change_bindings_pass(self) -> None:
        command = (
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current "
            "--target . --diff-ref HEAD --approval-record approval.json "
            "--approval-record approval-2.json --change-package package.json"
        )
        self.assertEqual(
            self.validate(self.current_change_contract(command)),
            set(),
        )

    def test_missing_or_semantically_modified_delegate_fails(self) -> None:
        self.delegate_path.unlink()
        self.assertIn("VALIDATION_CONTRACT_DELEGATE_CONTENT", self.validate())

        self.delegate_path.write_text(
            (ROOT / "templates/target" / DELEGATE_PATH).read_text(encoding="utf-8")
            + "\nCANONICAL_OPERATION_DISABLED = True\n",
            encoding="utf-8",
        )
        self.assertIn("VALIDATION_CONTRACT_DELEGATE_CONTENT", self.validate())

    def test_comment_only_delegate_change_preserves_semantics(self) -> None:
        self.delegate_path.write_text(
            "# target checkout comment\n"
            + (ROOT / "templates/target" / DELEGATE_PATH).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        self.assertEqual(self.validate(), set())


if __name__ == "__main__":
    unittest.main()
