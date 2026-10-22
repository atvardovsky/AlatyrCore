from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_change_packages import changed_index_validator, git
from check_engineering_evidence import fixture_index, fixture_record
from target_adapter_validation.active_tasks import INDEX_PATH, validate_active_tasks
from target_adapter_validation.harness_scenarios.analysis_strategies import _model, _write_model
from target_adapter_validation.context import TargetRepositoryView


class ActiveTaskFixture(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name)
        git(self.target, "init", "-q")
        git(self.target, "config", "user.email", "fixture@example.invalid")
        git(self.target, "config", "user.name", "Fixture")
        (self.target / ".ai").mkdir()
        shutil.copy2(ROOT / "templates/target/.ai/.gitignore", self.target / ".ai/.gitignore")
        (self.target / "design.md").write_text("accepted design\n", encoding="utf-8")
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "design")
        self.base = git(self.target, "rev-parse", "HEAD")
        (self.target / "src").mkdir()
        (self.target / "src/example.txt").write_text("implementation\n", encoding="utf-8")
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "implement")
        self.result = git(self.target, "rev-parse", "HEAD")
        self.task = {"task_id": "fixture-task", "state": "active", "task_class": "standard-task", "problem_model": None, "completion_evidence": None, "canonical_owners": ["design.md"], "changed_fact_ids": ["change-1"], "incident_family_id": "none", "predecessor_task_ids": [], "latest_failed_gate_id": "none"}
        descriptor = self.target / ".ai/assistant/analysis-strategies/invariant-first.json"
        descriptor.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "templates/target/.ai/assistant/analysis-strategies/invariant-first.json", descriptor)
        self.model = _model()
        self.task["operation_id"] = self.model["operation_id"]
        self.model_path = self.target / ".ai/.runtime/problem-models/fixture.json"
        self.write_model()
        self.write_index()


    def bind(self, path):
        return {"path": path.relative_to(self.target).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


    def snapshot(self, paths):
        digest = hashlib.sha256()
        for path in sorted(paths):
            digest.update(path.encode() + b"\0" + (self.target / path).read_bytes() + b"\0")
        return digest.hexdigest()


    def write_model(self):
        _write_model(self.target, self.model_path, self.model)
        self.task["problem_model"] = self.bind(self.model_path)


    def write_index(self, tasks=None):
        self.task["repair_review_required"] = any(item.get("id") == "repair-evidence-review" and item.get("required") is True for item in self.model.get("proof_obligations", []))
        path = self.target / INDEX_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": 1, "index_kind": "target-active-task-index", "tasks": [self.task] if tasks is None else tasks}), encoding="utf-8")


    def check(self, *, selected=True, scope="full", comparison=True):
        checked = changed_index_validator(self.target)
        if not comparison:
            checked.diff_ref = None
        checked.current_task_id = "fixture-task" if selected else None
        checked.validation_scope = scope
        phase = next(phase for phase in checked.validation_phases(None, "core", set()) if phase.phase_id == "active-tasks")
        phase.run()
        return checked


    def errors(self, checked):
        return {finding.code for finding in checked.findings if finding.level == "error"}


    def close(self):
        self.closure = {"schema_version": 1, "record_kind": "alatyr-task-closure", "task_id": "fixture-task", "delivery": {"implementation": "complete", "evidence_finalization": "final", "publication": "not-requested"}, "engineering_evidence": {"state": "skipped", "materiality": "non-material", "reason": "No reusable finding beyond existing design", "record_ids": [], "preserved_owners": [], "next_safe_action": "none"}, "repository_binding": {"kind": "commit", "binding_state": "final", "base_revision": self.base, "result_revision": self.result, "prior_bindings": []}, "publication_evidence": [], "canonical_owners": ["design.md"], "implementation_surfaces": ["src/example.txt"], "changed_fact_ids": ["change-1"], "incident_family_id": "none", "predecessor_task_ids": [], "latest_failed_gate_id": "none", "knowledge_review": {"state": "not-required", "reason": "Existing owner is already routable", "candidate_ids": []}}
        self.task["state"] = "closed"
        self.closure["task_id"] = self.task["task_id"]
        self.closure["operation_id"] = self.task["operation_id"]
        self.closure["engineering_evidence"]["preservation"] = []
        self.closure["architecture_review"] = {"state": "not-required", "reason": "No architecture item changes in this fixture", "item_ids": []}
        self.write_closure()


    def write_closure(self):
        if self.model_path.is_file():
            directory = self.target / ".ai/assistant/task-evidence" / self.task["task_id"]
            directory.mkdir(parents=True, exist_ok=True)
            retained_model = directory / "model.json"
            retained_projection = directory / "projection.json"
            retained_model.write_bytes(self.model_path.read_bytes())
            projection = self.target / self.model["active_projection"]["path"]
            retained_projection.write_bytes(projection.read_bytes())
            self.closure["analysis_witness"] = {"model": self.bind(retained_model), "projection": self.bind(retained_projection), "retention_review": "fixture:retention-reviewed"}
        path = self.target / ".ai/assistant/task-closures" / (self.task["task_id"] + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.closure), encoding="utf-8")
        self.task["completion_evidence"] = self.bind(path)
        self.write_index()
