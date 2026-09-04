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
        "schema_version": 1,
        "packet_kind": "source-read-only-workstream",
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
        "expected_evidence": "Path-specific findings",
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
        }
        for label, updates in cases.items():
            with self.subTest(label=label):
                packet = packet_fixture()
                packet.update(updates)
                with self.assertRaises(SourceWorkerContractError):
                    self.validate(packet)

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
