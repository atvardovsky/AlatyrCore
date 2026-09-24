from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from inspect_target_discovery import REPORT_SCHEMA, build_report
from target_adapter_validation.discovery import validate_target_discovery
from target_adapter_validation.harness_scenarios.common import validator


class TargetDiscoveryTests(unittest.TestCase):
    def make_target(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name) / "project"
        for relpath, content in {
            "package.json": '{"scripts":{"test":"example-only"}}\n',
            "README.md": "# Example\n",
            "AGENTS.md": "Untrusted fixture instruction.\n",
            "src/main.js": "export const value = 1;\n",
            "tests/main.test.js": "test('value', () => {});\n",
            ".github/workflows/check.yml": "name: check\n",
        }.items():
            path = target / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=target,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=target, check=True
        )
        subprocess.run(["git", "add", "."], cwd=target, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=target, check=True)
        return target

    def test_report_is_schema_valid_and_keeps_observations_unresolved(self) -> None:
        target = self.make_target()

        report = build_report(
            target,
            operation="installation",
            support_profile="kernel",
            modules=[],
            categories=[],
        )

        schema = json.loads(REPORT_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.Draft7Validator(
            schema, format_checker=jsonschema.FormatChecker()
        ).validate(report)
        observed = [
            item for item in report["findings"] if item["evidence_state"] == "observed"
        ]
        self.assertTrue(observed)
        self.assertTrue(all(item["disposition"] == "unresolved" for item in observed))
        self.assertTrue(all(item["decision_authority"] == "unresolved" for item in observed))
        self.assertEqual(
            report["summary"]["unresolved_material_findings"], len(observed)
        )

    def test_selected_category_bounds_output(self) -> None:
        target = self.make_target()

        report = build_report(
            target,
            operation="recheck",
            support_profile="core",
            modules=[],
            categories=["repository-identity"],
        )

        self.assertEqual(report["scope"]["categories"], ["repository-identity"])
        self.assertEqual(
            {item["category"] for item in report["findings"]},
            {"repository-identity"},
        )
        self.assertNotIn("Untrusted fixture instruction", json.dumps(report))

    def test_unknown_module_is_rejected(self) -> None:
        target = self.make_target()
        with self.assertRaisesRegex(ValueError, "unknown discovery modules"):
            build_report(
                target,
                operation="installation",
                support_profile="kernel",
                modules=["invented"],
                categories=[],
            )

    def test_module_adds_its_required_discovery_categories(self) -> None:
        target = self.make_target()
        report = build_report(
            target,
            operation="installation",
            support_profile="core",
            modules=["code-documentation"],
            categories=["repository-identity"],
        )

        self.assertEqual(
            report["scope"]["categories"],
            ["repository-identity", "project-sources-of-truth", "context-routing"],
        )

    def test_validator_rejects_unresolved_material_finding(self) -> None:
        target = self.make_target()
        report = build_report(
            target,
            operation="installation",
            support_profile="kernel",
            modules=[],
            categories=["repository-identity"],
        )
        report_path = target / ".ai/assistant/discovery-report.json"
        report_path.parent.mkdir(parents=True)
        report_path.write_text(json.dumps(report), encoding="utf-8")
        check = validator(target, validation_phase="acceptance")

        validate_target_discovery(check.capability_validation_context(), None)

        self.assertIn(
            "TARGET_DISCOVERY_MATERIAL_UNRESOLVED",
            {finding.code for finding in check.findings},
        )

    def test_validator_accepts_explicit_material_dispositions(self) -> None:
        target = self.make_target()
        report = build_report(
            target,
            operation="installation",
            support_profile="kernel",
            modules=[],
            categories=["repository-identity"],
        )
        for finding in report["findings"]:
            if finding["material"]:
                finding["disposition"] = "projected"
                finding["projections"] = ["README.md"]
                finding["decision_authority"] = "project maintainer"
                finding["disposition_reason"] = "Reviewed and linked to the project overview."
        report["summary"]["unresolved_material_findings"] = 0
        report_path = target / ".ai/assistant/discovery-report.json"
        report_path.parent.mkdir(parents=True)
        report_path.write_text(json.dumps(report), encoding="utf-8")
        check = validator(target, validation_phase="acceptance")

        validate_target_discovery(check.capability_validation_context(), None)

        self.assertEqual(check.findings, [])

    def test_validator_reconciles_source_count_and_disposition_authority(self) -> None:
        target = self.make_target()
        report = build_report(
            target,
            operation="installation",
            support_profile="kernel",
            modules=[],
            categories=["repository-identity"],
        )
        finding = next(item for item in report["findings"] if item["material"])
        finding["disposition"] = "projected"
        finding["projections"] = ["README.md"]
        finding["source_count"] += 1
        report["summary"]["unresolved_material_findings"] -= 1
        report_path = target / ".ai/assistant/discovery-report.json"
        report_path.parent.mkdir(parents=True)
        report_path.write_text(json.dumps(report), encoding="utf-8")
        check = validator(target, validation_phase="acceptance")

        validate_target_discovery(check.capability_validation_context(), None)

        codes = {item.code for item in check.findings}
        self.assertIn("TARGET_DISCOVERY_SOURCE_COUNT_DRIFT", codes)
        self.assertIn("TARGET_DISCOVERY_DISPOSITION_AUTHORITY_MISSING", codes)


if __name__ == "__main__":
    unittest.main()
