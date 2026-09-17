"""Validate the portable session-continuity contract and selected packets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from target_validation_support import (
    CANONICAL_CHANGE_SET_HASH_CONTRACT,
    canonical_json_sha256,
    is_target_relative_path,
)
from target_adapter_validation.assistant_capabilities import (
    SURFACE_CAPABILITY_SCHEMA_VERSION,
    capability_record_path,
)
from target_adapter_validation.analysis_strategies import (
    load_problem_model_schema,
    validate_selected_problem_model,
)


POLICY_RELPATH = ".ai/assistant/policies/session-continuity.json"
FLOW_RELPATH = ".ai/assistant/flows/session-continuity.flow.md"
GATE_RELPATH = ".ai/assistant/gates/session-continuity.md"
TEMPLATE_RELPATH = ".ai/assistant/templates/session-continuity-packet.json"
OVERLAY_RELPATH = ".ai/assistant/context/task-scales/session-continuity.json"
RUNTIME_DIRECTORY = ".ai/.runtime/continuity"
PACKET_SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "alatyr-session-continuity-packet.schema.json"
)
PHASES = {"inspect", "modify", "commit", "publish", "live-external"}
MAX_PACKET_BYTES = 65536
ORDERED_SET_PATHS = (
    ("routing", "profiles"),
    ("routing", "overlays"),
    ("routing", "project_areas"),
    ("routing", "rule_ids"),
    ("routing", "loaded_paths"),
    ("routing", "omitted_context"),
    ("authorization", "recorded_phases"),
    ("authorization", "deliberately_not_authorized"),
    ("repository", "changed_paths"),
    ("analysis", "open_proof_obligation_ids"),
    ("analysis", "completed_review_ids"),
    ("analysis", "invalidated_assumption_ids"),
    ("decisions",),
    ("unresolved",),
)


def _canonical_digest(packet: dict[str, Any]) -> str:
    payload = dict(packet)
    payload.pop("integrity", None)
    return canonical_json_sha256(payload)


def _load_schema() -> dict[str, Any]:
    value = json.loads(PACKET_SCHEMA.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("session continuity schema must contain an object")
    jsonschema.Draft7Validator.check_schema(value)
    return value


def _rule_ids(validator: Any) -> set[str]:
    registry = validator.load_json_object(
        validator.target_path(".ai/framework/rule-registry.json"),
        "SESSION_CONTINUITY_RULE_REGISTRY",
    )
    if not isinstance(registry, dict):
        return set()
    return {
        rule_id
        for category in registry.get("category_owners", [])
        if isinstance(category, dict)
        for rule_id in category.get("rule_ids", [])
        if isinstance(rule_id, str)
    }


def _check_static_contract(validator: Any) -> None:
    policy = validator.load_json_object(
        validator.target_path(POLICY_RELPATH), "SESSION_CONTINUITY_POLICY"
    )
    if not isinstance(policy, dict):
        return
    expected = {
        "schema_version": 2,
        "policy_kind": "target-session-continuity",
        "canonical_rule": "ALATYR-CONTINUITY-001",
        "canonical_owner": ".ai/framework/session-continuity.md",
        "flow": FLOW_RELPATH,
        "gate": GATE_RELPATH,
        "packet_template": TEMPLATE_RELPATH,
        "packet_schema": "alatyr-session-continuity-packet-v2",
        "runtime_directory": RUNTIME_DIRECTORY,
    }
    for field, value in expected.items():
        if policy.get(field) != value:
            validator.error(
                "SESSION_CONTINUITY_POLICY_DRIFT",
                f"session continuity policy requires {field}={value!r}",
                POLICY_RELPATH,
            )
    storage = policy.get("storage")
    if not isinstance(storage, dict) or storage.get("automatic_commit") is not False:
        validator.error(
            "SESSION_CONTINUITY_STORAGE",
            "continuity storage must forbid automatic commit",
            POLICY_RELPATH,
        )
    resume = policy.get("resume")
    if not isinstance(resume, dict):
        validator.error(
            "SESSION_CONTINUITY_RESUME_POLICY",
            "session continuity policy requires a resume contract",
            POLICY_RELPATH,
        )
    else:
        if resume.get("initial_mode") != (
            "inspect-only-pending-current-scope-revalidation"
        ):
            validator.error(
                "SESSION_CONTINUITY_RESUME_POLICY",
                "resume must start inspect-only pending current-scope revalidation",
                POLICY_RELPATH,
            )
        if resume.get("restore_publish_or_live_external") is not False:
            validator.error(
                "SESSION_CONTINUITY_AUTHORITY",
                "resume policy must not restore publish or live-external authority",
                POLICY_RELPATH,
            )
        if resume.get("full_corpus_reload") is not False:
            validator.error(
                "SESSION_CONTINUITY_CONTEXT_COST",
                "resume policy must not require a full-corpus reload",
                POLICY_RELPATH,
            )

    router = validator.load_json_object(
        validator.target_path(".ai/assistant/context-router.json"),
        "SESSION_CONTINUITY_ROUTER",
    )
    route = (
        router.get("task_scale_overlays", {}).get("session-continuity")
        if isinstance(router, dict)
        and isinstance(router.get("task_scale_overlays"), dict)
        else None
    )
    if not isinstance(route, dict) or route.get("descriptor") != OVERLAY_RELPATH:
        validator.error(
            "SESSION_CONTINUITY_ROUTE",
            "context router must expose the session-continuity overlay",
            ".ai/assistant/context-router.json",
        )

    gate_index = validator.load_json_object(
        validator.target_path(".ai/assistant/gates/index.json"),
        "SESSION_CONTINUITY_GATE_INDEX",
    )
    gate = (
        gate_index.get("gates", {}).get("session-continuity")
        if isinstance(gate_index, dict)
        and isinstance(gate_index.get("gates"), dict)
        else None
    )
    if not isinstance(gate, dict) or gate.get("path") != GATE_RELPATH:
        validator.error(
            "SESSION_CONTINUITY_GATE_ROUTE",
            "gate index must expose the session-continuity gate",
            ".ai/assistant/gates/index.json",
        )

    ignore_path = validator.target_path(".ai/.gitignore")
    if validator.is_target_file(ignore_path):
        ignore_read = validator.context.read_text_result(ignore_path)
        ignored = (ignore_read.value or "").splitlines()
        if ".runtime/" not in {line.strip() for line in ignored}:
            validator.error(
                "SESSION_CONTINUITY_RUNTIME_TRACKING",
                ".ai/.gitignore must exclude ephemeral .runtime records",
                ".ai/.gitignore",
            )


def _check_analysis_binding(
    validator: Any, packet: dict[str, Any], relpath: str
) -> None:
    analysis = packet.get("analysis")
    if not isinstance(analysis, dict):
        return
    problem_model = analysis.get("problem_model")
    if not isinstance(problem_model, dict) or problem_model.get("state") != "available":
        return
    model_path = problem_model.get("path")
    if not isinstance(model_path, str) or not is_target_relative_path(model_path):
        validator.error(
            "SESSION_CONTINUITY_PROBLEM_MODEL_PATH",
            f"invalid problem-model path: {model_path}",
            relpath,
        )
        return
    selected_model = validator.target_path(model_path)
    if not validator.is_target_file(selected_model):
        validator.error(
            "SESSION_CONTINUITY_PROBLEM_MODEL_MISSING",
            f"problem model is unavailable: {model_path}",
            relpath,
        )
        return
    if problem_model.get("sha256") != validator.context.content_digest(
        selected_model
    ):
        validator.error(
            "SESSION_CONTINUITY_PROBLEM_MODEL_DRIFT",
            f"problem model changed: {model_path}",
            relpath,
        )
        return
    try:
        model_schema = load_problem_model_schema()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        validator.error(
            "SESSION_CONTINUITY_PROBLEM_MODEL_SCHEMA", str(exc), relpath
        )
        return
    model = validate_selected_problem_model(
        validator,
        selected_model,
        model_schema,
        require_completion=False,
    )
    if not isinstance(model, dict):
        return
    if analysis.get("primary_strategy_id") != model.get("primary_strategy_id"):
        validator.error(
            "SESSION_CONTINUITY_ANALYSIS_DRIFT",
            "continuity strategy differs from the bound problem model",
            relpath,
        )
    expected_analysis = {
        "open_proof_obligation_ids": sorted(
            item["id"]
            for item in model.get("proof_obligations", [])
            if isinstance(item, dict)
            and item.get("status") in {"open", "failed", "blocked"}
            and isinstance(item.get("id"), str)
        ),
        "completed_review_ids": sorted(
            item["id"]
            for item in model.get("review_results", [])
            if isinstance(item, dict)
            and item.get("status") == "passed"
            and isinstance(item.get("id"), str)
        ),
        "invalidated_assumption_ids": sorted(
            item["id"]
            for item in model.get("assumptions", [])
            if isinstance(item, dict)
            and item.get("status") == "invalidated"
            and isinstance(item.get("id"), str)
        ),
    }
    for field, expected in expected_analysis.items():
        if analysis.get(field) != expected:
            validator.error(
                "SESSION_CONTINUITY_ANALYSIS_DRIFT",
                f"continuity {field} differs from the bound problem model",
                relpath,
            )
    packet_task = packet.get("task")
    model_task = model.get("task_binding")
    if isinstance(packet_task, dict) and isinstance(model_task, dict) and (
        packet_task.get("operation_id") != model.get("operation_id")
        or packet_task.get("task_id") not in model_task.get("task_ids", [])
    ):
        validator.error(
            "SESSION_CONTINUITY_ANALYSIS_BINDING",
            "continuity task identity differs from the bound problem model",
            relpath,
        )


def _check_packet(
    validator: Any, packet_path: Path, schema: dict[str, Any]
) -> dict[str, Any] | None:
    relpath = validator.rel(packet_path)
    if not relpath.startswith(RUNTIME_DIRECTORY + "/") or not relpath.endswith(
        ".json"
    ):
        validator.error(
            "SESSION_CONTINUITY_PACKET_LOCATION",
            f"continuity packets must be JSON files below {RUNTIME_DIRECTORY}",
            relpath,
        )
    content = validator.context.read_bytes_result(packet_path).value
    if content is not None and len(content) > MAX_PACKET_BYTES:
        validator.error(
            "SESSION_CONTINUITY_PACKET_SIZE",
            f"continuity packet exceeds {MAX_PACKET_BYTES} bytes",
            relpath,
        )
    tracked = validator.git.is_tracked(relpath)
    ignored = validator.git.is_ignored(relpath)
    if tracked is True:
        validator.error(
            "SESSION_CONTINUITY_PACKET_TRACKED",
            "ephemeral continuity packets must not be tracked by Git",
            relpath,
        )
    if ignored is not True:
        validator.error(
            "SESSION_CONTINUITY_PACKET_NOT_IGNORED",
            "ephemeral continuity packets must be ignored by Git",
            relpath,
        )
    packet = validator.load_json_object(packet_path, "SESSION_CONTINUITY_PACKET")
    if not isinstance(packet, dict):
        return None
    for error in sorted(
        jsonschema.Draft7Validator(schema).iter_errors(packet),
        key=lambda item: list(item.absolute_path),
    ):
        location = ".".join(str(item) for item in error.absolute_path) or "root"
        validator.error(
            "SESSION_CONTINUITY_PACKET_SCHEMA",
            f"session continuity packet {location}: {error.message}",
            relpath,
        )

    integrity = packet.get("integrity")
    recorded_digest = integrity.get("packet_sha256") if isinstance(integrity, dict) else None
    if recorded_digest != _canonical_digest(packet):
        validator.error(
            "SESSION_CONTINUITY_PACKET_DIGEST",
            "session continuity packet digest does not match canonical content",
            relpath,
        )

    for field_path in ORDERED_SET_PATHS:
        value: Any = packet
        for field in field_path:
            value = value.get(field) if isinstance(value, dict) else None
        if isinstance(value, list) and value != sorted(value):
            validator.error(
                "SESSION_CONTINUITY_PACKET_ORDER",
                f"{'.'.join(field_path)} must use canonical sorted order",
                relpath,
            )

    authorization = packet.get("authorization")
    if isinstance(authorization, dict):
        recorded = set(authorization.get("recorded_phases", []))
        denied = set(authorization.get("deliberately_not_authorized", []))
        if recorded & denied or recorded | denied != PHASES:
            validator.error(
                "SESSION_CONTINUITY_AUTHORIZATION_PARTITION",
                "recorded and deliberately unauthorized phases must form a disjoint complete partition",
                relpath,
            )
        if authorization.get("resume_mode") != (
            "inspect-only-pending-current-scope-revalidation"
        ) or authorization.get("revalidation_required") is not True:
            validator.error(
                "SESSION_CONTINUITY_AUTHORITY",
                "a packet must resume inspect-only and require current-scope revalidation",
                relpath,
            )

    known_rules = _rule_ids(validator)
    routing = packet.get("routing")
    if isinstance(routing, dict) and known_rules:
        unknown = sorted(set(routing.get("rule_ids", [])) - known_rules)
        if unknown:
            validator.error(
                "SESSION_CONTINUITY_RULE_UNKNOWN",
                f"continuity packet references unknown rules: {unknown}",
                relpath,
            )
    if isinstance(routing, dict):
        for loaded_path in routing.get("loaded_paths", []):
            if not isinstance(loaded_path, str) or not is_target_relative_path(
                loaded_path
            ):
                validator.error(
                    "SESSION_CONTINUITY_LOADED_PATH",
                    f"invalid loaded path: {loaded_path}",
                    relpath,
                )
            elif not validator.is_target_file(validator.target_path(loaded_path)):
                validator.error(
                    "SESSION_CONTINUITY_LOADED_PATH_DRIFT",
                    f"previously loaded path is no longer available: {loaded_path}",
                    relpath,
                )

    _check_analysis_binding(validator, packet, relpath)

    boundary = packet.get("boundary")
    if isinstance(boundary, dict) and boundary.get(
        "capability_record_state"
    ) == "available":
        capability_path = boundary.get("capability_record")
        if not isinstance(capability_path, str) or not is_target_relative_path(
            capability_path
        ):
            validator.error(
                "SESSION_CONTINUITY_CAPABILITY_PATH",
                f"invalid capability record path: {capability_path}",
                relpath,
            )
        else:
            expected_capability_path = capability_record_path(
                str(boundary.get("assistant_surface"))
            )
            if capability_path != expected_capability_path:
                validator.error(
                    "SESSION_CONTINUITY_CAPABILITY_PATH",
                    "capability record path does not match the boundary surface",
                    relpath,
                )
            selected = validator.target_path(capability_path)
            capability = validator.load_json_object(
                selected, "SESSION_CONTINUITY_CAPABILITY"
            )
            if not isinstance(capability, dict):
                validator.error(
                    "SESSION_CONTINUITY_CAPABILITY_MISSING",
                    f"capability record is unavailable: {capability_path}",
                    relpath,
                )
            else:
                if boundary.get("capability_record_sha256") != (
                    validator.context.content_digest(selected)
                ):
                    validator.error(
                        "SESSION_CONTINUITY_CAPABILITY_DRIFT",
                        f"capability record changed: {capability_path}",
                        relpath,
                    )
                if capability.get("assistant_surface") != boundary.get(
                    "assistant_surface"
                ):
                    validator.error(
                        "SESSION_CONTINUITY_CAPABILITY_ID",
                        "capability record identity differs from the boundary surface",
                        relpath,
                    )
                if capability.get("schema_version") != (
                    SURFACE_CAPABILITY_SCHEMA_VERSION
                ):
                    validator.error(
                        "SESSION_CONTINUITY_CAPABILITY_SCHEMA",
                        "capability record schema is incompatible with session continuity",
                        relpath,
                    )

    if isinstance(routing, dict):
        context_packet = routing.get("context_packet")
        if isinstance(context_packet, dict) and context_packet.get(
            "state"
        ) == "available":
            context_path = context_packet.get("path")
            if not isinstance(context_path, str) or not is_target_relative_path(
                context_path
            ):
                validator.error(
                    "SESSION_CONTINUITY_CONTEXT_PATH",
                    f"invalid context packet path: {context_path}",
                    relpath,
                )
            else:
                selected = validator.target_path(context_path)
                context_value = validator.load_json_object(
                    selected, "SESSION_CONTINUITY_CONTEXT_PACKET"
                )
                if not isinstance(context_value, dict):
                    validator.error(
                        "SESSION_CONTINUITY_CONTEXT_MISSING",
                        f"referenced context packet is missing or invalid: {context_path}",
                        relpath,
                    )
                elif (
                    context_value.get("schema_version") != 4
                    or context_value.get("packet_kind") != "alatyr-context-packet"
                ):
                    validator.error(
                        "SESSION_CONTINUITY_CONTEXT_IDENTITY",
                        "referenced context packet has an incompatible schema or kind",
                        relpath,
                    )
                if isinstance(context_value, dict) and context_packet.get("sha256") != (
                    validator.context.content_digest(selected)
                ):
                    validator.error(
                        "SESSION_CONTINUITY_CONTEXT_DRIFT",
                        f"referenced context packet changed: {context_path}",
                        relpath,
                    )

    repository = packet.get("repository")
    if isinstance(repository, dict) and repository.get("evidence_state") == "available":
        current_branch = validator.git.branch_name()
        current_head = validator.git.head_revision()
        if current_branch is None or current_head is None:
            validator.error(
                "SESSION_CONTINUITY_GIT_UNAVAILABLE",
                "packet claims repository evidence but current Git evidence is unavailable",
                relpath,
            )
        else:
            if repository.get("branch") != current_branch:
                validator.error(
                    "SESSION_CONTINUITY_GIT_DRIFT",
                    f"packet branch differs from current branch {current_branch}",
                    relpath,
                )
            if repository.get("head_revision") != current_head:
                validator.error(
                    "SESSION_CONTINUITY_GIT_DRIFT",
                    "packet HEAD revision differs from current HEAD",
                    relpath,
                )
            base = repository.get("base_revision")
            contract = repository.get("change_set_hash_contract")
            if isinstance(base, str) and contract == CANONICAL_CHANGE_SET_HASH_CONTRACT:
                change_set = validator.git.change_set(base)
                if change_set is None:
                    validator.error(
                        "SESSION_CONTINUITY_GIT_UNAVAILABLE",
                        f"cannot resolve packet base revision {base}",
                        relpath,
                    )
                else:
                    if repository.get("change_set_sha256") != change_set.content_sha256:
                        validator.error(
                            "SESSION_CONTINUITY_CHANGE_SET_DRIFT",
                            "packet change-set digest differs from current repository state",
                            relpath,
                        )
                    if sorted(repository.get("changed_paths", [])) != sorted(
                        change_set.changed_files
                    ):
                        validator.error(
                            "SESSION_CONTINUITY_CHANGE_SET_DRIFT",
                            "packet changed paths differ from current repository state",
                            relpath,
                        )

    for approval in packet.get("approvals", []):
        if not isinstance(approval, dict):
            continue
        approval_path = approval.get("path")
        if not isinstance(approval_path, str) or not is_target_relative_path(
            approval_path
        ):
            validator.error(
                "SESSION_CONTINUITY_APPROVAL_PATH",
                f"invalid approval path: {approval_path}",
                relpath,
            )
            continue
        target_approval = validator.target_path(approval_path)
        if not validator.is_target_file(target_approval):
            validator.error(
                "SESSION_CONTINUITY_APPROVAL_MISSING",
                f"referenced approval is missing: {approval_path}",
                relpath,
            )
        elif approval.get("sha256") != validator.context.content_digest(
            target_approval
        ):
            validator.error(
                "SESSION_CONTINUITY_APPROVAL_DRIFT",
                f"referenced approval changed: {approval_path}",
                relpath,
            )
    return packet


def validate_session_continuity(validator: Any) -> None:
    """Validate static target routes and explicitly selected runtime packets."""

    _check_static_contract(validator)
    if not validator.continuity_packets:
        return
    try:
        schema = _load_schema()
    except (OSError, ValueError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        validator.error(
            "SESSION_CONTINUITY_SCHEMA_INVALID",
            f"cannot load session continuity packet schema: {exc}",
        )
        return
    packets = [
        packet
        for packet_path in validator.continuity_packets
        for packet in [_check_packet(validator, packet_path, schema)]
        if packet is not None
    ]
    digests: dict[str, dict[str, Any]] = {}
    identities: set[tuple[str, int]] = set()
    for packet in packets:
        integrity = packet.get("integrity")
        digest = integrity.get("packet_sha256") if isinstance(integrity, dict) else None
        task = packet.get("task")
        task_id = task.get("task_id") if isinstance(task, dict) else None
        sequence = packet.get("packet_sequence")
        identity = (str(task_id), int(sequence)) if isinstance(sequence, int) else None
        if isinstance(digest, str) and digest in digests:
            validator.error(
                "SESSION_CONTINUITY_PACKET_REPLAY",
                "the same continuity packet digest was selected more than once",
            )
        elif isinstance(digest, str):
            digests[digest] = packet
        if identity is not None and identity in identities:
            validator.error(
                "SESSION_CONTINUITY_PACKET_SEQUENCE",
                f"duplicate continuity packet sequence for task {task_id}: {sequence}",
            )
        elif identity is not None:
            identities.add(identity)

    for packet in packets:
        sequence = packet.get("packet_sequence")
        previous = packet.get("previous_packet_sha256")
        prior = digests.get(previous) if isinstance(previous, str) else None
        if isinstance(sequence, int) and sequence > 1 and prior is not None:
            prior_sequence = prior.get("packet_sequence")
            prior_task = prior.get("task")
            current_task = packet.get("task")
            if (
                prior_sequence != sequence - 1
                or not isinstance(prior_task, dict)
                or not isinstance(current_task, dict)
                or prior_task.get("task_id") != current_task.get("task_id")
            ):
                validator.error(
                    "SESSION_CONTINUITY_PACKET_CHAIN",
                    "selected continuity packet chain has a task or sequence discontinuity",
                )
