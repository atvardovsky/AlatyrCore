from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_tool_compat import assert_write_compatible  # noqa: E402


class TargetToolCompatTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
