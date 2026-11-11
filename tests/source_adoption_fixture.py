from __future__ import annotations

import json
import shutil
from unittest.mock import patch

from tests.active_task_fixture import ActiveTaskFixture, ROOT, git
from tests.test_request_brief import brief_fixture, action_fixture

import lifecycle_checkpoints as hooks
import source_adoption as adoption
from inspect_session_context import SOURCE_ANCHORS, capture


class SourceAdoptionFixture(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        policy = json.loads((ROOT / adoption.POLICY).read_bytes())
        knowledge = json.loads((ROOT / policy["knowledge_catalog"]).read_bytes())
        paths = {adoption.POLICY, policy["lifecycle_policy"], policy["knowledge_catalog"], policy["guide"],
                 "framework/capabilities.json", "conformance/runs/assistant-surfaces.json",
                 "tools/source_adoption.py", "tools/source_scope.py", *SOURCE_ANCHORS,
                 "tools/lifecycle_checkpoints.py", "tools/run_lifecycle_checkpoint.py", "tools/lifecycle_policy.py",
                 "tools/request_brief.py", "tools/delivery_control.py", "tools/delivery_progress.py", "tools/delivery_receipts.py"}
        paths.update(row["owner"] for row in knowledge["items"].values())
        paths.update(adoption.SOURCE_CONTROL_INPUTS)
        paths.update(path for row in policy["modules"].values() for path in row["references"])
        paths.update(path.relative_to(ROOT).as_posix() for path in
                     (ROOT / "templates/target/.ai/assistant/analysis-strategies").glob("*.json"))
        for relative in paths:
            destination = self.target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        (self.target / ".gitignore").write_text("/.ai/\n/CLAUDE.md\n/.cursor/\n", encoding="utf-8")
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "source inputs")
        self.source_base = git(self.target, "rev-parse", "HEAD")
        self.addCleanup(patch.stopall)
        patch.object(adoption, "ROOT", self.target).start()
        adoption.reconcile(self.target, write=True)
        self.brief_path = ".ai/.runtime/source-brief.json"
        self.baseline = ".ai/.runtime/source-baseline.json"
        self.request = self.event("request")
        self.brief = brief_fixture(self.model["objective"], self.model["proof_obligations"][0]["id"])
        self.brief.update(request_id=self.request["request_id"], source_ref="owner-message:source-test")
        self.write_brief()

    def event(self, event, **payload):
        return hooks.handle(self.target, "procedural", event, {"session_id": "source-fixture", **payload}, source_contour=True)

    def write_brief(self):
        (self.target / self.brief_path).write_text(json.dumps(self.brief), encoding="utf-8")

    def refresh_baseline(self, extra=()):
        selected = hooks.selected_task(self.target, "fixture-task", source_contour=True)
        paths = [*selected["checkpoint_inputs"], hooks.POLICY, self.brief_path, *extra]
        retained = capture(self.target, paths, source_contour=True)[0]
        (self.target / self.baseline).write_text(json.dumps(retained), encoding="utf-8")
        return retained

    def bind_request(self, **extra):
        return hooks.handle(self.target, "procedural", "before-action", {"session_id": "source-fixture"},
            bind={"request_id": self.request["request_id"], "baseline": self.baseline,
                  "task_id": "fixture-task", "request_brief": self.brief_path, **extra}, source_contour=True)

    def action(self, **changes):
        return action_fixture(request_id=self.request["request_id"], **changes)
