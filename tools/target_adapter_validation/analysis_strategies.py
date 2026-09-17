"""Validate installed analysis-strategy and problem-model contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from analysis_strategy_contract import (
    PRIMARY_STRATEGY_IDS,
    MAX_ACTIVE_PROJECTION_FILE_BYTES,
    MAX_PROBLEM_MODEL_FILE_BYTES,
    PROBLEM_MODEL_PROJECTION_RUNTIME_PREFIX,
    PROBLEM_MODEL_PROJECTION_SCHEMA_ID,
    PROBLEM_MODEL_PROJECTION_TEMPLATE_RELPATH,
    PROBLEM_MODEL_RUNTIME_PREFIX,
    PROBLEM_MODEL_SCHEMA_ID,
    PROBLEM_MODEL_TEMPLATE_RELPATH,
    STRATEGY_INDEX_RELPATH,
    build_active_problem_model_projection,
    required_obligations_resolved,
    required_reviews_passed,
    validate_active_problem_model_projection,
    validate_problem_model,
    validate_problem_model_projection_schema,
    validate_problem_model_schema,
    validate_strategy_catalog,
    validate_strategy_requirements,
)
from target_validation_support import is_target_relative_path


PROBLEM_MODEL_SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "alatyr-problem-model.schema.json"
)
PROBLEM_MODEL_PROJECTION_SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "alatyr-problem-model-active-projection.schema.json"
)
POLICY_RELPATH = ".ai/assistant/task-decomposition.json"
ROUTER_RELPATH = ".ai/assistant/context-router.json"
COMPLETION_RELPATH = ".ai/assistant/templates/operation-completion-evidence.json"
GATE_RELPATH = ".ai/assistant/gates/analysis-strategy.md"
REQUIRED_PATHS = (
    STRATEGY_INDEX_RELPATH,
    PROBLEM_MODEL_TEMPLATE_RELPATH,
    PROBLEM_MODEL_PROJECTION_TEMPLATE_RELPATH,
    GATE_RELPATH,
    ".ai/assistant/analysis-strategies/invariant-first.json",
    ".ai/assistant/analysis-strategies/hypothesis-driven.json",
    ".ai/assistant/analysis-strategies/architecture-comparison.json",
    ".ai/assistant/analysis-strategies/evidence-synthesis.json",
    ".ai/assistant/analysis-strategies/exploratory-design.json",
    ".ai/assistant/analysis-strategies/adversarial-review.json",
)


def load_problem_model_schema() -> dict[str, Any]:
    value = json.loads(PROBLEM_MODEL_SCHEMA.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("problem-model schema must contain an object")
    return value


def load_problem_model_projection_schema() -> dict[str, Any]:
    value = json.loads(PROBLEM_MODEL_PROJECTION_SCHEMA.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("active problem-model projection schema must contain an object")
    return value


def validate_analysis_strategies(validator: Any) -> None:
    """Validate static strategy routing and explicitly selected problem models."""

    for relpath in REQUIRED_PATHS:
        if not validator.is_target_file(validator.target_path(relpath)):
            validator.error(
                "ANALYSIS_STRATEGY_REQUIRED_FILE_MISSING",
                "installed adapter is missing an analysis-strategy surface",
                relpath,
            )

    def load_object(path: Path) -> dict[str, Any]:
        value = validator.load_json_object(path, "ANALYSIS_STRATEGY_CATALOG")
        if not isinstance(value, dict):
            raise ValueError(f"{validator.rel(path)} must contain a JSON object")
        return value

    def count_words(path: Path) -> int:
        return len(
            re.findall(r"\S+", validator.context.read_text_result(path).value or "")
        )

    for failure in validate_strategy_catalog(
        validator.target,
        object_loader=load_object,
        count_words=count_words,
    ):
        validator.error(
            "ANALYSIS_STRATEGY_CATALOG",
            failure,
            STRATEGY_INDEX_RELPATH,
        )

    policy = validator.load_json_object(
        validator.target_path(POLICY_RELPATH), "ANALYSIS_STRATEGY_POLICY"
    )
    strategy = policy.get("analysis_strategy") if isinstance(policy, dict) else None
    if not isinstance(policy, dict) or policy.get("schema_version") != 2:
        validator.error(
            "ANALYSIS_STRATEGY_POLICY_SCHEMA",
            "task-decomposition policy must use schema_version 2",
            POLICY_RELPATH,
        )
    if not isinstance(strategy, dict):
        validator.error(
            "ANALYSIS_STRATEGY_POLICY_MISSING",
            "task-decomposition policy must define analysis_strategy",
            POLICY_RELPATH,
        )
    else:
        expected = {
            "catalog": STRATEGY_INDEX_RELPATH,
            "problem_model_schema": PROBLEM_MODEL_SCHEMA_ID,
            "problem_model_template": PROBLEM_MODEL_TEMPLATE_RELPATH,
            "active_projection_schema": PROBLEM_MODEL_PROJECTION_SCHEMA_ID,
            "active_projection_template": PROBLEM_MODEL_PROJECTION_TEMPLATE_RELPATH,
            "debug_mode_activation": "never automatic",
        }
        for field, value in expected.items():
            if strategy.get(field) != value:
                validator.error(
                    "ANALYSIS_STRATEGY_POLICY_DRIFT",
                    f"analysis strategy policy requires {field}={value!r}",
                    POLICY_RELPATH,
                )
        if strategy.get("primary_strategy_ids") != list(PRIMARY_STRATEGY_IDS):
            validator.error(
                "ANALYSIS_STRATEGY_PRIMARY_IDS",
                "analysis strategy policy primary IDs are incomplete or reordered",
                POLICY_RELPATH,
            )

    router = validator.load_json_object(
        validator.target_path(ROUTER_RELPATH), "ANALYSIS_STRATEGY_ROUTER"
    )
    route = router.get("task_decomposition") if isinstance(router, dict) else None
    if not isinstance(route, dict) or route.get("schema_version") != 2:
        validator.error(
            "ANALYSIS_STRATEGY_ROUTE",
            "context router task_decomposition must use schema_version 2",
            ROUTER_RELPATH,
        )
    elif (
        route.get("analysis_strategy_index") != STRATEGY_INDEX_RELPATH
        or route.get("problem_model_template") != PROBLEM_MODEL_TEMPLATE_RELPATH
        or route.get("active_projection_template")
        != PROBLEM_MODEL_PROJECTION_TEMPLATE_RELPATH
        or "without loading" not in str(route.get("small_task_behavior", ""))
        or "exactly one selected descriptor" not in str(route.get("strategy_loading", ""))
        or "active projection" not in str(route.get("problem_state_loading", ""))
    ):
        validator.error(
            "ANALYSIS_STRATEGY_ROUTE",
            "context router analysis-strategy route is incomplete",
            ROUTER_RELPATH,
        )

    completion = validator.load_json_object(
        validator.target_path(COMPLETION_RELPATH), "ANALYSIS_STRATEGY_COMPLETION"
    )
    decomposition = completion.get("task_decomposition") if isinstance(completion, dict) else None
    completion_strategy = (
        decomposition.get("analysis_strategy") if isinstance(decomposition, dict) else None
    )
    if (
        not isinstance(decomposition, dict)
        or not isinstance(completion_strategy, dict)
        or not isinstance(completion_strategy.get("active_projection"), dict)
        or not isinstance(decomposition.get("proof_obligations"), list)
    ):
        validator.error(
            "ANALYSIS_STRATEGY_COMPLETION_EVIDENCE",
            "operation completion evidence must record strategy, reviews, and obligations",
            COMPLETION_RELPATH,
        )

    gate_index = validator.load_json_object(
        validator.target_path(".ai/assistant/gates/index.json"),
        "ANALYSIS_STRATEGY_GATE_INDEX",
    )
    gates = gate_index.get("gates") if isinstance(gate_index, dict) else None
    gate = gates.get("analysis-strategy") if isinstance(gates, dict) else None
    if not isinstance(gate, dict) or gate.get("path") != GATE_RELPATH:
        validator.error(
            "ANALYSIS_STRATEGY_GATE_ROUTE",
            "gate index must expose the analysis-strategy gate",
            ".ai/assistant/gates/index.json",
        )

    try:
        schema = load_problem_model_schema()
        projection_schema = load_problem_model_projection_schema()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        validator.error("ANALYSIS_PROBLEM_MODEL_SCHEMA", str(exc))
        return
    for failure in validate_problem_model_schema(schema):
        validator.error("ANALYSIS_PROBLEM_MODEL_SCHEMA", failure)
    for failure in validate_problem_model_projection_schema(projection_schema):
        validator.error("ANALYSIS_PROBLEM_MODEL_PROJECTION_SCHEMA", failure)
    for model_path in validator.problem_models:
        validate_selected_problem_model(
            validator,
            model_path,
            schema,
            projection_schema=projection_schema,
            require_completion=True,
        )


def validate_selected_problem_model(
    validator: Any,
    model_path: Path,
    schema: dict[str, Any],
    *,
    projection_schema: dict[str, Any] | None = None,
    require_completion: bool,
) -> dict[str, Any] | None:
    relpath = validator.rel(model_path)
    if not relpath.startswith(PROBLEM_MODEL_RUNTIME_PREFIX) or not relpath.endswith(
        ".json"
    ):
        validator.error(
            "ANALYSIS_PROBLEM_MODEL_LOCATION",
            f"problem models must be JSON below {PROBLEM_MODEL_RUNTIME_PREFIX}",
            relpath,
        )
    if validator.git.is_tracked(relpath) is True:
        validator.error(
            "ANALYSIS_PROBLEM_MODEL_TRACKED",
            "runtime problem models must not be tracked by Git",
            relpath,
        )
    if validator.git.is_ignored(relpath) is not True:
        validator.error(
            "ANALYSIS_PROBLEM_MODEL_NOT_IGNORED",
            "runtime problem models must be ignored by Git",
            relpath,
        )
    model_read = validator.context.read_bytes_result(model_path)
    if model_read.value is None:
        validator.error(
            "ANALYSIS_PROBLEM_MODEL_READ",
            model_read.error or "problem model could not be read",
            relpath,
        )
        return None
    if len(model_read.value) > MAX_PROBLEM_MODEL_FILE_BYTES:
        validator.error(
            "ANALYSIS_PROBLEM_MODEL_FILE_SIZE",
            f"runtime problem model exceeds {MAX_PROBLEM_MODEL_FILE_BYTES} file bytes",
            relpath,
        )
        return None
    model = validator.load_json_object(model_path, "ANALYSIS_PROBLEM_MODEL")
    if not isinstance(model, dict):
        return None
    model_failures = validate_problem_model(model, schema)
    for failure in model_failures:
        validator.error("ANALYSIS_PROBLEM_MODEL_INVALID", failure, relpath)
    if not model_failures:
        selected_projection_schema = projection_schema
        if selected_projection_schema is None:
            try:
                selected_projection_schema = load_problem_model_projection_schema()
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                validator.error(
                    "ANALYSIS_PROBLEM_MODEL_PROJECTION_SCHEMA", str(exc), relpath
                )
        if isinstance(selected_projection_schema, dict):
            validate_selected_problem_model_projection(
                validator,
                model_path,
                model,
                selected_projection_schema,
            )
    strategy_id = model.get("primary_strategy_id")
    descriptor = None
    if isinstance(strategy_id, str) and strategy_id != "direct-local":
        descriptor = validator.load_json_object(
            validator.target_path(
                f".ai/assistant/analysis-strategies/{strategy_id}.json"
            ),
            "ANALYSIS_STRATEGY_DESCRIPTOR",
        )
    for failure in validate_strategy_requirements(model, descriptor):
        validator.error("ANALYSIS_STRATEGY_REQUIREMENT", failure, relpath)
    if require_completion and not required_obligations_resolved(model):
        validator.error(
            "ANALYSIS_REQUIRED_OBLIGATION_OPEN",
            "selected problem model has unresolved required proof obligations",
            relpath,
        )
    if require_completion and not required_reviews_passed(model):
        validator.error(
            "ANALYSIS_REQUIRED_REVIEW_OPEN",
            "selected problem model has an incomplete required review",
            relpath,
        )
    return model


def validate_selected_problem_model_projection(
    validator: Any,
    model_path: Path,
    model: dict[str, Any],
    schema: dict[str, Any],
) -> dict[str, Any] | None:
    projection_ref = model.get("active_projection")
    if not isinstance(projection_ref, dict):
        return None
    projection_relpath = projection_ref.get("path")
    if (
        not isinstance(projection_relpath, str)
        or not is_target_relative_path(projection_relpath)
        or not projection_relpath.startswith(PROBLEM_MODEL_PROJECTION_RUNTIME_PREFIX)
        or not projection_relpath.endswith(".json")
    ):
        validator.error(
            "ANALYSIS_PROBLEM_MODEL_PROJECTION_LOCATION",
            f"invalid active problem-model projection path: {projection_relpath}",
            validator.rel(model_path),
        )
        return None
    projection_path = validator.target_path(projection_relpath)
    if not validator.is_target_file(projection_path):
        validator.error(
            "ANALYSIS_PROBLEM_MODEL_PROJECTION_MISSING",
            "selected problem model active projection is unavailable",
            projection_relpath,
        )
        return None
    if validator.git.is_tracked(projection_relpath) is True:
        validator.error(
            "ANALYSIS_PROBLEM_MODEL_PROJECTION_TRACKED",
            "runtime active problem-model projections must not be tracked by Git",
            projection_relpath,
        )
    if validator.git.is_ignored(projection_relpath) is not True:
        validator.error(
            "ANALYSIS_PROBLEM_MODEL_PROJECTION_NOT_IGNORED",
            "runtime active problem-model projections must be ignored by Git",
            projection_relpath,
        )
    projection_read = validator.context.read_bytes_result(projection_path)
    if projection_read.value is None:
        validator.error(
            "ANALYSIS_PROBLEM_MODEL_PROJECTION_READ",
            projection_read.error or "active projection could not be read",
            projection_relpath,
        )
        return None
    if len(projection_read.value) > MAX_ACTIVE_PROJECTION_FILE_BYTES:
        validator.error(
            "ANALYSIS_PROBLEM_MODEL_PROJECTION_FILE_SIZE",
            "active problem-model projection exceeds "
            f"{MAX_ACTIVE_PROJECTION_FILE_BYTES} file bytes",
            projection_relpath,
        )
        return None
    projection = validator.load_json_object(
        projection_path, "ANALYSIS_PROBLEM_MODEL_PROJECTION"
    )
    if not isinstance(projection, dict):
        return None
    expected = build_active_problem_model_projection(
        model,
        source_path=validator.rel(model_path),
        source_sha256=validator.context.content_digest(model_path),
    )
    for failure in validate_active_problem_model_projection(
        projection, schema, expected=expected
    ):
        validator.error(
            "ANALYSIS_PROBLEM_MODEL_PROJECTION_INVALID",
            failure,
            projection_relpath,
        )
    return projection
