from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from adapter_health_views import finding_groups, tooling_comparison, work_overview
from cooperation_preflight import preflight
from report_adapter_health import render_text
from target_adapter_validation.context import TargetRepositoryView
from tests import test_cooperation_planning as cooperation_fixtures
from tests.active_task_fixture import ActiveTaskFixture


class HealthViewTests(unittest.TestCase):
    def test_grouping_preserves_every_raw_finding_and_exposes_other_blockers(self):
        findings = [{"level": "error", "code": "STALE", "path": "current.json", "message": f"stale input {i}"} for i in range(63)]
        findings.append({"level": "error", "code": "OTHER_BLOCKER", "path": "contract.json", "message": "independent blocker"})
        before = copy.deepcopy(findings)
        groups = finding_groups(findings)
        self.assertEqual([g["count"] for g in groups], [63, 1])
        self.assertEqual(sorted(i for g in groups for i in g["finding_indexes"]), list(range(64)))
        payload = {"adapter_health": {"state": "blocked"}, "findings": findings, "counts": {"errors": 64}, "health_layers": {}, "evidence": {}, "placeholder_validation": {}, "capability_advisory": {}}
        text = render_text(payload)
        self.assertIn("63 findings", text)
        self.assertIn("OTHER_BLOCKER", text)
        self.assertEqual(findings, before)

    def test_comparison_distinguishes_versions_without_waiving_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); source = root / "source"; source.mkdir()
            target = root / "target"; (target / ".ai").mkdir(parents=True)
            for name, value in (("VERSION", "0.1.0-alpha.105"), ("ADAPTER_SCHEMA_VERSION", "86"), ("TEMPLATE_VERSION", "100")):
                (source / name).write_text(value)
            (target / ".ai/alatyr.yaml").write_text("schema_version: 76\nframework:\n  version: 0.1.0-alpha.94\n  template_version: 89\n")
            report = tooling_comparison(TargetRepositoryView(target), source)
            self.assertEqual(report["state"], "different-tooling-baseline")
            self.assertFalse(report["acceptance_granted"])
            self.assertFalse(report["findings_waived"])
            (target / ".ai/alatyr.yaml").write_bytes(b"\xff")
            self.assertEqual(tooling_comparison(TargetRepositoryView(target), source)["state"], "unknown")
            self.assertIsNone(work_overview(TargetRepositoryView(target))["team_claims"]["reported_entries"])

    def test_unknown_team_and_task_data_do_not_mean_no_work(self):
        with tempfile.TemporaryDirectory() as directory:
            view = TargetRepositoryView(Path(directory).resolve())
            result = work_overview(view)
            self.assertIsNone(result["analysis_tasks"]["active_count"])
            self.assertIsNone(result["team_claims"]["reported_entries"])
            self.assertEqual(result["sessions"]["state"], "not-observed")

    def test_overview_bounds_and_malformed_fields_remain_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = root / ".ai/assistant/team/active-work-index.json"
            path.parent.mkdir(parents=True)
            for count in (127, 128, 129):
                path.write_text(json.dumps({"entries": [{} for _ in range(count)], "generated_at": {"invalid": True}}))
                team = work_overview(TargetRepositoryView(root))["team_claims"]
                self.assertEqual(team["reported_entries"], count if count <= 128 else None)
                self.assertIsNone(team["recorded_at"])
            for size in (512 * 1024 - 1, 512 * 1024, 512 * 1024 + 1):
                content = b'{"entries": []}'
                path.write_bytes(content + b" " * (size - len(content)))
                team = work_overview(TargetRepositoryView(root))["team_claims"]
                self.assertEqual(team["reported_entries"], 0 if size <= 512 * 1024 else None)


class OwnerOverviewTests(ActiveTaskFixture):
    def test_empty_team_projection_does_not_hide_an_active_task(self):
        path = self.target / ".ai/assistant/team/active-work-index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": 1, "generated_at": "2026-01-01", "entries": []}))
        report = work_overview(TargetRepositoryView(self.target))
        self.assertEqual(report["analysis_tasks"]["active_count"], 1)
        self.assertEqual(report["team_claims"]["reported_entries"], 0)
        self.assertEqual(report["team_claims"]["freshness"], "not-verified")
        self.assertIn("do not mean no active", report["limitation"])


class StrictCooperationTests(unittest.TestCase):
    setUp = cooperation_fixtures.CooperationRuntimeTests.setUp
    git = cooperation_fixtures.CooperationRuntimeTests.git
    set_policy = cooperation_fixtures.CooperationRuntimeTests.set_policy

    def test_public_cli_preserves_advisory_mode_and_strictly_refuses_conflict(self):
        from session_presence_store import operate
        operate(self.target, "register", write=True, task="Peer", scope=["path:tools"])
        args = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "cooperation-preflight", "--target", str(self.target), "--scope", "path:tools"]
        advisory = subprocess.run(args, capture_output=True, text=True)
        strict = subprocess.run([*args, "--require-clear"], capture_output=True, text=True)
        self.assertEqual(advisory.returncode, 0, advisory.stderr)
        self.assertEqual(strict.returncode, 1, strict.stderr)
        self.assertEqual(json.loads(strict.stdout)["decision"], "coordinate-before-work")

    def test_malformed_coordination_is_unknown_not_clear(self):
        for bad in ({}, {"enabled": True, "coordination": {}, "sessions": []}, {"enabled": True, "coordination": [], "sessions": [{}]}):
            with patch("cooperation_preflight.operate", return_value=bad):
                self.assertEqual(preflight(self.target, ["path:tools"])["decision"], "unknown")

    def test_malformed_or_conflicting_peer_cannot_hide_behind_zero_counters(self):
        baseline = {"enabled": True, "coordination": {"reported_overlaps": 0, "unknown_scope_peers": 0, "same_worktree_uncertain": 0}, "sessions": [], "omitted_sessions": 0}
        for value in (None, True, 3, [], {}, "unrecognized", "unknown", "not-compared"):
            report = copy.deepcopy(baseline)
            report["sessions"] = [{"freshness": "recent", "overlap": value}]
            with self.subTest(value=value), patch("cooperation_preflight.operate", return_value=report):
                self.assertEqual(preflight(self.target, ["path:tools"])["decision"], "unknown")
        report["sessions"] = [{"freshness": "recent"}]
        with patch("cooperation_preflight.operate", return_value=report):
            self.assertEqual(preflight(self.target, ["path:tools"])["decision"], "unknown")
        report["sessions"][0]["overlap"] = "reported-overlap"
        with patch("cooperation_preflight.operate", return_value=report):
            self.assertEqual(preflight(self.target, ["path:tools"])["decision"], "coordinate-before-work")

    def test_public_strict_clear_does_not_claim_a_reservation(self):
        args = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "cooperation-preflight", "--target", str(self.target), "--scope", "path:tools", "--require-clear"]
        run = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("not a reservation", json.loads(run.stdout)["limitation"])


if __name__ == "__main__":
    unittest.main()
