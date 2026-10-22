from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import context_catalog
import tests.test_context_planning as planning_fixture
import tests.test_consistency_map_validation as map_fixture
import tests.test_test_execution_contract as execution_fixture
from tests.test_behavior_acceptance import behavior_model
from analysis_strategy_contract import validate_problem_model
from behavior_acceptance import behavior_failures
from context_catalog import discover_context_catalog, validate_context_catalog
from context_planning import ContextPlanRequest, plan_target_context
from impact_graph import build_reverse_index, load_impact_graph, matching_node_ids
from registry_ownership import owner_paths, owner_binding_matches, owner_declarations, ownership_failures
from repair_classification import classify_repairs
from reviewed_warnings import selected_candidate_warnings
from target_adapter_validation.harness_scenarios.common import validator
from test_execution_contract import BINDING, SURFACES, TestExecutionContract


class RegistryCoverageTests(unittest.TestCase):
    def test_multiple_owners_through_registered_capability(self):
        helper = map_fixture.ConsistencyMapValidationTests()
        self.addCleanup(helper.doCleanups)
        target = helper.make_target()
        registry = target / ".ai/project/source-of-truth-registry.md"
        registry.write_text(registry.read_text() + "Canonical owner: [catalog](docs/catalog.json)\nDecision owner: Architecture team\n")
        (target / "docs/catalog.json").write_text("{}")
        shard_path = target / ".ai/project/consistency/areas/core.json"
        shard = json.loads(shard_path.read_text())
        node = shard["nodes"][0]
        binding = {**node["bindings"][0], "id": "owner", "path": "docs/business.md", "authority": "canonical"}
        node["bindings"].append(binding)
        map_fixture.write_json(shard_path, shard)
        check = validator(target); check.check_consistency_map()
        missing = [item for item in check.findings if item.code == "CONSISTENCY_REGISTRY_OWNER_BINDING"]
        self.assertEqual(len(missing), 1)
        self.assertIn("docs/catalog.json", missing[0].message)
        node["bindings"].append({**binding, "id": "catalog", "path": "docs/catalog.json"})
        map_fixture.write_json(shard_path, shard)
        check = validator(target); check.check_consistency_map()
        self.assertNotIn("CONSISTENCY_REGISTRY_OWNER_BINDING", [item.code for item in check.findings])

    def test_paths_do_not_split_names_or_guess_scope(self):
        self.assertEqual(owner_paths("`docs/a,b.md`; [decision](<docs/Architecture Decision.md#scope>)"), ("docs/a,b.md", "docs/Architecture Decision.md#scope"))
        for invalid in ("docs/a.md and docs/b.md", "`docs/a.md` narrative", "../a.md", "C:/a.md", "[bad](https://host/a.md)"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                owner_paths(invalid)
        binding = {"authority": "canonical", "path": "docs/**", "selector_kind": "glob", "selector": "all"}
        self.assertTrue(owner_binding_matches("docs/", binding))
        self.assertFalse(owner_binding_matches("docs/*.md", binding))
        self.assertFalse(owner_binding_matches("docs/a.md", binding))
        self.assertFalse(owner_binding_matches("docs/", {**binding, "authority": "derived"}))
        self.assertFalse(owner_binding_matches("docs/a.md#scope", {**binding, "path": "docs/a.md", "selector_kind": "file", "selector": "whole-file"}))
        self.assertTrue(owner_binding_matches("src/[id]/route.ts", {**binding, "path": "src/[id]/route.ts", "selector_kind": "file", "selector": "whole-file"}))
        self.assertTrue(owner_binding_matches("src/[ab].py", {**binding, "path": "src/[ab].py"}))
        self.assertTrue(owner_binding_matches("src/[id]/route.ts#scope", {**binding, "path": "src/[id]/route.ts", "selector_kind": "markdown-section", "selector": "scope"}))
        self.assertFalse(owner_binding_matches("src/[id]/route.ts#scope", {**binding, "path": "src/[id]/route.ts", "selector_kind": "glob", "selector": "whole-file"}))

    def test_missing_and_wrapped_declarations_cannot_hide_an_owner(self):
        node = {"bindings": [{"authority": "canonical", "path": "docs/a.md", "selector_kind": "file", "selector": "whole-file"}]}
        for block in ("", "Canonical owner: `docs/a.md`,\n  `docs/b.md`\n", "Canonical owner: `docs/a.md`\n  and `docs/b.md`\n"):
            self.assertTrue(ownership_failures(owner_declarations(block, 10), node))
        self.assertTrue(ownership_failures(owner_declarations("Canonical owner: `docs/a.md`\n", 10), {}))


class LazyPlanningTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.target = Path(directory.name)
        self.fixture = planning_fixture.TargetFixture(self.target); self.fixture.build()

    def request(self, **changes):
        return ContextPlanRequest(**{"target": self.target, "profile": "code-local", "operation": "product-change", "changed_paths": ("src/payment/retry.py",), **changes})

    def test_discovery_defers_leaf_io_without_relaxing_full_validation(self):
        root = self.fixture.project / "context-index.json"
        reads = []
        original = context_catalog.catalog_content_bytes
        def measure(path):
            reads.append(path)
            return original(path)
        with patch.object(context_catalog, "catalog_content_bytes", side_effect=measure):
            discovery = discover_context_catalog(root)
        self.assertFalse(reads)
        self.assertTrue(all(item.estimated_characters is None for item in discovery.items))
        with patch.object(context_catalog, "catalog_content_bytes", side_effect=measure):
            result = plan_target_context(self.request())
        self.assertEqual(result["status"], "ready", result)
        self.assertNotIn(self.fixture.project / "optional.md", reads)
        (self.fixture.project / "optional.md").write_text("stale unrelated leaf")
        self.assertEqual(plan_target_context(self.request())["status"], "ready")
        with self.assertRaises(context_catalog.ContextCatalogError):
            validate_context_catalog(root)

    def test_overflow_preserves_selected_items_and_stays_blocked(self):
        ready = plan_target_context(self.request())
        blocked = plan_target_context(self.request(max_words=1))
        self.assertEqual(blocked["status"], "blocked")
        self.assertIsNone(blocked["context_packet"])
        proposal = blocked["errors"][0]["details"]["decomposition"]
        self.assertFalse(proposal["execution_ready"])
        proposed = {item["id"] for group in proposal["groups"] for item in group}
        self.assertEqual(proposed, {item["id"] for item in ready["context_packet"]["selected_items"]})

    def test_added_canonical_binding_is_selected_without_context_id(self):
        graph = load_impact_graph(self.target)
        shard_path = self.target / graph.source_paths[-1]
        # Locate the actual shard, independent of source-path ordering.
        shard_path = next(self.target / path for path in graph.source_paths if "nodes" in json.loads((self.target / path).read_text()) and path != ".ai/project/consistency-map.json")
        shard = json.loads(shard_path.read_text())
        node = shard["nodes"][0]
        node["bindings"].append({**node["bindings"][0], "id": "second-owner", "path": "docs/second.md", "selector_kind": "file", "selector": "whole-file", "authority": "canonical", "context_ids": []})
        planning_fixture.write_text(self.target / "docs/second.md", "second accepted owner")
        planning_fixture.write_json(shard_path, shard)
        planning_fixture.write_json(self.fixture.assistant / "consistency-reverse-index.json", build_reverse_index(load_impact_graph(self.target)))
        self.fixture.refresh_catalogs()
        result = plan_target_context(self.request())
        self.assertEqual(result["status"], "ready", result)
        self.assertIn("docs/second.md", [item["path"] for item in result["context_packet"]["selected_items"]])
        node["canonical_owner"] = "docs/billing.md#accepted-rule"
        planning_fixture.write_json(shard_path, shard)
        planning_fixture.write_json(self.fixture.assistant / "consistency-reverse-index.json", build_reverse_index(load_impact_graph(self.target)))
        self.fixture.refresh_catalogs()
        section_plan = plan_target_context(self.request())
        self.assertEqual(section_plan["status"], "ready", section_plan)
        self.assertEqual(section_plan["impact"]["canonical_owners"][0]["selector"], "accepted-rule")


class AdditionalTestingSurfacesTests(unittest.TestCase):
    def test_policy_bounds_and_malformed_inputs(self):
        contract = TestExecutionContract()
        for invalid in (None, {}, True, 7, ["../outside.md"], ["C:/outside.md"], ["docs/*.md"], [SURFACES[0]], ["docs/a.md"] * 2, [f"docs/{i}.md" for i in range(17)]):
            policy = execution_fixture.policy(); policy["execution_contract"]["additional_evidence_templates"] = invalid
            with self.subTest(invalid=invalid):
                self.assertTrue(contract.policy_failures(policy))

    def test_registered_template_binding_and_manual_gate(self):
        helper = execution_fixture.RegisteredTestingExecutionTests()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory); policy, run = helper.fixture(target)
            policy["execution_contract"].update(additional_evidence_templates=["docs/test-evidence.md"], evidence_records=[])
            helper.write(target, ".ai/project/testing/test-first-policy.json", policy)
            helper.write(target, "docs/test-evidence.md", "RED then GREEN immediately")
            self.assertIn("TDD_SURFACE_POLICY_BINDING", [item.code for item in helper.findings(target)])
            text = "---\nalatyr_test_execution:\n" + "".join(f"  {key}: {value}\n" for key, value in BINDING.items()) + "---\n# Project evidence\n"
            helper.write(target, "docs/test-evidence.md", text)
            self.assertNotIn("TDD_SURFACE_POLICY_BINDING", [item.code for item in helper.findings(target)])
            self.assertEqual(policy["execution_contract"]["timing"], "after-manual-review")
            self.assertEqual(policy["execution_contract"]["red_requirement"], "when-authorized")

    def test_additional_template_byte_boundary_and_missing_file(self):
        helper = execution_fixture.RegisteredTestingExecutionTests()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory); policy, _ = helper.fixture(target)
            policy["execution_contract"].update(additional_evidence_templates=["docs/test-evidence.md"], evidence_records=[])
            helper.write(target, ".ai/project/testing/test-first-policy.json", policy)
            self.assertIn("TDD_SURFACE_POLICY_BINDING", [item.code for item in helper.findings(target)])
            content = (ROOT / "templates/target" / SURFACES[0]).read_bytes()
            path = target / "docs/test-evidence.md"; path.parent.mkdir(parents=True, exist_ok=True)
            for size, fails in ((128 * 1024 - 1, False), (128 * 1024, False), (128 * 1024 + 1, True)):
                path.write_bytes(content + b" " * (size - len(content)))
                errors = [item.code for item in helper.findings(target)]
                self.assertEqual("TDD_SURFACE_POLICY_BINDING" in errors, fails)

    def test_static_inventory_and_discovery_cannot_claim_execution(self):
        contract = TestExecutionContract()
        policy = execution_fixture.policy()
        policy["commands"][0]["execution"].update(kind="metadata-check", proof_boundary="static-metadata")
        run = execution_fixture.record()
        self.assertTrue(contract.evidence_failures(run, policy["commands"][0], policy["execution_contract"]))
        policy = execution_fixture.policy()
        run.update(state="discovered", counts={"discovered": 1, "executed": 0, "passed": 0, "failed": 0, "skipped": 0, "not_run": 1}, result_artifact=None)
        run["files"]["executed"] = []
        self.assertTrue(contract.evidence_failures(run, policy["commands"][0], policy["execution_contract"]))
        run["claim"] = "none"
        self.assertEqual(contract.evidence_failures(run, policy["commands"][0], policy["execution_contract"]), [])


class RestorationClassificationTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads((ROOT / "schemas/alatyr-problem-model.schema.json").read_text())

    def test_settled_correction_and_legacy_model(self):
        model = behavior_model()
        self.assertEqual(validate_problem_model(model, self.schema), [])
        self.assertEqual(behavior_failures(model, completion=True), [])
        model["behavior_review"]["deltas"][0].pop("repair")
        self.assertTrue(validate_problem_model(model, self.schema))
        model["schema_version"] = 5
        old = json.loads((ROOT / "schemas/alatyr-problem-model-v5.schema.json").read_text())
        self.assertEqual(validate_problem_model(model, old), [])

    def test_missing_bad_and_unresolved_classifications(self):
        for field in ("kind", "source_refs", "invariant_ids", "proof_obligation_ids", "reason"):
            for bad in (None, {}, [], True, 7, "unknown"):
                model = behavior_model(); model["behavior_review"]["deltas"][0]["repair"][field] = bad
                with self.subTest(field=field, bad=bad):
                    self.assertTrue(validate_problem_model(model, self.schema))
        for field, bad in (("invariant_ids", ["missing"]), ("proof_obligation_ids", ["missing"]), ("source_refs", ["unknown"])):
            model = behavior_model(); model["behavior_review"]["deltas"][0]["repair"][field] = bad
            self.assertTrue(validate_problem_model(model, self.schema))

    def test_completion_cannot_use_waived_open_or_failed_restoration_proof(self):
        for status in ("open", "failed", "blocked", "waived"):
            model = behavior_model(); model["proof_obligations"][0]["status"] = status
            self.assertTrue(behavior_failures(model, completion=True))
        model = behavior_model(); model["incident"].update(mode="systemic-repair", trigger="recurring-correction")
        self.assertTrue(behavior_failures(model))

    def test_shared_classification_rejects_malformed_collections_without_crashing(self):
        for field in ("invariants", "proof_obligations"):
            for bad in (None, True, 7, "invalid", {}, [None], [{}]):
                model = behavior_model(); model[field] = bad
                self.assertTrue(classify_repairs(model).failures)
                self.assertTrue(behavior_failures(model))


class ReviewedWarningTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.target = Path(directory.name)
        self.path = ".ai/project/consistency/relationship-candidates.json"
        finding = {"schema_version": 1, "record_kind": "target-reviewed-document-warning", "finding_id": "F-1", "document": "docs/backlog.md", "comparison_sources": ["docs/architecture.md"], "source_node": "fact.billing", "target_node": "fact.backlog", "reason": "Feature implemented; backlog stale"}
        contents = {"docs/backlog.md": "dated unfinished feature", "docs/review.json": json.dumps(finding), "docs/architecture.md": "accepted implementation state"}
        for path, text in contents.items():
            planning_fixture.write_text(self.target / path, text)
        self.review = {"state": "reviewed", "reason": "Backlog contradicts accepted architecture", "reviewer": "maintainer", "reviewed_at": "2026-10-21T09:00:00Z", "changed_fact_ids": ["fact.billing"],
                       "inputs": [{"path": path, "sha256": hashlib.sha256(text.encode()).hexdigest()} for path, text in contents.items()]}
        self.graph = SimpleNamespace(nodes={"fact.billing": {"canonical_owner": "docs/architecture.md"}, "fact.backlog": {"canonical_owner": "docs/backlog.md"}})
        self.candidate = {"id": "backlog-stale", "state": "proposed", "source_node": "fact.billing", "target_node": "fact.backlog", "relationship_type": "documents", "evidence": ["docs/review.json#F-1"], "observed_revision": "a" * 40, "decision_owner": "maintainer",
                          "reviewed_warning": {"kind": "stale-document", "document": "docs/backlog.md", "finding_ref": "docs/review.json#F-1", "comparison_sources": ["docs/architecture.md"], "source_review": self.review}}
        self.save()

    def save(self):
        planning_fixture.write_json(self.target / self.path, {"schema_version": 2, "record_kind": "target-consistency-relationship-candidates", "records": [self.candidate]})

    def warnings(self, selected=("fact.billing",)):
        return selected_candidate_warnings(self.target, self.path, selected, graph=self.graph)

    def test_selected_warning_is_bound_non_authoritative_and_stale_after_edit(self):
        value = self.warnings()
        self.assertEqual(value["diagnostics"], [])
        self.assertEqual(value["warnings"][0]["state"], "reviewed-warning")
        self.assertEqual(value["warnings"][0]["authority"], "none")
        self.assertEqual(self.warnings(("unrelated",))["warnings"], [])
        for path in ("docs/backlog.md", "docs/review.json", "docs/architecture.md"):
            original = (self.target / path).read_bytes()
            (self.target / path).write_bytes(b"changed")
            self.assertEqual(self.warnings()["warnings"][0]["state"], "revalidation-required")
            (self.target / path).write_bytes(original)

    def test_missing_malformed_and_unbound_review_never_becomes_authority(self):
        for bad in ({}, [], None, True, 7, "unknown"):
            self.candidate["reviewed_warning"]["source_review"] = bad; self.save()
            result = self.warnings()
            self.assertTrue(result["diagnostics"] or any(item["state"] == "revalidation-required" for item in result["warnings"]))
        self.candidate["reviewed_warning"]["source_review"] = self.review
        self.review["inputs"] = []; self.save()
        self.assertEqual(self.warnings()["warnings"][0]["state"], "revalidation-required")

    def test_candidate_semantics_unsafe_paths_and_retargeting_fail_closed(self):
        for field, value in (("target_node", "missing"), ("relationship_type", "bogus")):
            original = self.candidate[field]; self.candidate[field] = value; self.save()
            self.assertTrue(self.warnings()["diagnostics"])
            self.candidate[field] = original
        self.save()
        for value in ([], {}, True, 7, "../outside.json", "/absolute.json", "C:/absolute.json"):
            result = selected_candidate_warnings(self.target, value, ("fact.billing",), graph=self.graph)
            self.assertTrue(result["diagnostics"])
        for field, value in (("finding_ref", "docs/review.json#missing"), ("document", "docs/architecture.md"), ("comparison_sources", ["docs/backlog.md"])):
            warning = self.candidate["reviewed_warning"]; original = warning[field]
            warning[field] = value; self.save()
            self.assertEqual(self.warnings()["warnings"][0]["state"], "revalidation-required")
            warning[field] = original

    def test_planner_cli_delivers_warning_without_expanding_graph(self):
        fixture = planning_fixture.TargetFixture(self.target); fixture.build()
        graph = load_impact_graph(self.target)
        ids = sorted(graph.nodes)
        self.candidate.update(source_node=ids[0], target_node=ids[0])
        self.candidate["reviewed_warning"]["comparison_sources"] = ["docs/billing.md"]
        path = self.target / "docs/review.json"
        finding = json.loads(path.read_text()); finding.update(comparison_sources=["docs/billing.md"], source_node=ids[0], target_node=ids[0])
        planning_fixture.write_json(path, finding)
        self.review["inputs"] = [{"path": name, "sha256": hashlib.sha256((self.target / name).read_bytes()).hexdigest()} for name in ("docs/backlog.md", "docs/review.json", "docs/billing.md")]
        self.save()
        root_path = fixture.project / "consistency-map.json"
        root = json.loads(root_path.read_text()); root["relationship_candidates"] = self.path
        planning_fixture.write_json(root_path, root)
        planning_fixture.write_json(fixture.assistant / "consistency-reverse-index.json", build_reverse_index(load_impact_graph(self.target)))
        fixture.refresh_catalogs()
        command = [sys.executable, "-B", str(ROOT / "tools/plan_target_context.py"), "--target", str(self.target), "--profile", "code-local", "--operation", "product-change", "--changed-path", "src/payment/retry.py"]
        result = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["impact"]["selected_node_ids"], [ids[0]])
        self.assertEqual(plan["impact"]["reviewed_warnings"]["warnings"][0]["state"], "reviewed-warning")


if __name__ == "__main__":
    unittest.main()
