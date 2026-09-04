from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation import harness_scenarios as scenarios  # noqa: E402
from target_adapter_validation.harness_scenarios.common import validator  # noqa: E402
import check_target_adapter_validator as harness  # noqa: E402


class TargetAdapterValidatorHarnessTests(unittest.TestCase):
    def test_scenario_registry_preserves_aggregate_order(self) -> None:
        self.assertEqual(
            [name for name, _ in scenarios.SCENARIOS],
            [
                "context-catalogs",
                "assistant-surfaces",
                "authorization",
                "context-routing",
                "framework-packaging",
                "capabilities-delegation",
                "operation-catalog",
                "module-surfaces",
                "testing-dependencies",
                "workspace-modes",
                "extensions",
                "support-information",
                "team-collaboration",
                "approval-scope",
                "evidence-contracts",
            ],
        )

    def test_scenario_orchestrator_runs_each_group_once(self) -> None:
        calls = []

        def scenario(name):
            def run(target: Path, failures: list[str]) -> None:
                calls.append((name, target))
                if name == "second":
                    failures.append("recorded failure")

            return run

        target = Path("fixture-target")
        failures = []
        registry = (
            ("first", scenario("first")),
            ("second", scenario("second")),
            ("third", scenario("third")),
        )

        with patch.object(scenarios, "SCENARIOS", registry):
            scenarios.run_scenarios(target, failures)

        self.assertEqual(
            calls,
            [("first", target), ("second", target), ("third", target)],
        )
        self.assertEqual(failures, ["recorded failure"])

    def test_aggregate_cli_preserves_success_contract(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/check_target_adapter_validator.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "OK: checked target adapter validator routing, scope, and evidence contracts\n",
        )
        self.assertEqual(result.stderr, "")

    def test_aggregate_main_preserves_failure_contract(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        def fail_scenario(target: Path, failures: list[str]) -> None:
            failures.extend(["first failure", "second failure"])

        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(harness, "check_core_contracts"))
            stack.enter_context(
                patch.object(harness, "run_scenarios", side_effect=fail_scenario)
            )
            stack.enter_context(contextlib.redirect_stdout(stdout))
            stack.enter_context(contextlib.redirect_stderr(stderr))
            result = harness.main()

        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue(),
            "FAIL: first failure\nFAIL: second failure\n",
        )

    def test_empty_target_validator_run_preserves_finding_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target_validator = validator(Path(directory))
            target_validator.run()

        payload = [
            {
                "level": finding.level,
                "code": finding.code,
                "message": finding.message,
                "path": finding.path,
            }
            for finding in target_validator.findings
        ]
        digest = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        self.assertEqual(len(payload), 93)
        self.assertEqual(
            digest,
            "23c9013250aed00acfc61ce3d794f687e7067b0ce8373991a4ee79acc00f9cb6",
        )
        self.assertEqual(
            payload[0],
            {
                "level": "error",
                "code": "REQUIRED_FILE_MISSING",
                "message": "required adapter file is missing",
                "path": "AGENTS.md",
            },
        )
        self.assertEqual(
            payload[-1],
            {
                "level": "info",
                "code": "EVIDENCE_SCOPE_CURRENT_STATE",
                "message": (
                    "validator findings describe current structural state; historical "
                    "actions require dated operation, approval, or migration records"
                ),
                "path": None,
            },
        )


if __name__ == "__main__":
    unittest.main()
