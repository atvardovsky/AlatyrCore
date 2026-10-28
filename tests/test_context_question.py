from __future__ import annotations

import copy
import dataclasses
import json
import subprocess
import sys
from unittest.mock import patch

from tests.active_task_fixture import ActiveTaskFixture, ROOT
from tests.test_analysis_evidence import add_evidence
from tests.test_context_planning import TargetFixture, write_json
from tests.test_context_working_set import request_document
from context_planning import ContextPlanRequest, plan_target_context
from context_plan_view import compact_plan_view
from context_input_snapshot import ContextInputSnapshot


class ContextQuestionTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        self.fixture = TargetFixture(self.target)
        self.fixture.build()
        add_evidence(self.model, self.target)
        proof = copy.deepcopy(self.model["proof_obligations"][0])
        proof.update(id="next-proof", status="open", evidence_refs=[])
        self.model["proof_obligations"].append(proof)
        probe = copy.deepcopy(self.model["analysis_evidence"]["probes"][0])
        probe.update(obligation_id="next-proof", result=None)
        self.model["analysis_evidence"]["probes"].append(probe)
        self.write_model(); self.write_index()
        self.request = ContextPlanRequest(self.target, "code-local", "product-change", working_set_request="request.json")
        self.document = request_document(question_binding={"task_id": "fixture-task", "model_sha256": self.task["problem_model"]["sha256"], "obligation_id": "next-proof"})

    def plan(self, **kwargs):
        write_json(self.target / "request.json", self.document)
        return plan_target_context(dataclasses.replace(self.request, **kwargs))

    def test_registered_question_retains_inputs_owners_and_bounded_question_not_model(self):
        result = self.plan()
        self.assertEqual(result["status"], "ready", result)
        question = result["question"]
        self.assertEqual(question["model"], self.task["problem_model"])
        self.assertEqual(question["obligation_id"], "next-proof")
        self.assertIn("design.md", [row["path"] for row in result["context_packet"]["selected_items"]])
        self.assertIn("target.required.", " ".join(result["working_set"]["mandatory_item_ids"]))
        self.assertNotIn("facts", question)
        self.assertFalse(question["authorization_granted"])
        self.assertEqual(question["actual_use"], "not-observed")
        self.assertEqual(compact_plan_view(result)["question"]["probe_sha256"], question["probe_sha256"])

    def test_default_neither_imports_question_resolver_nor_reads_active_tasks(self):
        request = dataclasses.replace(self.request, working_set_request=None)
        with patch("context_question.resolve_context_question", side_effect=AssertionError("unused")):
            self.assertEqual(plan_target_context(request)["status"], "ready")
        script = "import sys; from pathlib import Path; sys.path.insert(0,str(Path.cwd()/'tools')); from context_planning import ContextPlanRequest,plan_target_context; assert plan_target_context(ContextPlanRequest(Path(sys.argv[1]),'code-local','product-change'))['status']=='ready'; assert 'context_question' not in sys.modules"
        result = subprocess.run([sys.executable, "-B", "-c", script, str(self.target)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_question_metadata_is_charged_at_word_and_character_boundaries(self):
        full = self.plan()
        self.assertEqual(full["status"], "ready", full)
        router_path = self.fixture.assistant / "context-router.json"
        router = json.loads(router_path.read_text())
        router["context_budgets"]["profile_default"]["max_total_characters"] = 100000
        write_json(router_path, router)
        for field, option in (("total_words", "max_words"), ("total_characters", "max_characters")):
            limit = full["delivery_budget"][field]
            for delta in (-1, 0, 1):
                with self.subTest(field=field, delta=delta):
                    result = self.plan(**{option: limit + delta})
                    self.assertEqual(result["status"] == "ready", delta >= 0, result)
                    if delta < 0:
                        self.assertIsNone(result["context_packet"])

    def test_stale_missing_closed_settled_and_unknown_bindings_fail_closed(self):
        for mutation in ("stale-request", "stale-header", "closed", "settled", "missing-task", "missing-proof", "missing-model"):
            document, task, model = copy.deepcopy(self.document), copy.deepcopy(self.task), copy.deepcopy(self.model)
            model_bytes = self.model_path.read_bytes()
            if mutation == "stale-request": self.document["question_binding"]["model_sha256"] = "a" * 64
            elif mutation == "stale-header": self.task["problem_model"]["sha256"] = "a" * 64
            elif mutation == "closed":
                self.task["state"] = "closed"
                self.task["completion_evidence"] = self.bind(self.target / "design.md")
            elif mutation == "settled": self.document["question_binding"]["obligation_id"] = "proof-1"
            elif mutation == "missing-task": self.document["question_binding"]["task_id"] = "missing"
            elif mutation == "missing-proof": self.document["question_binding"]["obligation_id"] = "missing"
            else: self.model_path.unlink()
            self.write_index()
            with self.subTest(mutation=mutation):
                result = self.plan()
                self.assertEqual(result["status"], "blocked", result)
                self.assertIsNone(result["context_packet"])
            self.model, self.task, self.document = model, task, document
            self.model_path.write_bytes(model_bytes)
            self.write_index()

    def test_malformed_binding_and_selected_model_never_raise(self):
        good = copy.deepcopy(self.document)
        for value in (None, [], True, 3, "unknown", {}, {"task_id": {}}):
            self.document["question_binding"] = value
            with self.subTest(value=value):
                self.assertEqual(self.plan()["status"], "blocked")
        self.document = good
        for value in (None, [], True, 3, {"schema_version": 7}):
            write_json(self.model_path, value)
            self.task["problem_model"] = self.bind(self.model_path)
            self.document["question_binding"]["model_sha256"] = self.task["problem_model"]["sha256"]
            self.write_index()
            with self.subTest(model=value):
                self.assertEqual(self.plan()["status"], "blocked")

    def test_stale_probe_artifact_and_concurrent_model_change_block_delivery(self):
        path = self.target / "design.md"
        raw = path.read_bytes()
        path.write_bytes(raw + b"changed rule")
        self.assertEqual(self.plan()["errors"][0]["code"], "CONTEXT_QUESTION_INVALID")
        path.write_bytes(raw)
        original = ContextInputSnapshot.verify
        def mutate(snapshot):
            self.model_path.write_bytes(self.model_path.read_bytes() + b" ")
            return original(snapshot)
        with patch.object(ContextInputSnapshot, "verify", mutate):
            result = self.plan()
        self.assertNotEqual(result["status"], "ready")
        self.assertIsNone(result["context_packet"])

    def test_explicit_question_preserves_blocked_waiting_and_unknown_dispositions(self):
        for state in ("blocked", "waiting", "dependency-unconfigured"):
            self.model["proof_obligations"][-1]["status"] = "blocked" if state == "blocked" else "open"
            if state == "dependency-unconfigured":
                self.model.pop("execution_dependencies", None)
            else:
                self.model["execution_dependencies"] = [{"obligation_id": row["id"], "requires": []} for row in self.model["proof_obligations"]]
                if state == "waiting":
                    self.model["proof_obligations"].append({**self.model["proof_obligations"][-1], "id": "prerequisite", "status": "blocked"})
                    self.model["execution_dependencies"][-1]["requires"] = ["prerequisite"]
                    self.model["execution_dependencies"].append({"obligation_id": "prerequisite", "requires": []})
            self.write_model(); self.write_index()
            self.document["question_binding"]["model_sha256"] = self.task["problem_model"]["sha256"]
            with self.subTest(state=state):
                result = self.plan()
                self.assertEqual(result["status"], "ready", result)
                self.assertEqual(result["question"]["obligation_id"], "next-proof")
                self.assertEqual(result["question"]["eligibility"], state)
                self.assertTrue(result["question"]["selection_review_required"])
            if state == "waiting": self.model["proof_obligations"].pop()

    def test_phase_excluded_owner_remains_mandatory_and_unrelated_leaf_is_not_read(self):
        self.task["canonical_owners"] = ["design.md", ".ai/project/optional.md"]
        self.write_index()
        self.document["optional_context"] = [{"context_id": "project.optional", "topics": ["owner"], "phases": ["validate"]}]
        result = self.plan()
        self.assertEqual(result["status"], "ready", result)
        self.assertIn("project.optional", result["working_set"]["mandatory_item_ids"])
        self.assertTrue(result["working_set"]["mandatory_retained"])

    def test_blocked_question_retains_its_unsettled_prerequisite(self):
        self.model["proof_obligations"][-1]["status"] = "blocked"
        self.model["proof_obligations"].append({**self.model["proof_obligations"][-1], "id": "prerequisite"})
        self.model["execution_dependencies"] = [{"obligation_id": row["id"], "requires": ["prerequisite"] if row["id"] == "next-proof" else []} for row in self.model["proof_obligations"]]
        self.write_model(); self.write_index()
        self.document["question_binding"]["model_sha256"] = self.task["problem_model"]["sha256"]
        result = self.plan()
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(result["question"]["eligibility"], "blocked")
        self.assertEqual(result["question"]["unsettled_prerequisites"], ["prerequisite"])

    def test_question_and_knowledge_share_one_budget_including_optional_owner_cost(self):
        from check_project_knowledge import fixture
        index, shard, _ = fixture(self.target)
        shard["entries"][0]["freshness"]["triggers"] = shard["entries"][0]["freshness"]["triggers"][:1]
        write_json(self.target / ".ai/project/knowledge/index.json", index)
        write_json(self.target / ".ai/project/knowledge/routes/hydration.json", shard)
        write_json(self.target / "knowledge-query.json", {"schema_version": 1, "stage": "initial", "shard_ids": ["hydration"], "selectors": {"project_areas": ["hydration"]}, "limit": 1})
        result = self.plan(knowledge_request="knowledge-query.json")
        self.assertEqual(result["status"], "ready", result)
        budget = result["delivery_budget"]
        rendered_question = json.dumps(result["question"], indent=2, sort_keys=True, ensure_ascii=True)
        rendered_knowledge = json.dumps(result["knowledge"], indent=2, sort_keys=True, ensure_ascii=True)
        self.assertEqual(budget["question_words"], len(rendered_question.split()))
        self.assertEqual(budget["knowledge_words"], len(rendered_knowledge.split()))
        self.assertEqual(budget["question_characters"], len(rendered_question))
        self.assertEqual(budget["knowledge_characters"], len(rendered_knowledge))
        self.assertEqual(budget["total_words"], result["context_packet"]["budget"]["total_words"] + len(rendered_question.split()) + len(rendered_knowledge.split()))
        self.assertEqual(budget["total_characters"], result["context_packet"]["budget"]["total_characters"] + len(rendered_question) + len(rendered_knowledge))
        self.document["optional_context"] = [{"context_id": "project.optional", "topics": ["diagnosis"]}]
        for option, field in (("max_words", "total_words"), ("max_characters", "total_characters")):
            for delta in (-1, 0, 1):
                with self.subTest(option=option, delta=delta):
                    checked = self.plan(knowledge_request="knowledge-query.json", **{option: budget[field] + delta})
                    self.assertEqual(checked["status"] == "ready", delta >= 0, checked)
                    if delta == 0:
                        self.assertNotIn("project.optional", {row["id"] for row in checked["context_packet"]["selected_items"]})

    def test_unsafe_and_missing_paths_and_duplicate_headers_return_diagnostics(self):
        original = copy.deepcopy(self.task)
        for path in ("../outside.json", "/outside.json", ".ai/.runtime/missing.json"):
            self.task["problem_model"]["path"] = path
            self.write_index()
            with self.subTest(path=path): self.assertEqual(self.plan()["status"], "blocked")
        self.task = original
        self.write_index([self.task, copy.deepcopy(self.task)])
        self.assertEqual(self.plan()["status"], "blocked")

    def test_question_view_overflow_does_not_return_partial_context(self):
        result = self.plan()
        self.assertEqual(result["status"], "ready", result)
        characters = len(json.dumps(result["question"], indent=2, sort_keys=True, ensure_ascii=True))
        for delta in (-1, 0, 1):
            with self.subTest(delta=delta), patch("context_question.MAX_QUESTION_CHARACTERS", characters + delta):
                checked = self.plan()
                self.assertEqual(checked["status"] == "ready", delta >= 0, checked)
        words = len(json.dumps(result["question"], indent=2, sort_keys=True, ensure_ascii=True).split())
        for delta in (-1, 0, 1):
            with self.subTest(words_delta=delta), patch("context_question.MAX_QUESTION_WORDS", words + delta):
                checked = self.plan()
                self.assertEqual(checked["status"] == "ready", delta >= 0, checked)

    def test_deep_json_and_symlinked_model_produce_diagnostics(self):
        import tempfile
        raw = self.model_path.read_bytes()
        self.model_path.write_text('[' * 2000 + '0' + ']' * 2000, encoding="utf-8")
        self.task["problem_model"] = self.bind(self.model_path)
        self.document["question_binding"]["model_sha256"] = self.task["problem_model"]["sha256"]
        self.write_index()
        self.assertEqual(self.plan()["status"], "blocked")
        self.model_path.write_bytes(raw)
        self.task["problem_model"] = self.bind(self.model_path)
        self.document["question_binding"]["model_sha256"] = self.task["problem_model"]["sha256"]
        self.write_index()
        with tempfile.TemporaryDirectory() as directory:
            outside = self.target.__class__(directory) / "model.json"
            outside.write_bytes(raw)
            self.model_path.unlink()
            try:
                self.model_path.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.model_path.write_bytes(raw)
                return
            self.assertEqual(self.plan()["status"], "blocked")

    def test_public_cli_emits_question_and_rejects_a_stale_request(self):
        self.plan()
        command = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "context-plan", "--target", str(self.target), "--profile", "code-local", "--operation", "product-change", "--working-set-request", "request.json"]
        valid = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(json.loads(valid.stdout)["question"]["obligation_id"], "next-proof")
        self.document["question_binding"]["model_sha256"] = "a" * 64
        write_json(self.target / "request.json", self.document)
        invalid = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertEqual(json.loads(invalid.stdout)["errors"][0]["code"], "CONTEXT_QUESTION_INVALID")
