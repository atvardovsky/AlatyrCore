"""Target-validator scenarios for bounded analysis strategies."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from target_adapter_validation.analysis_strategies import validate_analysis_strategies

from .common import ROOT, validator, write_json


STATIC_PATHS = (
    ".ai/.gitignore",
    ".ai/assistant/context-router.json",
    ".ai/assistant/gates/analysis-strategy.md",
    ".ai/assistant/gates/index.json",
    ".ai/assistant/task-decomposition.json",
    ".ai/assistant/templates/operation-completion-evidence.json",
    ".ai/assistant/templates/problem-model.json",
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
        "schema_version": 1,
        "model_kind": "alatyr-bounded-problem-model",
        "model_id": "fixture-problem",
        "operation_id": "fixture-operation",
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
    write_json(model_path, _model())
    valid_codes = _codes(strategy_target, model_path)
    if valid_codes:
        failures.append(
            "valid analysis strategy fixture produced errors: "
            + ", ".join(sorted(valid_codes))
        )

    open_model = _model()
    obligations = open_model["proof_obligations"]
    assert isinstance(obligations, list) and isinstance(obligations[0], dict)
    obligations[0]["status"] = "open"
    obligations[0]["evidence_refs"] = []
    write_json(model_path, open_model)
    if "ANALYSIS_REQUIRED_OBLIGATION_OPEN" not in _codes(strategy_target, model_path):
        failures.append("open required proof obligation was not rejected")

    pending_review = _model()
    reviews = pending_review["review_results"]
    assert isinstance(reviews, list) and isinstance(reviews[0], dict)
    reviews[0]["status"] = "pending"
    reviews[0]["evidence_refs"] = []
    write_json(model_path, pending_review)
    if "ANALYSIS_REQUIRED_REVIEW_OPEN" not in _codes(strategy_target, model_path):
        failures.append("pending adversarial review was not rejected")

    private_model = _model()
    private_model["private_reasoning"] = "must not be persisted"
    write_json(model_path, private_model)
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
