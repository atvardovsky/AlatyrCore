"""Target-validator scenarios for bounded analysis strategies."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from target_adapter_validation.analysis_strategies import validate_analysis_strategies
from analysis_strategy_contract import build_active_problem_model_projection

from .common import ROOT, validator, write_json


STATIC_PATHS = (
    ".ai/.gitignore",
    ".ai/assistant/context-router.json",
    ".ai/assistant/gates/analysis-strategy.md",
    ".ai/assistant/gates/index.json",
    ".ai/assistant/task-decomposition.json",
    ".ai/assistant/templates/operation-completion-evidence.json",
    ".ai/assistant/templates/problem-model.json",
    ".ai/assistant/templates/problem-model-active-projection.json",
    ".ai/assistant/analysis-strategies/index.json",
    ".ai/assistant/analysis-strategies/invariant-first.json",
    ".ai/assistant/analysis-strategies/hypothesis-driven.json",
    ".ai/assistant/analysis-strategies/architecture-comparison.json",
    ".ai/assistant/analysis-strategies/evidence-synthesis.json",
    ".ai/assistant/analysis-strategies/exploratory-design.json",
    ".ai/assistant/analysis-strategies/adversarial-review.json",
)


def _git(target: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=target,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _model() -> dict[str, object]:
    return {
        "schema_version": 2,
        "model_kind": "alatyr-bounded-problem-model",
        "model_id": "fixture-problem",
        "operation_id": "fixture-operation",
        "active_projection": {
            "schema_version": 1,
            "path": ".ai/.runtime/problem-model-projections/fixture-problem.json",
        },
        "primary_strategy_id": "invariant-first",
        "risk_classes": ["protected"],
        "protected_change": True,
        "required_review_ids": ["adversarial-review"],
        "review_results": [
            {
                "id": "adversarial-review",
                "status": "passed",
                "evidence_refs": ["fixture:review"],
            }
        ],
        "objective": "preserve the fixture invariant",
        "repository_binding": {
            "state": "available",
            "branch": "fixture",
            "base_revision": "fixture-revision",
        },
        "task_binding": {"task_ids": ["fixture-task"], "workstream_ids": []},
        "predecessor": {"state": "none", "model_id": "none", "sha256": "none"},
        "strategy_transitions": [],
        "non_goals": [],
        "facts": [],
        "assumptions": [],
        "unknowns": [],
        "changed_facts": [
            {
                "id": "change-1",
                "statement": "fixture behavior changes",
                "owner_ref": "fixture:owner",
                "evidence_refs": ["fixture:test"],
            }
        ],
        "invariants": [
            {
                "id": "invariant-1",
                "statement": "fixture remains valid",
                "owner_ref": "fixture:owner",
                "evidence_refs": ["fixture:test"],
                "status": "preserved",
            }
        ],
        "hypotheses": [],
        "alternatives": [],
        "proof_obligations": [
            {
                "id": "proof-1",
                "statement": "fixture invariant remains true",
                "evidence_owner": "primary",
                "acceptance_owner": "primary",
                "required": True,
                "status": "passed",
                "evidence_refs": ["fixture:test"],
                "waiver": None,
            }
        ],
        "counterexamples": [],
        "unresolved_decisions": [],
        "evidence_refs": ["fixture:test"],
    }


def _codes(target: Path, model_path: Path) -> set[str]:
    checked = validator(target, problem_models=[model_path])
    validate_analysis_strategies(checked)
    return {
        finding.code
        for finding in checked.findings
        if finding.level == "error" and finding.code.startswith("ANALYSIS_")
    }


def _write_model(target: Path, model_path: Path, model: dict[str, object]) -> None:
    write_json(model_path, model)
    projection_ref = model["active_projection"]
    assert isinstance(projection_ref, dict)
    projection_path = target / str(projection_ref["path"])
    projection = build_active_problem_model_projection(
        model,
        source_path=model_path.relative_to(target).as_posix(),
        source_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
    )
    write_json(projection_path, projection)


def run(target: Path, failures: list[str]) -> None:
    strategy_target = target / "analysis-strategies"
    strategy_target.mkdir(parents=True)
    for relpath in STATIC_PATHS:
        source = ROOT / "templates" / "target" / relpath
        destination = strategy_target / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    _git(strategy_target, "init")
    _git(strategy_target, "config", "user.email", "fixture@example.test")
    _git(strategy_target, "config", "user.name", "Fixture")
    _git(strategy_target, "add", ".")
    _git(strategy_target, "commit", "-m", "fixture baseline")

    model_path = strategy_target / ".ai/.runtime/problem-models/fixture.json"
    _write_model(strategy_target, model_path, _model())
    valid_codes = _codes(strategy_target, model_path)
    if valid_codes:
        failures.append(
            "valid analysis strategy fixture produced errors: "
            + ", ".join(sorted(valid_codes))
        )

    transitioned = _model()
    transitioned["assumptions"] = [
        {
            "id": "assumption-1",
            "statement": "historical fixture assumption",
            "evidence_refs": ["fixture:evidence"],
            "status": "invalidated",
        }
    ]
    transitioned["strategy_transitions"] = [
        {
            "from": "hypothesis-driven",
            "to": "invariant-first",
            "reason": "evidence changed the selected strategy",
            "evidence_refs": ["fixture:evidence"],
            "invalidated_assumption_ids": ["assumption-1"],
            "reopened_obligation_ids": ["proof-1"],
        }
    ]
    _write_model(strategy_target, model_path, transitioned)
    if _codes(strategy_target, model_path):
        failures.append(
            "historically reopened obligation could not later reach passed state"
        )

    projection_ref = transitioned["active_projection"]
    assert isinstance(projection_ref, dict)
    projection_path = strategy_target / str(projection_ref["path"])
    stale_projection = json.loads(projection_path.read_text(encoding="utf-8"))
    stale_projection["payload"]["objective"] = "stale projection"
    write_json(projection_path, stale_projection)
    if "ANALYSIS_PROBLEM_MODEL_PROJECTION_INVALID" not in _codes(
        strategy_target, model_path
    ):
        failures.append("stale active problem-model projection was not rejected")

    oversized_projection = dict(stale_projection)
    oversized_projection["padding"] = "x" * 70000
    write_json(projection_path, oversized_projection)
    if "ANALYSIS_PROBLEM_MODEL_PROJECTION_FILE_SIZE" not in _codes(
        strategy_target, model_path
    ):
        failures.append("oversized active projection file was not rejected")

    oversized = _model()
    oversized["objective"] = "word " * 20000
    write_json(model_path, oversized)
    if "ANALYSIS_PROBLEM_MODEL_INVALID" not in _codes(strategy_target, model_path):
        failures.append("oversized installed problem model was not rejected")

    open_model = _model()
    obligations = open_model["proof_obligations"]
    assert isinstance(obligations, list) and isinstance(obligations[0], dict)
    obligations[0]["status"] = "open"
    obligations[0]["evidence_refs"] = []
    _write_model(strategy_target, model_path, open_model)
    if "ANALYSIS_REQUIRED_OBLIGATION_OPEN" not in _codes(strategy_target, model_path):
        failures.append("open required proof obligation was not rejected")

    pending_review = _model()
    reviews = pending_review["review_results"]
    assert isinstance(reviews, list) and isinstance(reviews[0], dict)
    reviews[0]["status"] = "pending"
    reviews[0]["evidence_refs"] = []
    _write_model(strategy_target, model_path, pending_review)
    if "ANALYSIS_REQUIRED_REVIEW_OPEN" not in _codes(strategy_target, model_path):
        failures.append("pending adversarial review was not rejected")

    private_model = _model()
    private_model["private_reasoning"] = "must not be persisted"
    _write_model(strategy_target, model_path, private_model)
    private_codes = _codes(strategy_target, model_path)
    if "ANALYSIS_PROBLEM_MODEL_INVALID" not in private_codes:
        failures.append("private reasoning field was not rejected")

    descriptor_path = (
        strategy_target
        / ".ai/assistant/analysis-strategies/invariant-first.json"
    )
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    descriptor["id"] = "hypothesis-driven"
    write_json(descriptor_path, descriptor)
    if "ANALYSIS_STRATEGY_CATALOG" not in _codes(strategy_target, model_path):
        failures.append("strategy descriptor identity drift was not rejected")
