"""Shared validation for bounded analysis strategies and problem models."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

import jsonschema


PRIMARY_STRATEGY_IDS = (
    "direct-local",
    "invariant-first",
    "hypothesis-driven",
    "architecture-comparison",
    "evidence-synthesis",
    "exploratory-design",
)
REVIEW_STRATEGY_IDS = ("adversarial-review",)
DESCRIPTOR_FIELDS = {
    "schema_version",
    "strategy_kind",
    "id",
    "use_when",
    "sequence",
    "required_nonempty_fields",
    "completion_rule",
}
PROBLEM_MODEL_SCHEMA_ID = "alatyr-problem-model-v3"
PROBLEM_MODEL_PROJECTION_SCHEMA_ID = "alatyr-problem-model-active-projection-v2"
STRATEGY_INDEX_RELPATH = ".ai/assistant/analysis-strategies/index.json"
PROBLEM_MODEL_TEMPLATE_RELPATH = ".ai/assistant/templates/problem-model.json"
PROBLEM_MODEL_PROJECTION_TEMPLATE_RELPATH = (
    ".ai/assistant/templates/problem-model-active-projection.json"
)
PROBLEM_MODEL_RUNTIME_PREFIX = ".ai/.runtime/problem-models/"
PROBLEM_MODEL_PROJECTION_RUNTIME_PREFIX = (
    ".ai/.runtime/problem-model-projections/"
)
MAX_INITIAL_STRATEGY_WORDS = 400
MAX_PROBLEM_MODEL_UTF8_BYTES = 65536
MAX_PROBLEM_MODEL_WORDS = 6000
MAX_PROBLEM_MODEL_FILE_BYTES = 131072
MAX_ACTIVE_PROJECTION_UTF8_BYTES = 16384
MAX_ACTIVE_PROJECTION_WORDS = 1200
REQUIRED_LIFECYCLE_OUTCOMES = frozenset(
    {"success", "rejection", "deferral", "expiry", "recovery", "failure"}
)
REQUIRED_LIFECYCLE_BOUNDARIES = frozenset(
    {"producer", "orchestrator", "persistence", "consumer"}
)
SYSTEMIC_INCIDENT_TRIGGERS = frozenset(
    {"escaped-defect", "failed-required-gate", "recurring-correction"}
)
MAX_ACTIVE_PROJECTION_FILE_BYTES = 65536
FORBIDDEN_REASONING_KEYS = {
    "chain_of_thought",
    "chain-of-thought",
    "private_reasoning",
    "hidden_reasoning",
    "internal_monologue",
    "scratchpad",
}


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def word_count(path: Path) -> int:
    return len(re.findall(r"\S+", path.read_text(encoding="utf-8")))


def canonical_utf8_size(value: Any) -> int:
    return len(
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def structured_word_count(value: Any) -> int:
    if isinstance(value, str):
        return len(re.findall(r"\S+", value))
    if isinstance(value, dict):
        return sum(structured_word_count(item) for item in value.values())
    if isinstance(value, list):
        return sum(structured_word_count(item) for item in value)
    return 0


def validate_problem_model_schema(schema: dict[str, Any]) -> list[str]:
    try:
        jsonschema.Draft7Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        return [f"problem-model schema is invalid: {exc.message}"]
    return []


def validate_problem_model_projection_schema(schema: dict[str, Any]) -> list[str]:
    try:
        jsonschema.Draft7Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        return [f"active problem-model projection schema is invalid: {exc.message}"]
    return []


def _validate_incident_continuity(model: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    incident = model.get("incident")
    lifecycle = model.get("lifecycle_model")
    if not isinstance(incident, dict) or not isinstance(lifecycle, dict):
        return failures

    mode = incident.get("mode")
    family_id = incident.get("family_id")
    trigger = incident.get("trigger")
    iteration = incident.get("corrective_iteration")
    predecessor_models = incident.get("predecessor_model_ids", [])
    predecessor_packages = incident.get("predecessor_package_ids", [])
    failed_gate = incident.get("latest_failed_gate")

    if mode == "none":
        if family_id != "none" or trigger != "none" or iteration != 0:
            failures.append(
                "non-incident problem models require family_id=none, trigger=none, and corrective_iteration=0"
            )
        if predecessor_models or predecessor_packages:
            failures.append("non-incident problem models cannot declare predecessors")
    else:
        if family_id in {None, "", "none"}:
            failures.append("incident problem models require a stable family_id")
        if trigger == "none":
            failures.append("incident problem models require a concrete trigger")

    if mode in {"continuation", "systemic-repair"}:
        if not isinstance(iteration, int) or isinstance(iteration, bool) or iteration < 1:
            failures.append("continued incident work requires corrective_iteration >= 1")
        if not predecessor_models and not predecessor_packages:
            failures.append("continued incident work requires predecessor lineage")
    if isinstance(iteration, int) and not isinstance(iteration, bool) and iteration >= 2:
        if mode != "systemic-repair":
            failures.append(
                "the second corrective iteration and later require systemic-repair mode"
            )
        if trigger != "recurring-correction":
            failures.append(
                "the second corrective iteration and later require recurring-correction trigger"
            )
    if trigger == "recurring-correction" and mode != "systemic-repair":
        failures.append("recurring-correction requires systemic-repair mode")

    gate_state = failed_gate.get("state") if isinstance(failed_gate, dict) else None
    gate_id = failed_gate.get("id") if isinstance(failed_gate, dict) else None
    gate_evidence = (
        failed_gate.get("evidence_refs", []) if isinstance(failed_gate, dict) else []
    )
    if gate_state == "none" and (gate_id != "none" or gate_evidence):
        failures.append("latest_failed_gate state none cannot carry identity or evidence")
    if gate_state in {"open", "resolved"} and (
        gate_id in {None, "", "none"} or not gate_evidence
    ):
        failures.append("an open or resolved failed gate requires identity and evidence")

    lifecycle_required = lifecycle.get("required") is True
    if mode == "systemic-repair" or trigger in SYSTEMIC_INCIDENT_TRIGGERS:
        if not lifecycle_required:
            failures.append(
                "systemic, escaped, recurring, or failed-gate work requires a lifecycle model"
            )
    if lifecycle_required:
        outcomes = set(lifecycle.get("required_outcomes", []))
        if outcomes != REQUIRED_LIFECYCLE_OUTCOMES:
            failures.append(
                "required lifecycle model must cover success, rejection, deferral, expiry, recovery, and failure"
            )
        states = lifecycle.get("states", [])
        transitions = lifecycle.get("transitions", [])
        boundaries = lifecycle.get("boundaries", [])
        conservation_rules = lifecycle.get("conservation_rules", [])
        if not states or not transitions or not conservation_rules:
            failures.append(
                "required lifecycle model needs states, transitions, and conservation rules"
            )
        boundary_kinds = {
            item.get("kind") for item in boundaries if isinstance(item, dict)
        }
        missing_boundaries = sorted(REQUIRED_LIFECYCLE_BOUNDARIES - boundary_kinds)
        if missing_boundaries:
            failures.append(
                "required lifecycle model is missing boundaries: "
                + ", ".join(missing_boundaries)
            )
        state_ids = {
            item.get("id") for item in states if isinstance(item, dict)
        }
        for transition in transitions:
            if not isinstance(transition, dict):
                continue
            if transition.get("from") not in state_ids or transition.get("to") not in state_ids:
                failures.append(
                    f"lifecycle transition {transition.get('id')!r} references an unknown state"
                )
            if not transition.get("evidence_refs"):
                failures.append(
                    f"lifecycle transition {transition.get('id')!r} requires evidence"
                )
        for boundary in boundaries:
            if isinstance(boundary, dict) and not boundary.get("evidence_refs"):
                failures.append(
                    f"lifecycle boundary {boundary.get('id')!r} requires evidence"
                )
        for rule in conservation_rules:
            if isinstance(rule, dict) and not rule.get("evidence_refs"):
                failures.append(
                    f"lifecycle conservation rule {rule.get('id')!r} requires evidence"
                )

    if gate_state == "open":
        obligations = model.get("proof_obligations", [])
        unresolved = [
            item
            for item in obligations
            if isinstance(item, dict)
            and item.get("required") is True
            and item.get("status") in {"open", "failed", "blocked"}
            and (
                item.get("id") == gate_id
                or gate_id in item.get("evidence_refs", [])
                or any(ref in item.get("evidence_refs", []) for ref in gate_evidence)
            )
        ]
        if not unresolved:
            failures.append(
                "open latest_failed_gate must remain a required unresolved proof obligation"
            )
        if not model.get("counterexamples"):
            failures.append("open latest_failed_gate requires a retained counterexample")
    return failures


def validate_problem_model(
    model: dict[str, Any], schema: dict[str, Any]
) -> list[str]:
    failures = [
        f"problem model {'.'.join(str(part) for part in error.absolute_path) or 'root'}: {error.message}"
        for error in sorted(
            jsonschema.Draft7Validator(schema).iter_errors(model),
            key=lambda item: list(item.absolute_path),
        )
    ]
    model_bytes = canonical_utf8_size(model)
    model_words = structured_word_count(model)
    if model_bytes > MAX_PROBLEM_MODEL_UTF8_BYTES:
        failures.append(
            "problem model exceeds "
            f"{MAX_PROBLEM_MODEL_UTF8_BYTES} canonical UTF-8 bytes"
        )
    if model_words > MAX_PROBLEM_MODEL_WORDS:
        failures.append(f"problem model exceeds {MAX_PROBLEM_MODEL_WORDS} words")
    failures.extend(_forbidden_reasoning_failures(model))
    projection_ref = model.get("active_projection")
    model_id = model.get("model_id")
    if isinstance(projection_ref, dict) and isinstance(model_id, str):
        expected_projection_path = (
            f"{PROBLEM_MODEL_PROJECTION_RUNTIME_PREFIX}{model_id}.json"
        )
        if projection_ref.get("path") != expected_projection_path:
            failures.append(
                "problem model active projection path must match model_id"
            )
        active_projection = build_active_problem_model_projection(
            model,
            source_path=f"{PROBLEM_MODEL_RUNTIME_PREFIX}{model_id}.json",
            source_sha256="0" * 64,
        )
        measurements = active_projection["measurements"]
        if measurements["payload_utf8_bytes"] > MAX_ACTIVE_PROJECTION_UTF8_BYTES:
            failures.append(
                "problem model active state exceeds "
                f"{MAX_ACTIVE_PROJECTION_UTF8_BYTES} projection payload bytes"
            )
        if measurements["payload_words"] > MAX_ACTIVE_PROJECTION_WORDS:
            failures.append(
                "problem model active state exceeds "
                f"{MAX_ACTIVE_PROJECTION_WORDS} projection words"
            )
    task_binding = model.get("task_binding")
    if isinstance(task_binding, dict) and not task_binding.get(
        "task_ids"
    ) and not task_binding.get("workstream_ids"):
        failures.append("problem model must bind at least one task or workstream")
    failures.extend(_validate_incident_continuity(model))

    statement_ids: list[str] = []
    for collection in (
        "facts",
        "assumptions",
        "unknowns",
        "changed_facts",
        "invariants",
        "hypotheses",
        "alternatives",
        "counterexamples",
    ):
        for item in model.get(collection, []):
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            if isinstance(item_id, str):
                statement_ids.append(item_id)
            status = item.get("status")
            conclusive = (
                collection in {"facts", "changed_facts", "counterexamples"}
                or status
                in {
                    "preserved",
                    "violated",
                    "supported",
                    "rejected",
                    "selected",
                }
            )
            if conclusive and not item.get("evidence_refs"):
                failures.append(
                    f"conclusive {collection} item {item_id!r} requires evidence"
                )
    duplicate_statements = sorted(
        {item for item in statement_ids if statement_ids.count(item) > 1}
    )
    if duplicate_statements:
        failures.append(f"duplicate problem statement IDs: {duplicate_statements}")

    obligation_ids: list[str] = []
    for obligation in model.get("proof_obligations", []):
        if not isinstance(obligation, dict):
            continue
        obligation_id = obligation.get("id")
        if isinstance(obligation_id, str):
            obligation_ids.append(obligation_id)
        status = obligation.get("status")
        evidence = obligation.get("evidence_refs")
        if status == "passed" and not evidence:
            failures.append(f"passed obligation {obligation_id!r} requires evidence")
        waiver = obligation.get("waiver")
        if status == "waived" and not isinstance(waiver, dict):
            failures.append(
                f"waived obligation {obligation_id!r} requires authority evidence"
            )
        if status == "waived" and isinstance(waiver, dict) and (
            waiver.get("decision_owner") != "primary-assistant"
            or str(waiver.get("authority_ref", "")).casefold()
            in {"", "none", "unknown", "unavailable", "not-applicable"}
            or not waiver.get("evidence_refs")
        ):
            failures.append(
                f"waived obligation {obligation_id!r} requires primary target-authority evidence"
            )
        if status != "waived" and waiver is not None:
            failures.append(
                f"non-waived obligation {obligation_id!r} must not carry waiver evidence"
            )
    duplicates = sorted({item for item in obligation_ids if obligation_ids.count(item) > 1})
    if duplicates:
        failures.append(f"duplicate proof obligation IDs: {duplicates}")
    required_reviews = model.get("required_review_ids", [])
    review_results = model.get("review_results", [])
    result_ids = [
        item.get("id")
        for item in review_results
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    if len(result_ids) != len(set(result_ids)):
        failures.append("duplicate analysis review result IDs")
    for review_id in required_reviews:
        matches = [item for item in review_results if isinstance(item, dict) and item.get("id") == review_id]
        if len(matches) != 1:
            failures.append(f"required review {review_id!r} needs exactly one result")
        elif matches[0].get("status") == "passed" and not matches[0].get("evidence_refs"):
            failures.append(f"passed review {review_id!r} requires evidence")
    protected_risks = {
        "security",
        "protected",
        "destructive",
        "public-contract",
        "approval-sensitive",
        "live-external",
        "high-impact",
    }
    if (
        model.get("protected_change") is True
        or protected_risks.intersection(model.get("risk_classes", []))
    ) and "adversarial-review" not in required_reviews:
        failures.append("protected or high-impact work requires adversarial-review")
    transitions = model.get("strategy_transitions", [])
    previous_to: str | None = None
    assumption_ids = {
        item.get("id")
        for item in model.get("assumptions", [])
        if isinstance(item, dict)
    }
    known_obligations = {
        item.get("id")
        for item in model.get("proof_obligations", [])
        if isinstance(item, dict)
    }
    for transition in transitions:
        if not isinstance(transition, dict):
            continue
        if previous_to is not None and transition.get("from") != previous_to:
            failures.append("analysis strategy transitions must form one ordered chain")
        if transition.get("from") == transition.get("to"):
            failures.append("analysis strategy transition must change strategy")
        if not transition.get("invalidated_assumption_ids") and not transition.get(
            "reopened_obligation_ids"
        ):
            failures.append(
                "analysis strategy transition must invalidate an assumption or reopen an obligation"
            )
        if not transition.get("evidence_refs"):
            failures.append("analysis strategy transition requires evidence")
        if not set(transition.get("invalidated_assumption_ids", [])) <= (
            assumption_ids
        ):
            failures.append(
                "analysis strategy transition references an unknown assumption"
            )
        if not set(transition.get("reopened_obligation_ids", [])) <= (
            known_obligations
        ):
            failures.append(
                "analysis strategy transition references an unknown obligation"
            )
        previous_to = transition.get("to")
    if transitions and isinstance(transitions[-1], dict) and transitions[-1].get(
        "to"
    ) != model.get("primary_strategy_id"):
        failures.append("latest strategy transition must end at primary_strategy_id")
    return failures


def build_active_problem_model_projection(
    model: dict[str, Any], *, source_path: str, source_sha256: str
) -> dict[str, Any]:
    required_reviews = set(model.get("required_review_ids", []))
    review_results = {
        item.get("id"): item
        for item in model.get("review_results", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    review_projection = [
        {
            "id": review_id,
            "status": review_results.get(review_id, {}).get("status", "missing"),
            "evidence_refs": review_results.get(review_id, {}).get(
                "evidence_refs", []
            ),
        }
        for review_id in sorted(required_reviews)
    ]
    obligations = [
        item
        for item in model.get("proof_obligations", [])
        if isinstance(item, dict)
        and (
            item.get("required") is True
            or item.get("status") in {"open", "failed", "blocked"}
        )
    ]
    transitions = [
        item for item in model.get("strategy_transitions", []) if isinstance(item, dict)
    ]
    payload = {
        "objective": model.get("objective"),
        "non_goals": model.get("non_goals", []),
        "repository_binding": model.get("repository_binding"),
        "task_binding": model.get("task_binding"),
        "incident": model.get("incident"),
        "lifecycle_model": model.get("lifecycle_model"),
        "primary_strategy_id": model.get("primary_strategy_id"),
        "risk_classes": model.get("risk_classes", []),
        "protected_change": model.get("protected_change"),
        "facts": model.get("facts", []),
        "changed_facts": model.get("changed_facts", []),
        "active_assumptions": [
            item
            for item in model.get("assumptions", [])
            if isinstance(item, dict) and item.get("status") == "active"
        ],
        "invalidated_assumption_ids": sorted(
            item["id"]
            for item in model.get("assumptions", [])
            if isinstance(item, dict)
            and item.get("status") == "invalidated"
            and isinstance(item.get("id"), str)
        ),
        "unknowns": model.get("unknowns", []),
        "active_invariants": [
            item
            for item in model.get("invariants", [])
            if isinstance(item, dict)
            and item.get("status") in {"required", "violated", "unresolved"}
        ],
        "current_hypotheses": [
            item
            for item in model.get("hypotheses", [])
            if isinstance(item, dict) and item.get("status") != "rejected"
        ],
        "current_alternatives": [
            item
            for item in model.get("alternatives", [])
            if isinstance(item, dict) and item.get("status") != "rejected"
        ],
        "counterexamples": model.get("counterexamples", []),
        "required_reviews": review_projection,
        "proof_obligations": obligations,
        "unresolved_decisions": model.get("unresolved_decisions", []),
        "latest_transition": transitions[-1] if transitions else None,
        "evidence_refs": model.get("evidence_refs", []),
        "omitted_history_counts": {
            "rejected_hypotheses": len(
                [
                    item
                    for item in model.get("hypotheses", [])
                    if isinstance(item, dict) and item.get("status") == "rejected"
                ]
            ),
            "rejected_alternatives": len(
                [
                    item
                    for item in model.get("alternatives", [])
                    if isinstance(item, dict) and item.get("status") == "rejected"
                ]
            ),
            "invalidated_assumptions": len(model.get("assumptions", []))
            - len(
                [
                    item
                    for item in model.get("assumptions", [])
                    if isinstance(item, dict) and item.get("status") == "active"
                ]
            ),
            "preserved_invariants": len(model.get("invariants", []))
            - len(
                [
                    item
                    for item in model.get("invariants", [])
                    if isinstance(item, dict)
                    and item.get("status")
                    in {"required", "violated", "unresolved"}
                ]
            ),
            "previous_transitions": max(0, len(transitions) - 1),
        },
    }
    return {
        "schema_version": 2,
        "projection_kind": "alatyr-active-problem-model",
        "model_id": model.get("model_id"),
        "operation_id": model.get("operation_id"),
        "source_model": {
            "path": source_path,
            "sha256": source_sha256,
        },
        "limits": {
            "max_payload_utf8_bytes": MAX_ACTIVE_PROJECTION_UTF8_BYTES,
            "max_payload_words": MAX_ACTIVE_PROJECTION_WORDS,
        },
        "payload": payload,
        "measurements": {
            "payload_utf8_bytes": canonical_utf8_size(payload),
            "payload_words": structured_word_count(payload),
        },
    }


def validate_active_problem_model_projection(
    projection: dict[str, Any],
    schema: dict[str, Any],
    *,
    expected: dict[str, Any],
) -> list[str]:
    failures = [
        f"active problem-model projection {'.'.join(str(part) for part in error.absolute_path) or 'root'}: {error.message}"
        for error in sorted(
            jsonschema.Draft7Validator(schema).iter_errors(projection),
            key=lambda item: list(item.absolute_path),
        )
    ]
    payload = projection.get("payload")
    if isinstance(payload, dict):
        payload_bytes = canonical_utf8_size(payload)
        payload_words = structured_word_count(payload)
        if payload_bytes > MAX_ACTIVE_PROJECTION_UTF8_BYTES:
            failures.append(
                "active problem-model projection exceeds "
                f"{MAX_ACTIVE_PROJECTION_UTF8_BYTES} payload UTF-8 bytes"
            )
        if payload_words > MAX_ACTIVE_PROJECTION_WORDS:
            failures.append(
                "active problem-model projection exceeds "
                f"{MAX_ACTIVE_PROJECTION_WORDS} payload words"
            )
    if projection != expected:
        failures.append("active problem-model projection differs from current model")
    return failures


def validate_strategy_requirements(
    model: dict[str, Any], descriptor: dict[str, Any] | None
) -> list[str]:
    if model.get("primary_strategy_id") == "direct-local":
        return []
    if not isinstance(descriptor, dict):
        return ["selected non-local strategy descriptor is unavailable"]
    failures: list[str] = []
    for field in descriptor.get("required_nonempty_fields", []):
        if not model.get(field):
            failures.append(
                f"strategy {descriptor.get('id')!r} requires non-empty {field}"
            )
    if descriptor.get("id") == "architecture-comparison" and len(
        model.get("alternatives", [])
    ) < 2:
        failures.append("architecture-comparison requires at least two alternatives")
    return failures


def validate_strategy_catalog(
    adapter_root: Path,
    *,
    object_loader: Callable[[Path], dict[str, Any]] | None = None,
    count_words: Callable[[Path], int] | None = None,
) -> list[str]:
    failures: list[str] = []
    load_object = object_loader or load_json_object
    count = count_words or word_count
    index_path = adapter_root / STRATEGY_INDEX_RELPATH
    try:
        index = load_object(index_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)]

    if index.get("schema_version") != 2:
        failures.append("analysis strategy catalog schema_version must be 2")
    if index.get("catalog_kind") != "target-analysis-strategy-catalog":
        failures.append("analysis strategy catalog kind is invalid")
    if index.get("problem_model_schema") != PROBLEM_MODEL_SCHEMA_ID:
        failures.append("analysis strategy catalog problem-model schema is invalid")
    if index.get("problem_model_template") != PROBLEM_MODEL_TEMPLATE_RELPATH:
        failures.append("analysis strategy catalog problem-model template is invalid")
    if index.get("active_projection_schema") != PROBLEM_MODEL_PROJECTION_SCHEMA_ID:
        failures.append("analysis strategy catalog active-projection schema is invalid")
    if index.get("active_projection_template") != (
        PROBLEM_MODEL_PROJECTION_TEMPLATE_RELPATH
    ):
        failures.append("analysis strategy catalog active-projection template is invalid")
    expected_limits = {
        "max_utf8_bytes": MAX_PROBLEM_MODEL_UTF8_BYTES,
        "max_words": MAX_PROBLEM_MODEL_WORDS,
        "max_active_projection_utf8_bytes": MAX_ACTIVE_PROJECTION_UTF8_BYTES,
        "max_active_projection_words": MAX_ACTIVE_PROJECTION_WORDS,
    }
    if index.get("problem_model_limits") != expected_limits:
        failures.append("analysis strategy catalog problem-model limits are invalid")
    if index.get("load_mode") != "index-plus-one-selected-descriptor":
        failures.append("analysis strategy catalog must load one selected descriptor")
    if "without loading" not in str(index.get("small_task_behavior", "")):
        failures.append("small tasks must skip the analysis strategy catalog")
    if index.get("primary_strategy_ids") != list(PRIMARY_STRATEGY_IDS):
        failures.append("analysis strategy primary IDs or order are invalid")
    if index.get("review_strategy_ids") != list(REVIEW_STRATEGY_IDS):
        failures.append("analysis strategy review IDs are invalid")

    descriptors = index.get("descriptors")
    expected_descriptor_ids = set(PRIMARY_STRATEGY_IDS) - {"direct-local"}
    expected_descriptor_ids.update(REVIEW_STRATEGY_IDS)
    if not isinstance(descriptors, dict) or set(descriptors) != expected_descriptor_ids:
        failures.append("analysis strategy descriptor map is incomplete or contains unknown IDs")
        return failures

    if "direct-local" in descriptors:
        failures.append("direct-local must remain descriptor-free for small tasks")
    initial_words = count(index_path)
    descriptor_ids: list[str] = []
    for strategy_id, relpath in descriptors.items():
        expected_relpath = f".ai/assistant/analysis-strategies/{strategy_id}.json"
        if relpath != expected_relpath:
            failures.append(f"strategy {strategy_id} has an invalid descriptor path")
            continue
        descriptor_path = adapter_root / relpath
        try:
            descriptor = load_object(descriptor_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failures.append(str(exc))
            continue
        descriptor_ids.append(str(descriptor.get("id")))
        if set(descriptor) != DESCRIPTOR_FIELDS:
            failures.append(f"strategy {strategy_id} descriptor fields are invalid")
        expected_kind = "review" if strategy_id in REVIEW_STRATEGY_IDS else "primary"
        if descriptor.get("schema_version") != 1:
            failures.append(f"strategy {strategy_id} schema_version must be 1")
        if descriptor.get("id") != strategy_id:
            failures.append(f"strategy {strategy_id} descriptor identity differs")
        if descriptor.get("strategy_kind") != expected_kind:
            failures.append(f"strategy {strategy_id} kind must be {expected_kind}")
        for field in ("use_when", "sequence", "required_nonempty_fields"):
            value = descriptor.get(field)
            if not isinstance(value, list) or not value or not all(
                isinstance(item, str) and item for item in value
            ):
                failures.append(f"strategy {strategy_id} {field} must be non-empty")
        if not isinstance(descriptor.get("completion_rule"), str) or not descriptor[
            "completion_rule"
        ]:
            failures.append(f"strategy {strategy_id} completion rule is missing")
        if initial_words + count(descriptor_path) > MAX_INITIAL_STRATEGY_WORDS:
            failures.append(
                f"strategy {strategy_id} initial context exceeds {MAX_INITIAL_STRATEGY_WORDS} words"
            )
    if len(descriptor_ids) != len(set(descriptor_ids)):
        failures.append("analysis strategy descriptor IDs are duplicated")
    return failures


def required_obligations_resolved(model: dict[str, Any]) -> bool:
    return all(
        not isinstance(obligation, dict)
        or obligation.get("required") is not True
        or obligation.get("status") in {"passed", "waived"}
        for obligation in model.get("proof_obligations", [])
    )


def required_reviews_passed(model: dict[str, Any]) -> bool:
    required = model.get("required_review_ids", [])
    results = {
        item.get("id"): item
        for item in model.get("review_results", [])
        if isinstance(item, dict)
    }
    return all(
        review_id in results
        and results[review_id].get("status") == "passed"
        and bool(results[review_id].get("evidence_refs"))
        for review_id in required
    )


def _forbidden_reasoning_failures(value: Any, path: tuple[str, ...] = ()) -> list[str]:
    failures: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = path + (str(key),)
            if str(key).casefold() in FORBIDDEN_REASONING_KEYS:
                failures.append(
                    f"problem model contains forbidden private-reasoning field {'.'.join(child_path)}"
                )
            failures.extend(_forbidden_reasoning_failures(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            failures.extend(_forbidden_reasoning_failures(child, path + (str(index),)))
    return failures
