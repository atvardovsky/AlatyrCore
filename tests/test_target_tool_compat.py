from __future__ import annotations

import tempfile
import subprocess
import unittest
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_tool_compat import (  # noqa: E402
    assert_write_compatible,
    generation_provenance,
    generation_provenance_from_manifest_text,
    repository_state,
    source_template_provenance_errors,
)


class TargetToolCompatTests(unittest.TestCase):
    def test_repository_state_reads_revision_and_paths_with_spaces(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name)
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)
        subprocess.run(
            ["git", "config", "user.email", "fixture@example.invalid"],
            cwd=target,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Fixture"], cwd=target, check=True
        )
        tracked = target / "tracked file.txt"
        tracked.write_text("before\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=target, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=target, check=True)
        tracked.write_text("after\n", encoding="utf-8")
        (target / "new file.txt").write_text("new\n", encoding="utf-8")

        state = repository_state(target)

        self.assertRegex(state.revision, r"^[0-9a-f]{40}$")
        self.assertTrue(state.available)
        self.assertEqual(
            set(state.dirty_paths),
            {"tracked file.txt", "new file.txt"},
        )

    def test_repository_state_reports_both_sides_of_a_staged_rename(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name)
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)
        subprocess.run(
            ["git", "config", "user.email", "fixture@example.invalid"],
            cwd=target,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Fixture"], cwd=target, check=True
        )
        original = target / "before name.txt"
        original.write_text("content\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=target, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=target, check=True)
        subprocess.run(
            ["git", "mv", "before name.txt", "after name.txt"], cwd=target, check=True
        )

        state = repository_state(target)

        self.assertEqual(
            state.dirty_paths,
            ("after name.txt", "before name.txt"),
        )

    def test_generation_provenance_marks_a_non_repository_target_dirty(self) -> None:
        target = self.make_target(
            version=(ROOT / "VERSION").read_text(encoding="utf-8").strip(),
            schema=(ROOT / "ADAPTER_SCHEMA_VERSION").read_text(encoding="utf-8").strip(),
            template=(ROOT / "TEMPLATE_VERSION").read_text(encoding="utf-8").strip(),
        )

        provenance = generation_provenance(target, tool_name="fixture.py")

        self.assertEqual(provenance["target_worktree_state"], "dirty")
        self.assertEqual(
            provenance["target_dirty_paths"],
            ["<git-state-unavailable>"],
        )

    def make_target(self, *, version: str, schema: str, template: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name)
        (target / ".ai").mkdir()
        (target / ".ai/alatyr.yaml").write_text(
            f"""\
schema_version: {schema}
framework:
  version: {version}
  template_version: {template}
""",
            encoding="utf-8",
        )
        return target

    def test_write_guard_rejects_mismatched_target_without_migration_mode(self) -> None:
        target = self.make_target(version="0.1.0-alpha.1", schema="1", template="1")

        with self.assertRaisesRegex(ValueError, "refuses to write"):
            assert_write_compatible(target, tool_name="fixture.py")

    def test_write_guard_allows_explicit_migration_mode(self) -> None:
        target = self.make_target(version="0.1.0-alpha.1", schema="1", template="1")

        assert_write_compatible(
            target,
            tool_name="fixture.py",
            migration_staging=True,
        )

    def test_write_guard_ignores_unresolved_template_placeholders(self) -> None:
        target = self.make_target(
            version="{ALATYR_CORE_VERSION}",
            schema="{ALATYR_ADAPTER_SCHEMA_VERSION}",
            template="{ALATYR_TEMPLATE_VERSION}",
        )

        assert_write_compatible(target, tool_name="fixture.py")

    def test_source_template_provenance_is_stable(self) -> None:
        manifest_text = (ROOT / "templates/target/.ai/alatyr.yaml").read_text(
            encoding="utf-8",
        )

        provenance = generation_provenance_from_manifest_text(
            ROOT / "templates/target",
            tool_name="fixture.py",
            manifest_text=manifest_text,
        )

        self.assertEqual(
            source_template_provenance_errors(
                provenance,
                expected_tool="fixture.py",
            ),
            [],
        )
        self.assertEqual(provenance["source_revision"], "source-template")
        self.assertEqual(provenance["source_dirty_paths"], [])


if __name__ == "__main__":
    unittest.main()
