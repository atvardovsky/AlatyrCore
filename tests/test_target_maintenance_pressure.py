from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.harness_scenarios.common import validator  # noqa: E402


class TargetMaintenancePressureTests(unittest.TestCase):
    def test_unsharded_approval_root_reports_pressure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            approval_root = target / ".ai/assistant/approvals"
            approval_root.mkdir(parents=True)
            records = []
            for index in range(65):
                record = approval_root / f"A-{index:03d}.md"
                record.write_text(f"Approval ID: A-{index}\n", encoding="utf-8")
                records.append(record)
            target_validator = validator(target)

            target_validator.check_approval_archive_pressure(records)

        self.assertIn(
            "APPROVAL_ARCHIVE_PRESSURE",
            {finding.code for finding in target_validator.findings},
        )

    def test_untyped_and_oversized_package_artifacts_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            package_root = target / ".ai/assistant/change-packages"
            package_root.mkdir(parents=True)
            artifact = package_root / "raw-replay.json"
            artifact.write_text(
                json.dumps({"events": ["x" * (65 * 1024)]}),
                encoding="utf-8",
            )
            target_validator = validator(target)

            target_validator.check_change_package_directory_hygiene()

        codes = {finding.code for finding in target_validator.findings}
        self.assertIn("PACKAGE_DIRECTORY_ARTIFACT_ROLE", codes)
        self.assertIn("PACKAGE_DIRECTORY_ARTIFACT_SIZE", codes)


if __name__ == "__main__":
    unittest.main()
