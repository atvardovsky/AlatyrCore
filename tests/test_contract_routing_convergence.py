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

import context_planning
from context_planning import ContextPlanRequest, plan_target_context
from current_task_view import incident_frontier
from context_input_snapshot import ContextInputChanged, ContextInputSnapshot, read_context_bytes
from impact_graph import ImpactGraphError, ImpactLookup, assert_graph_current, build_reverse_index, load_impact_graph, relationship_review_paths, traverse_impact, validate_graph
from target_adapter_validation.harness_scenarios.common import parse_manifest, validator
from tests.test_context_planning import TargetFixture, catalog_entry, write_json
from tests import test_impact_graph as graph_fixture


class BaselineSectionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.target = Path(directory.name)
        self.claim = self.target / "docs/ALATYR_CORE.md"
        self.claim.parent.mkdir()
        self.manifest = self.target / ".ai/alatyr.yaml"
        self.manifest.parent.mkdir()
        self.manifest.write_text("schema_version: '88'\nframework:\n  version: 0.1.0-alpha.107\n  template_version: '102'\n  source_commit: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n")

    def findings(self, text):
        self.claim.write_text(text)
        checked = validator(self.target)
        manifest = parse_manifest(self.manifest)
        phase = next(item for item in checked.validation_phases(manifest, "core", set()) if item.phase_id == "baseline-claims")
        phase.run()
        return [item for item in checked.findings if item.level == "error"]

    def test_original_wrapped_prose_reports_all_four_stale_claims(self):
        findings = self.findings("## Current Baseline\nThe update installs `0.1.0-alpha.94`, adapter76/template89, pinned to\n`bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb`.\n")
        self.assertEqual(len(findings), 4, findings)
        self.assertEqual({item.code for item in findings}, {"BASELINE_CLAIM_DRIFT"})
        self.assertTrue(all(item.path == "docs/ALATYR_CORE.md:2" for item in findings))

    def test_matching_wrapped_fields_and_source_abbreviation(self):
        self.assertEqual(self.findings("Current Alatyr Baseline\n----------------------\nFramework version:\n  `0.1.0-alpha.107`\n\nAdapter schema version: `88`.\nTemplate version: `102`.\nSource revision: `aaaaaaa`.\n"), [])

    def test_history_examples_and_both_fence_kinds_remain_non_authoritative(self):
        for fence in ("```", "~~~~"):
            text = f"## History\n### Current Baseline\nFramework version: 0.1.0-alpha.1\n## Examples\nFramework version: 0.1.0-alpha.2\n## Current Baseline\n{fence}\nFramework version: 0.1.0-alpha.3\n{fence}\nFramework version: 0.1.0-alpha.107\n"
            with self.subTest(fence=fence):
                self.assertEqual(self.findings(text), [])

    def test_stale_current_claim_not_hidden_by_previous_clause(self):
        findings = self.findings("Framework version: `0.1.0-alpha.94`; previous `0.1.0-alpha.1`.\n")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "BASELINE_CLAIM_DRIFT")

    def test_unrelated_versions_and_baseline_explanations_are_not_claims(self):
        self.assertEqual(self.findings("## Current Baseline\nRequires Python 3.13.16.\nThe template supports target-owned facts.\nAdapter facts remain target-owned.\n\nFramework version: 0.1.0-alpha.107; Python 3.13.16.\n"), [])

    def test_missing_typed_value_cannot_borrow_the_next_field(self):
        findings = self.findings("Framework version:\nAdapter schema version: 88\n")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "BASELINE_CLAIM_INVALID")

    def test_fractional_and_unknown_values_do_not_pass_as_matching_integers(self):
        for value in ("88.5", "unknown", "-88", "88suffix"):
            with self.subTest(value=value):
                self.assertEqual(self.findings(f"Adapter schema version: `{value}`\n")[0].code, "BASELINE_CLAIM_INVALID")

    def test_bold_labels_and_unresolved_framework_claims(self):
        self.assertEqual(self.findings("**Framework version:** `0.1.0-alpha.107`\n"), [])
        self.assertEqual(self.findings("Framework version: unknown\n")[0].code, "BASELINE_CLAIM_INVALID")
        self.assertEqual(self.findings("## Current AlatyrCore Baseline\nAlatyr Core: 0.1.0-alpha.94\n")[0].code, "BASELINE_CLAIM_DRIFT")

    def test_missing_expectation_does_not_suppress_other_drift(self):
        self.manifest.write_text(self.manifest.read_text().replace("  template_version: '102'\n", ""))
        findings = self.findings("Framework version: 0.1.0-alpha.94\nTemplate version: 102\n")
        self.assertEqual({item.code for item in findings}, {"BASELINE_CLAIM_DRIFT", "BASELINE_CLAIM_INVALID"})

    def test_public_cli_reports_current_section_drift(self):
        self.claim.write_text("## Current Baseline\nThe update installs 0.1.0-alpha.94.\n")
        result = subprocess.run([sys.executable, str(ROOT / "tools/validate_target_adapter.py"), "--target", str(self.target), "--validation-phase", "migration-staging"], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BASELINE_CLAIM_DRIFT", result.stdout + result.stderr)


class TypedRoutingTests(unittest.TestCase):
    def setUp(self):
        helper = graph_fixture.ImpactGraphTests()
        self.addCleanup(helper.doCleanups)
        _, self.target = helper.make_graph()
        self.root_path = self.target / ".ai/project/consistency-map.json"
        self.shard_path = self.target / ".ai/project/consistency/areas/billing.json"

    def graph(self, *, typed=False, condition=None):
        root = json.loads(self.root_path.read_text())
        if typed:
            root["impact_policy"]["routing_semantics"] = 1
        write_json(self.root_path, root)
        if condition is not None:
            shard = json.loads(self.shard_path.read_text())
            shard["nodes"][0]["relationships"][0]["applicability"] = condition
            write_json(self.shard_path, shard)
        return load_impact_graph(self.target)

    def test_changed_document_owner_and_changed_surface_find_fact(self):
        lookup = ImpactLookup(self.graph())
        self.assertEqual(lookup.matching("docs/billing.md"), {"fact.payment-retry"})
        result = lookup.resolve(["tests/payment/test_retry.py"])
        self.assertEqual(result["owner_lookup_node_ids"], ["fact.payment-retry"])
        self.assertEqual(set(result["selected_node_ids"]), {"fact.payment-retry", "surface.payment-tests"})

    def test_only_accepted_fact_associations_are_used_for_owner_lookup(self):
        shard = json.loads(self.shard_path.read_text())
        shard["nodes"][0]["relationships"][0]["state"] = "proposed"
        write_json(self.shard_path, shard)
        result = ImpactLookup(self.graph()).resolve(["tests/payment/test_retry.py"])
        self.assertEqual(result["owner_lookup_node_ids"], [])
        self.assertEqual(result["selected_node_ids"], ["surface.payment-tests"])

    def test_supplied_reverse_index_cannot_suppress_bound_paths(self):
        graph = self.graph()
        for reverse in ({}, {"exact_paths": {}, "patterns": [], "graph_digest": "old"},
                        {**build_reverse_index(graph), "patterns": []}):
            with self.subTest(reverse=reverse), self.assertRaisesRegex(ImpactGraphError, "reverse index differs"):
                ImpactLookup(graph, reverse)

    def test_legacy_implicit_acceptance_applies_to_reverse_dependants(self):
        shard = json.loads(self.shard_path.read_text())
        edge = shard["nodes"][0]["relationships"][0]
        edge["type"] = "depends-on"
        for schema in (1, 2):
            for state in (None, "accepted", "proposed"):
                relation = dict(edge)
                relation.pop("state", None)
                if state is not None:
                    relation["state"] = state
                nodes = copy.deepcopy(shard["nodes"])
                nodes[0]["relationships"] = [relation]
                write_json(self.root_path, {"schema_version": schema, "map_kind": "target-consistency-map", "nodes": nodes,
                    "impact_policy": {"routing_semantics": 1}})
                result = traverse_impact(load_impact_graph(self.target), ["surface.payment-tests"])[0]
                with self.subTest(schema=schema, state=state):
                    self.assertEqual("fact.payment-retry" in result, state != "proposed")

    def test_public_traversal_rejects_malformed_conditions_without_crashing(self):
        for condition in ({}, {"change_kinds": [{}]}, {"change_kinds": None}):
            graph = self.graph(typed=True, condition=condition)
            with self.subTest(condition=condition), self.assertRaises(ImpactGraphError):
                traverse_impact(graph, ["fact.payment-retry"], change_kinds=["testing"])

    def test_excluded_association_cannot_seed_fact_or_unrelated_fanout(self):
        shard = json.loads(self.shard_path.read_text())
        shard["nodes"][0]["relationships"][0]["applicability"] = {"change_kinds": ["testing"]}
        shard["nodes"][0]["relationships"].append({"id": "edge.fanout", "type": "constrains", "state": "accepted", "target": "surface.other"})
        other = copy.deepcopy(shard["nodes"][1])
        other.update(id="surface.other", canonical_owner="docs/other.md", bindings=[])
        shard["nodes"].append(other)
        write_json(self.shard_path, shard)
        lookup = ImpactLookup(self.graph(typed=True))
        result = lookup.resolve(["tests/payment/test_retry.py"], change_kinds=["documentation"])
        self.assertEqual(result["selected_node_ids"], ["surface.payment-tests"])
        self.assertEqual(result["owner_lookup_node_ids"], [])
        self.assertEqual(result["skipped_edges"][0]["traversal"], "owner-lookup")
        self.assertEqual(set(lookup.resolve(["tests/payment/test_retry.py"], change_kinds=["testing"])["selected_node_ids"]),
                         {"fact.payment-retry", "surface.payment-tests", "surface.other"})

    def test_legacy_keeps_outbound_closure_and_unknown_conditions_expand(self):
        graph = self.graph()
        old = traverse_impact(graph, ["fact.payment-retry"])
        result = ImpactLookup(graph).resolve([], ["fact.payment-retry"])
        self.assertEqual((result["selected_node_ids"], result["selected_edges"], result["skipped_edges"]), old)
        typed = self.graph(typed=True, condition={"change_kinds": ["testing"]})
        self.assertEqual(len(ImpactLookup(typed).resolve([], ["fact.payment-retry"])["selected_node_ids"]), 2)

    def test_explicit_applicability_keeps_skip_evidence_and_never_approves(self):
        graph = self.graph(typed=True, condition={"change_kinds": ["testing"]})
        skipped = ImpactLookup(graph).resolve([], ["fact.payment-retry"], change_kinds=["documentation"])
        self.assertEqual(skipped["selected_node_ids"], ["fact.payment-retry"])
        self.assertEqual(skipped["skipped_edges"][0]["reason"], "condition-not-applicable")
        selected = ImpactLookup(graph).resolve([], ["fact.payment-retry"], change_kinds=["testing"])
        self.assertEqual(len(selected["selected_node_ids"]), 2)

    def test_changed_dependency_reaches_dependants_only_with_explicit_semantics(self):
        shard = json.loads(self.shard_path.read_text())
        shard["nodes"][0]["relationships"][0]["type"] = "depends-on"
        write_json(self.shard_path, shard)
        self.assertEqual(traverse_impact(self.graph(), ["surface.payment-tests"])[0], ["surface.payment-tests"])
        selected, edges, _ = traverse_impact(self.graph(typed=True), ["surface.payment-tests"])
        self.assertEqual(set(selected), {"fact.payment-retry", "surface.payment-tests"})
        self.assertTrue(any(edge.get("traversal") == "dependent" for edge in edges))

    def test_malformed_typed_conditions_return_failures_not_exceptions(self):
        for condition in ({}, {"change_kinds": []}, {"change_kinds": [{}]}, {"change_kinds": [True]}, {"change_kinds": ["unknown"]}, {"change_kinds": ["testing", "testing"]}):
            graph = self.graph(typed=True, condition=condition)
            with self.subTest(condition=condition):
                self.assertTrue(validate_graph(graph))
                with self.assertRaises(ImpactGraphError):
                    ImpactLookup(graph)

    def test_boundary_and_mutation_fail_closed(self):
        lookup = ImpactLookup(self.graph())
        self.assertEqual(len(lookup.resolve([], ["fact.payment-retry"], max_nodes=2)["selected_node_ids"]), 2)
        with self.assertRaises(ImpactGraphError):
            lookup.resolve([], ["fact.payment-retry"], max_nodes=1)
        self.shard_path.write_text(self.shard_path.read_text() + "\n")
        with self.assertRaisesRegex(ImpactGraphError, "changed during lookup"):
            assert_graph_current(lookup.graph, self.target)

    def test_hash_freshness_is_not_replaced_by_metadata_on_coarse_filesystems(self):
        import impact_graph
        stamp = impact_graph._stamp
        def coarse(path):
            return (*stamp(path)[:3], 0, 0)
        with patch.object(impact_graph, "_stamp", side_effect=coarse):
            graph = self.graph()
            self.shard_path.write_bytes(self.shard_path.read_bytes().replace(b"payment", b"invoice"))
            with self.assertRaisesRegex(ImpactGraphError, "changed during lookup"):
                assert_graph_current(graph, self.target)

    def test_shard_schema_boolean_is_not_a_version_integer(self):
        shard = json.loads(self.shard_path.read_text())
        shard["schema_version"] = True
        write_json(self.shard_path, shard)
        with self.assertRaises(ImpactGraphError):
            load_impact_graph(self.target)

    def test_closed_cycle_at_depth_boundary_is_not_missing_coverage(self):
        shard = json.loads(self.shard_path.read_text())
        shard["nodes"][0]["relationships"][0]["type"] = "depends-on"
        write_json(self.shard_path, shard)
        result = ImpactLookup(self.graph(typed=True)).resolve([], ["fact.payment-retry"], max_depth=1)
        self.assertEqual(result["skipped_edges"], [])
        self.assertEqual(len(result["selected_node_ids"]), 2)

    def test_lookup_reuses_compiled_patterns_and_never_exposes_mutable_cache(self):
        graph = self.graph()
        with patch("impact_graph.PathSpec", wraps=__import__("impact_graph").PathSpec) as compile_pattern:
            lookup = ImpactLookup(graph)
            for _ in range(10):
                result = lookup.matching("src/payment/retry.py")
                result.clear()
                self.assertEqual(lookup.matching("src/payment/retry.py"), {"fact.payment-retry"})
        self.assertEqual(compile_pattern.call_count, 2)

    def test_structured_product_contracts_trigger_review_without_generated_index_noise(self):
        paths = ["api/openapi.yaml", "schema/event.json", "pyproject.toml", ".ai/project/context-index.json", ".ai/assistant/consistency-reverse-index.json"]
        self.assertEqual(relationship_review_paths(paths), ["api/openapi.yaml", "pyproject.toml", "schema/event.json"])


class CompactGraphContextTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.target = Path(directory.name)
        self.fixture = TargetFixture(self.target)
        self.fixture.build()
        root_path = self.fixture.project / "consistency-map.json"
        root = json.loads(root_path.read_text())
        root["node_shards"].append({"id": "unrelated", "path": ".ai/project/consistency/areas/unrelated.json"})
        self.other = self.fixture.project / "consistency/areas/unrelated.json"
        write_json(self.other, {"schema_version": 1, "shard_kind": "target-consistency-map-shard", "id": "unrelated", "project_area": "other", "nodes": [{"id": "fact.unrelated", "fact_type": "other", "level": "fact", "canonical_owner": "docs/unrelated.md", "coverage_state": "isolated-verified", "bindings": [], "relationships": [], "notes": "historical context " * 4000}]})
        write_json(root_path, root)
        write_json(self.fixture.assistant / "consistency-reverse-index.json", build_reverse_index(load_impact_graph(self.target)))
        self.fixture.refresh_catalogs()
        path = self.fixture.project / "context-index.json"
        catalog = json.loads(path.read_text())
        catalog["entries"].append(catalog_entry(self.fixture.project, "project.unrelated-shard", "consistency/areas/unrelated.json"))
        write_json(path, catalog)

    def request(self, **changes):
        return ContextPlanRequest(**{"target": self.target, "profile": "code-local", "operation": "product-change", "changed_paths": ("src/payment/retry.py",), **changes})

    def test_compact_delivery_keeps_whole_graph_validation_and_original_owners(self):
        plan = plan_target_context(self.request())
        self.assertEqual(plan["status"], "ready", plan)
        paths = {item["path"] for item in plan["context_packet"]["selected_items"]}
        self.assertNotIn(".ai/project/consistency/areas/unrelated.json", paths)
        self.assertIn(".ai/project/consistency/areas/billing.json", paths)
        self.assertIn("docs/billing.md", paths)
        self.assertIn(".ai/project/consistency/areas/unrelated.json", plan["impact"]["graph_evidence"]["validated_paths"])
        self.assertEqual(plan["task_contract"]["fact_ids"], ["fact.payment-retry"])
        self.assertFalse(plan["task_contract"]["acceptance_granted"])
        self.assertLess(plan["context_packet"]["budget"]["total_words"], 8000)
        shard = json.loads(self.other.read_text())
        shard["nodes"][0]["coverage_state"] = "invalid"
        write_json(self.other, shard)
        self.assertEqual(plan_target_context(self.request())["errors"][0]["code"], "CONSISTENCY_GRAPH_INVALID")

    def test_unselected_graph_mutation_during_lookup_blocks_packet(self):
        original = context_planning._verify_selected_content
        def mutate(target, selected):
            original(target, selected)
            self.other.write_text(self.other.read_text() + "\n")
        with patch.object(context_planning, "_verify_selected_content", side_effect=mutate):
            plan = plan_target_context(self.request())
        self.assertEqual(plan["errors"][0]["code"], "CONSISTENCY_INPUT_CHANGED")
        self.assertIsNone(plan["context_packet"])

    def test_selected_graph_coarse_stamp_mutation_does_not_reuse_an_old_hash(self):
        import impact_graph
        stamp = impact_graph._stamp
        original = context_planning._verify_selected_content
        def coarse(path):
            return (*stamp(path)[:3], 0, 0)
        def mutate(target, selected):
            verified = original(target, selected)
            path = self.fixture.project / "consistency/areas/billing.json"
            path.write_bytes(path.read_bytes().replace(b"payment", b"invoice"))
            return verified
        with patch.object(impact_graph, "_stamp", side_effect=coarse), patch.object(context_planning, "_verify_selected_content", side_effect=mutate):
            result = plan_target_context(self.request())
        self.assertEqual(result["errors"][0]["code"], "CONTEXT_INPUT_CHANGED")
        self.assertIsNone(result["context_packet"])

    def test_routing_mutation_cannot_bind_new_bytes_to_old_selection(self):
        original = context_planning._verify_selected_content
        def mutate(target, selected):
            result = original(target, selected)
            path = self.fixture.assistant / "context/profiles/code-local.json"
            data = json.loads(path.read_text())
            data["profile"] = "different-profile"
            write_json(path, data)
            return result
        with patch.object(context_planning, "_verify_selected_content", side_effect=mutate):
            result = plan_target_context(self.request(changed_paths=()))
        self.assertEqual(result["errors"][0]["code"], "CONTEXT_INPUT_CHANGED")
        self.assertIsNone(result["context_packet"])

    def test_non_json_request_values_have_structured_serializable_errors(self):
        for field in ("max_words", "max_characters", "profile", "operation", "assistant_surface"):
            for value in (Path("bad"), object(), {"bad"}):
                with self.subTest(field=field, value=type(value).__name__):
                    result = plan_target_context(self.request(**{field: value}))
                    self.assertEqual(result["status"], "invalid-request")
                    self.assertIsNone(result["context_packet"])
                    json.dumps(result, allow_nan=False)

    def test_cached_and_uncached_plans_have_identical_contracts_and_failures(self):
        expected = plan_target_context(self.request())
        for cap in (0, 1, 4 * 1024 * 1024):
            with self.subTest(cap=cap), patch.object(context_planning, "ContextInputSnapshot",
                    side_effect=lambda root: ContextInputSnapshot(root, cache_bytes=cap)):
                self.assertEqual(plan_target_context(self.request()), expected)
        path = self.fixture.assistant / "context/profiles/code-local.json"
        before = path.read_bytes()
        verify = context_planning._verify_selected_content
        def mutate(target, selected):
            result = verify(target, selected)
            data = json.loads(path.read_text())
            data["profile"] = "changed"
            write_json(path, data)
            return result
        outcomes = []
        for cap in (0, 4 * 1024 * 1024):
            path.write_bytes(before)
            with patch.object(context_planning, "ContextInputSnapshot", side_effect=lambda root: ContextInputSnapshot(root, cache_bytes=cap)), \
                    patch.object(context_planning, "_verify_selected_content", side_effect=mutate):
                outcomes.append(plan_target_context(self.request(changed_paths=())))
        self.assertEqual(outcomes[0], outcomes[1])


    def test_mapped_code_still_requests_relationship_review_and_no_graph_for_local_docs(self):
        plan = plan_target_context(self.request())
        self.assertEqual(plan["impact"]["relationship_candidate_triggers"], ["src/payment/retry.py"])
        with patch.object(context_planning, "load_impact_graph", side_effect=AssertionError("no graph for unrelated request")):
            local = plan_target_context(self.request(changed_paths=()))
        self.assertEqual(local["status"], "ready", local)

    def test_explicit_warning_lookup_reuses_the_invocation_graph_snapshot(self):
        with patch.object(context_planning, "load_impact_graph", wraps=load_impact_graph) as load:
            plan = plan_target_context(self.request(document_warnings=True))
        self.assertEqual(plan["status"], "ready", plan)
        self.assertEqual(load.call_count, 1)

    def test_no_cross_request_cache_hides_new_relationships_or_new_owners(self):
        first = plan_target_context(self.request())
        shard_path = self.fixture.project / "consistency/areas/billing.json"
        shard = json.loads(shard_path.read_text())
        shard["nodes"][0]["canonical_owner"] = "docs/missing.md"
        write_json(shard_path, shard)
        write_json(self.fixture.assistant / "consistency-reverse-index.json", build_reverse_index(load_impact_graph(self.target)))
        self.fixture.refresh_catalogs()
        second = plan_target_context(self.request())
        self.assertEqual(first["status"], "ready")
        self.assertEqual(second["errors"][0]["code"], "CANONICAL_OWNER_UNAVAILABLE")


class ContextInputSnapshotTests(unittest.TestCase):
    def test_package_style_readers_share_the_package_snapshot(self):
        program = (
            "from pathlib import Path; import tempfile; "
            "from tools.context_input_snapshot import ContextInputSnapshot, ContextInputChanged; "
            "from tools.target_adapter_validation.context import TargetRepositoryView; "
            "from tools.context_catalog import catalog_content_stats; "
            "d=tempfile.TemporaryDirectory(); root=Path(d.name).resolve(); p=root/'input.md'; p.write_bytes(b'abc'); "
            "snapshot=ContextInputSnapshot(root); snapshot.__enter__(); "
            "assert catalog_content_stats(p).words == 1; "
            "assert TargetRepositoryView(root).read_bytes_result(p,max_bytes=3).value == b'abc'; "
            "p.write_bytes(b'xyz')\n"
            "try: snapshot.__exit__(None,None,None)\n"
            "except ContextInputChanged: pass\n"
            "else: raise AssertionError('package snapshot did not verify its input')\n"
            "d.cleanup()\n"
        )
        result = subprocess.run([sys.executable, "-B", "-c", program], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def fixture(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name).resolve()
        path = root / "input.json"
        path.write_bytes(b"abc")
        return root, path

    def test_cache_below_at_and_above_file_size_keeps_verification(self):
        for cap in (2, 3, 4):
            root, path = self.fixture()
            snapshot = ContextInputSnapshot(root, cache_bytes=cap)
            with self.subTest(cap=cap), self.assertRaises(ContextInputChanged):
                with snapshot:
                    self.assertEqual(read_context_bytes(path), b"abc")
                    self.assertLessEqual(snapshot.used, cap)
                    path.write_bytes(b"xyz")
            self.assertEqual(snapshot.used, 0)
            self.assertEqual(snapshot.inputs, {})

    def test_eviction_and_nested_targets_do_not_mix_or_persist_inputs(self):
        root, path = self.fixture()
        other_root, other = self.fixture()
        other.write_bytes(b"xyz")
        with ContextInputSnapshot(root, cache_bytes=0):
            self.assertEqual(read_context_bytes(path), b"abc")
            with ContextInputSnapshot(other_root):
                self.assertEqual(read_context_bytes(other), b"xyz")
            self.assertEqual(read_context_bytes(path), b"abc")
        path.write_bytes(b"new")
        with ContextInputSnapshot(root):
            self.assertEqual(read_context_bytes(path), b"new")

    def test_bounded_target_view_inputs_join_the_same_snapshot(self):
        from target_adapter_validation.context import TargetRepositoryView
        root, path = self.fixture()
        with self.assertRaises(ContextInputChanged):
            with ContextInputSnapshot(root):
                value = TargetRepositoryView(root).read_bytes_result(path, max_bytes=3)
                self.assertEqual(value.value, b"abc")
                path.write_bytes(b"xyz")

    def test_foreign_symlink_after_a_read_is_rejected_before_following_it(self):
        root, path = self.fixture()
        other_root, other = self.fixture()
        try:
            probe = root / "probe"
            probe.symlink_to(other)
            probe.unlink()
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        with self.assertRaises(ContextInputChanged):
            with ContextInputSnapshot(root):
                read_context_bytes(path)
                path.unlink()
                path.symlink_to(other)


class IncidentFrontierTests(unittest.TestCase):
    def task(self, name, predecessors=(), state="active"):
        return {"task_id": name, "incident_family_id": "case", "state": state,
                "predecessor_task_ids": list(predecessors), "problem_model": {"path": name, "sha256": "a" * 64},
                "latest_failed_gate_id": "original-flow"}

    def test_concurrent_heads_are_not_chosen_by_order_or_iteration(self):
        prior, left, right = self.task("prior"), self.task("left", ["prior"]), self.task("right", ["prior"])
        view = incident_frontier([right, prior, left], left)
        self.assertEqual(view["head_task_ids"], ["left", "right"])
        self.assertTrue(view["multiple_heads"])
        self.assertFalse(view["automatic_closure"])
        self.assertEqual(view["unclosed_predecessors"][0]["obligations"], "not-loaded-not-discharged")
        self.assertEqual(prior["state"], "active")

    def test_absent_incident_family_does_not_group_unrelated_tasks(self):
        selected, other = self.task("selected"), self.task("unrelated")
        selected["incident_family_id"] = other["incident_family_id"] = "none"
        view = incident_frontier([selected, other], selected)
        self.assertEqual(view["head_task_ids"], ["selected"])
        self.assertFalse(view["multiple_heads"])


class ReverseIndexFinalizationTests(unittest.TestCase):
    def fixture(self):
        helper = graph_fixture.ImpactGraphTests()
        self.addCleanup(helper.doCleanups)
        _, target = helper.make_graph()
        root = target / ".ai/project/consistency-map.json"
        data = json.loads(root.read_text())
        data["reverse_index"] = ".ai/assistant/consistency-reverse-index.json"
        write_json(root, data)
        manifest = target / ".ai/alatyr.yaml"
        manifest.write_text("modules:\n  selected: [consistency-map]\n  enabled: [consistency-map]\n")
        return target, manifest

    def test_only_enabled_default_index_joins_canonical_finalizer(self):
        from finalize_target_support import build_steps
        from target_support_outputs import step_outputs
        target, manifest = self.fixture()
        def steps():
            return build_steps(target=target, write=True, migration_staging=True, diff_ref=None, approval_records=[], change_packages=[])
        order = [item.step_id for item in steps()]
        self.assertLess(order.index("consistency-reverse-index"), order.index("entry-packet"))
        outputs = step_outputs("consistency-reverse-index", target)
        self.assertEqual(json.loads(next(iter(outputs.values()))), build_reverse_index(load_impact_graph(target)))
        manifest.write_text("modules:\n  selected: []\n  enabled: []\n")
        (target / ".ai/project/consistency-map.json").write_text("not JSON")
        self.assertNotIn("consistency-reverse-index", [item.step_id for item in steps()])

    def test_later_failure_rolls_back_reverse_index_and_preserves_graph(self):
        from finalize_target_support import Step, execute_write_steps
        import target_support_outputs
        target, _ = self.fixture()
        reverse = target / ".ai/assistant/consistency-reverse-index.json"
        reverse.parent.mkdir(parents=True, exist_ok=True)
        reverse.write_bytes(b"{\"old\": true}\n")
        graph = target / ".ai/project/consistency-map.json"
        before = graph.read_bytes()
        original = target_support_outputs.step_outputs
        def builder(step, target):
            if step == "entry-packet":
                raise ValueError("downstream failure")
            return original(step, target)
        with patch("finalize_target_support.step_outputs", side_effect=builder):
            code, failed, conflicts = execute_write_steps(target, [Step("consistency-reverse-index", "unused", ()), Step("entry-packet", "unused", ())])
        self.assertNotEqual(code, 0)
        self.assertEqual(failed, "entry-packet")
        self.assertEqual(conflicts, [])
        self.assertEqual(reverse.read_bytes(), b"{\"old\": true}\n")
        self.assertEqual(graph.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
