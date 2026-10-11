from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from tests import test_active_task_evidence as task_fixture
from architecture_review import BoundedReviewDigests, review_failures
from suggest_project_knowledge import recent_task_signals, target_owned_owner
from suggest_project_knowledge import suggestions
from tests import test_project_knowledge_suggestions as package_fixture
from target_adapter_validation.context import TargetRepositoryView


class TaskDiscoveryReviewTests(unittest.TestCase):
    def fixture(self):
        fixture = task_fixture.ActiveTaskTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.close()
        other_task = dict(fixture.task, task_id="second-task")
        other_closure = dict(fixture.closure, task_id="second-task")
        path = fixture.target / ".ai/assistant/task-closures/second-task.json"
        path.write_text(json.dumps(other_closure), encoding="utf-8")
        other_task["completion_evidence"] = fixture.bind(path)
        fixture.write_index([fixture.task, other_task])
        return fixture

    def review(self, fixture):
        return {"state": "reviewed", "reason": "Reviewed ownership against selected sources", "reviewer": "project-maintainer", "reviewed_at": "2026-01-01T00:00:00Z", "changed_fact_ids": ["change-1"], "inputs": [fixture.bind(fixture.target / "design.md")]}

    def test_reserved_owner_filter_is_normalized_and_precise(self):
        for owner in [".ai/framework/context.md", ".ai/FRAMEWORK/context.md", ".AI/framework/context.md", ".ai\\framework\\context.md", "./.ai/./framework/context.md", "../design.md", "/design.md"]:
            self.assertFalse(target_owned_owner(owner), owner)
        for owner in ["framework/design.md", ".ai/framework-docs/design.md", ".ai/project/design.md", ".ai/assistant/gates/test.md"]:
            self.assertTrue(target_owned_owner(owner), owner)

    def test_registered_final_closures_produce_bounded_review_signals(self):
        fixture = self.fixture()
        result = recent_task_signals(fixture.target)
        self.assertEqual(result["coverage"], "registered-only")
        self.assertEqual(result["signals"][0]["occurrences"], 2)
        self.assertEqual(result["signals"][0]["selector"], "design.md")
        for binding in result["source_files"]:
            self.assertEqual(binding["sha256"], hashlib.sha256((fixture.target / binding["path"]).read_bytes()).hexdigest())

    def test_missing_fields_on_both_sides_are_not_credited(self):
        fixture = self.fixture()
        index = json.loads((fixture.target / task_fixture.INDEX_PATH).read_text())
        for task in index["tasks"]:
            path = fixture.target / task["completion_evidence"]["path"]
            closure = json.loads(path.read_text())
            closure.pop("changed_fact_ids")
            path.write_text(json.dumps(closure))
            task.pop("changed_fact_ids")
            task["completion_evidence"] = fixture.bind(path)
        fixture.write_index(index["tasks"])
        result = recent_task_signals(fixture.target)
        self.assertEqual(result["signals"], [])
        self.assertEqual(result["coverage"], "incomplete")

    def test_optional_corruption_and_disappearance_return_incomplete_coverage(self):
        fixture = self.fixture()
        path = fixture.target / task_fixture.INDEX_PATH
        path.write_text("{")
        self.assertEqual(recent_task_signals(fixture.target)["coverage"], "unavailable")
        path.unlink()
        self.assertEqual(recent_task_signals(fixture.target)["coverage"], "unavailable")
        with patch.object(Path, "resolve", side_effect=OSError("concurrent disappearance")):
            self.assertEqual(recent_task_signals(fixture.target)["coverage"], "unavailable")

    def test_hash_and_decoding_share_one_bounded_read(self):
        fixture = self.fixture()
        calls = []
        original = TargetRepositoryView.read_bytes_result
        def observe(view, path, **kwargs):
            calls.append(path)
            return original(view, path, **kwargs)
        with patch.object(TargetRepositoryView, "read_bytes_result", observe), patch("suggest_project_knowledge.sha256", side_effect=AssertionError("split hash read")), patch("suggest_project_knowledge.load_object", side_effect=AssertionError("split decode read")):
            self.assertEqual(len(recent_task_signals(fixture.target)["signals"]), 1)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(set(calls)), 3)

    def test_review_freshness_is_independent_of_support_hashes(self):
        fixture = self.fixture()
        review = self.review(fixture)
        self.assertEqual(review_failures(review, BoundedReviewDigests(TargetRepositoryView(fixture.target))), [])
        (fixture.target / "design.md").write_text("changed decision\n")
        failures = review_failures(review, BoundedReviewDigests(TargetRepositoryView(fixture.target)))
        self.assertTrue(any("revalidation required" in failure for failure in failures))

    def test_review_reads_have_shared_file_total_and_unique_limits(self):
        fixture = self.fixture()
        path = fixture.target / "large.txt"
        path.write_bytes(b"x" * 1024 * 1024)
        digests = BoundedReviewDigests(TargetRepositoryView(fixture.target))
        self.assertIsNotNone(digests("large.txt"))
        self.assertEqual(digests("large.txt"), digests("large.txt"))
        self.assertEqual(digests.total_bytes, 1024 * 1024)
        path.write_bytes(b"x" * (1024 * 1024 + 1))
        with patch.object(Path, "open", side_effect=AssertionError("oversized input read")):
            self.assertIsNone(BoundedReviewDigests(TargetRepositoryView(fixture.target))("large.txt"))
        for index in range(9):
            (fixture.target / f"source-{index}.txt").write_bytes(b"x" * 1024 * 1024)
        digests = BoundedReviewDigests(TargetRepositoryView(fixture.target))
        for index in range(8):
            self.assertIsNotNone(digests(f"source-{index}.txt"))
        (fixture.target / "empty.txt").write_bytes(b"")
        self.assertEqual(digests("empty.txt"), hashlib.sha256(b"").hexdigest())
        self.assertEqual(digests.total_bytes, 8 * 1024 * 1024)
        self.assertIsNone(digests("source-8.txt"))
        digests = BoundedReviewDigests(TargetRepositoryView(fixture.target))
        for index in range(257):
            (fixture.target / f"tiny-{index}.txt").write_bytes(b"x")
            self.assertEqual(digests(f"tiny-{index}.txt") is not None, index < 256)

    def test_selected_closure_requires_related_current_architecture_review(self):
        fixture = self.fixture()
        catalog = {"schema_version": 2, "areas": [{"id": "main-area", "source_review": self.review(fixture)}], "patterns": []}
        path = fixture.target / ".ai/project/architecture/catalog.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(catalog))
        self.assertIn("TASK_ARCHITECTURE_REVIEW", fixture.errors(fixture.check()))
        fixture.closure["architecture_review"].update(state="reviewed", item_ids=["main-area"])
        fixture.write_closure()
        self.assertEqual(fixture.errors(fixture.check()), set())
        (fixture.target / "design.md").write_text("changed design")
        self.assertIn("TASK_ARCHITECTURE_REVIEW", fixture.errors(fixture.check()))
        catalog["areas"].append(copy.deepcopy(catalog["areas"][0]))
        path.write_text(json.dumps(catalog))
        self.assertIn("TASK_ARCHITECTURE_REVIEW", fixture.errors(fixture.check()))

    def test_registered_architecture_handler_reports_stale_inputs(self):
        fixture = self.fixture()
        for relative in [".ai/project/architecture/README.md", ".ai/assistant/context/intents/architecture-request.json", ".ai/assistant/flows/architecture-assistance.flow.md", ".ai/assistant/templates/architecture-pattern.md", ".ai/assistant/templates/architecture-area.md", ".ai/assistant/templates/architecture-discussion-result.md"]:
            destination = fixture.target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / "templates/target" / relative, destination)
        framework = fixture.target / ".ai/framework/architecture-knowledge.md"
        framework.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "framework/architecture-knowledge.md", framework)
        (fixture.target / ".ai/assistant/module-profile.md").write_text("Module: `architecture-knowledge`\nState: `enabled`\n")
        catalog = json.loads((ROOT / "templates/target/.ai/project/architecture/catalog.json").read_text())
        catalog["module_state"] = "enabled"
        catalog["areas"][0].update(id="main-area", source_review=self.review(fixture))
        path = fixture.target / ".ai/project/architecture/catalog.json"
        path.write_text(json.dumps(catalog))
        checked = fixture.check(selected=False)
        checked.check_architecture_knowledge(None)
        self.assertNotIn("ARCHITECTURE_REVALIDATION_REQUIRED", {finding.code for finding in checked.findings})
        (fixture.target / "design.md").write_text("changed design")
        checked = fixture.check(selected=False)
        checked.check_architecture_knowledge(None)
        self.assertIn("ARCHITECTURE_REVALIDATION_REQUIRED", {finding.code for finding in checked.findings})
        outside = fixture.target.parent / (fixture.target.name + "-module-outside.txt")
        outside.write_text("external input")
        self.addCleanup(outside.unlink)
        try:
            (fixture.target / "escaped.txt").symlink_to(outside)
        except (OSError, NotImplementedError):
            return
        catalog["areas"][0]["source_review"]["inputs"] = [{"path": "escaped.txt", "sha256": hashlib.sha256(outside.read_bytes()).hexdigest()}]
        path.write_text(json.dumps(catalog))
        checked = fixture.check(selected=False)
        checked.check_architecture_knowledge(None)
        self.assertIn("ARCHITECTURE_REVALIDATION_REQUIRED", {finding.code for finding in checked.findings})

    def test_optional_deep_json_preserves_package_candidates(self):
        fixture = self.fixture()
        package_fixture.ProjectKnowledgeSuggestionTests().write_target(fixture.target, [{"package_id": "A", "status": "complete"}, {"package_id": "B", "status": "complete"}])
        index_path = fixture.target / task_fixture.INDEX_PATH
        original_index = index_path.read_bytes()
        deep = "[" * 10000 + "0" + "]" * 10000
        for path in [index_path, fixture.target / fixture.task["completion_evidence"]["path"]]:
            index_path.write_bytes(original_index)
            path.write_text(deep)
            result = suggestions(fixture.target)
            self.assertEqual(len(result["candidates"]), 1)
            self.assertIn(result["recent_task_discovery"]["coverage"], {"unavailable", "incomplete"})

    def test_alias_review_paths_do_not_hide_related_stale_architecture(self):
        fixture = self.fixture()
        review = self.review(fixture)
        review["inputs"][0].update(path="./design.md", sha256="0" * 64)
        review["changed_fact_ids"] = []
        path = fixture.target / ".ai/project/architecture/catalog.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"schema_version": 2, "areas": [{"id": "main-area", "source_review": review}], "patterns": []}))
        self.assertIn("TASK_ARCHITECTURE_REVIEW", fixture.errors(fixture.check()))

    def test_escaping_review_input_reports_unavailable_without_crashing(self):
        fixture = self.fixture()
        outside = fixture.target.parent / (fixture.target.name + "-outside.txt")
        outside.write_text("external evidence")
        self.addCleanup(outside.unlink)
        link = fixture.target / "escaped.txt"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("host cannot create test symlinks")
        self.assertIsNone(BoundedReviewDigests(TargetRepositoryView(fixture.target))("escaped.txt"))
        review = self.review(fixture)
        review["inputs"] = [{"path": "escaped.txt", "sha256": hashlib.sha256(outside.read_bytes()).hexdigest()}]
        path = fixture.target / ".ai/project/architecture/catalog.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"schema_version": 2, "areas": [{"id": "main-area", "source_review": review}], "patterns": []}))
        fixture.closure["architecture_review"].update(state="reviewed", item_ids=["main-area"])
        fixture.write_closure()
        self.assertIn("TASK_ARCHITECTURE_REVIEW", fixture.errors(fixture.check()))


if __name__ == "__main__":
    unittest.main()
