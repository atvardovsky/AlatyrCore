from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from project_understanding import understanding_request, check_understanding
from inspect_project_understanding import main


class ProjectUnderstandingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.target = self.root / "target"
        self.target.mkdir()
        (self.target / "README.md").write_text("# Example\n", encoding="utf-8")
        self.source = {"path": "README.md", "sha256": hashlib.sha256(b"# Example\n").hexdigest()}
        request = understanding_request()
        self.data = {"schema_version": 1, "report_kind": "project-understanding-result",
                     "scenario_sha256": request["scenario_sha256"], "assistant_surface": "manual-review",
                     "session_evidence": "Unknown hidden context; synthetic shape test, not an agent run.",
                     "exposed_context": [self.source],
                     "answers": [{"question_id": question["id"], "answer": "Example observed behavior.",
                                  "knowledge_state": "observed", "sources": [self.source], "limitations": []}
                                 for question in request["questions"]]}
        self.path = self.root / "result.json"

    def save(self):
        self.path.write_text(json.dumps(self.data), encoding="utf-8")

    def check(self):
        self.save()
        return check_understanding(self.target, self.path)

    def cli(self, *, prepare=False):
        self.save()
        return subprocess.run([sys.executable, "-B", str(ROOT / "tools/alatyr.py"),
                               "project-understanding", "--target", str(self.target),
                               *([] if prepare else ["--report", str(self.path)])],
                              capture_output=True, text=True, check=False)

    def test_preparation_and_validation_never_establish_semantic_acceptance(self):
        request = json.loads(self.cli(prepare=True).stdout)
        self.assertEqual("prepared-not-executed", request["status"])
        result = self.cli()
        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["acceptance_granted"])
        self.assertEqual("structurally-valid-review-required", payload["status"])
        self.assertEqual("not-independently-verified", payload["fresh_session_isolation"])
        self.assertEqual(["README.md"], [path.name for path in self.target.iterdir()])

    def test_missing_duplicate_or_unknown_questions_are_rejected(self):
        original = copy.deepcopy(self.data)
        for mutation in ("missing", "duplicate", "unknown"):
            self.data = copy.deepcopy(original)
            if mutation == "missing":
                self.data["answers"].pop()
            else:
                self.data["answers"][0]["question_id"] = (
                    "other-question" if mutation == "unknown" else self.data["answers"][1]["question_id"])
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.check()

    def test_malformed_enum_and_collection_matrix_uses_public_cli(self):
        original = copy.deepcopy(self.data)
        for field in ("knowledge_state", "sources", "limitations", "question_id", "answer"):
            for value in ({}, None, True, 3):
                self.data = copy.deepcopy(original)
                self.data["answers"][0][field] = value
                with self.subTest(field=field, value=value):
                    result = self.cli()
                    self.assertEqual(1, result.returncode, result.stderr)
                    self.assertEqual("blocked", json.loads(result.stdout)["status"])
                    self.assertNotIn("Traceback", result.stderr)

    def test_unknown_answers_remain_visible_and_require_reason(self):
        self.data["answers"][0].update(knowledge_state="unknown", sources=[], limitations=["No owner evidence was found."])
        self.assertEqual(["orientation"], self.check()["unknown_questions"])
        self.data["answers"][0]["limitations"] = []
        with self.assertRaises(ValueError):
            self.check()

    def test_accepted_without_sources_or_contradiction_without_both_sides_fails(self):
        self.data["answers"][0].update(knowledge_state="accepted", sources=[])
        with self.assertRaises(ValueError):
            self.check()
        self.data["answers"][0].update(knowledge_state="contradicted", sources=[self.source], limitations=["Owners disagree."])
        with self.assertRaises(ValueError):
            self.check()
        (self.target / "decision.md").write_text("Accepted decision\n", encoding="utf-8")
        second = {"path": "decision.md", "sha256": hashlib.sha256(b"Accepted decision\n").hexdigest()}
        self.data["exposed_context"].append(second)
        self.data["answers"][0]["sources"].append(second)
        self.check()

    def test_citations_must_exist_match_hash_and_be_exposed(self):
        original = copy.deepcopy(self.data)
        for mutation in ("missing", "stale", "unexposed", "escape", "duplicate", "bad-hash"):
            self.data = copy.deepcopy(original)
            if mutation == "missing":
                self.data["exposed_context"][0]["path"] = "missing.md"
            elif mutation == "stale":
                self.data["exposed_context"][0]["sha256"] = "0" * 64
            elif mutation == "unexposed":
                self.data["exposed_context"] = []
            elif mutation == "escape":
                self.data["exposed_context"][0]["path"] = "../result.json"
            elif mutation == "duplicate":
                self.data["exposed_context"].append(self.data["exposed_context"][0])
            else:
                self.data["exposed_context"][0]["sha256"] = {}
            with self.subTest(mutation=mutation), self.assertRaises((ValueError, OSError)):
                self.check()

    def test_scenario_binding_cannot_be_relabelled(self):
        self.data["scenario_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.check()

    def test_malformed_scenario_requirements_have_public_diagnostics(self):
        original = json.loads((ROOT / "conformance/operations/project-understanding.json").read_bytes())
        scenario = self.root / "scenario.json"
        for value in (None, {}, [], True, 3, "instructions"):
            changed = copy.deepcopy(original)
            if value is None:
                changed.pop("required_for_every_surface")
            else:
                changed["required_for_every_surface"] = value
            scenario.write_text(json.dumps(changed), encoding="utf-8")
            output = io.StringIO()
            with self.subTest(value=value), patch("project_understanding.SCENARIO", scenario), patch.object(
                    sys, "argv", ["project-understanding", "--target", str(self.target)]), redirect_stdout(output):
                self.assertEqual(1, main())
                self.assertEqual("blocked", json.loads(output.getvalue())["status"])

    def test_scenario_change_during_check_is_rejected(self):
        from project_evidence import ProjectEvidence
        scenario = self.root / "scenario.json"
        scenario.write_bytes((ROOT / "conformance/operations/project-understanding.json").read_bytes())
        original = ProjectEvidence.bindings
        def mutate(evidence):
            value = original(evidence)
            with scenario.open("a", encoding="utf-8") as stream:
                stream.write(" ")
            return value
        with patch("project_understanding.SCENARIO", scenario), patch.object(ProjectEvidence, "bindings", mutate), self.assertRaises(ValueError):
            self.check()

    def test_real_source_change_invalidates_result(self):
        self.check()
        (self.target / "README.md").write_text("Changed\n", encoding="utf-8")
        result = self.cli()
        self.assertEqual(1, result.returncode)
        self.assertIn("source is stale", json.loads(result.stdout)["findings"][0]["message"])


if __name__ == "__main__":
    unittest.main()
