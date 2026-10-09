from __future__ import annotations

import copy
import json
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
        ]
        for command in cases:
            with self.subTest(command=command):
                self.assertIn(
                    "VALIDATION_CONTRACT_DELEGATE_ARGUMENTS",
                    self.validate(self.current_change_contract(command)),
                )

    def test_allowlisted_current_change_bindings_pass(self) -> None:
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
