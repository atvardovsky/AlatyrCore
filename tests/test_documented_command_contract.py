from __future__ import annotations

import argparse
import contextlib
import io
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from documented_command_contract import (  # noqa: E402
    DocumentedInvocation,
    argparse_documentation_failures,
)


INVOCATION = DocumentedInvocation("tool verify", "posix")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="tool verify")
    result.add_argument("--target", required=True)
    result.add_argument("--diff-ref", required=True)
    return result


def parser_accepts(command: str) -> bool:
    arguments = shlex_arguments(command.split("tool verify", 1)[1])
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            parser().parse_args(arguments)
        except SystemExit:
            return False
    return True


def shlex_arguments(arguments: str) -> list[str]:
    import shlex

    return shlex.split(arguments)


class DocumentedCommandContractTests(unittest.TestCase):
    def test_checker_and_parser_agree_for_boundary_mutations(self) -> None:
        cases = {
            "valid": "tool verify --target /repo --diff-ref HEAD~1",
            "quoted-value": 'tool verify --target "/repo with spaces" --diff-ref HEAD~1',
            "missing-first-required-option": "tool verify --diff-ref HEAD~1",
            "near-match-option": (
                "tool verify --target /repo --diff-ref-invalid HEAD~1"
            ),
            "missing-option-value": "tool verify --target --diff-ref HEAD~1",
            "unknown-option": (
                "tool verify --target /repo --diff-ref HEAD~1 --unknown value"
            ),
        }

        for name, command in cases.items():
            with self.subTest(name=name):
                parser_result = parser_accepts(command)
                checker_result = not argparse_documentation_failures(
                    {"example.md": command},
                    invocations=(INVOCATION,),
                    parser_factory=parser,
                )
                self.assertEqual(checker_result, parser_result)

    def test_missing_invocation_is_not_hidden_by_other_text(self) -> None:
        failures = argparse_documentation_failures(
            {"example.md": "No executable example.\n"},
            invocations=(INVOCATION,),
            parser_factory=parser,
        )

        self.assertEqual(failures, ["missing documented command example: tool verify"])

    def test_inline_markdown_command_is_parsed_without_delimiters(self) -> None:
        failures = argparse_documentation_failures(
            {
                "example.md": (
                    "- `tool verify --target /repo --diff-ref HEAD~1`\n"
                )
            },
            invocations=(INVOCATION,),
            parser_factory=parser,
        )

        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
