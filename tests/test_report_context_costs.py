from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from report_context_costs import build_installed_report, installed_path  # noqa: E402


class InstalledContextCostPathTests(unittest.TestCase):
    def test_installed_path_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir()

            self.assertIsNone(installed_path(target, "../outside.txt"))
            self.assertIsNone(installed_path(target, ".ai/../../outside.txt"))

    def test_installed_path_rejects_invalid_portable_spellings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)

            self.assertIsNone(installed_path(target, ""))
            self.assertIsNone(installed_path(target, r".ai\assistant\router.json"))
            self.assertIsNone(installed_path(target, "C:relative\\router.json"))

    def test_installed_path_rejects_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)

            self.assertIsNone(installed_path(target, str(target / "AGENTS.md")))
            self.assertIsNone(installed_path(target, r"C:\outside\AGENTS.md"))
            self.assertIsNone(installed_path(target, r"\\server\share\AGENTS.md"))

    def test_installed_path_accepts_target_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)

            self.assertEqual(
                installed_path(target, ".ai/assistant/context-router.json"),
                (target / ".ai/assistant/context-router.json").resolve(),
            )
            self.assertEqual(
                installed_path(target, "AGENTS.md"),
                (target / "AGENTS.md").resolve(),
            )

    def test_installed_path_rejects_symlink_escape_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir()
            outside = root / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            link = target / "linked-outside.txt"
            try:
                link.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            self.assertIsNone(installed_path(target, "linked-outside.txt"))

    def test_installed_report_rejects_symlinked_router_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            router_dir = target / ".ai" / "assistant"
            router_dir.mkdir(parents=True)
            outside = root / "outside-router.json"
            outside.write_text("{}\n", encoding="utf-8")
            try:
                (router_dir / "context-router.json").symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "outside target root"):
                build_installed_report(target)


if __name__ == "__main__":
    unittest.main()
