"""Typed read model for the source-owned installation context router."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SHA256_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
CONTRACT_ID_PATTERN = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
MINIMUM_CONTEXT_HEADROOM_RATIO = 0.20


@dataclass(frozen=True)
class InstallerStage:
    stage_id: str
    required_context: tuple[str, ...]
    conditional_context: tuple[str, ...]
    depends_on: tuple[str, ...]
    required_evidence: tuple[str, ...]
    required_outputs: tuple[str, ...]
    completion_checks: tuple[str, ...]
    context_budget_words: int
    authorization_ceiling: str
    prohibited_actions: tuple[str, ...]


@dataclass(frozen=True)
class InstallerStagePlan:
    schema_version: int
    stages: tuple[InstallerStage, ...]
    source_digest: str
    minimum_context_headroom_ratio: float
    output_contracts: tuple[tuple[str, str], ...]
    evidence_contracts: tuple[tuple[str, str], ...]
    completion_contracts: tuple[tuple[str, str], ...]

    def through(self, stage_id: str) -> tuple[InstallerStage, ...]:
        for index, stage in enumerate(self.stages):
            if stage.stage_id == stage_id:
                return self.stages[: index + 1]
        raise ValueError(f"unknown installer stage: {stage_id}")

    def required_output_ids_through(self, stage_id: str) -> tuple[str, ...]:
        return tuple(
            contract_id
            for stage in self.through(stage_id)
            for contract_id in stage.required_outputs
        )

    def required_evidence_ids_through(self, stage_id: str) -> tuple[str, ...]:
        return tuple(
            contract_id
            for stage in self.through(stage_id)
            for contract_id in stage.required_evidence
        )


@dataclass(frozen=True)
class InstallerContextBudget:
    stage_id: str
    required_words: int
    budget_words: int
    headroom_words: int
    headroom_ratio: float


@dataclass(frozen=True)
class CheckpointVerification:
    reusable: bool
    reasons: tuple[str, ...]


def _strings(value: Any, *, field: str, required: bool = False) -> tuple[str, ...]:
    if value is None and not required:
        return ()
    if not isinstance(value, list) or (required and not value) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"installer stage {field} must be a string list")
    return tuple(value)


def _contract_definitions(
    value: Any, *, field: str
) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"installer {field} must be a non-empty object")
    definitions: list[tuple[str, str]] = []
    for contract_id, description in value.items():
        if not isinstance(contract_id, str) or not CONTRACT_ID_PATTERN.fullmatch(
            contract_id
        ):
            raise ValueError(f"installer {field} contains invalid contract ID")
        if not isinstance(description, str) or len(description.split()) < 4:
            raise ValueError(
                f"installer {field}.{contract_id} must have a useful description"
            )
        definitions.append((contract_id, description))
    return tuple(definitions)


def _validate_contract_usage(
    stages: tuple[InstallerStage, ...],
    definitions: tuple[tuple[str, str], ...],
    *,
    field: str,
    stage_attribute: str,
) -> None:
    declared = {contract_id for contract_id, _description in definitions}
    used = [
        contract_id
        for stage in stages
        for contract_id in getattr(stage, stage_attribute)
    ]
    if len(used) != len(set(used)):
        raise ValueError(f"installer {field} contract IDs must have one owning stage")
    missing = sorted(set(used) - declared)
    unused = sorted(declared - set(used))
    if missing or unused:
        raise ValueError(
            f"installer {field} contract definitions differ from stage usage: "
            f"missing={missing}, unused={unused}"
        )


def load_installer_stage_plan(
    path: Path, *, source_root: Path | None = None
) -> InstallerStagePlan:
    """Load and close stage dependencies in declared routing order."""

    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("installer context router must contain an object")
    if data.get("schema_version") != 2:
        raise ValueError("installer context router schema_version must be 2")
    if data.get("router_kind") != "alatyr-installation-context-router":
        raise ValueError("installer context router kind is invalid")
    checkpoint_contract = data.get("checkpoint_contract")
    if (
        not isinstance(checkpoint_contract, dict)
        or checkpoint_contract.get("id")
        != "alatyr-installer-stage-checkpoint-v3"
    ):
        raise ValueError("installer checkpoint contract is invalid")
    headroom_ratio = data.get("minimum_required_context_headroom_ratio")
    if (
        not isinstance(headroom_ratio, (int, float))
        or isinstance(headroom_ratio, bool)
        or not MINIMUM_CONTEXT_HEADROOM_RATIO <= float(headroom_ratio) < 1
    ):
        raise ValueError(
            "installer minimum_required_context_headroom_ratio must be at least "
            f"{MINIMUM_CONTEXT_HEADROOM_RATIO:.2f} and less than 1"
        )
    contracts = data.get("contracts")
    if not isinstance(contracts, dict):
        raise ValueError("installer context router contracts must contain an object")
    output_contracts = _contract_definitions(
        contracts.get("outputs"), field="contracts.outputs"
    )
    evidence_contracts = _contract_definitions(
        contracts.get("evidence"), field="contracts.evidence"
    )
    completion_contracts = _contract_definitions(
        contracts.get("completion_checks"), field="contracts.completion_checks"
    )
    order = _strings(data.get("routing_order"), field="routing_order", required=True)
    entries = data.get("stages")
    if not isinstance(entries, dict) or set(entries) != set(order):
        raise ValueError("installer routing_order and stage IDs must match exactly")

    known: set[str] = set()
    stages: list[InstallerStage] = []
    for stage_id in order:
        if not CONTRACT_ID_PATTERN.fullmatch(stage_id):
            raise ValueError(f"installer stage ID is invalid: {stage_id}")
        entry = entries.get(stage_id)
        if not isinstance(entry, dict):
            raise ValueError(f"installer stage {stage_id} must contain an object")
        dependencies = _strings(entry.get("depends_on"), field=f"{stage_id}.depends_on")
        unknown = set(dependencies) - known
        if unknown:
            raise ValueError(
                f"installer stage {stage_id} depends on later or unknown stages: "
                f"{sorted(unknown)}"
            )
        context_budget_words = entry.get("context_budget_words")
        if (
            not isinstance(context_budget_words, int)
            or isinstance(context_budget_words, bool)
            or context_budget_words <= 0
        ):
            raise ValueError(
                f"installer stage {stage_id}.context_budget_words must be positive"
            )
        authorization_ceiling = entry.get("authorization_ceiling")
        if authorization_ceiling not in {"inspect", "modify"}:
            raise ValueError(
                f"installer stage {stage_id}.authorization_ceiling is invalid"
            )
        required_context = _strings(
            entry.get("required_context"), field=f"{stage_id}.required_context"
        )
        if len(required_context) != len(set(required_context)):
            raise ValueError(
                f"installer stage {stage_id}.required_context contains duplicates"
            )
        if not required_context and not dependencies:
            raise ValueError(
                f"installer stage {stage_id} needs context or a prior-stage dependency"
            )
        stages.append(
            InstallerStage(
                stage_id=stage_id,
                required_context=required_context,
                conditional_context=_strings(
                    entry.get("conditional_context"),
                    field=f"{stage_id}.conditional_context",
                ),
                depends_on=dependencies,
                required_evidence=_strings(
                    entry.get("required_evidence"),
                    field=f"{stage_id}.required_evidence",
                    required=True,
                ),
                required_outputs=_strings(
                    entry.get("required_outputs"),
                    field=f"{stage_id}.required_outputs",
                    required=True,
                ),
                completion_checks=_strings(
                    entry.get("completion_checks"),
                    field=f"{stage_id}.completion_checks",
                    required=True,
                ),
                context_budget_words=context_budget_words,
                authorization_ceiling=authorization_ceiling,
                prohibited_actions=_strings(
                    entry.get("prohibited_actions"),
                    field=f"{stage_id}.prohibited_actions",
                    required=True,
                ),
            )
        )
        known.add(stage_id)
    stage_tuple = tuple(stages)
    _validate_contract_usage(
        stage_tuple,
        output_contracts,
        field="output",
        stage_attribute="required_outputs",
    )
    _validate_contract_usage(
        stage_tuple,
        evidence_contracts,
        field="evidence",
        stage_attribute="required_evidence",
    )
    _validate_contract_usage(
        stage_tuple,
        completion_contracts,
        field="completion",
        stage_attribute="completion_checks",
    )
    plan = InstallerStagePlan(
        schema_version=2,
        stages=stage_tuple,
        source_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
        minimum_context_headroom_ratio=float(headroom_ratio),
        output_contracts=output_contracts,
        evidence_contracts=evidence_contracts,
        completion_contracts=completion_contracts,
    )
    if source_root is not None:
        validate_required_context_budgets(plan, source_root=source_root)
    return plan


def deterministic_word_count(text: str) -> int:
    """Count whitespace-delimited words consistently across supported hosts."""

    return len(text.split())


def required_context_budgets(
    plan: InstallerStagePlan, *, source_root: Path
) -> tuple[InstallerContextBudget, ...]:
    """Measure mandatory stage context without loading conditional sources."""

    usages: list[InstallerContextBudget] = []
    for stage in plan.stages:
        required_words = 0
        for relpath in stage.required_context:
            path = source_root / relpath
            if not path.is_file():
                raise ValueError(f"installer stage context is missing: {relpath}")
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise ValueError(
                    f"installer stage context cannot be read: {relpath}: {exc}"
                ) from exc
            required_words += deterministic_word_count(text)
        headroom_words = stage.context_budget_words - required_words
        usages.append(
            InstallerContextBudget(
                stage_id=stage.stage_id,
                required_words=required_words,
                budget_words=stage.context_budget_words,
                headroom_words=headroom_words,
                headroom_ratio=headroom_words / stage.context_budget_words,
            )
        )
    return tuple(usages)


def validate_required_context_budgets(
    plan: InstallerStagePlan, *, source_root: Path
) -> tuple[InstallerContextBudget, ...]:
    """Require every stage's mandatory context to retain declared headroom."""

    usages = required_context_budgets(plan, source_root=source_root)
    failures = [
        usage
        for usage in usages
        if usage.headroom_ratio + 1e-12 < plan.minimum_context_headroom_ratio
    ]
    if failures:
        details = ", ".join(
            f"{usage.stage_id}={usage.required_words}/{usage.budget_words} words "
            f"({usage.headroom_ratio:.1%} headroom)"
            for usage in failures
        )
        raise ValueError(
            "installer required context exceeds the minimum headroom: " + details
        )
    return usages


def _validate_digest(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise ValueError(
            f"installer checkpoint {field} must be canonical lowercase SHA-256"
        )
    return value


def _validate_digest_map(
    value: Any, *, field: str, required_ids: tuple[str, ...]
) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"installer checkpoint {field} must not be empty")
    observed_ids = set(value)
    expected_ids = set(required_ids)
    if observed_ids != expected_ids:
        raise ValueError(
            f"installer checkpoint {field} coverage differs from the stage contract: "
            f"missing={sorted(expected_ids - observed_ids)}, "
            f"unknown={sorted(observed_ids - expected_ids)}"
        )
    return {
        contract_id: _validate_digest(digest, field=f"{field}.{contract_id}")
        for contract_id, digest in value.items()
    }


def stage_checkpoint_identity(
    plan: InstallerStagePlan,
    stage_id: str,
    *,
    source_root: Path,
    target_revision: str,
    composition_digest: str,
    output_digests: dict[str, str],
    evidence_digests: dict[str, str],
) -> dict[str, Any]:
    """Bind a disposable checkpoint to source, target, outputs, and validation."""

    if not isinstance(target_revision, str) or not target_revision.strip():
        raise ValueError("installer checkpoint target_revision must be non-empty")
    composition_digest = _validate_digest(
        composition_digest, field="composition_digest"
    )
    checked_outputs = _validate_digest_map(
        output_digests,
        field="output_digests",
        required_ids=plan.required_output_ids_through(stage_id),
    )
    checked_evidence = _validate_digest_map(
        evidence_digests,
        field="evidence_digests",
        required_ids=plan.required_evidence_ids_through(stage_id),
    )

    stages = plan.through(stage_id)
    inputs: dict[str, str] = {}
    for stage in stages:
        for relpath in stage.required_context:
            path = source_root / relpath
            if not path.is_file():
                raise ValueError(f"installer stage context is missing: {relpath}")
            inputs[relpath] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "contract": "alatyr-installer-stage-checkpoint-v3",
        "router_digest": plan.source_digest,
        "completed_stage": stage_id,
        "required_input_digests": dict(sorted(inputs.items())),
        "target_revision": target_revision,
        "composition_digest": composition_digest,
        "output_digests": dict(sorted(checked_outputs.items())),
        "evidence_digests": dict(sorted(checked_evidence.items())),
        "authority": "optimization-only; never approval or semantic evidence",
    }


def verify_stage_checkpoint(
    checkpoint: Any,
    plan: InstallerStagePlan,
    stage_id: str,
    *,
    source_root: Path,
    target_revision: str,
    composition_digest: str,
    output_digests: dict[str, str],
    evidence_digests: dict[str, str],
) -> CheckpointVerification:
    """Verify whether a checkpoint is reusable for the exact current inputs."""

    expected = stage_checkpoint_identity(
        plan,
        stage_id,
        source_root=source_root,
        target_revision=target_revision,
        composition_digest=composition_digest,
        output_digests=output_digests,
        evidence_digests=evidence_digests,
    )
    if not isinstance(checkpoint, dict):
        return CheckpointVerification(False, ("checkpoint must contain an object",))
    reasons: list[str] = []
    for field in expected:
        if checkpoint.get(field) != expected[field]:
            reasons.append(f"checkpoint {field} does not match current inputs")
    unknown = sorted(set(checkpoint) - set(expected))
    if unknown:
        reasons.append(f"checkpoint contains unknown fields: {unknown}")
    return CheckpointVerification(not reasons, tuple(reasons))
