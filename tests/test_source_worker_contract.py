from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from source_worker_contract import (  # noqa: E402
    SourceWorkerContractError,
    validate_decision_evidence,
    validate_delegation_execution_tree,
    validate_runtime_capability,
    validate_source_worker_policy,
    validate_worker_packet,
)


NOW = datetime(2026, 9, 3, 12, 5, tzinfo=timezone.utc)
SESSION_ID = "opaque-session-binding"


def policy_fixture() -> dict[str, object]:
    return json.loads(
        (ROOT / "tools" / "source_worker_policy.json").read_text(encoding="utf-8")
    )


def capability_fixture() -> dict[str, object]:
    return {
        "schema_version": 2,
        "status": "available",
        "surface_id": "test-surface",
        "runtime_id": "test-runtime",
        "backend_kind": "native-worker",
        "role_ids": ["read-only-auditor"],
        "max_parallelism": 2,
        "write_isolation": "read-only",
        "result_delivery": True,
        "model_binding": "client-default",
        "verified_at": "2026-09-03T12:00:00Z",
        "expires_at": "2026-09-03T12:20:00Z",
        "freshness": "current-session",
        "session_id": SESSION_ID,
        "evidence": "runtime fixture",
    }


def packet_fixture() -> dict[str, object]:
    return {
        "schema_version": 3,
        "packet_kind": "source-read-only-workstream",
        "parent_packet_id": None,
        "depth": 1,
        "remaining_worker_budget": 7,
        "coverage_key": "source-worker-contract",
        "child_proposal_policy": "propose-only",
        "workstream_id": "source-contract",
        "role_id": "read-only-auditor",
        "objective": "Inspect the source worker contract",
        "bounded_context": ["tools/source_worker_contract.py"],
        "conditional_context": [],
        "non_goals": ["modify repository state"],
        "allowed_actions": ["inspect"],
        "write_scope": "none",
        "independent": True,
        "independence_key": "source-worker-contract",
        "semantic_scope": "source-worker-contract",
        "changed_fact_ids": [],
        "canonical_owner_refs": ["tools/source_worker_contract.py"],
        "surface_refs": ["tools/source_worker_contract.py"],
        "relationship_refs": [],
        "overlap_decision": "disjoint",
        "expected_evidence": "Path-specific findings",
    }


def execution_node(
    node_id: str,
    *,
    parent_node_id: str | None,
    depth: int,
    status: str,
    coverage_key: str,
    semantic_scope: str,
    context_words: int = 0,
    stop_reason_id: str | None = None,
) -> dict[str, object]:
    return {
        "node_id": node_id,
        "parent_node_id": parent_node_id,
        "packet_id": None if depth == 0 else f"packet-{node_id}",
        "result_id": None if status in {"PLANNED", "READY", "RUNNING"} else f"result-{node_id}",
        "depth": depth,
        "status": status,
        "role_id": "primary" if depth == 0 else "read-only-auditor",
        "assistant_surface": "primary" if depth == 0 else "test-surface",
        "dispatch_backend": "primary" if depth == 0 else "native-worker",
        "implementation_level": "L1",
        "coverage_key": coverage_key,
        "semantic_scope": semantic_scope,
        "changed_fact_ids": [],
        "canonical_owner_refs": ["tools/source_worker_contract.py"],
        "surface_refs": ["tools/source_worker_contract.py"],
        "relationship_refs": [],
        "allowed_actions": ["inspect"],
        "write_scope": "none",
        "context_words": context_words,
        "attempt": 0,
        "result_status": None if status in {"PLANNED", "READY", "RUNNING"} else "succeeded",
        "stop_reason_id": stop_reason_id,
        "child_proposals": [],
        "overlap_decision": "not-applicable" if depth == 0 else "disjoint",
    }


def execution_tree_fixture() -> dict[str, object]:
    return {
        "schema_version": 1,
        "tree_kind": "alatyr-delegation-execution-tree",
        "operation_id": "op-1",
        "base_revision": "base-revision",
        "current_user_authorization": {
            "scope": "read-only audit",
            "authorized_phases": ["inspect"],
        },
        "task_profile": "repository-audit",
        "policy_revision": "policy-sha",
        "capability_evidence": "capability-record",
        "aggregate_budget": {
            "max_total_delegates": 8,
            "max_parallel_delegates": 2,
            "max_children_per_parent": 4,
            "max_context_words_total": 24000,
            "max_retries_total": 2,
            "used_total_delegates": 2,
            "used_parallel_delegates": 2,
            "used_context_words": 30,
            "used_retries": 0,
        },
        "root_node_id": "root",
        "nodes": [
            execution_node(
                "root",
                parent_node_id=None,
                depth=0,
                status="DONE",
                coverage_key="root",
                semantic_scope="primary-convergence",
                stop_reason_id="evidence-sufficient",
            ),
            execution_node(
                "worker-1",
                parent_node_id="root",
                depth=1,
                status="DONE",
                coverage_key="coverage-1",
                semantic_scope="scope-1",
                context_words=10,
                stop_reason_id="scope-covered",
            ),
            execution_node(
                "worker-2",
                parent_node_id="root",
                depth=1,
                status="DONE",
                coverage_key="coverage-2",
                semantic_scope="scope-2",
                context_words=20,
                stop_reason_id="scope-covered",
            ),
        ],
        "edges": [
            {
                "parent_node_id": "root",
                "child_node_id": "worker-1",
                "edge_kind": "primary-approved-dispatch",
            },
            {
                "parent_node_id": "root",
                "child_node_id": "worker-2",
                "edge_kind": "primary-approved-dispatch",
            },
        ],
        "primary_convergence": {
            "status": "completed",
            "reviewed_result_ids": ["result-root", "result-worker-1", "result-worker-2"],
            "rejected_result_ids": [],
            "combined_validation": "passed",
            "logical_integrity_review": "passed",
            "residual_risk": "none",
            "final_stop_reason_id": "evidence-sufficient",
        },
    }


class SourceWorkerPolicyTests(unittest.TestCase):
    def test_repository_policy_is_valid(self) -> None:
        validate_source_worker_policy(policy_fixture(), root=ROOT)

    def test_required_policy_surfaces_fail_closed_when_removed(self) -> None:
        mutations = {
            "canonical rule": lambda item: item.pop("canonical_rule"),
            "activation": lambda item: item.pop("activation"),
            "activation task classes": lambda item: item["activation"].pop(
                "task_classes"
            ),
            "capability status": lambda item: item[
                "runtime_capability_contract"
            ].pop("status"),
            "capability backend kinds": lambda item: item[
                "runtime_capability_contract"
            ].pop("backend_kinds"),
            "capability role": lambda item: item[
                "runtime_capability_contract"
            ].pop("required_role_id"),
            "packet conditional context": lambda item: item["workstreams"][
                "framework-rules"
            ].pop("conditional_context"),
            "workstream independence": lambda item: item["workstreams"][
                "framework-rules"
            ].pop("independent"),
            "decision skip field": lambda item: item["decision_evidence"][
                "required_fields"
            ].remove("skip_reason_id"),
            "decision rules": lambda item: item["decision_evidence"].pop(
                "decision_rules"
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                policy = copy.deepcopy(policy_fixture())
                mutate(policy)
                with self.assertRaises(SourceWorkerContractError):
                    validate_source_worker_policy(policy, root=ROOT)

    def test_every_declared_contract_field_is_required(self) -> None:
        baseline = policy_fixture()
        targets = [
            ("policy", []),
            ("activation", ["activation"]),
            ("capability", ["runtime_capability_contract"]),
            ("decision", ["decision_evidence"]),
            ("packet contract", ["worker_packet_contract"]),
            ("workstream", ["workstreams", "framework-rules"]),
        ]
        for label, path in targets:
            target = baseline
            for part in path:
                target = target[part]
            for field in list(target):
                with self.subTest(label=label, field=field):
                    policy = copy.deepcopy(baseline)
                    mutated = policy
                    for part in path:
                        mutated = mutated[part]
                    mutated.pop(field)
                    with self.assertRaises(SourceWorkerContractError):
                        validate_source_worker_policy(policy, root=ROOT)

    def test_policy_rejects_provider_binding_and_duplicate_independence(self) -> None:
        for label, mutate in [
            (
                "provider binding",
                lambda item: item.update({"provider": "specific-provider"}),
            ),
            (
                "duplicate independence",
                lambda item: item["workstreams"]["installation-surfaces"].update(
                    {
                        "independence_key": item["workstreams"]["framework-rules"][
                            "independence_key"
                        ]
                    }
                ),
            ),
        ]:
            with self.subTest(label=label):
                policy = copy.deepcopy(policy_fixture())
                mutate(policy)
                with self.assertRaises(SourceWorkerContractError):
                    validate_source_worker_policy(policy, root=ROOT)


class RuntimeCapabilityTests(unittest.TestCase):
    def validate(self, record: dict[str, object]) -> dict[str, object]:
        policy = policy_fixture()
        return validate_runtime_capability(
            record,
            policy["runtime_capability_contract"],
            session_id=SESSION_ID,
            now=NOW,
        )

    def test_current_bound_capability_is_accepted(self) -> None:
        self.assertEqual(self.validate(capability_fixture()), capability_fixture())

    def test_invalid_time_or_session_evidence_is_rejected(self) -> None:
        cases = {
            "stale": {"verified_at": "2026-09-03T11:00:00Z"},
            "future": {"verified_at": "2026-09-03T12:07:00Z"},
            "naive": {"verified_at": "2026-09-03T12:00:00"},
            "expired": {"expires_at": "2026-09-03T12:04:00Z"},
            "overlong": {"expires_at": "2026-09-03T13:00:00Z"},
            "wrong session": {"session_id": "different-session"},
        }
        for label, updates in cases.items():
            with self.subTest(label=label):
                record = capability_fixture()
                record.update(updates)
                with self.assertRaises(SourceWorkerContractError):
                    self.validate(record)

    def test_capability_schema_is_exact_and_reference_time_is_aware(self) -> None:
        record = capability_fixture()
        record["undeclared_permission"] = "modify"
        with self.assertRaisesRegex(SourceWorkerContractError, "unexpected fields"):
            self.validate(record)
        with self.assertRaisesRegex(SourceWorkerContractError, "include a timezone"):
            validate_runtime_capability(
                capability_fixture(),
                policy_fixture()["runtime_capability_contract"],
                session_id=SESSION_ID,
                now=NOW.replace(tzinfo=None),
            )


class WorkerPacketTests(unittest.TestCase):
    def validate(self, packet: dict[str, object]) -> dict[str, object]:
        return validate_worker_packet(
            packet,
            policy_fixture()["worker_packet_contract"],
            root=ROOT,
        )

    def test_task_specific_packet_is_structured_and_inspect_only(self) -> None:
        self.assertEqual(self.validate(packet_fixture()), packet_fixture())
        cases = {
            "write action": {"allowed_actions": ["inspect", "modify"]},
            "write scope": {"write_scope": "tools/**"},
            "absolute context": {"bounded_context": ["/etc/passwd"]},
            "traversal context": {"bounded_context": ["../outside.md"]},
            "missing context": {"bounded_context": ["tools/not-present.py"]},
            "extra field": {"tools": ["shell"]},
            "recursive depth": {"depth": 2},
            "autonomous child": {"child_proposal_policy": "dispatch"},
            "missing semantic scope": {"semantic_scope": ""},
            "missing canonical owner": {"canonical_owner_refs": []},
            "invalid overlap decision": {"overlap_decision": "assume-disjoint"},
        }
        for label, updates in cases.items():
            with self.subTest(label=label):
                packet = packet_fixture()
                packet.update(updates)
                with self.assertRaises(SourceWorkerContractError):
                    self.validate(packet)

    def test_tree_policy_limits_and_stop_reasons_fail_closed(self) -> None:
        cases = {
            "autonomous dispatch": ("tree_policy", "worker_child_behavior", "dispatch"),
            "recursive source depth": ("tree_policy", "hard_max_depth", 2),
            "zero worker budget": ("tree_policy", "max_total_delegates", 0),
            "zero parallel budget": ("tree_policy", "max_parallel_delegates", 0),
            "worker budget below activation": ("tree_policy", "max_total_delegates", 1),
            "parallel budget below activation": ("tree_policy", "max_parallel_delegates", 1),
            "child budget below activation": ("tree_policy", "max_children_per_parent", 1),
            "parallel exceeds total": ("tree_policy", "max_parallel_delegates", 9),
            "missing stop reason": ("stop_policy", "stop_reason_ids", ["scope-covered"]),
        }
        for label, (section, field, value) in cases.items():
            with self.subTest(label=label):
                policy = policy_fixture()
                policy[section][field] = value
            with self.assertRaises(SourceWorkerContractError):
                validate_source_worker_policy(policy, root=ROOT)

    def test_packet_context_cannot_escape_through_a_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "repository"
            root.mkdir()
            outside = base / "outside.md"
            outside.write_text("outside", encoding="utf-8")
            try:
                (root / "escape.md").symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            packet = packet_fixture()
            packet["bounded_context"] = ["escape.md"]
            with self.assertRaises(SourceWorkerContractError):
                validate_worker_packet(
                    packet,
                    policy_fixture()["worker_packet_contract"],
                    root=root,
                )


class DelegationExecutionTreeTests(unittest.TestCase):
    def validate(self, tree: dict[str, object]) -> dict[str, object]:
        return validate_delegation_execution_tree(tree, policy_fixture())

    def test_execution_tree_records_cumulative_budget_and_convergence(self) -> None:
        tree = execution_tree_fixture()
        self.assertEqual(self.validate(tree), tree)

    def test_execution_tree_rejects_budget_and_topology_drift(self) -> None:
        cases = {
            "worker write action": lambda item: item["nodes"][1].update(
                {"allowed_actions": ["inspect", "modify"]}
            ),
            "worker write scope": lambda item: item["nodes"][1].update(
                {"write_scope": "tools/**"}
            ),
            "worker role drift": lambda item: item["nodes"][1].update(
                {"role_id": "implementer"}
            ),
            "missing packet": lambda item: item["nodes"][1].update(
                {"packet_id": None}
            ),
            "terminal missing result": lambda item: item["nodes"][1].update(
                {"result_id": None}
            ),
            "terminal wrong result status": lambda item: item["nodes"][1].update(
                {"result_status": "failed"}
            ),
            "non-terminal result claim": lambda item: item["nodes"][1].update(
                {
                    "status": "RUNNING",
                    "result_id": "result-worker-1",
                    "result_status": "succeeded",
                    "stop_reason_id": "scope-covered",
                }
            ),
            "duplicate coverage": lambda item: item["nodes"][2].update(
                {"coverage_key": "coverage-1"}
            ),
            "semantic overlap": lambda item: item["nodes"][2].update(
                {"semantic_scope": "scope-1"}
            ),
            "missing stop reason": lambda item: item["nodes"][1].update(
                {"stop_reason_id": None}
            ),
            "wrong aggregate context": lambda item: item["aggregate_budget"].update(
                {"used_context_words": 31}
            ),
            "too many delegates": lambda item: item["aggregate_budget"].update(
                {"used_total_delegates": 9}
            ),
            "wrong parallel usage": lambda item: item["aggregate_budget"].update(
                {"used_parallel_delegates": 1}
            ),
            "parallel cap exceeds policy": lambda item: item[
                "aggregate_budget"
            ].update({"max_parallel_delegates": 3}),
            "missing parent": lambda item: item["nodes"][1].update(
                {"parent_node_id": "missing"}
            ),
            "edge mismatch": lambda item: item["edges"][0].update(
                {"parent_node_id": "worker-2"}
            ),
            "missing edge": lambda item: item["edges"].pop(),
            "duplicate edge": lambda item: item["edges"].append(
                copy.deepcopy(item["edges"][0])
            ),
            "invalid final stop": lambda item: item["primary_convergence"].update(
                {"final_stop_reason_id": "not-a-stop"}
            ),
            "unreviewed terminal result": lambda item: item[
                "primary_convergence"
            ].update({"reviewed_result_ids": ["result-root", "result-worker-1"]}),
            "unknown reviewed result": lambda item: item[
                "primary_convergence"
            ].update(
                {
                    "reviewed_result_ids": [
                        "result-root",
                        "result-worker-1",
                        "result-worker-2",
                        "result-missing",
                    ]
                }
            ),
            "unknown rejected result": lambda item: item[
                "primary_convergence"
            ].update({"rejected_result_ids": ["result-missing"]}),
            "rejected result not reviewed": lambda item: item[
                "primary_convergence"
            ].update(
                {
                    "reviewed_result_ids": ["result-root", "result-worker-1"],
                    "rejected_result_ids": ["result-worker-2"],
                }
            ),
        }
        for label, mutate in cases.items():
            with self.subTest(label=label):
                tree = copy.deepcopy(execution_tree_fixture())
                mutate(tree)
                with self.assertRaises(SourceWorkerContractError):
                    self.validate(tree)

    def test_execution_tree_allows_primary_reconciled_semantic_overlap(self) -> None:
        tree = copy.deepcopy(execution_tree_fixture())
        tree["nodes"][2]["semantic_scope"] = "scope-1"
        tree["nodes"][2]["overlap_decision"] = "primary-reconciled-overlap"
        self.validate(tree)


class DecisionEvidenceTests(unittest.TestCase):
    def test_skip_reason_nullability_is_enforced_for_every_decision(self) -> None:
        contract = policy_fixture()["decision_evidence"]
        cases = [
            ("runtime-verification-required", None, "required", "unknown", [], True),
            ("runtime-verification-required", "capability-unverified", "required", "unknown", [], False),
            ("workstream-identification-required", "insufficient-independent-work", "required", "unknown", [], True),
            ("workstream-identification-required", None, "required", "unknown", [], False),
            ("delegation-recommended", None, "required", "available", ["one", "two"], True),
            ("delegation-recommended", "user-restricted", "required", "available", ["one", "two"], False),
            ("delegation-recommended", None, "required", "available", ["one"], False),
            ("delegation-recommended", None, "required", "unknown", ["one", "two"], False),
            ("kept-local", "user-restricted", "required", "available", [], True),
            ("kept-local", None, "required", "available", [], False),
            ("primary-assistant", "insufficient-independent-work", "not-required", "unknown", [], True),
            ("primary-assistant", None, "not-required", "unknown", [], False),
            ("primary-assistant", "insufficient-independent-work", "required", "unknown", [], False),
        ]
        for decision, skip_reason_id, evaluation, runtime, selected, accepted in cases:
            with self.subTest(decision=decision, skip_reason_id=skip_reason_id):
                evidence = {
                    "evaluation_status": evaluation,
                    "runtime_capability_status": runtime,
                    "selected_workstream_ids": selected,
                    "decision": decision,
                    "reason": "deterministic test evidence",
                    "skip_reason_id": skip_reason_id,
                }
                if accepted:
                    validate_decision_evidence(evidence, contract)
                else:
                    with self.assertRaises(SourceWorkerContractError):
                        validate_decision_evidence(evidence, contract)


if __name__ == "__main__":
    unittest.main()
