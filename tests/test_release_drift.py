from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_release_drift import (  # noqa: E402
    SCHEMA_CONTRACT_PATHS,
    contract_digest,
    materialize,
    nearest_release_baseline,
    nearest_tagged_baseline,
    prior_changelog_versions,
    validate_committed_report,
)
from check_versioning import (  # noqa: E402
    validate_current_release_binding,
    validate_release_tag,
)


class ReleaseBaselineTests(unittest.TestCase):
    def test_committed_report_requires_completed_source_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "docs/releases/2.0.0-migration.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "\n".join(
                    [
                        "From manifest: `baseline:framework/rule-registry.json`",
                        "To manifest: `source-tree:framework/rule-registry.json`",
                        "From framework version: `1.0.0`",
                        "To framework version: `2.0.0`",
                        "From adapter schema version: `1`",
                        "To adapter schema version: `1`",
                        "From template version: `1`",
                        "To template version: `2`",
                        "From contract SHA-256: `from-digest`",
                        "To contract SHA-256: `to-digest`",
                        "Source validation: `passed`",
                        "Source validation commands:",
                        "- `python3 tools/check_all.py --profile full`",
                        "Source validation result: `all checks passed`",
                        "Source validation revision: `fixture-tree`",
                        "Source validation completed at: `2026-09-04T12:00:00+00:00`",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            args = {
                "baseline": "baseline",
                "from_version": "1.0.0",
                "to_version": "2.0.0",
                "from_adapter": "1",
                "to_adapter": "1",
                "from_template": "1",
                "to_template": "2",
                "from_digest": "from-digest",
                "to_digest": "to-digest",
            }
            with patch("check_release_drift.ROOT", root):
                self.assertEqual(validate_committed_report(**args), [])
                report.write_text(
                    report.read_text(encoding="utf-8").replace(
                        "Source validation: `passed`",
                        "Source validation: `pending`",
                    ),
                    encoding="utf-8",
                )
                self.assertTrue(validate_committed_report(**args))

                report.write_text(
                    report.read_text(encoding="utf-8")
                    .replace("Source validation: `pending`", "Source validation: `passed`")
                    .replace(
                        "Source validation completed at: `2026-09-04T12:00:00+00:00`",
                        "Source validation completed at: `2026-09-04 12:00:00`",
                    ),
                    encoding="utf-8",
                )
                failures = validate_committed_report(**args)
                self.assertTrue(
                    any("timezone-aware ISO-8601" in failure for failure in failures)
                )

    def test_prefers_reviewed_incremental_checkpoint_over_distant_tag(self) -> None:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

        baseline, intervening = nearest_release_baseline(version)
        nearest_prior = prior_changelog_versions(version)[0]

        self.assertEqual(baseline.label, f"release-checkpoint:{nearest_prior}")
        self.assertEqual(baseline.kind, "checkpoint")
        self.assertEqual(intervening, [])

    def test_uses_nearest_real_tag_and_preserves_intervening_report_chain(self) -> None:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

        tag, intervening = nearest_tagged_baseline(version)

        self.assertEqual(tag, "v0.1.0-alpha.3")
        self.assertEqual(intervening[0], prior_changelog_versions(version)[0])
        self.assertEqual(intervening[-1], "0.1.0-alpha.4")
        self.assertEqual(
            prior_changelog_versions(version)[: len(intervening)], intervening
        )

    def test_all_shipped_schemas_are_release_contract_paths(self) -> None:
        schema_paths = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "schemas").rglob("*.json")
        }

        self.assertTrue(schema_paths)
        self.assertTrue(schema_paths.issubset(SCHEMA_CONTRACT_PATHS))

    def test_contract_digest_changes_with_schema_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "framework").mkdir()
            (root / "schemas").mkdir()
            (root / "templates" / "target").mkdir(parents=True)
            (root / "schemas/example.json").write_text("{}\n", encoding="utf-8")
            for name in ["VERSION", "ADAPTER_SCHEMA_VERSION", "TEMPLATE_VERSION"]:
                (root / name).write_text("1\n", encoding="utf-8")

            before = contract_digest(root)
            (root / "schemas/example.json").write_text(
                '{"type":"object"}\n', encoding="utf-8"
            )

            self.assertNotEqual(contract_digest(root), before)

    def test_materialize_restores_baseline_contract_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            materialize("HEAD", "framework", root)

            self.assertTrue((root / "framework" / "rule-registry.json").is_file())

    def test_release_tag_must_match_version(self) -> None:
        self.assertEqual(validate_release_tag("1.2.3", "v1.2.3"), [])
        self.assertTrue(validate_release_tag("1.2.3", "v1.2.4"))

    def test_current_release_binding_requires_tag_on_head(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "alatyr@example.invalid"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Alatyr Check"],
                cwd=root,
                check=True,
            )
            (root / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)

            self.assertTrue(validate_current_release_binding("1.2.3", root))
            subprocess.run(["git", "tag", "v1.2.3"], cwd=root, check=True)
            self.assertEqual(validate_current_release_binding("1.2.3", root), [])

            (root / "README.md").write_text("next\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-qam", "next"], cwd=root, check=True)
            self.assertTrue(validate_current_release_binding("1.2.3", root))


if __name__ == "__main__":
    unittest.main()
