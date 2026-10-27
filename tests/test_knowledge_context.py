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
from check_project_knowledge import fixture as knowledge_fixture
from context_planning import ContextPlanRequest, plan_target_context
from tests.test_context_planning import TargetFixture, write_json


class KnowledgeContextTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.target = Path(temporary.name).resolve()
        TargetFixture(self.target).build()
        self.index, self.shard, _ = knowledge_fixture(self.target)
        self.shard["entries"][0]["freshness"]["triggers"] = self.shard["entries"][0]["freshness"]["triggers"][:1]
        unrelated = dict(self.index["shards"][0], shard_id="unrelated", path=".ai/project/knowledge/routes/unrelated.json", project_areas=["other"])
        self.index["shards"].append(unrelated)
        self.query = {"schema_version": 1, "stage": "initial", "shard_ids": ["hydration"],
                      "selectors": {"project_areas": ["hydration"]}, "limit": 1}
        self.save()

    def save(self):
        write_json(self.target / ".ai/project/knowledge/index.json", self.index)
        write_json(self.target / ".ai/project/knowledge/routes/hydration.json", self.shard)
        write_json(self.target / ".ai/.runtime/knowledge-query.json", self.query)

    def plan(self, **overrides):
        return plan_target_context(ContextPlanRequest(target=self.target, profile="code-local", operation="product-change",
            knowledge_request=".ai/.runtime/knowledge-query.json", **overrides))

    def test_explicit_query_delivers_owner_and_not_unrelated_shard(self):
        plan = self.plan()
        self.assertEqual(plan["status"], "ready", plan)
        self.assertEqual(plan["knowledge"]["searched_shard_ids"], ["hydration"])
        self.assertEqual(plan["knowledge"]["unsearched_shard_ids"], ["unrelated"])
        self.assertFalse(plan["knowledge"]["global_coverage"])
        self.assertEqual(plan["knowledge"]["actual_use"], "not-observed")
        selected = {row["path"] for row in plan["context_packet"]["selected_items"]}
        self.assertIn("docs/contracts/result-mapping.md", selected)
        self.assertFalse((self.target / ".ai/project/knowledge/routes/unrelated.json").exists())
        self.assertGreater(plan["delivery_budget"]["total_words"], plan["context_packet"]["budget"]["total_words"])
        again = self.plan()
        self.assertEqual(plan, again)

    def test_actual_cli_uses_same_query_and_blocks_contradictions(self):
        command = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "context-plan", "--target", str(self.target),
                   "--profile", "code-local", "--operation", "product-change", "--knowledge-request", ".ai/.runtime/knowledge-query.json"]
        completed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertEqual(json.loads(completed.stdout)["knowledge"]["searched_shard_ids"], ["hydration"])
        self.shard["entries"][0]["freshness"]["state"] = "contradicted"
        self.save()
        completed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("contradicted knowledge", completed.stdout)

    def test_refined_fact_selector_and_no_match_scope_are_distinct(self):
        self.query.update(stage="refined", selectors={"fact_ids": ["FACT-RESULT-KEY-TRANSFORM"]})
        self.save()
        self.assertEqual(len(self.plan()["knowledge"]["selection"]["constraints"]), 1)
        self.query["selectors"] = {"fact_ids": ["not-the-fact"]}
        self.save()
        plan = self.plan()
        self.assertEqual(plan["status"], "ready", plan)
        self.assertEqual(plan["knowledge"]["selection"]["constraints"], [])
        self.assertFalse(plan["knowledge"]["global_coverage"])

    def test_default_planning_does_not_read_knowledge(self):
        import context_planning
        original = context_planning.read_context_bytes
        paths = []
        def read(path, **kwargs):
            paths.append(str(path))
            return original(path, **kwargs)
        with patch.object(context_planning, "read_context_bytes", side_effect=read):
            plan = plan_target_context(ContextPlanRequest(self.target, "code-local", "product-change"))
        self.assertEqual(plan["status"], "ready", plan)
        self.assertNotIn("knowledge", plan)
        self.assertFalse(any("/knowledge/" in path or "knowledge-query" in path for path in paths), paths)

    def test_constraint_overflow_and_stale_owner_fail_closed(self):
        other = copy.deepcopy(self.shard["entries"][0])
        other["knowledge_id"] = "second-constraint"
        self.shard["entries"].append(other)
        self.save()
        self.assertIn("would omit relevant", json.dumps(self.plan()))
        self.shard["entries"].pop()
        self.save()
        (self.target / "docs/contracts/result-mapping.md").write_bytes(b"changed canonical source\n")
        self.assertIn("owner changed", json.dumps(self.plan()))

    def test_unverified_freshness_is_a_warning_and_declared_conflicts_block(self):
        entry = self.shard["entries"][0]
        entry["freshness"]["triggers"].append({"kind": "dependency-version", "subject": "example/package", "expected": "1", "evidence": "lockfile", "action": "revalidate"})
        self.save()
        plan = self.plan()
        self.assertEqual(plan["status"], "ready", plan)
        self.assertEqual(plan["knowledge"]["selection"]["constraints"], [])
        warning = plan["knowledge"]["selection"]["warnings"][0]
        self.assertEqual(warning["declared_freshness_state"], "current")
        self.assertEqual(warning["freshness_state"], "revalidation-required")
        self.assertEqual(warning["unverified_trigger_kinds"], ["dependency-version"])
        entry["relations"]["conflicts_with"] = ["another-guidance-item"]
        self.save()
        self.assertIn("unresolved conflict", json.dumps(self.plan()))

    def test_owner_trigger_must_match_and_shard_paths_cannot_traverse(self):
        self.shard["entries"][0]["freshness"]["triggers"][0]["expected"] = "0" * 64
        self.save()
        self.assertIn("trigger disagrees", json.dumps(self.plan()))
        self.index["shards"][0]["path"] = ".ai/project/knowledge/routes/../other.json"
        self.save()
        self.assertNotEqual(self.plan()["status"], "ready")

    def test_contradiction_beyond_limit_is_not_hidden(self):
        other = copy.deepcopy(self.shard["entries"][0])
        other["knowledge_id"] = "zz-conflicted"
        other["freshness"]["state"] = "contradicted"
        self.shard["entries"].append(other)
        self.save()
        self.assertIn("zz-conflicted", json.dumps(self.plan()))

    def test_knowledge_delivery_obeys_word_budget_boundary(self):
        ready = self.plan()
        words = ready["delivery_budget"]["total_words"]
        for limit in (words - 1, words, words + 1):
            result = self.plan(max_words=limit)
            with self.subTest(limit=limit):
                self.assertEqual(result["status"], "blocked" if limit < words else "ready", result)

    def test_working_set_reserves_knowledge_cost_before_optional_ranking(self):
        from tests.test_context_working_set import request_document
        base = self.plan()
        query = request_document(optional_context=[{"context_id": "project.optional", "topics": ["diagnosis"]}])
        write_json(self.target / ".ai/.runtime/working.json", query)
        roomy = self.plan(working_set_request=".ai/.runtime/working.json")
        self.assertEqual(roomy["status"], "ready", roomy)
        self.assertIn("project.optional", {row["id"] for row in roomy["context_packet"]["selected_items"]})
        for dimension, limit in (("max_words", base["delivery_budget"]["total_words"]), ("max_characters", base["delivery_budget"]["total_characters"])):
            plan = self.plan(working_set_request=".ai/.runtime/working.json", **{dimension: limit})
            with self.subTest(dimension=dimension):
                self.assertEqual(plan["status"], "ready", plan)
                self.assertNotIn("project.optional", {row["id"] for row in plan["context_packet"]["selected_items"]})
                self.assertIn("docs/contracts/result-mapping.md", {row["path"] for row in plan["context_packet"]["selected_items"]})
                self.assertTrue(plan["working_set"]["mandatory_retained"])

    def test_character_budget_and_concurrent_owner_mutation_fail_closed(self):
        ready = self.plan()
        characters = ready["delivery_budget"]["total_characters"]
        for limit in (characters - 1, characters, characters + 1):
            result = self.plan(max_characters=limit)
            with self.subTest(limit=limit):
                self.assertEqual(result["status"], "blocked" if limit < characters else "ready", result)
        import context_planning
        original = context_planning.read_context_bytes
        owner = self.target / "docs/contracts/result-mapping.md"
        mutated = False
        def read(path, **kwargs):
            nonlocal mutated
            raw = original(path, **kwargs)
            if path == owner and not mutated:
                mutated = True
                owner.write_bytes(raw + b"concurrent update\n")
            return raw
        with patch.object(context_planning, "read_context_bytes", side_effect=read):
            plan = self.plan()
        self.assertEqual(plan["status"], "blocked")
        self.assertEqual(plan["errors"][0]["code"], "CONTEXT_INPUT_CHANGED")

    def test_malformed_requests_return_diagnostics_not_exceptions(self):
        for field in ("stage", "shard_ids", "selectors", "limit"):
            for invalid in ({}, [], None, True, 3, "unknown"):
                if field == "limit" and type(invalid) is int:
                    invalid = 0
                query = copy.deepcopy(self.query)
                self.query[field] = invalid
                self.save()
                with self.subTest(field=field, invalid=invalid):
                    self.assertEqual(self.plan()["status"], "blocked")
                self.query = query
        self.save()


if __name__ == "__main__":
    unittest.main()
