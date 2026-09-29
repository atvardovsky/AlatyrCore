from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from approval_archive import build_archive_index  # noqa: E402
from target_adapter_validation.harness_scenarios.common import Finding, validator  # noqa: E402


class ApprovalArchiveTests(unittest.TestCase):
    def test_monthly_shards_are_content_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            shard = target / ".ai/assistant/approvals/archive/2026-09"
            shard.mkdir(parents=True)
            record = shard / "approval.json"
            record.write_text('{"approval_id":"A"}\n', encoding="utf-8")

            before = build_archive_index(target)
            record.write_text('{"approval_id":"B"}\n', encoding="utf-8")
            after = build_archive_index(target)

        self.assertEqual(before["shards"][0]["record_count"], 1)
        self.assertNotEqual(
            before["shards"][0]["digest"], after["shards"][0]["digest"]
        )

    def test_empty_archive_has_no_shards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(build_archive_index(Path(directory))["shards"], [])

    def test_validator_detects_tampered_archive_shard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            shard = target / ".ai/assistant/approvals/archive/2026-09"
            shard.mkdir(parents=True)
            record = shard / "approval.json"
            record.write_text('{"approval_id":"A"}\n', encoding="utf-8")
            index = target / ".ai/assistant/approvals/archive-index.json"
            index.write_text(
                json.dumps(build_archive_index(target), indent=2) + "\n",
                encoding="utf-8",
            )

            current = validator(target)
            self.assertTrue(current.check_approval_archive_index())
            record.write_text('{"approval_id":"B"}\n', encoding="utf-8")
            tampered = validator(target)
            self.assertFalse(tampered.check_approval_archive_index())

        self.assertIn(
            "APPROVAL_ARCHIVE_INDEX_STALE",
            {finding.code for finding in tampered.findings},
        )

    def test_repeated_archive_information_is_compacted_without_losing_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            instance = validator(Path(directory))
            instance.findings.extend(
                Finding("info", "ARCHIVE_DETAIL", "detail", f"record-{index}.json")
                for index in range(6)
            )
            instance._compact_approval_archive_findings(0)

        self.assertEqual(len(instance.findings), 1)
        self.assertEqual(instance.findings[0].level, "info")
        self.assertIn("6 historical approval finding", instance.findings[0].message)
        self.assertEqual(instance.approval_archive_summary["findings_grouped"], 6)


if __name__ == "__main__":
    unittest.main()
