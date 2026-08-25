from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from conformance_execution.contract import (  # noqa: E402
    collect_reports,
    executor_capability,
    new_execution_record,
    record_execution,
    record_validation,
    validate_execution_record,
    write_execution_record,
)
from check_conformance_reports import validate_execution_record_file  # noqa: E402


class ConformanceExecutionTests(unittest.TestCase):
    def test_native_executor_records_complete_lifecycle(self) -> None:
        record = new_execution_record(
            executor_id="codex-cli",
            assistant_surface="codex",
            run_id="test-run",
            source_commit="test-commit",
            record_kind="assistant-conformance-execution",
        )
        record_execution(
            record,
            mode="native-invoke",
            outcome="completed",
            detail="test invocation",
        )
        collect_reports(record, [Path("reports") / "fixture.json"])
        record_validation(record, passed=True, detail="test validation")

        self.assertEqual(record["status"], "validated")
        self.assertEqual(validate_execution_record(record), [])

    def test_manual_executor_cannot_claim_native_invocation(self) -> None:
        record = new_execution_record(
            executor_id="manual-import",
            assistant_surface="claude",
            run_id="manual-run",
            source_commit="test-commit",
            record_kind="assistant-conformance-execution",
        )

        with self.assertRaisesRegex(ValueError, "does not support mode native-invoke"):
            record_execution(
                record,
                mode="native-invoke",
                outcome="completed",
                detail="invalid claim",
            )

    def test_manual_executor_remains_manual_evidence_only(self) -> None:
        capability = executor_capability("manual-import")

        self.assertEqual(capability["availability"], "manual-evidence-only")
        self.assertEqual(capability["execution_modes"], ["manual-import"])

    def test_lifecycle_record_is_found_beside_a_report_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            reports = Path(directory) / "reports"
            reports.mkdir()
            record = new_execution_record(
                executor_id="manual-import",
                assistant_surface="claude",
                run_id="manual-run",
                source_commit="test-commit",
                record_kind="assistant-conformance-execution",
            )
            record_execution(
                record,
                mode="manual-import",
                outcome="completed",
                detail="reviewed manual import",
            )
            collect_reports(record, [Path("reports") / "fixture.json"])
            record_validation(record, passed=True, detail="reviewed fixture reports")
            write_execution_record(reports.parent / "execution-record.json", record)

            self.assertEqual(
                validate_execution_record_file(
                    reports, require_execution_record=True
                ),
                [],
            )

    def test_operation_routing_protocol_matches_catalog_and_authorization(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "check_operation_catalog.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_delivery_contract_templates_are_checked(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "check_output_contracts.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
