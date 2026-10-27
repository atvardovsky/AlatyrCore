from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from context_catalog import CatalogItem, context_packet_usage, file_digest
from context_input_snapshot import ContextInputLimit, ContextInputSnapshot, read_context_bytes
from context_planning import ContextPlanRequest, plan_target_context
from context_plan_view import compact_plan_view
from context_working_set import MAX_SCOPE_CATALOG_ITEMS, WorkingSetError, canonical_digest, required_selection
from tests.test_context_planning import TargetFixture, catalog_entry, write_json, write_text


def request_document(**changes):
    return {"schema_version": 1, "request_kind": "alatyr-context-working-set-request",
            "phase": "discover", "information_need": "local-change",
            "required_context_ids": [], "optional_context": [], **changes}


class WorkingSetTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.fixture = TargetFixture(self.root)
        self.fixture.build()
        self.request = ContextPlanRequest(self.root, "code-local", "product-change")

    def plan(self, document=None, **kwargs):
        if document is None:
            return plan_target_context(dataclasses.replace(self.request, **kwargs))
        write_json(self.root / "request.json", document)
        return plan_target_context(dataclasses.replace(self.request, working_set_request="request.json", **kwargs))

    def ids(self, plan):
        return {row["id"] for row in plan["context_packet"]["selected_items"]}

    def optional(self, **changes):
        return request_document(optional_context=[{"context_id": "project.optional", "topics": ["diagnosis"], **changes}])

    def test_default_is_unchanged_and_does_not_activate_new_selection(self):
        baseline = self.plan()
        with patch("context_working_set.required_selection", side_effect=AssertionError("not optional")):
            self.assertEqual(self.plan(), baseline)
        self.assertNotIn("working_set", baseline)

    def test_default_does_not_import_working_set_or_json_schema(self):
        script = "import sys; from pathlib import Path; sys.path.insert(0,str(Path.cwd()/'tools')); from context_planning import ContextPlanRequest,plan_target_context; assert plan_target_context(ContextPlanRequest(Path(sys.argv[1]),'code-local','product-change'))['status']=='ready'; assert 'context_working_set' not in sys.modules"
        result = subprocess.run([sys.executable, "-B", "-c", script, str(self.root)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_phase_only_filters_optional_context(self):
        before = self.plan()
        document = self.optional(phases=["discover"])
        discovery = self.plan(document)
        self.assertEqual(discovery["status"], "ready", discovery)
        self.assertLessEqual(self.ids(before), self.ids(discovery))
        self.assertIn("project.optional", self.ids(discovery))
        document["phase"] = "implement"
        implementation = self.plan(document)
        self.assertEqual(self.ids(implementation), self.ids(before))
        self.assertEqual(implementation["working_set"]["optional_omissions"], [{"id": "project.optional", "reason": "phase-not-selected"}])
        self.assertFalse(implementation["working_set"]["authorization_granted"])

    def test_required_context_wins_over_an_optional_phase_filter(self):
        document = self.optional(phases=["validate"])
        document["required_context_ids"] = ["project.optional"]
        result = self.plan(document)
        self.assertIn("project.optional", self.ids(result))
        self.assertIn("project.optional", result["working_set"]["mandatory_item_ids"])

    def test_exhaustive_scope_enumerates_all_project_items(self):
        document = request_document(information_need="exhaustive-review", exhaustive_contours=["project"])
        result = self.plan(document)
        expected = {row["id"] for row in json.loads((self.fixture.project / "context-index.json").read_text())["entries"]}
        self.assertEqual(result["status"], "ready", result)
        self.assertLessEqual(expected, self.ids(result))
        self.assertLessEqual(expected, set(result["working_set"]["mandatory_item_ids"]))
        self.assertFalse(result["working_set"]["scope"]["semantic_review_performed"])
        self.assertEqual(result["working_set"]["scope"]["unindexed_source_coverage"], "not-established")

    def test_exhaustive_scope_cannot_be_truncated_to_fit(self):
        result = self.plan(request_document(information_need="exhaustive-review", exhaustive_contours=["project"]), max_words=1)
        self.assertEqual(result["status"], "blocked")
        self.assertIsNone(result["context_packet"])
        self.assertIn("decomposition", result["errors"][0]["details"])

    def test_exhaustive_scan_has_an_explicit_pre_enumeration_bound(self):
        items = dict.fromkeys((str(number) for number in range(MAX_SCOPE_CATALOG_ITEMS + 1)))
        with self.assertRaises(WorkingSetError) as failure:
            required_selection(request_document(information_need="exhaustive-review", exhaustive_contours=["project"]), items, {}, {})
        self.assertEqual(failure.exception.code, "CONTEXT_WORKING_SET_WORK_LIMIT")
        self.assertFalse(failure.exception.details["enumeration_complete"])

    def test_scope_work_bound_stops_instead_of_creating_a_partial_packet(self):
        item = CatalogItem("project.test", "content", ".ai/project/test.md", "test", {}, (), (), (), 1, 1, "sha256:" + "a" * 64)
        items = {f"project.{number}": dataclasses.replace(item, item_id=f"project.{number}") for number in range(514)}
        with self.assertRaises(WorkingSetError) as failure:
            required_selection(request_document(information_need="exhaustive-review", exhaustive_contours=["project"]), items, {}, {})
        self.assertFalse(failure.exception.details["enumeration_complete"])

    def test_optional_word_budget_below_at_above_boundary(self):
        baseline = self.plan()
        limit = baseline["context_packet"]["budget"]["total_words"] + 3
        for delta in (-1, 0, 1):
            with self.subTest(delta=delta):
                result = self.plan(self.optional(), max_words=limit + delta)
                self.assertEqual(result["status"], "ready", result)
                self.assertEqual("project.optional" in self.ids(result), delta >= 0)
                self.assertTrue(result["working_set"]["mandatory_retained"])

    def test_character_budget_counts_the_same_owner_and_semantic_costs(self):
        baseline = self.plan()
        router = json.loads((self.fixture.assistant / "context-router.json").read_text())
        limit = baseline["context_packet"]["budget"]["total_characters"] + len("optional project guidance\n")
        router["context_budgets"]["profile_default"]["max_total_characters"] = 100000
        write_json(self.fixture.assistant / "context-router.json", router)
        for delta in (-1, 0, 1):
            with self.subTest(delta=delta):
                result = self.plan(self.optional(), max_characters=limit + delta)
                self.assertEqual(result["status"], "ready", result)
                self.assertEqual("project.optional" in self.ids(result), delta >= 0)

    def test_unselected_phase_does_not_hydrate_a_stale_optional_leaf(self):
        write_text(self.fixture.project / "optional.md", "changed without refreshing its index")
        result = self.plan(self.optional(phases=["validate"]))
        self.assertEqual(result["status"], "ready", result)
        selected = self.plan(self.optional())
        self.assertEqual(selected["status"], "unavailable")
        self.assertEqual(selected["errors"][0]["code"], "CONTEXT_CATALOG_STALE")

    def test_duplicate_and_unknown_ids_are_not_silently_ignored(self):
        document = self.optional()
        document["optional_context"].append({"context_id": "project.optional", "topics": ["different"]})
        self.assertEqual(self.plan(document)["errors"][0]["code"], "CONTEXT_WORKING_SET_INVALID")
        self.assertEqual(self.plan(request_document(required_context_ids=["missing"]))["errors"][0]["code"], "CONTEXT_WORKING_SET_UNKNOWN_ID")

    def test_json_compatible_malformed_request_fields_never_crash(self):
        baseline = self.optional()
        mutations = [(field, value) for field in baseline for value in (None, {}, [], True, 3, "unknown")
                     if not (field in {"required_context_ids", "optional_context"} and value == [])]
        mutations += [("optional_context", [{"context_id": value, "topics": ["x"]}]) for value in (None, {}, [], True, 3)]
        mutations += [("optional_context", [{"context_id": "project.optional", "topics": [value]}]) for value in (None, {}, [], True, 3)]
        for field, value in mutations:
            document = copy.deepcopy(baseline); document[field] = value
            with self.subTest(field=field, value=value):
                result = self.plan(document)
                self.assertNotEqual(result["status"], "ready", result)
                self.assertIsNone(result["context_packet"])

    def test_optional_input_paths_are_type_checked(self):
        for field in ("working_set_request", "previous_plan", "delivery_observation"):
            for value in (True, {}, [], 3):
                with self.subTest(field=field, value=value):
                    self.assertEqual(self.plan(**{field: value})["status"], "invalid-request")

    def test_previous_report_round_trip_is_digest_and_target_bound(self):
        first = self.plan(self.optional(phases=["discover"]))
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "previous.json"; write_json(report, first)
            document = self.optional(phases=["discover"]); document["phase"] = "implement"
            result = self.plan(document, previous_plan=str(report))
            self.assertEqual(result["status"], "ready", result)
            self.assertEqual(result["working_set"]["delta"]["retired_ids"], ["project.optional"])
            self.assertFalse(result["working_set"]["delta"]["host_eviction_performed"])
            first["working_set"]["target_identity"] = "wrong"
            first["plan_digest"] = canonical_digest({key: value for key, value in first.items() if key != "plan_digest"})
            write_json(report, first)
            self.assertEqual(self.plan(document, previous_plan=str(report))["errors"][0]["code"], "CONTEXT_PREVIOUS_PLAN_INVALID")

    def test_previous_plan_tampering_or_malformed_identity_is_rejected(self):
        baseline = self.plan(request_document())
        for mutation in ("digest", "packet", "identity", "boolean-version"):
            previous = copy.deepcopy(baseline)
            if mutation == "digest": previous["plan_digest"] = "wrong"
            elif mutation == "packet": previous["context_packet"] = []
            elif mutation == "identity": previous["context_packet"]["selected_items"][0]["id"] = {}
            else: previous["schema_version"] = True
            if mutation != "digest": previous["plan_digest"] = canonical_digest({key: value for key, value in previous.items() if key != "plan_digest"})
            write_json(self.root / "previous.json", previous)
            with self.subTest(mutation=mutation):
                self.assertEqual(self.plan(request_document(), previous_plan="previous.json")["errors"][0]["code"], "CONTEXT_PREVIOUS_PLAN_INVALID")

    def test_previous_semantic_identity_changes_are_not_hidden_by_retained_files(self):
        previous = self.plan(request_document())
        term = previous["context_packet"]["semantic_term_identities"][0]
        term_id = term["id"]
        term["definition_digest"] = "sha256:" + "f" * 64
        previous["plan_digest"] = canonical_digest({key: value for key, value in previous.items() if key != "plan_digest"})
        write_json(self.root / "previous.json", previous)
        result = self.plan(request_document(), previous_plan="previous.json")
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(result["working_set"]["delta"]["changed_ids"], [])
        self.assertEqual(result["working_set"]["delta"]["semantic_changed_ids"], [term_id])

    def test_previous_item_count_is_bounded_before_identity_processing(self):
        previous = self.plan(request_document())
        previous["context_packet"]["selected_items"] *= 513
        previous["plan_digest"] = canonical_digest({key: value for key, value in previous.items() if key != "plan_digest"})
        write_json(self.root / "previous.json", previous)
        result = self.plan(request_document(), previous_plan="previous.json")
        self.assertEqual(result["errors"][0]["code"], "CONTEXT_PREVIOUS_PLAN_INVALID")

    def observation(self, plan):
        packet = plan["context_packet"]
        context = {"paths": [item["path"] for item in packet["selected_items"]], "approximate_words": packet["budget"]["total_words"]}
        return {"schema_version": 1, "observation_kind": "alatyr-context-delivery-observation", "packet_digest": packet["source_packet"]["content_bound_digest"],
                "context_receipt": {"schema_version": 1, "receipt_kind": "alatyr-context-receipt", "measurement_state": "observed", "planned": context,
                    "resolved": {"status": "recorded", **context},
                    "observed": {"evidence_level": "partial", "source": "manual", "files_loaded": "unknown", "input_tokens": 300, "output_tokens": 20, "evidence": "fixture observation, not verified provider telemetry"}}}

    def test_observation_separates_recorded_usage_from_unknown_total_cost(self):
        baseline = self.plan(request_document())
        write_json(self.root / "observation.json", self.observation(baseline))
        result = self.plan(request_document(), delivery_observation="observation.json")
        self.assertEqual(result["status"], "ready", result)
        accounting = result["working_set"]["accounting"]
        self.assertEqual(accounting["observed"]["input_tokens"], 300)
        self.assertEqual(accounting["total_task_and_worker_tokens"], "unknown")
        self.assertFalse(accounting["independently_verified"])
        self.assertEqual(self.plan(request_document())["working_set"]["accounting"]["input_tokens"], "unknown")

    def test_malformed_observation_types_and_wrong_binding_fail_closed(self):
        baseline = self.observation(self.plan(request_document()))
        mutations = [("packet_digest", "sha256:" + "f" * 64)]
        mutations += [(field, value) for field in ("evidence_level", "source", "input_tokens", "output_tokens") for value in ({}, [], None, True, -1, 1.5)]
        for field, value in mutations:
            item = copy.deepcopy(baseline)
            if field == "packet_digest": item[field] = value
            else: item["context_receipt"]["observed"][field] = value
            write_json(self.root / "observation.json", item)
            with self.subTest(field=field, value=value):
                result = self.plan(request_document(), delivery_observation="observation.json")
                self.assertEqual(result["status"], "blocked", result)
                self.assertIsNone(result["context_packet"])

    def test_observation_does_not_copy_large_evidence_and_accepts_different_path_order(self):
        baseline = self.observation(self.plan(request_document()))
        evidence = "untrusted observed text " * 10000
        baseline["context_receipt"]["observed"]["evidence"] = evidence
        baseline["context_receipt"]["resolved"]["paths"].reverse()
        write_json(self.root / "observation.json", baseline)
        result = self.plan(request_document(), delivery_observation="observation.json")
        self.assertEqual(result["status"], "ready", result)
        reference = result["working_set"]["accounting"]["evidence_reference"]
        self.assertEqual(reference["character_count"], len(evidence))
        self.assertEqual(reference["sha256"], "sha256:" + hashlib.sha256(evidence.encode()).hexdigest())
        self.assertNotIn(evidence, json.dumps(result))
        self.assertNotIn(evidence, json.dumps(compact_plan_view(result)))

    def test_compact_view_preserves_diagnostics_without_claiming_delivery(self):
        full = self.plan(self.optional())
        compact = compact_plan_view(full)
        self.assertEqual(compact["source_plan_digest"], full["plan_digest"])
        self.assertFalse(compact["executable_packet"])
        self.assertLess(len(json.dumps(compact)), len(json.dumps(full)))
        error = self.plan(self.optional(), max_words=1)
        compact = compact_plan_view(error)
        self.assertEqual(compact["errors"][0]["code"], error["errors"][0]["code"])
        self.assertEqual(compact["required_actions"], error["required_actions"])
        self.assertIsNone(compact["source_report"])

    def test_cli_compact_output_and_previous_plan_use_external_report(self):
        write_json(self.root / "request.json", self.optional())
        base = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "context-plan", "--target", str(self.root), "--profile", "code-local", "--operation", "product-change", "--working-set-request", "request.json"]
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "plan.json"
            first = subprocess.run([*base, "--compact", "--output", str(report)], capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            view = json.loads(first.stdout)
            self.assertEqual(view["source_report"]["sha256"], "sha256:" + hashlib.sha256(report.read_bytes()).hexdigest())
            second = subprocess.run([*base, "--compact", "--previous-plan", str(report)], capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(json.loads(second.stdout)["working_set"]["delta"]["changed_count"], 0)
        rejected = subprocess.run([*base, "--compact", "--output", str(self.root / "forbidden.json")], capture_output=True, text=True)
        self.assertEqual(rejected.returncode, 2)
        self.assertEqual(json.loads(rejected.stdout)["errors"][0]["code"], "OUTPUT_INSIDE_TARGET")
        self.assertFalse((self.root / "forbidden.json").exists())

    def test_cli_combines_phase_delta_receipt_and_compact_navigation(self):
        previous = self.plan(self.optional(phases=["discover"]))
        document = self.optional(phases=["discover"]); document["phase"] = "implement"
        current = self.plan(document)
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory)
            write_json(outside / "previous.json", previous)
            write_json(outside / "observation.json", self.observation(current))
            result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "context-plan",
                "--target", str(self.root), "--profile", "code-local", "--operation", "product-change",
                "--working-set-request", "request.json", "--previous-plan", str(outside / "previous.json"),
                "--delivery-observation", str(outside / "observation.json"), "--compact", "--output", str(outside / "full.json")],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            full = json.loads((outside / "full.json").read_text())
            compact = json.loads(result.stdout)
            self.assertEqual(full["working_set"]["delta"]["retired_ids"], ["project.optional"])
            self.assertEqual(compact["working_set"]["delta"]["retired_count"], 1)
            self.assertEqual(compact["working_set"]["accounting"]["measurement"], "recorded-observation")
            self.assertTrue(compact["working_set"]["mandatory_retained"])
            self.assertFalse(compact["executable_packet"])

    def test_cli_rejects_missing_values_and_lookalike_options(self):
        base = [sys.executable, "-B", str(ROOT / "tools/alatyr.py"), "context-plan", "--target", str(self.root), "--profile", "code-local", "--operation", "product-change"]
        for option in ("--working-set-request", "--previous-plan", "--delivery-observation", "--working-set-reques"):
            with self.subTest(option=option):
                result = subprocess.run([*base, option], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def add_item(self, contour, item_id, path, text, **attributes):
        write_text(contour / path, text)
        index = contour / "context-index.json"
        data = json.loads(index.read_text())
        data["entries"].append(catalog_entry(contour, item_id, path, **attributes))
        write_json(index, data)

    def test_optional_owner_closure_is_counted_and_never_partially_selected(self):
        baseline = self.plan()["context_packet"]["budget"]["total_words"]
        self.add_item(self.fixture.framework, "framework.extra-owner", "extra-owner.md", "owner " * 40, rule_ids=["ALATYR-EXTRA-001"])
        self.add_item(self.fixture.project, "project.extra", "extra.md", "extra guidance", owner_refs=["ALATYR-EXTRA-001"])
        document = request_document(optional_context=[{"context_id": "project.extra", "topics": ["extra"]}])
        for delta in (-1, 0, 1):
            with self.subTest(delta=delta):
                result = self.plan(document, max_words=baseline + 42 + delta)
                self.assertEqual(result["status"], "ready", result)
                self.assertEqual("project.extra" in self.ids(result), delta >= 0)
                self.assertEqual("framework.extra-owner" in self.ids(result), delta >= 0)

    def test_redundant_optional_candidates_do_not_resolve_unused_owners_or_terms(self):
        self.add_item(self.fixture.project, "project.bad-owner", "bad-owner.md", "unused", owner_refs=["ALATYR-MISSING-001"])
        self.add_item(self.fixture.project, "project.bad-semantic", "bad-semantic.md", "unused", semantic_refs=["alatyr:missing@1"])
        rows = [{"context_id": item_id, "topics": ["already-covered"]} for item_id in ("project.billing", "project.bad-owner", "project.bad-semantic")]
        for ordered in (rows, list(reversed(rows))):
            with self.subTest(order=ordered):
                result = self.plan(request_document(optional_context=ordered))
                self.assertEqual(result["status"], "ready", result)
                self.assertEqual({row["reason"] for row in result["working_set"]["optional_omissions"]}, {"no-new-declared-topic"})
                self.assertNotIn("project.bad-owner", self.ids(result))
                self.assertNotIn("project.bad-semantic", self.ids(result))

    def test_mandatory_synthetic_identity_cannot_be_replaced_by_a_catalog_collision(self):
        item = CatalogItem("collision", "content", "README.md", "required", {}, (), (), (), 1, 4, "sha256:" + "a" * 64)
        selected = {item.item_id: item}
        with self.assertRaises(WorkingSetError) as failure:
            required_selection(request_document(required_context_ids=[item.item_id]), {item.item_id: dataclasses.replace(item, path="other.md")}, selected, {})
        self.assertEqual(failure.exception.code, "CONTEXT_ID_COLLISION")
        self.assertEqual(selected, {item.item_id: item})

    def test_public_planner_blocks_catalog_collision_with_required_source(self):
        profile_path = self.fixture.assistant / "context/profiles/code-local.json"
        profile = json.loads(profile_path.read_text()); profile["required_context"].append("README.md")
        write_json(profile_path, profile)
        write_text(self.root / "README.md", "required root knowledge")
        self.fixture.refresh_catalogs()
        item_id = "target.required." + hashlib.sha256(b"README.md").hexdigest()
        self.add_item(self.fixture.project, item_id, "collision.md", "different catalog knowledge")
        for document in (request_document(), request_document(required_context_ids=[item_id])):
            with self.subTest(document=document):
                result = self.plan(document)
                self.assertEqual(result["status"], "blocked", result)
                self.assertEqual(result["errors"][0]["code"], "CONTEXT_ID_COLLISION")
                self.assertIsNone(result["context_packet"])

    def add_expensive_semantic_item(self):
        self.add_item(self.fixture.project, "project.expensive", "expensive.md", "short", semantic_refs=["alatyr:expensive@1"])
        data = json.loads((self.fixture.framework / "semantics/core.json").read_text())
        term = copy.deepcopy(data["terms"][0])
        term.update(id="alatyr:expensive@1", definition="definition " * 100)
        data["shard_id"] = "expensive"; data["preload"] = False; data["terms"] = [term]
        data["selectors"] = {}
        write_json(self.fixture.framework / "semantics/expensive.json", data)
        index_path = self.fixture.framework / "semantics/index.json"
        index = json.loads(index_path.read_text())
        index["shards"].append({"id": "expensive", "path": "expensive.json", "preload": False, "selectors": {}, "term_ids": [term["id"]], "content_digest": file_digest(self.fixture.framework / "semantics/expensive.json")})
        write_json(index_path, index)

    def test_optional_ranking_includes_new_semantic_definition_cost(self):
        self.add_expensive_semantic_item()
        document = request_document(optional_context=[{"context_id": "project.expensive", "topics": ["shared-topic"]}, {"context_id": "project.optional", "topics": ["shared-topic"]}])
        result = self.plan(document)
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(result["working_set"]["optional_selected_ids"], ["project.optional"])
        self.assertNotIn("project.expensive", self.ids(result))

    def test_optional_semantic_words_and_characters_share_packet_boundaries(self):
        self.add_expensive_semantic_item()
        document = request_document(optional_context=[{"context_id": "project.expensive", "topics": ["semantic"]}])
        baseline = self.plan()["context_packet"]["budget"]
        unbounded = self.plan(document)["context_packet"]["budget"]
        self.assertGreater(unbounded["total_words"], baseline["total_words"] + 1)
        router_path = self.fixture.assistant / "context-router.json"
        router = json.loads(router_path.read_text())
        router["context_budgets"]["profile_default"]["max_total_characters"] = 100000
        write_json(router_path, router)
        for dimension, option in (("total_words", "max_words"), ("total_characters", "max_characters")):
            for delta in (-1, 0, 1):
                with self.subTest(dimension=dimension, delta=delta):
                    result = self.plan(document, **{option: unbounded[dimension] + delta})
                    self.assertEqual(result["status"], "ready", result)
                    self.assertEqual("project.expensive" in self.ids(result), delta >= 0)

    def test_catalog_routing_inputs_cannot_change_during_optional_selection(self):
        from context_working_set import select_optional

        def mutate(*args, **kwargs):
            result = select_optional(*args, **kwargs)
            path = self.fixture.assistant / "context-router.json"
            path.write_bytes(path.read_bytes() + b" ")
            return result
        with patch("context_working_set.select_optional", side_effect=mutate):
            result = self.plan(self.optional())
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(result["errors"][0]["code"], "CONTEXT_INPUT_CHANGED")

    def test_compact_view_reports_omitted_mandatory_references(self):
        plan = self.plan(request_document())
        packet = plan["context_packet"]
        for number in range(25):
            packet["selected_items"].append({"id": f"test.{number}", "path": f"test/{number}.md", "content_digest": "sha256:" + "a" * 64})
            plan["working_set"]["mandatory_item_ids"].append(f"test.{number}")
        view = compact_plan_view(plan)
        self.assertEqual(len(view["selected_items"]), 16)
        self.assertGreater(view["omitted_mandatory_count"], 0)
        self.assertFalse(view["executable_packet"])

    def test_receipt_paths_and_sizes_must_match_current_packet(self):
        baseline = self.observation(self.plan(request_document()))
        for stage, field, value in (("planned", "paths", []), ("resolved", "approximate_words", 1), ("resolved", "paths", [])):
            item = copy.deepcopy(baseline); item["context_receipt"][stage][field] = value
            write_json(self.root / "observation.json", item)
            with self.subTest(stage=stage, field=field):
                self.assertEqual(self.plan(request_document(), delivery_observation="observation.json")["errors"][0]["code"], "CONTEXT_DELIVERY_OBSERVATION_INVALID")

    def test_missing_inputs_and_absent_working_set_are_diagnostics(self):
        self.assertEqual(self.plan(previous_plan="missing.json")["status"], "invalid-request")
        self.assertNotEqual(self.plan(request_document(), previous_plan="missing.json")["status"], "ready")

    def test_large_or_deep_input_produces_structured_local_diagnostics(self):
        for content in (" " * (4 * 1024 * 1024 + 1), "[" * 2000 + "]" * 2000):
            with self.subTest(size=len(content)):
                write_text(self.root / "request.json", content)
                result = plan_target_context(dataclasses.replace(self.request, working_set_request="request.json"))
                self.assertEqual(result["status"], "blocked", result)
                self.assertFalse(result["upgrade_required"])
                self.assertIsNone(result["context_packet"])
                write_text(self.root / "previous.json", content)
                self.assertEqual(self.plan(request_document(), previous_plan="previous.json")["errors"][0]["code"], "CONTEXT_PLAN_EVIDENCE_INVALID")

    def test_windows_style_request_path_is_normalized_before_digest_binding(self):
        write_json(self.root / "sub/request.json", request_document())
        result = plan_target_context(dataclasses.replace(self.request, working_set_request="sub\\request.json"))
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(result["routing_sources"]["working_set_request"]["path"], "sub/request.json")

    def test_optional_candidates_reuse_owner_index_once(self):
        import context_planning

        with patch("context_planning._owner_index", wraps=context_planning._owner_index) as build:
            result = self.plan(self.optional())
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(build.call_count, 1)

    def test_package_import_uses_the_same_bounded_snapshot(self):
        script = "from pathlib import Path; import tempfile; from tools.context_input_snapshot import ContextInputSnapshot; from tools.context_working_set import read_evidence; d=tempfile.TemporaryDirectory(); root=Path(d.name).resolve(); p=root/'e.json'; p.write_bytes(b'{}'); s=ContextInputSnapshot(root); s.__enter__(); assert read_evidence('e.json',root)=={}; s.__exit__(None,None,None); d.cleanup()"
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_relative_evidence_cannot_escape_through_a_parent_symlink(self):
        from context_working_set import read_evidence

        with tempfile.TemporaryDirectory() as directory:
            external = Path(directory).resolve()
            write_json(external / "record.json", {})
            try:
                (self.root / "linked").symlink_to(external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlinks unavailable")
            with self.assertRaises(WorkingSetError):
                read_evidence("linked/record.json", self.root)
            self.assertEqual(read_evidence(str(external / "record.json"), self.root), {})


class BoundedContextInputTests(unittest.TestCase):
    def test_below_at_above_bound_and_cached_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); path = root / "input.json"
            for size in (2, 3, 4):
                path.write_bytes(b"x" * size)
                with self.subTest(size=size):
                    if size > 3:
                        with self.assertRaises(ContextInputLimit): read_context_bytes(path, max_bytes=3)
                    else:
                        with ContextInputSnapshot(root):
                            self.assertEqual(read_context_bytes(path, max_bytes=3), b"x" * size)
                            self.assertEqual(read_context_bytes(path, max_bytes=3), b"x" * size)
            path.write_bytes(b"xxxx")
            with self.assertRaises(ContextInputLimit), ContextInputSnapshot(root):
                read_context_bytes(path)
                read_context_bytes(path, max_bytes=3)

    def test_input_growth_is_bounded_during_final_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); path = root / "input.json"; path.write_bytes(b"xxx")
            with self.assertRaises(ContextInputLimit), ContextInputSnapshot(root):
                read_context_bytes(path, max_bytes=3)
                path.write_bytes(b"x" * 100000)


if __name__ == "__main__":
    unittest.main()
