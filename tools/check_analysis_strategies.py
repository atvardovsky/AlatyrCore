#!/usr/bin/env python3
"""Validate source analysis-strategy and problem-model contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from analysis_strategy_contract import (
    PRIMARY_STRATEGY_IDS,
    build_active_problem_model_projection,
    load_json_object,
    required_obligations_resolved,
    required_reviews_passed,
    validate_active_problem_model_projection,
    validate_problem_model,
    validate_problem_model_projection_schema,
    validate_problem_model_schema,
    validate_strategy_catalog,
    validate_strategy_requirements,
)


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
SCHEMA_PATH = ROOT / "schemas" / "alatyr-problem-model.schema.json"
PROJECTION_SCHEMA_PATH = (
    ROOT / "schemas" / "alatyr-problem-model-active-projection.schema.json"
)


def sample_model(strategy_id: str) -> dict[str, object]:
    return {
        "schema_version": 2,
        "model_kind": "alatyr-bounded-problem-model",
        "model_id": f"fixture-{strategy_id}",
        "operation_id": "fixture-operation",
        "active_projection": {
            "schema_version": 1,
            "path": f".ai/.runtime/problem-model-projections/fixture-{strategy_id}.json",
        },
        "primary_strategy_id": strategy_id,
        "risk_classes": [],
        "protected_change": False,
        "required_review_ids": [],
        "review_results": [],
        "objective": "verify bounded analysis",
        "repository_binding": {
            "state": "available",
            "branch": "fixture",
            "base_revision": "fixture-revision",
        },
        "task_binding": {"task_ids": ["fixture-task"], "workstream_ids": []},
        "predecessor": {"state": "none", "model_id": "none", "sha256": "none"},
        "strategy_transitions": [],
        "non_goals": [],
        "facts": [{"id": "fact-1", "statement": "observed fixture", "evidence_refs": ["fixture:evidence"]}],
        "assumptions": [],
        "unknowns": [{"id": "unknown-1", "statement": "fixture uncertainty"}],
        "changed_facts": [{"id": "change-1", "statement": "fixture changes", "owner_ref": "fixture:owner", "evidence_refs": ["fixture:evidence"]}],
        "invariants": [{"id": "invariant-1", "statement": "fixture remains valid", "owner_ref": "fixture:owner", "evidence_refs": ["fixture:evidence"], "status": "preserved"}],
        "hypotheses": [{"id": "hypothesis-1", "statement": "fixture explanation", "evidence_refs": ["fixture:evidence"], "status": "supported"}],
        "alternatives": [
            {"id": "alternative-1", "statement": "first option", "evidence_refs": ["fixture:evidence"], "status": "selected"},
            {"id": "alternative-2", "statement": "second option", "evidence_refs": ["fixture:evidence"], "status": "rejected"},
        ],
        "proof_obligations": [
            {
                "id": "proof-1",
                "statement": "the selected contract is satisfied",
                "evidence_owner": "primary",
                "acceptance_owner": "primary",
                "required": True,
                "status": "passed",
                "evidence_refs": ["fixture:evidence"],
                "waiver": None,
            }
        ],
        "counterexamples": [],
        "unresolved_decisions": [],
        "evidence_refs": ["fixture:evidence"],
    }


def main() -> int:
    failures: list[str] = []
    try:
        schema = load_json_object(SCHEMA_PATH)
        projection_schema = load_json_object(PROJECTION_SCHEMA_PATH)
        failures.extend(validate_problem_model_schema(schema))
        failures.extend(
            validate_problem_model_projection_schema(projection_schema)
        )
        failures.extend(validate_strategy_catalog(TARGET))
        catalog = load_json_object(TARGET / ".ai/assistant/analysis-strategies/index.json")
        descriptors = catalog.get("descriptors", {})
        for strategy_id in PRIMARY_STRATEGY_IDS:
            model = sample_model(strategy_id)
            failures.extend(validate_problem_model(model, schema))
            descriptor = None
            if strategy_id != "direct-local" and isinstance(descriptors, dict):
                descriptor_path = descriptors.get(strategy_id)
                if isinstance(descriptor_path, str):
                    descriptor = load_json_object(TARGET / descriptor_path)
            failures.extend(validate_strategy_requirements(model, descriptor))

        projected_model = sample_model("invariant-first")
        projection = build_active_problem_model_projection(
            projected_model,
            source_path=".ai/.runtime/problem-models/fixture-invariant-first.json",
            source_sha256="0" * 64,
        )
        failures.extend(
            validate_active_problem_model_projection(
                projection,
                projection_schema,
                expected=projection,
            )
        )
        projection_payload = projection.get("payload")
        if not isinstance(projection_payload, dict) or projection_payload.get(
            "changed_facts"
        ) != projected_model.get("changed_facts"):
            failures.append("active projection omitted the current changed facts")
        if not isinstance(projection_payload, dict) or projection_payload.get(
            "non_goals"
        ) != projected_model.get("non_goals"):
            failures.append("active projection omitted the current non-goals")

        transitioned = sample_model("invariant-first")
        transitioned["assumptions"] = [
            {
                "id": "assumption-1",
                "statement": "fixture assumption",
                "evidence_refs": ["fixture:evidence"],
                "status": "active",
            }
        ]
        transitioned["strategy_transitions"] = [
            {
                "from": "hypothesis-driven",
                "to": "invariant-first",
                "reason": "new evidence changed the analysis method",
                "evidence_refs": ["fixture:evidence"],
                "invalidated_assumption_ids": ["assumption-1"],
                "reopened_obligation_ids": ["proof-1"],
            }
        ]
        transitioned_obligations = transitioned["proof_obligations"]
        assert isinstance(transitioned_obligations, list)
        assert isinstance(transitioned_obligations[0], dict)
        transitioned_obligations[0]["status"] = "open"
        transitioned_obligations[0]["evidence_refs"] = []
        failures.extend(validate_problem_model(transitioned, schema))
        transitioned_obligations[0]["status"] = "passed"
        transitioned_obligations[0]["evidence_refs"] = ["fixture:resolved"]
        failures.extend(validate_problem_model(transitioned, schema))
        if not required_obligations_resolved(transitioned):
            failures.append("resolved historically reopened obligation stayed blocked")

        unknown_transition = sample_model("invariant-first")
        unknown_transition["strategy_transitions"] = [
            {
                "from": "hypothesis-driven",
                "to": "invariant-first",
                "reason": "invalid fixture reference",
                "evidence_refs": ["fixture:evidence"],
                "invalidated_assumption_ids": [],
                "reopened_obligation_ids": ["missing-proof"],
            }
        ]
        if not any(
            "unknown obligation" in failure
            for failure in validate_problem_model(unknown_transition, schema)
        ):
            failures.append("unknown transitioned obligation was accepted")

        oversized = sample_model("invariant-first")
        oversized["objective"] = "word " * 20000
        if not validate_problem_model(oversized, schema):
            failures.append("oversized problem model was accepted")

        oversized_active_state = sample_model("invariant-first")
        oversized_active_state["unknowns"] = [
            {
                "id": f"unknown-{index}",
                "statement": "word " * 100,
            }
            for index in range(20)
        ]
        if not any(
            "active state exceeds" in failure
            for failure in validate_problem_model(oversized_active_state, schema)
        ):
            failures.append("oversized active projection state was accepted")

        private_reasoning = sample_model("evidence-synthesis")
        private_reasoning["chain_of_thought"] = "must never be persisted"
        if not any(
            "private-reasoning" in failure
            for failure in validate_problem_model(private_reasoning, schema)
        ):
            failures.append("problem-model validation did not reject private reasoning")

        open_obligation = sample_model("invariant-first")
        obligations = open_obligation["proof_obligations"]
        assert isinstance(obligations, list) and isinstance(obligations[0], dict)
        obligations[0]["status"] = "open"
        obligations[0]["evidence_refs"] = []
        if required_obligations_resolved(open_obligation):
            failures.append("open required obligation was accepted as resolved")

        protected = sample_model("invariant-first")
        protected["required_review_ids"] = ["adversarial-review"]
        protected["review_results"] = [
            {"id": "adversarial-review", "status": "pending", "evidence_refs": []}
        ]
        if required_reviews_passed(protected):
            failures.append("pending adversarial review was accepted as passed")

        unauthorized_waiver = sample_model("invariant-first")
        waived = unauthorized_waiver["proof_obligations"]
        assert isinstance(waived, list) and isinstance(waived[0], dict)
        waived[0]["status"] = "waived"
        waived[0]["evidence_refs"] = []
        waived[0]["waiver"] = {
            "decision_owner": "worker",
            "authority_ref": "none",
            "evidence_refs": [],
        }
        if not validate_problem_model(unauthorized_waiver, schema):
            failures.append("waived obligation without authority was accepted")

        missing_review = sample_model("invariant-first")
        missing_review["protected_change"] = True
        if not any(
            "requires adversarial-review" in failure
            for failure in validate_problem_model(missing_review, schema)
        ):
            failures.append("protected work without adversarial review was accepted")

        high_impact = sample_model("invariant-first")
        high_impact["protected_change"] = False
        high_impact["risk_classes"] = ["high-impact"]
        if not any(
            "requires adversarial-review" in failure
            for failure in validate_problem_model(high_impact, schema)
        ):
            failures.append("high-impact work without adversarial review was accepted")

        policy = load_json_object(TARGET / ".ai/assistant/task-decomposition.json")
        strategy = policy.get("analysis_strategy")
        if policy.get("schema_version") != 2 or not isinstance(strategy, dict):
            failures.append("task-decomposition policy does not expose analysis strategy v2")
        elif strategy.get("debug_mode_activation") != "never automatic":
            failures.append("analysis strategy selection must not enable Debug Mode")
        gate_index = load_json_object(TARGET / ".ai/assistant/gates/index.json")
        gate = gate_index.get("gates", {}).get("analysis-strategy")
        if not isinstance(gate, dict) or gate.get("path") != (
            ".ai/assistant/gates/analysis-strategy.md"
        ):
            failures.append("analysis-strategy gate is absent from the gate index")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: analysis strategies, problem models, obligations, and context cost")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
