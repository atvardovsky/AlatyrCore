from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_source_context_routing as routing
from source_state import source_snapshot


class SourceContextInventoryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.target = Path(directory.name)
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Fixture")
        (self.target / "tests").mkdir()
        (self.target / ".gitignore").write_text("tests/00-ignored.py\n", encoding="utf-8")
        (self.target / "tests/z-existing.py").write_text("small fixture\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "initial fixture")
        root_patch = patch.object(routing, "ROOT", self.target)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.addCleanup(routing._source_files.cache_clear)
        self.entry = {
            "id": "fixture-tests",
            "resolver": "path-pattern",
            "path_or_registry_query": "tests/**",
        }

    def git(self, *arguments):
        return subprocess.run(
            ["git", *arguments], cwd=self.target, check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    def select(self):
        routing._source_files.cache_clear()
        return routing._source_files(), routing._fixture_selectors([self.entry])

    def test_inventory_and_selection_match_before_staging_and_after_commit(self):
        (self.target / "tests/a-new.py").write_text("new fixture\n", encoding="utf-8")
        (self.target / "tests/00-ignored.py").write_text("ignored\n", encoding="utf-8")
        expected_paths = (".gitignore", "tests/a-new.py", "tests/z-existing.py")
        expected_selection = {"requested_paths": ["tests/a-new.py"]}
        for phase in ("untracked", "staged", "committed"):
            with self.subTest(phase=phase):
                if phase == "staged":
                    self.git("add", "tests/a-new.py")
                elif phase == "committed":
                    self.git("commit", "-qm", "new fixture")
                paths, selectors = self.select()
                self.assertEqual(paths, expected_paths)
                self.assertEqual(selectors, expected_selection)
                self.assertEqual(set(paths), set(source_snapshot(self.target)))
                self.assertEqual(len(paths), len(set(paths)))

    def test_oversized_untracked_fixture_is_measured_before_staging(self):
        (self.target / "tests/a-new.py").write_text("word " * 101, encoding="utf-8")
        for phase in ("untracked", "staged", "committed"):
            with self.subTest(phase=phase):
                if phase == "staged":
                    self.git("add", "tests/a-new.py")
                elif phase == "committed":
                    self.git("commit", "-qm", "oversized fixture")
                _, selectors = self.select()
                self.assertEqual(selectors, {"requested_paths": ["tests/a-new.py"]})
                measured = routing.word_count(selectors["requested_paths"])
                self.assertEqual(measured, 101)
                self.assertGreater(measured, 100)


if __name__ == "__main__":
    unittest.main()
