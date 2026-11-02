from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_engineering_evidence as engineering
from prepare_effectiveness_benchmark import MODES, render_prompt


class CognitiveReportToolTests(unittest.TestCase):
    def test_help_and_invalid_arguments_do_not_run_checks_or_fixtures(self):
        for args, code in ((["--help"], 0), (["-h"], 0), (["--unknown"], 2)):
            with self.subTest(args=args), patch.object(engineering, "require_text", side_effect=AssertionError("check ran")), \
                    patch.object(engineering, "validate_fixture", side_effect=AssertionError("fixture ran")), \
                    patch.object(Path, "read_text", side_effect=AssertionError("source read")), \
                    patch.object(subprocess, "run", side_effect=AssertionError("command ran")), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit) as result:
                engineering.main(args)
            self.assertEqual(result.exception.code, code)
        result = subprocess.run([sys.executable, str(ROOT / "tools/check_engineering_evidence.py"), "--help"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)
        self.assertNotIn("OK: checked", result.stdout)

    def test_every_prompt_mode_supplies_exact_unambiguous_report_name(self):
        task = {"id": "T01", "name": 'Repair "quotes", `ticks`, \u03bb\nand a newline',
                "class_id": "bounded-repair", "request": "Fix the selected boundary", "allowed_actions": "code-and-tests",
                "task_profile": "code-local", "acceptance_criteria": ["original behavior holds"]}
        for mode in MODES:
            prompt = render_prompt(task=task, mode=mode, run_id="run-1", repetition=1,
                                   target=Path("/target"), report=Path("/run with spaces/report.json"), benchmark_id="benchmark-1",
                                   commit="a" * 40, evidence_contract_digest="b" * 64, baseline_hash="c" * 64)
            line = next(row for row in prompt.splitlines() if row.startswith("- Report `task`"))
            self.assertEqual(json.loads(line.split(": ", 1)[1]), task["name"])
            self.assertIn("run-contract.json", prompt)
            arguments = json.loads(next(row for row in prompt.splitlines() if row.startswith('["--run-contract"')))
            self.assertEqual(arguments, ["--run-contract", str(Path("/run with spaces/run-contract.json")),
                                         "--report", str(Path("/run with spaces/report.json"))])
            self.assertIn("not establish independent review", prompt)


if __name__ == "__main__":
    unittest.main()
