from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft7Validator


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from delegation_evidence import (  # noqa: E402
    DelegationEvidenceError,
    validate_execution_tree,
)
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
        "schema_version": 5,
        "packet_kind": "source-read-only-workstream",
        "parent_packet_id": None,
        "depth": 1,
        "remaining_worker_budget": 7,
        "coverage_key": "source-worker-contract",
        "child_dispatch_mode": "propose-only",
        "branch_envelope_sha256": None,
        "workstream_id": "source-contract",
        "role_id": "read-only-auditor",
        "objective": "Inspect the source worker contract",
        "bounded_context": ["tools/source_worker_contract.py"],
        "max_initial_words": 10000,
        "max_result_words": 1600,
        "max_summary_words": 600,
        "parent_context_packet_sha256": None,
        "context_delta": {"add": [], "remove": []},
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


def canonical_digest(value: dict[str, object], excluded: str) -> str:
    import hashlib

    payload = {key: item for key, item in value.items() if key != excluded}
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_value_digest(value: object) -> str:
    import hashlib

    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_artifact(root: Path, relpath: str, text: str) -> dict[str, object]:
    import hashlib

    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    payload = path.read_bytes()
    return {
        "path": relpath,
        "word_count": len(text.split()),
        "character_count": len(text),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def recursive_execution_fixture(root: Path) -> dict[str, object]:
    capability = write_artifact(
        root,
        "evidence/capability.json",
        '{"status":"available","nested_dispatch":true}\n',
    )
    envelope = {
        "schema_version": 1,
        "envelope_kind": "alatyr-delegation-branch-envelope",
        "envelope_id": "envelope-1",
        "operation_id": "op-1",
        "root_packet_id": "packet-coordinator",
        "parent_node_id": "coordinator",
        "issued_by": "primary-assistant",
        "base_revision": "base-revision",
        "authorized_phases": ["inspect"],
        "max_depth": 2,
        "max_children": 2,
        "max_context_words": 100,
        "max_result_words": 100,
        "max_summary_words": 50,
        "max_retries": 0,
        "allowed_actions": ["inspect"],
        "write_scope": "none",
        "allowed_tools": ["read"],
        "allowed_surface_refs": ["tools/**"],
        "semantic_scope": "source-worker-contract",
        "coverage_prefix": "source-worker-contract/",
        "context_packet_sha256": None,
        "capability_evidence_sha256": capability["sha256"],
        "required_validation": ["unit tests"],
        "expires_at": "2099-01-01T00:00:00Z",
        "envelope_sha256": "pending",
    }
    envelope["envelope_sha256"] = canonical_digest(envelope, "envelope_sha256")
    envelope_path = root / "evidence/envelope.json"
    envelope_path.parent.mkdir(parents=True, exist_ok=True)
    envelope_path.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")

    def worker_result(node_id: str, depth: int, parent_packet: str | None, child_ids: list[str], child_digests: list[str]) -> tuple[dict[str, object], dict[str, object]]:
        raw = write_artifact(root, f"evidence/{node_id}-raw.md", f"raw finding for {node_id}\n")
        summary = write_artifact(root, f"evidence/{node_id}-summary.md", f"summary {node_id}\n")
        result = {
            "schema_version": 1,
            "result_kind": "alatyr-normalized-worker-result",
            "result_id": f"result-{node_id}",
            "packet_id": f"packet-{node_id}",
            "parent_packet_id": parent_packet,
            "node_id": node_id,
            "depth": depth,
            "base_revision": "base-revision",
            "status": "succeeded",
            "measurement_state": "observed",
            "input_context_packet_sha256": None,
            "raw_payload": raw,
            "accepted_summary": summary,
            "summary_covers_result_ids": child_ids,
            "child_result_sha256": child_digests,
            "evidence_manifest": [],
            "touched_surfaces": [],
            "tools_used": ["read"],
            "scope_violation": "none",
            "authorization_concern": "none",
            "validation": ["unit tests"],
            "stop_reason_id": "scope-covered",
            "subtree_sha256": "pending",
        }
        result["subtree_sha256"] = canonical_digest(result, "subtree_sha256")
        result_path = root / f"evidence/{node_id}-result.json"
        result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result, write_artifact(
            root,
            f"evidence/{node_id}-result.json",
            result_path.read_text(encoding="utf-8"),
        )

    child_result, child_result_artifact = worker_result(
        "child", 2, "packet-coordinator", [], []
    )
    coordinator_result, coordinator_result_artifact = worker_result(
        "coordinator",
        1,
        None,
        ["result-child"],
        [child_result_artifact["sha256"]],
    )
    checkpoint = {
        "schema_version": 1,
        "checkpoint_kind": "alatyr-delegation-branch-checkpoint",
        "checkpoint_id": "checkpoint-1",
        "previous_checkpoint_id": None,
        "operation_id": "op-1",
        "node_id": "coordinator",
        "branch_envelope_sha256": envelope["envelope_sha256"],
        "base_revision": "base-revision",
        "accepted_result_ids": ["result-child"],
        "accepted_result_sha256": [child_result_artifact["sha256"]],
        "rejected_result_ids": [],
        "completed_coverage_keys": ["source-worker-contract/child"],
        "accepted_summary": coordinator_result["accepted_summary"],
        "context_packet_sha256": None,
        "semantic_guidance_sha256": None,
        "evidence_manifest_sha256": canonical_value_digest(
            {"result-child": child_result["evidence_manifest"]}
        ),
        "validation_sha256": canonical_value_digest(
            {"result-child": child_result["validation"]}
        ),
        "unresolved_escalations": [],
        "next_ready_action": "primary convergence",
        "stop_reason_id": "scope-covered",
        "checkpoint_sha256": "pending",
    }
    checkpoint["checkpoint_sha256"] = canonical_digest(
        checkpoint, "checkpoint_sha256"
    )
    checkpoint_path = root / "evidence/checkpoint.json"
    checkpoint_path.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")

    def node(
        node_id: str,
        *,
        parent: str | None,
        depth: int,
        context_words: int,
        result: dict[str, object] | None,
        result_artifact: dict[str, object] | None,
    ) -> dict[str, object]:
        is_root = depth == 0
        context_evidence = None
        if not is_root:
            context_evidence = write_artifact(
                root,
                f"evidence/{node_id}-context.md",
                ("context " * context_words).strip() + "\n",
            )
        return {
            "node_id": node_id,
            "parent_node_id": parent,
            "packet_id": None if is_root else f"packet-{node_id}",
            "parent_packet_id": None if depth < 2 else "packet-coordinator",
            "result_id": None if is_root else f"result-{node_id}",
            "depth": depth,
            "status": "DONE",
            "role_id": "primary" if is_root else "read-only-auditor",
            "assistant_surface": "primary" if is_root else "test-surface",
            "dispatch_backend": "primary" if is_root else "native-worker",
            "implementation_level": "L1",
            "coverage_key": "root" if is_root else f"source-worker-contract/{node_id}",
            "semantic_scope": (
                "primary-convergence"
                if is_root
                else "source-worker-contract"
                if depth == 1
                else "source-worker-contract/child"
            ),
            "changed_fact_ids": [],
            "canonical_owner_refs": ["tools/source_worker_contract.py"],
            "surface_refs": ["tools/source_worker_contract.py"],
            "relationship_refs": [],
            "allowed_actions": ["inspect"],
            "write_scope": "none",
            "context_evidence": context_evidence,
            "context_words": context_words,
            "max_result_words": 0 if is_root else 100,
            "max_summary_words": 0 if is_root else 50,
            "dispatch_group_id": None if is_root else ("group-1" if depth == 1 else "group-2"),
            "branch_envelope": "evidence/envelope.json" if node_id == "coordinator" else None,
            "branch_envelope_sha256": envelope["envelope_sha256"] if node_id == "coordinator" else None,
            "branch_checkpoint": "evidence/checkpoint.json" if node_id == "coordinator" else None,
            "branch_checkpoint_sha256": checkpoint["checkpoint_sha256"] if node_id == "coordinator" else None,
            "result_evidence": result_artifact,
            "accepted_summary_evidence": None if result is None else result["accepted_summary"],
            "summary_covers_result_ids": [] if result is None else result["summary_covers_result_ids"],
            "satisfied_acceptance_ids": [] if is_root else [f"accept-{node_id}"],
            "produced_evidence_ids": [] if is_root else [f"evidence-{node_id}"],
            "attempt": 0,
            "result_status": None if is_root else "succeeded",
            "stop_reason_id": "evidence-sufficient" if is_root else "scope-covered",
            "child_proposals": [],
            "overlap_decision": "not-applicable" if is_root else "disjoint",
        }

    raw_words = (
        coordinator_result["raw_payload"]["word_count"]
        + child_result["raw_payload"]["word_count"]
    )
    return {
        "schema_version": 2,
        "tree_kind": "alatyr-delegation-execution-tree",
        "operation_id": "op-1",
        "recorded_at": "2026-09-03T12:05:00Z",
        "base_revision": "base-revision",
        "current_user_authorization": {
            "scope": "read-only",
            "allowed_actions": ["read-only"],
            "authorized_phases": ["inspect"],
            "approval_record": None,
        },
        "task_profile": "repository-audit",
        "policy_revision": canonical_value_digest(policy_fixture()),
        "capability_evidence": capability["path"],
        "capability_evidence_sha256": capability["sha256"],
        "aggregate_budget": {
            "max_total_delegates": 8,
            "max_parallel_delegates": 2,
            "max_children_per_parent": 4,
            "max_context_words_total": 24000,
            "max_result_words_total": 12000,
            "max_primary_summary_words_total": 4000,
            "max_retries_total": 2,
            "used_total_delegates": 2,
            "used_parallel_delegates": 1,
            "used_context_words": 30,
            "used_result_words": raw_words,
            "used_primary_summary_words": coordinator_result["accepted_summary"]["word_count"],
            "used_retries": 0,
        },
        "root_node_id": "root",
        "nodes": [
            node("root", parent=None, depth=0, context_words=0, result=None, result_artifact=None),
            node("coordinator", parent="root", depth=1, context_words=10, result=coordinator_result, result_artifact=coordinator_result_artifact),
            node("child", parent="coordinator", depth=2, context_words=20, result=child_result, result_artifact=child_result_artifact),
        ],
        "edges": [
            {"parent_node_id": "root", "child_node_id": "coordinator", "edge_kind": "primary-approved-dispatch"},
            {"parent_node_id": "coordinator", "child_node_id": "child", "edge_kind": "primary-envelope-dispatch"},
        ],
        "primary_convergence": {
            "status": "completed",
            "required_acceptance_ids": ["accept-coordinator", "accept-child"],
            "required_evidence_ids": ["evidence-coordinator", "evidence-child"],
            "reviewed_result_ids": ["result-coordinator"],
            "indirect_result_ids": ["result-child"],
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
            "invalid initial budget": {"max_initial_words": 0},
            "invalid result budget": {"max_result_words": 0},
            "extra field": {"tools": ["shell"]},
            "recursive depth without parent": {"depth": 2},
            "autonomous child": {"child_dispatch_mode": "dispatch"},
            "summary exceeds result": {"max_summary_words": 1601},
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

    def test_packet_rejects_bounded_context_over_budget(self) -> None:
        packet = packet_fixture()
        packet["max_initial_words"] = 1

        with self.assertRaisesRegex(SourceWorkerContractError, "exceeds"):
            self.validate(packet)

    def test_tree_policy_limits_and_stop_reasons_fail_closed(self) -> None:
        cases = {
            "autonomous dispatch": ("tree_policy", "worker_child_behavior", "dispatch"),
            "unbounded recursive source depth": ("tree_policy", "hard_max_depth", 3),
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

    def test_workstream_result_and_summary_use_their_own_aggregate_budgets(self) -> None:
        cases = {
            "result budget": ("max_result_words", 12001),
            "summary budget": ("max_summary_words", 4001),
        }
        for label, (field, value) in cases.items():
            with self.subTest(label=label):
                policy = policy_fixture()
                workstream = policy["workstreams"]["framework-rules"]
                workstream[field] = value
                if field == "max_summary_words":
                    workstream["max_result_words"] = 5000
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
    def validate(self, tree: dict[str, object], root: Path) -> dict[str, object]:
        return validate_delegation_execution_tree(
            tree, policy_fixture(), artifact_root=root
        )

    def rewrite_worker_result(
        self,
        tree: dict[str, object],
        root: Path,
        node_id: str,
        mutate: object,
    ) -> None:
        node = next(item for item in tree["nodes"] if item["node_id"] == node_id)
        result_path = root / node["result_evidence"]["path"]
        result = json.loads(result_path.read_text(encoding="utf-8"))
        mutate(result)
        result["subtree_sha256"] = canonical_digest(result, "subtree_sha256")
        result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        node["result_evidence"] = write_artifact(
            root,
            node["result_evidence"]["path"],
            result_path.read_text(encoding="utf-8"),
        )

    def test_recursive_tree_measures_compacted_primary_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            self.assertEqual(self.validate(tree, root), tree)
            budget = tree["aggregate_budget"]
            self.assertLess(
                budget["used_primary_summary_words"],
                budget["used_result_words"],
            )

    def test_recursive_evidence_matches_shipped_schemas(self) -> None:
        schemas = {
            "tree.json": "alatyr-delegation-execution-tree.schema.json",
            "evidence/envelope.json": "alatyr-delegation-branch-envelope.schema.json",
            "evidence/checkpoint.json": "alatyr-delegation-branch-checkpoint.schema.json",
            "evidence/coordinator-result.json": "alatyr-worker-result.schema.json",
            "evidence/child-result.json": "alatyr-worker-result.schema.json",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            (root / "tree.json").write_text(
                json.dumps(tree, indent=2) + "\n", encoding="utf-8"
            )
            for evidence_path, schema_name in schemas.items():
                record = json.loads((root / evidence_path).read_text(encoding="utf-8"))
                schema = json.loads(
                    (ROOT / "schemas" / schema_name).read_text(encoding="utf-8")
                )
                Draft7Validator(schema).validate(record)

    def test_recursive_tree_rejects_artifact_and_budget_drift(self) -> None:
        cases = {
            "false result words": lambda item: item["aggregate_budget"].update(
                {"used_result_words": 999}
            ),
            "false primary summary words": lambda item: item[
                "aggregate_budget"
            ].update({"used_primary_summary_words": 999}),
            "duplicate packet": lambda item: item["nodes"][2].update(
                {"packet_id": "packet-coordinator"}
            ),
            "wrong parent packet": lambda item: item["nodes"][2].update(
                {"parent_packet_id": None}
            ),
            "unapproved recursive edge": lambda item: item["edges"][1].update(
                {"edge_kind": "primary-approved-dispatch"}
            ),
            "missing indirect result": lambda item: item[
                "primary_convergence"
            ].update({"indirect_result_ids": []}),
            "missing acceptance closure": lambda item: item[
                "primary_convergence"
            ].update({"required_acceptance_ids": ["missing"]}),
            "recursive write": lambda item: item["nodes"][2].update(
                {"allowed_actions": ["inspect", "modify"]}
            ),
            "coverage escape": lambda item: item["nodes"][2].update(
                {"coverage_key": "outside"}
            ),
            "semantic scope escape": lambda item: item["nodes"][2].update(
                {"semantic_scope": "unrelated-scope"}
            ),
            "surface escape": lambda item: item["nodes"][2].update(
                {"surface_refs": ["docs/outside.md"]}
            ),
            "expired branch envelope": lambda item: item.update(
                {"recorded_at": "2100-01-01T00:00:00Z"}
            ),
            "stale capability binding": lambda item: item.update(
                {"capability_evidence_sha256": "1" * 64}
            ),
            "stale policy binding": lambda item: item.update(
                {"policy_revision": "1" * 64}
            ),
            "depth-one source write": lambda item: item["nodes"][1].update(
                {"allowed_actions": ["modify"], "write_scope": "src/**"}
            ),
            "unmeasured context reduction": lambda item: (
                item["nodes"][1].update({"context_words": 0}),
                item["aggregate_budget"].update({"used_context_words": 20}),
            ),
            "schema-invalid overlap decision": lambda item: item["nodes"][1].update(
                {"overlap_decision": "invented-overlap"}
            ),
            "unknown stop reason": lambda item: item["nodes"][2].update(
                {"stop_reason_id": "invented-stop"}
            ),
        }
        for label, mutate in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                tree = recursive_execution_fixture(root)
                mutate(tree)
                with self.assertRaises(SourceWorkerContractError):
                    self.validate(tree, root)

    def test_recursive_tree_rejects_tampered_result_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            (root / "evidence/child-summary.md").write_text(
                "tampered summary\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(SourceWorkerContractError, "SHA-256"):
                self.validate(tree, root)

    def test_recursive_tree_rejects_tampered_capability_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            (root / tree["capability_evidence"]).write_text(
                '{"status":"unavailable"}\n', encoding="utf-8"
            )
            with self.assertRaisesRegex(SourceWorkerContractError, "capability"):
                self.validate(tree, root)

    def test_tree_rejects_topology_and_convergence_drift(self) -> None:
        cases = {
            "branch evidence on leaf": lambda item: item["nodes"][2].update(
                {"branch_envelope": "evidence/envelope.json"}
            ),
            "wrong depth-one edge kind": lambda item: item["edges"][0].update(
                {"edge_kind": "primary-envelope-dispatch"}
            ),
            "unknown convergence status": lambda item: item[
                "primary_convergence"
            ].update({"status": "apparently-finished"}),
            "root convergence mismatch": lambda item: item["nodes"][0].update(
                {"status": "BLOCKED"}
            ),
            "root stop mismatch": lambda item: item["nodes"][0].update(
                {"stop_reason_id": "scope-covered"}
            ),
        }
        for label, mutate in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                tree = recursive_execution_fixture(root)
                mutate(tree)
                with self.assertRaises(SourceWorkerContractError):
                    self.validate(tree, root)

    def test_worker_result_rejects_scope_validation_and_artifact_aliases(self) -> None:
        cases = {
            "surface outside node": lambda result, tree: result.update(
                {"touched_surfaces": ["docs/outside.md"]}
            ),
            "successful result without validation": lambda result, tree: result.update(
                {"validation": []}
            ),
            "reused summary artifact": lambda result, tree: result.update(
                {
                    "accepted_summary": tree["nodes"][2][
                        "accepted_summary_evidence"
                    ]
                }
            ),
        }
        for label, mutate in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                tree = recursive_execution_fixture(root)

                def apply(result: dict[str, object]) -> None:
                    mutate(result, tree)

                self.rewrite_worker_result(tree, root, "coordinator", apply)
                if label == "reused summary artifact":
                    tree["nodes"][1]["accepted_summary_evidence"] = tree[
                        "nodes"
                    ][2]["accepted_summary_evidence"]
                with self.assertRaises(SourceWorkerContractError):
                    self.validate(tree, root)

    def test_recursive_worker_tools_stay_inside_branch_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            self.rewrite_worker_result(
                tree,
                root,
                "child",
                lambda result: result.update({"tools_used": ["shell"]}),
            )
            with self.assertRaisesRegex(SourceWorkerContractError, "tool outside"):
                self.validate(tree, root)

    def test_completed_convergence_rejects_unfinished_worker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            coordinator = tree["nodes"][1]
            tree["nodes"] = tree["nodes"][:2]
            tree["edges"] = tree["edges"][:1]
            for field in [
                "branch_envelope", "branch_envelope_sha256",
                "branch_checkpoint", "branch_checkpoint_sha256",
                "result_evidence", "accepted_summary_evidence",
            ]:
                coordinator[field] = None
            coordinator.update(
                {
                    "status": "RUNNING",
                    "result_status": None,
                    "stop_reason_id": None,
                    "summary_covers_result_ids": [],
                    "satisfied_acceptance_ids": [],
                    "produced_evidence_ids": [],
                }
            )
            tree["aggregate_budget"].update(
                {
                    "used_total_delegates": 1,
                    "used_context_words": coordinator["context_words"],
                    "used_result_words": 0,
                    "used_primary_summary_words": 0,
                }
            )
            tree["primary_convergence"].update(
                {
                    "required_acceptance_ids": [],
                    "required_evidence_ids": [],
                    "indirect_result_ids": [],
                }
            )
            with self.assertRaisesRegex(SourceWorkerContractError, "unfinished"):
                self.validate(tree, root)

    def test_branch_checkpoint_rejects_invalid_history_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            checkpoint_path = root / tree["nodes"][1]["branch_checkpoint"]
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            checkpoint["previous_checkpoint_id"] = []
            checkpoint_path.write_text(
                json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8"
            )
            with self.assertRaises(SourceWorkerContractError):
                self.validate(tree, root)

    def test_recursive_tree_rejects_malformed_resolved_policy_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            policy = policy_fixture()
            policy["context_compaction"]["max_result_words_total"] = "unresolved"
            with self.assertRaises(SourceWorkerContractError):
                validate_delegation_execution_tree(
                    tree, policy, artifact_root=root
                )

    def test_recursive_tree_requires_policy_authorized_child_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            policy = policy_fixture()
            policy["tree_policy"]["worker_child_behavior"] = "propose-only"
            tree["policy_revision"] = canonical_value_digest(policy)
            with self.assertRaisesRegex(DelegationEvidenceError, "does not authorize"):
                validate_execution_tree(
                    tree, policy, artifact_root=root
                )

    def test_schema_one_tree_is_legacy_not_acceptance_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            tree["schema_version"] = 1
            with self.assertRaisesRegex(SourceWorkerContractError, "identity"):
                self.validate(tree, root)

    def test_portable_cli_accepts_valid_evidence_and_rejects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = recursive_execution_fixture(root)
            policy_path = root / "policy.json"
            tree_path = root / "tree.json"
            policy_path.write_text(
                json.dumps(policy_fixture(), indent=2) + "\n", encoding="utf-8"
            )
            tree_path.write_text(json.dumps(tree, indent=2) + "\n", encoding="utf-8")
            command = [
                sys.executable,
                str(ROOT / "tools" / "validate_delegation_execution_tree.py"),
                "--target-root",
                str(root),
                "--policy",
                str(policy_path),
                "--tree",
                str(tree_path),
                "--artifact-root",
                str(root),
            ]
            completed = subprocess.run(
                command, check=False, capture_output=True, text=True
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            (root / "evidence/child-summary.md").write_text(
                "tampered summary\n", encoding="utf-8"
            )
            completed = subprocess.run(
                command, check=False, capture_output=True, text=True
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("SHA-256", completed.stderr)


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
