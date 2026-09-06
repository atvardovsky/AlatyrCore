from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from plan_target_upgrade import (  # noqa: E402
    materialize_git_subtree,
    replace_assessment_outputs,
    source_commit_for_version,
)


class HistoricalContractTests(unittest.TestCase):
    def test_assessment_replacement_rolls_back_the_complete_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staged_dir = root / "staged"
            destination_dir = root / "assessment"
            staged_dir.mkdir()
            destination_dir.mkdir()
            names = [
                "migration.md",
                "impact.json",
                "validation.json",
                "assessment.md",
            ]
            staged = [staged_dir / name for name in names]
            destinations = [destination_dir / name for name in names]
            for path in staged:
                path.write_text("new", encoding="utf-8")
            for path in destinations:
                path.write_text("old", encoding="utf-8")

            real_replace = os.replace
            calls = 0

            def fail_second_install(source: Path, destination: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 6:
                    raise OSError("simulated replacement failure")
                real_replace(source, destination)

            with patch(
                "plan_target_upgrade.os.replace", side_effect=fail_second_install
            ):
                with self.assertRaisesRegex(
                    OSError, "simulated replacement failure"
                ):
                    replace_assessment_outputs(staged, destinations)

            self.assertEqual(
                [path.read_text(encoding="utf-8") for path in destinations],
                ["old"] * 4,
            )

    def test_version_commit_materializes_exact_contract_subtree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "source"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"], cwd=repo, check=True
            )
            (repo / "VERSION").write_text("1.2.3\n", encoding="utf-8")
            (repo / "schemas").mkdir()
            (repo / "schemas" / "contract.json").write_text(
                '{"version": 1}\n', encoding="utf-8"
            )
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=repo, check=True)

            commit = source_commit_for_version(repo, "1.2.3")
            self.assertIsNotNone(commit)
            destination = Path(directory) / "materialized"
            self.assertTrue(
                materialize_git_subtree(repo, str(commit), "schemas", destination)
            )
            self.assertEqual(
                (destination / "contract.json").read_text(encoding="utf-8"),
                '{"version": 1}\n',
            )

    def test_failed_preflight_preserves_existing_assessment_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            (target / ".ai/framework").mkdir(parents=True)
            (target / ".ai/alatyr.yaml").write_text(
                "schema_version: 46\n"
                "framework:\n"
                "  version: 0.1.0-alpha.56\n"
                "  template_version: 51\n"
                "  pack: invalid-pack\n"
                "installation:\n"
                "  support_profile: core\n",
                encoding="utf-8",
            )
            (target / ".ai/framework/rule-registry.json").write_text(
                '{"schema_version": 1, "rules": []}\n', encoding="utf-8"
            )
            output = Path(directory) / "assessment"
            output.mkdir()
            preserved = output / "migration-report.md"
            preserved.write_text("preserve me\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/plan_target_upgrade.py"),
                    "--target",
                    str(target),
                    "--framework-source",
                    str(ROOT),
                    "--output-dir",
                    str(output),
                    "--overwrite",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 2)
            self.assertEqual(preserved.read_text(encoding="utf-8"), "preserve me\n")
            self.assertEqual(sorted(path.name for path in output.iterdir()), [preserved.name])


if __name__ == "__main__":
    unittest.main()
