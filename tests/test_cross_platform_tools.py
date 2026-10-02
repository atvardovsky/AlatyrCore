from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_cross_platform_tools import (  # noqa: E402
    changed_tree_paths,
    source_tool_surface_failures,
    tree_hashes,
    verify_upgrade_documentation_failures,
)


POSIX_PREFIX = "python3 tools/alatyr.py verify-upgrade"
POWERSHELL_EXAMPLE = (
    ".\\tools\\alatyr.ps1 verify-upgrade --target C:\\repo "
    "--migration-diff migration.md --output result.json --diff-ref HEAD~1 "
    "--approval-record approval.json"
)
CMD_EXAMPLE = (
    "tools\\alatyr.cmd verify-upgrade --target C:\\repo "
    "--migration-diff migration.md --output result.json --diff-ref HEAD~1 "
    "--approval-record approval.json"
)
REQUIRED_OPTIONS = (
    "--target",
    "--migration-diff",
    "--output",
    "--diff-ref",
    "--approval-record",
)


def documentation_with_posix(arguments: list[str]) -> dict[str, str]:
    return {
        "INSTALL.md": " ".join([POSIX_PREFIX, *arguments]) + "\n",
        "tools/README.md": POWERSHELL_EXAMPLE + "\n" + CMD_EXAMPLE + "\n",
    }


class CrossPlatformToolTests(unittest.TestCase):
    def test_tree_hashes_ignore_git_metadata_but_detect_project_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            metadata = target / ".git"
            metadata.mkdir()
            index = metadata / "index"
            index.write_bytes(b"before")
            project_file = target / "project.txt"
            project_file.write_text("before\n", encoding="utf-8")

            before = tree_hashes(target)
            index.write_bytes(b"after")

            self.assertEqual(tree_hashes(target), before)

            project_file.write_text("after\n", encoding="utf-8")
            after = tree_hashes(target)

            self.assertEqual(changed_tree_paths(before, after), ["project.txt"])

    def test_current_verify_upgrade_documentation_uses_valid_parser_inputs(self) -> None:
        self.assertEqual(source_tool_surface_failures(), [])

    def test_verify_upgrade_rejects_every_missing_required_option(self) -> None:
        complete = [
            "--target", "/repo",
            "--migration-diff", "migration.md",
            "--output", "result.json",
            "--diff-ref", "HEAD~1",
            "--approval-record", "approval.json",
        ]

        for option in REQUIRED_OPTIONS:
            with self.subTest(option=option):
                index = complete.index(option)
                mutated = complete[:index] + complete[index + 2 :]
                failures = verify_upgrade_documentation_failures(
                    documentation_with_posix(mutated)
                )
                self.assertTrue(failures)
                self.assertIn("INSTALL.md:1", failures[0])

    def test_verify_upgrade_rejects_near_match_options(self) -> None:
        complete = [
            "--target", "/repo",
            "--migration-diff", "migration.md",
            "--output", "result.json",
            "--diff-ref", "HEAD~1",
            "--approval-record", "approval.json",
        ]

        for option in REQUIRED_OPTIONS:
            with self.subTest(option=option):
                mutated = [
                    option + "-invalid" if token == option else token
                    for token in complete
                ]
                failures = verify_upgrade_documentation_failures(
                    documentation_with_posix(mutated)
                )
                self.assertTrue(failures)
                self.assertIn("INSTALL.md:1", failures[0])

    def test_verify_upgrade_rejects_missing_option_values(self) -> None:
        complete = [
            "--target", "/repo",
            "--migration-diff", "migration.md",
            "--output", "result.json",
            "--diff-ref", "HEAD~1",
            "--approval-record", "approval.json",
        ]

        for option in REQUIRED_OPTIONS:
            with self.subTest(option=option):
                index = complete.index(option)
                mutated = complete[: index + 1] + complete[index + 2 :]
                failures = verify_upgrade_documentation_failures(
                    documentation_with_posix(mutated)
                )
                self.assertTrue(failures)
                self.assertIn("INSTALL.md:1", failures[0])


if __name__ == "__main__":
    unittest.main()
