from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_cross_platform_tools import (  # noqa: E402
    changed_tree_paths,
    tree_hashes,
    verify_upgrade_documentation_failures,
)
from verify_target_upgrade import required_cli_option_groups  # noqa: E402


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

    def test_verify_upgrade_required_options_come_from_parser(self) -> None:
        required = {option for group in required_cli_option_groups() for option in group}

        self.assertEqual(
            required,
            {
                "--target",
                "--migration-diff",
                "--output",
                "--diff-ref",
                "--approval-record",
            },
        )

    def test_verify_upgrade_documentation_rejects_stale_example(self) -> None:
        failures = verify_upgrade_documentation_failures(
            {
                "example.md": (
                    "python3 tools/alatyr.py verify-upgrade --target /target "
                    "--migration-diff migration.md --output result.json\n"
                )
            }
        )

        self.assertEqual(len(failures), 1)
        self.assertIn("--diff-ref", failures[0])
        self.assertIn("--approval-record", failures[0])

    def test_verify_upgrade_documentation_accepts_complete_example(self) -> None:
        failures = verify_upgrade_documentation_failures(
            {
                "example.md": (
                    "python3 tools/alatyr.py verify-upgrade --target /target "
                    "--migration-diff migration.md --output result.json "
                    "--diff-ref PRE_UPDATE_COMMIT "
                    "--approval-record /target/approval.json\n"
                )
            }
        )

        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
