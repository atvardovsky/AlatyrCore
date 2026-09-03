#!/usr/bin/env python3
"""Plan the smallest quality-preserving AlatyrCore source work route."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from check_all import (
    default_changed_from,
    effective_baseline,
    environment_report,
    load_manifest,
    resolve_changed_from,
    resolved_command,
    select_check_plan,
    selection_report,
    source_identity,
)
from source_check_reuse import check_input_fingerprint, load_reuse_report, reuse_decisions
from source_state import source_snapshot


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROUTER = ROOT / "tools" / "source_context_router.json"
SOURCE_WORKER_POLICY = ROOT / "tools" / "source_worker_policy.json"
RUNTIME_CAPABILITY_STATES = ["unknown", "available", "unavailable"]
DELEGATION_DECISIONS = ["kept-local"]
SMALL_SOURCE_PROFILES = {"docs-local", "source-tooling"}


def _load_source_router() -> dict[str, Any]:
    router = json.loads(SOURCE_ROUTER.read_text(encoding="utf-8"))
    if not isinstance(router, dict) or not isinstance(router.get("profiles"), dict):
        raise ValueError("source context router must define profiles")
    return router


def _load_source_worker_policy() -> dict[str, Any]:
    policy = json.loads(SOURCE_WORKER_POLICY.read_text(encoding="utf-8"))
    if (
        not isinstance(policy, dict)
        or policy.get("schema_version") != 1
        or policy.get("policy_kind") != "alatyr-source-worker-policy"
    ):
        raise ValueError("source worker policy schema or kind is invalid")
    for field in [
        "workstreams",
        "worker_packet_contract",
        "decision_evidence",
        "runtime_capability_contract",
    ]:
        if not isinstance(policy.get(field), dict):
            raise ValueError(f"source worker policy must define {field}")
    return policy


def _load_source_tooling_context() -> dict[str, Any]:
    return _load_source_profile_context("source-tooling")


def _load_source_profile_context(source_profile: str) -> dict[str, Any]:
    router = _load_source_router()
    profiles = router.get("profiles", {})
    profile = profiles.get(source_profile)
    if not isinstance(profile, dict):
        raise ValueError(f"unknown source profile: {source_profile}")
    return {
        "source_profile": source_profile,
        "preloaded_context": router.get("preloaded_context", []),
        "bootstrap_context": router.get("bootstrap_context", []),
        "required_context": profile.get("required_context", []),
        "conditional_context": profile.get("conditional_context", []),
        "expansion_triggers": router.get("task_classification", {}).get(
            "expansion_triggers", []
        ),
    }


def _recommended_command(
    *,
    effective_profile: str,
    changed_from: str | None,
    from_ref: str | None,
    reuse_report: Path | None,
) -> list[str]:
    command = [sys.executable, "tools/check_all.py", "--profile", effective_profile]
    if effective_profile in {"micro", "fast"} and changed_from:
        command.extend(["--changed-from", changed_from])
    if from_ref:
        command.extend(["--from-ref", from_ref])
    if reuse_report:
        command.extend(["--reuse-report", str(reuse_report)])
    command.extend(
        ["--report", f"tmp/source-check-plan-result-{effective_profile}.json"]
    )
    return command


def _task_class(
    effective_profile: str,
    changed_paths: list[str],
    *,
    source_profile: str,
    explicit_small_scope: bool,
) -> str:
    if source_profile in {"repository-audit", "release-versioning"}:
        return "large-or-resumable"
    if (
        source_profile in SMALL_SOURCE_PROFILES
        and effective_profile in {"micro", "fast"}
        and changed_paths
    ):
        return "small-task"
    if effective_profile == "micro" and (changed_paths or explicit_small_scope):
        return "small-task"
    if effective_profile == "micro":
        return "standard-task"
    if effective_profile in {"quick", "fast"}:
        return "standard-task"
    return "large-or-resumable"


def _requested_validation_profiles(
    requested_profile: str,
    source_profile: str | None,
) -> tuple[str, list[str]]:
    if source_profile is None:
        selected = "micro" if requested_profile == "auto" else requested_profile
        return selected, []

    profile = _load_source_router()["profiles"].get(source_profile)
    if not isinstance(profile, dict):
        raise ValueError(f"unknown source profile: {source_profile}")
    routed_profile = profile.get("check_profile")
    if not isinstance(routed_profile, str) or not routed_profile:
        raise ValueError(f"source profile has no validation profile: {source_profile}")
    additional = profile.get("additional_check_profiles", [])
    if not isinstance(additional, list) or not all(
        isinstance(item, str) and item for item in additional
    ):
        raise ValueError(f"source profile has invalid additional profiles: {source_profile}")
    if requested_profile == "auto":
        return routed_profile, additional

    configured = {routed_profile, *additional}
    if requested_profile not in configured and requested_profile != "full":
        raise ValueError(
            f"validation profile {requested_profile} is weaker or incompatible with "
            f"source profile {source_profile}"
        )
    if requested_profile == "full" and requested_profile not in configured:
        remaining = list(additional)
    else:
        remaining = [
            item for item in [routed_profile, *additional] if item != requested_profile
        ]
    return requested_profile, remaining


def _decomposition(source_profile: str, task_class: str) -> dict[str, Any]:
    if source_profile == "repository-audit":
        router = _load_source_router()
        profile = router["profiles"][source_profile]
        route = profile.get("decomposition")
        if not isinstance(route, dict):
            raise ValueError("repository-audit must define decomposition routing")
        candidate_ids = route.get("candidate_workstreams")
        if not isinstance(candidate_ids, list) or not candidate_ids:
            raise ValueError("repository-audit must define candidate workstreams")
        policy = _load_source_worker_policy()
        policy_workstreams = policy["workstreams"]
        packet_contract = policy["worker_packet_contract"]
        workstreams: list[dict[str, Any]] = []
        for workstream_id in candidate_ids:
            workstream = policy_workstreams.get(workstream_id)
            if not isinstance(workstream_id, str) or not isinstance(workstream, dict):
                raise ValueError(
                    f"repository-audit references unknown workstream: {workstream_id}"
                )
            workstreams.append(
                {
                    "workstream_id": workstream_id,
                    "role_id": packet_contract["role_id"],
                    "objective": workstream["objective"],
                    "bounded_context": workstream["required_context"],
                    "conditional_context": workstream["conditional_context"],
                    "non_goals": workstream["non_goals"],
                    "allowed_actions": packet_contract["allowed_actions"],
                    "write_scope": packet_contract["write_scope"],
                    "expected_evidence": workstream["expected_evidence"],
                }
            )
        return {
            "required": True,
            "strategy": "bounded-independent-read-only-review",
            "candidate_workstreams": workstreams,
            "independent_worker_candidates": candidate_ids,
            "decision_contract": policy["decision_evidence"],
            "primary_critical_path": [
                "run authoritative source validation",
                "resolve conflicting findings",
                "perform final consistency synthesis",
            ],
        }

    return {
        "required": task_class == "large-or-resumable",
        "strategy": "primary-owned-until-bounded-workstreams-are-identified",
        "candidate_workstreams": [],
        "independent_worker_candidates": [],
        "primary_critical_path": ["plan and validate the selected source task"],
    }


def _validate_runtime_capability_record(
    record: dict[str, Any],
) -> dict[str, Any]:
    policy = _load_source_worker_policy()["runtime_capability_contract"]
    required_fields = policy["required_fields"]
    missing = [field for field in required_fields if field not in record]
    if missing:
        raise ValueError(f"worker capability record is missing fields: {missing}")
    expected_scalars = {
        "schema_version": policy["schema_version"],
        "status": policy["status"],
        "write_isolation": policy["write_isolation"],
        "result_delivery": policy["result_delivery"],
        "freshness": policy["freshness"],
    }
    for field, expected in expected_scalars.items():
        if record.get(field) != expected:
            raise ValueError(f"worker capability record requires {field}={expected!r}")
    for field in ["surface_id", "runtime_id", "model_binding", "evidence"]:
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"worker capability record has invalid {field}")
    if record.get("backend_kind") not in policy["backend_kinds"]:
        raise ValueError("worker capability record has unsupported backend_kind")
    role_ids = record.get("role_ids")
    if not isinstance(role_ids, list) or policy["required_role_id"] not in role_ids:
        raise ValueError("worker capability record lacks the read-only audit role")
    max_parallelism = record.get("max_parallelism")
    if (
        not isinstance(max_parallelism, int)
        or isinstance(max_parallelism, bool)
        or max_parallelism < policy["minimum_parallelism"]
    ):
        raise ValueError("worker capability record has insufficient parallelism")
    verified_at = record.get("verified_at")
    if not isinstance(verified_at, str):
        raise ValueError("worker capability record has invalid verified_at")
    try:
        datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("worker capability record has invalid verified_at") from exc
    return record


def _delegation_assessment(
    decomposition: dict[str, Any],
    *,
    runtime_capability: str,
    decision_override: str | None,
    skip_reason_id: str | None,
    reason: str | None,
    selected_workstream_ids: list[str] | None,
    runtime_capability_record: dict[str, Any] | None,
) -> dict[str, Any]:
    candidates = decomposition["independent_worker_candidates"]
    evaluation_required = len(candidates) >= 2
    if runtime_capability not in RUNTIME_CAPABILITY_STATES:
        raise ValueError(f"invalid worker runtime capability: {runtime_capability}")
    if decision_override not in {None, *DELEGATION_DECISIONS}:
        raise ValueError(f"invalid delegation decision: {decision_override}")

    selected_ids = list(selected_workstream_ids or [])
    unknown_ids = sorted(set(selected_ids) - set(candidates))
    if unknown_ids:
        raise ValueError(f"unknown selected worker workstreams: {unknown_ids}")
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("selected worker workstreams must be unique")

    decision_contract = decomposition.get("decision_contract", {})
    allowed_skip_reasons = set(decision_contract.get("skip_reason_ids", []))
    if skip_reason_id is not None and skip_reason_id not in allowed_skip_reasons:
        raise ValueError(f"invalid delegation skip reason: {skip_reason_id}")

    verified_capability: dict[str, Any] | None = None
    if runtime_capability_record is not None:
        if runtime_capability == "unavailable":
            raise ValueError("unavailable capability conflicts with an available record")
        verified_capability = _validate_runtime_capability_record(
            runtime_capability_record
        )
        runtime_capability = "available"
    elif runtime_capability == "available":
        raise ValueError("available worker capability requires a capability record")
    if runtime_capability != "available" and selected_ids:
        raise ValueError("worker workstreams require verified available capability")
    if decision_override == "kept-local" and selected_ids:
        raise ValueError("kept-local work cannot select worker workstreams")

    if not evaluation_required:
        if decision_override == "delegated" or selected_ids:
            raise ValueError("delegation requires at least two independent workstreams")
        decision = "primary-assistant"
        resolved_reason = reason or "no bounded independent worker set was identified"
        resolved_skip_reason = "insufficient-independent-work"
    elif runtime_capability == "unknown":
        if decision_override == "delegated":
            raise ValueError("delegation requires verified available worker capability")
        if decision_override == "kept-local":
            if skip_reason_id != "capability-unverified" or not reason:
                raise ValueError(
                    "kept-local with unknown capability requires "
                    "capability-unverified and a concrete reason"
                )
            decision = "kept-local"
            resolved_reason = reason
            resolved_skip_reason = skip_reason_id
        else:
            decision = "runtime-verification-required"
            resolved_reason = (
                "worker capability must be verified for independent audit workstreams"
            )
            resolved_skip_reason = None
    elif runtime_capability == "unavailable":
        if decision_override == "delegated":
            raise ValueError("unavailable worker capability cannot be delegated")
        decision = "kept-local"
        resolved_reason = reason or "the active assistant reported workers unavailable"
        resolved_skip_reason = skip_reason_id or "capability-unavailable"
        if resolved_skip_reason != "capability-unavailable":
            raise ValueError(
                "unavailable worker capability requires capability-unavailable"
            )
    elif decision_override == "kept-local":
        if skip_reason_id in {None, "capability-unavailable", "capability-unverified"}:
            raise ValueError("available workers kept local require an applicable skip reason")
        if not reason:
            raise ValueError("available workers kept local require a concrete reason")
        decision = "kept-local"
        resolved_reason = reason
        resolved_skip_reason = skip_reason_id
    else:
        if not selected_ids:
            selected_ids = list(candidates[:2])
        if len(selected_ids) < 2:
            raise ValueError("repository-audit delegation requires at least two workstreams")
        max_parallelism = verified_capability["max_parallelism"]
        if len(selected_ids) > max_parallelism:
            raise ValueError("selected workstreams exceed verified worker parallelism")
        decision = "delegation-recommended"
        resolved_reason = reason or "verified workers can execute independent audit workstreams"
        resolved_skip_reason = None

    reasons = [resolved_reason]
    if evaluation_required:
        reasons.insert(0, "multiple bounded independent workstreams are available")
    return {
        "evaluation_status": "required" if evaluation_required else "not-required",
        "evaluation_required": evaluation_required,
        "candidate": bool(candidates),
        "candidate_workstream_ids": candidates,
        "selected_workstream_ids": selected_ids,
        "runtime_capability_status": runtime_capability,
        "runtime_capability": runtime_capability,
        "runtime_capability_evidence": verified_capability,
        "decision": decision,
        "reason": resolved_reason,
        "skip_reason_id": resolved_skip_reason,
        "reasons": reasons,
        "fallback": "primary-assistant",
        "provider_probe_performed": False,
    }


def build_plan(
    *,
    requested_profile: str,
    changed_from: str | None,
    from_ref: str | None,
    reuse_report_path: Path | None,
    platform: str | None = None,
    source_profile: str | None = None,
    runtime_capability: str = "unknown",
    delegation_decision: str | None = None,
    delegation_skip_reason: str | None = None,
    delegation_reason: str | None = None,
    worker_workstream_ids: list[str] | None = None,
    runtime_capability_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks = load_manifest()
    selected_profile, additional_profiles = _requested_validation_profiles(
        requested_profile,
        source_profile,
    )
    resolved_changed_from = resolve_changed_from(selected_profile, changed_from)
    plan = select_check_plan(
        checks,
        selected_profile,
        resolved_changed_from,
        platform=platform,
    )
    baseline = effective_baseline(
        plan.effective_profile,
        resolved_changed_from,
        from_ref,
    )
    selected = plan.selected
    commands_by_id = {
        check["id"]: resolved_command(check, baseline) for check in selected
    }
    snapshot = source_snapshot(ROOT)
    input_fingerprints = {
        check["id"]: check_input_fingerprint(check, snapshot) for check in selected
    }
    previous_report = load_reuse_report(reuse_report_path) if reuse_report_path else None
    current_source = source_identity()
    current_environment = environment_report()
    reuse = reuse_decisions(
        selected=selected,
        previous_report=previous_report,
        current_source=current_source,
        current_environment=current_environment,
        input_fingerprints=input_fingerprints,
        commands_by_id=commands_by_id,
    )
    reusable_ids = [
        check_id for check_id, decision in reuse.items() if decision["reusable"] is True
    ]
    selection = selection_report(
        profile=selected_profile,
        changed_from=resolved_changed_from,
        plan=plan,
    )
    heavy_checks = [
        check["id"] for check in selected if check.get("resource_class") == "heavy"
    ]
    resolved_source_profile = source_profile or "source-tooling"
    task_class = _task_class(
        plan.effective_profile,
        plan.changed_paths,
        source_profile=resolved_source_profile,
        explicit_small_scope=requested_profile == "micro",
    )
    decomposition = _decomposition(resolved_source_profile, task_class)
    return {
        "schema_version": 1,
        "report_kind": "alatyr-source-minimum-work-plan",
        "scope": "source-repository",
        "source_profile": resolved_source_profile,
        "requested_source_profile": source_profile,
        "validation_profile": plan.effective_profile,
        "requested_profile": requested_profile,
        "effective_profile": plan.effective_profile,
        "task_class": task_class,
        "changed_from": resolved_changed_from,
        "changed_paths": plan.changed_paths,
        "selection": selection,
        "context_packet": (
            _load_source_tooling_context()
            if source_profile is None
            else _load_source_profile_context(source_profile)
        ),
        "decomposition": decomposition,
        "delegation_assessment": _delegation_assessment(
            decomposition,
            runtime_capability=runtime_capability,
            decision_override=delegation_decision,
            skip_reason_id=delegation_skip_reason,
            reason=delegation_reason,
            selected_workstream_ids=worker_workstream_ids,
            runtime_capability_record=runtime_capability_record,
        ),
        "check_plan": {
            "declared_check_ids": (
                _load_source_router()["profiles"][source_profile]["checks"]
                if source_profile is not None
                else []
            ),
            "selected_check_ids": [check["id"] for check in selected],
            "selected_check_count": len(selected),
            "heavy_check_ids": heavy_checks,
            "command": _recommended_command(
                effective_profile=plan.effective_profile,
                changed_from=resolved_changed_from,
                from_ref=from_ref,
                reuse_report=reuse_report_path,
            ),
            "additional_commands": [
                _recommended_command(
                    effective_profile=profile,
                    changed_from=resolved_changed_from,
                    from_ref=from_ref,
                    reuse_report=reuse_report_path,
                )
                for profile in additional_profiles
            ],
        },
        "validation_profiles": [plan.effective_profile, *additional_profiles],
        "reuse": {
            "reuse_report": str(reuse_report_path) if reuse_report_path else None,
            "reusable_check_ids": reusable_ids,
            "reusable_check_count": len(reusable_ids),
            "decisions": reuse,
        },
        "target_adapter_hint": {
            "first_step": "tools/alatyr.py support-delta --target <target-repo> --diff-ref <base>",
            "impact_step": "tools/alatyr.py impact --target <target-repo> --diff-ref <base> --fact-id <id>",
            "boundary": "target support hashes and impact routing select context; agents still re-derive semantic facts and invariants",
        },
        "quality_boundary": (
            "This plan narrows context and checks. It does not approve edits, "
            "publish changes, or replace logical integrity review."
        ),
    }


def render_summary(plan: dict[str, Any]) -> str:
    check_plan = plan["check_plan"]
    reuse = plan["reuse"]
    lines = [
        f"Source profile: {plan['source_profile']}",
        f"Task class: {plan['task_class']}",
        f"Validation profile: {plan['validation_profile']}",
        f"Effective profile: {plan['effective_profile']}",
        f"Changed paths: {len(plan['changed_paths'])}",
        f"Selected checks: {check_plan['selected_check_count']}",
        f"Reusable checks: {reuse['reusable_check_count']}",
    ]
    if plan["selection"].get("escalated_from_micro"):
        lines.append("Micro escalation: yes")
        for reason in plan["selection"].get("micro_escalation_reasons", []):
            lines.append(f"- {reason}")
    if check_plan["heavy_check_ids"]:
        lines.append("Heavy checks:")
        for check_id in check_plan["heavy_check_ids"]:
            lines.append(f"- {check_id}")
    delegation = plan["delegation_assessment"]
    lines.append(f"Delegation: {delegation['decision']}")
    commands = [check_plan["command"], *check_plan["additional_commands"]]
    lines.append("Recommended command:" if len(commands) == 1 else "Recommended commands:")
    for command in commands:
        if plan["selection"]["platform"] == "windows":
            lines.append(subprocess.list2cmdline(command))
        else:
            lines.append(shlex.join(command))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=["auto", "micro", "quick", "fast", "full", "change", "platform", "release"],
        default="auto",
    )
    parser.add_argument(
        "--source-profile",
        help="Source task profile from tools/source_context_router.json.",
    )
    parser.add_argument(
        "--worker-capability",
        choices=RUNTIME_CAPABILITY_STATES,
        default="unknown",
        help="Worker capability reported by the active assistant; no provider probe is performed.",
    )
    parser.add_argument(
        "--delegation-decision",
        choices=DELEGATION_DECISIONS,
        help="Optional current-plan worker decision after runtime verification.",
    )
    parser.add_argument(
        "--delegation-skip-reason",
        help="Policy reason ID required when eligible verified workers stay local.",
    )
    parser.add_argument(
        "--delegation-reason",
        help="Concrete evidence supporting an explicit delegation decision.",
    )
    parser.add_argument(
        "--worker-workstream",
        action="append",
        default=[],
        help="Selected source worker workstream ID; repeat for multiple workstreams.",
    )
    parser.add_argument(
        "--worker-capability-record",
        type=Path,
        help="Provider-neutral current-session worker capability evidence JSON.",
    )
    parser.add_argument(
        "--changed-from",
        help="Baseline for changed-path planning. Defaults to origin/main or HEAD for micro/fast.",
    )
    parser.add_argument("--from-ref", help="Baseline substituted into change checks.")
    parser.add_argument("--reuse-report", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    try:
        capability_record = None
        if args.worker_capability_record is not None:
            capability_record = json.loads(
                args.worker_capability_record.read_text(encoding="utf-8")
            )
            if not isinstance(capability_record, dict):
                raise ValueError("worker capability record must contain an object")
        changed_from = args.changed_from
        if args.profile == "auto" and changed_from is None:
            changed_from = default_changed_from()
        plan = build_plan(
            requested_profile=args.profile,
            changed_from=changed_from,
            from_ref=args.from_ref,
            reuse_report_path=args.reuse_report,
            source_profile=args.source_profile,
            runtime_capability=args.worker_capability,
            delegation_decision=args.delegation_decision,
            delegation_skip_reason=args.delegation_skip_reason,
            delegation_reason=args.delegation_reason,
            worker_workstream_ids=args.worker_workstream,
            runtime_capability_record=capability_record,
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if args.summary:
        print(render_summary(plan), end="")
    else:
        print(json.dumps(plan, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
