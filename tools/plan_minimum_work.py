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

from path_spec import PathDialect, matches_any

from check_all import (
    SelectionResult,
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
from source_worker_contract import (
    load_source_worker_policy,
    make_builtin_packet,
    validate_decision_evidence,
    validate_runtime_capability,
    validate_worker_packet,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROUTER = ROOT / "tools" / "source_context_router.json"
SOURCE_WORKER_POLICY = ROOT / "tools" / "source_worker_policy.json"
RUNTIME_CAPABILITY_STATES = ["unknown", "available", "unavailable"]
DELEGATION_DECISIONS = ["kept-local"]


def _load_source_router() -> dict[str, Any]:
    router = json.loads(SOURCE_ROUTER.read_text(encoding="utf-8"))
    if not isinstance(router, dict) or not isinstance(router.get("profiles"), dict):
        raise ValueError("source context router must define profiles")
    return router


def _load_source_worker_policy() -> dict[str, Any]:
    return load_source_worker_policy(SOURCE_WORKER_POLICY, root=ROOT)


def _load_source_tooling_context() -> dict[str, Any]:
    return _load_source_profile_context("source-tooling")


def _load_source_profile_context(
    source_profile: str,
    *,
    changed_paths: list[str] | None = None,
    selection_details: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    router = _load_source_router()
    profiles = router.get("profiles", {})
    profile = profiles.get(source_profile)
    if not isinstance(profile, dict):
        raise ValueError(f"unknown source profile: {source_profile}")
    required = [*router.get("preloaded_context", []), *router.get("bootstrap_context", []), *profile.get("required_context", [])]
    selectors = {
        "changed_paths": sorted(changed_paths or []),
        "check_ids": sorted((selection_details or {}).keys()),
    }
    return {
        "source_profile": source_profile,
        "preloaded_context": router.get("preloaded_context", []),
        "bootstrap_context": router.get("bootstrap_context", []),
        "required_context": profile.get("required_context", []),
        "conditional_context": profile.get("conditional_context", []),
        "selected_items": [
            {"path": path, "reason": ["source-profile:" + source_profile]}
            for path in dict.fromkeys(required)
        ],
        "selectors": selectors,
        "omitted_candidates": profile.get("conditional_context", []),
        "unresolved_selector_behavior": "load the canonical owner and report the routing gap",
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
    command_baseline = from_ref
    if effective_profile == "release" and command_baseline is None:
        command_baseline = changed_from
    if command_baseline:
        command.extend(["--from-ref", command_baseline])
    if reuse_report:
        command.extend(["--reuse-report", str(reuse_report)])
    command.extend(
        ["--report", f"tmp/source-check-plan-result-{effective_profile}.json"]
    )
    return command


def _matches_any(path: str, patterns: list[str]) -> bool:
    return matches_any(path, patterns, dialect=PathDialect.PORTABLE_FNMATCH_V1)


def _task_classification(
    selection: SelectionResult,
    *,
    source_profile: str,
    explicit_small_scope: bool,
) -> dict[str, Any]:
    router = _load_source_router()
    contract = router["task_classification"]["small_task_eligibility"]
    changed_paths = selection.changed_paths
    reasons: list[str] = []
    if source_profile in {"repository-audit", "release-versioning"}:
        return {
            "task_class": "large-or-resumable",
            "small_task_eligible": False,
            "reasons": [f"{source_profile} is always large-or-resumable"],
        }

    boundary_paths = [
        path
        for path in changed_paths
        if _matches_any(path, contract["boundary_path_patterns"])
    ]
    if boundary_paths:
        return {
            "task_class": "large-or-resumable",
            "small_task_eligible": False,
            "reasons": [f"boundary paths require expansion: {boundary_paths}"],
        }
    if selection.effective_profile not in {"micro", "fast"}:
        return {
            "task_class": "large-or-resumable",
            "small_task_eligible": False,
            "reasons": [
                f"validation profile {selection.effective_profile} is not bounded"
            ],
        }

    profile_contract = contract["profiles"].get(source_profile)
    if not isinstance(profile_contract, dict):
        reasons.append(f"source profile {source_profile} is not small-task enabled")
    if not changed_paths:
        reasons.append("no changed path proves a bounded task")
    if len(changed_paths) > contract["maximum_changed_paths"]:
        reasons.append("changed path count exceeds the small-task limit")
    if contract.get("requires_no_unmatched_paths") is True and (
        selection.unmatched_changed_paths
    ):
        reasons.append("unmatched changed paths require conservative routing")
    if contract.get("requires_no_full_fallback") is True and selection.fell_back_to_full:
        reasons.append("full-profile fallback prevents small-task classification")
    if selection.escalated_from_micro:
        reasons.append("micro escalation prevents small-task classification")
    if isinstance(profile_contract, dict):
        disallowed = [
            path
            for path in changed_paths
            if not _matches_any(path, profile_contract["allowed_path_patterns"])
        ]
        if disallowed:
            reasons.append(f"paths are outside the selected source profile: {disallowed}")
    if contract.get("requires_focused_check_coverage") is True:
        covered_paths = {
            path
            for detail in selection.selection_details.values()
            if isinstance(detail, dict)
            for path in detail.get("matched_changed_paths", [])
            if isinstance(path, str)
        }
        uncovered = sorted(set(changed_paths) - covered_paths)
        if changed_paths and uncovered:
            reasons.append(f"focused checks do not cover changed paths: {uncovered}")
    if explicit_small_scope and not changed_paths:
        reasons.append("explicit micro scope lacks changed-path evidence")

    eligible = not reasons
    return {
        "task_class": "small-task" if eligible else "standard-task",
        "small_task_eligible": eligible,
        "reasons": reasons or ["all structured small-task predicates passed"],
    }


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


def _decomposition(
    source_profile: str,
    task_class: str,
    *,
    task_worker_packets: list[dict[str, Any]] | None,
) -> dict[str, Any]:
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
        if task_worker_packets:
            raise ValueError("repository-audit uses policy workstreams, not task packets")
        workstreams = [make_builtin_packet(policy, item) for item in candidate_ids]
        return {
            "required": True,
            "strategy": "bounded-independent-read-only-review",
            "candidate_workstreams": workstreams,
            "independent_worker_candidates": candidate_ids,
            "decision_contract": policy["decision_evidence"],
            "workstream_identification_required": False,
            "primary_critical_path": [
                "run authoritative source validation",
                "resolve conflicting findings",
                "perform final consistency synthesis",
            ],
        }

    if task_worker_packets and task_class != "large-or-resumable":
        raise ValueError("task worker packets are accepted only for large-or-resumable work")
    if task_class == "large-or-resumable":
        policy = _load_source_worker_policy()
        packet_contract = policy["worker_packet_contract"]
        workstreams = [
            validate_worker_packet(packet, packet_contract, root=ROOT)
            for packet in (task_worker_packets or [])
        ]
        workstream_ids = [packet["workstream_id"] for packet in workstreams]
        independence_keys = [packet["independence_key"] for packet in workstreams]
        if len(workstream_ids) != len(set(workstream_ids)):
            raise ValueError("task worker packet workstream IDs must be unique")
        if len(independence_keys) != len(set(independence_keys)):
            raise ValueError("task worker packet independence keys must be unique")
        return {
            "required": True,
            "strategy": (
                "bounded-independent-read-only-review"
                if len(workstreams) >= policy["activation"]["minimum_independent_packets"]
                else "workstream-identification-required"
            ),
            "candidate_workstreams": workstreams,
            "independent_worker_candidates": workstream_ids,
            "decision_contract": policy["decision_evidence"],
            "workstream_identification_required": len(workstreams)
            < policy["activation"]["minimum_independent_packets"],
            "primary_critical_path": [
                "identify bounded independent workstreams when fewer than two are supplied",
                "retain all decisions, synthesis, mutations, and validation",
            ],
        }

    return {
        "required": False,
        "strategy": "primary-assistant",
        "candidate_workstreams": [],
        "independent_worker_candidates": [],
        "workstream_identification_required": False,
        "primary_critical_path": ["plan and validate the selected source task"],
    }


def _validate_runtime_capability_record(
    record: dict[str, Any],
    *,
    session_id: str,
    now: datetime | None,
) -> dict[str, Any]:
    policy = _load_source_worker_policy()["runtime_capability_contract"]
    return validate_runtime_capability(record, policy, session_id=session_id, now=now)


def _delegation_assessment(
    decomposition: dict[str, Any],
    *,
    runtime_capability: str,
    decision_override: str | None,
    skip_reason_id: str | None,
    reason: str | None,
    selected_workstream_ids: list[str] | None,
    runtime_capability_record: dict[str, Any] | None,
    worker_session_id: str | None,
    now: datetime | None,
) -> dict[str, Any]:
    candidates = decomposition["independent_worker_candidates"]
    has_independent_set = len(candidates) >= 2
    evaluation_required = bool(decomposition["required"])
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
            runtime_capability_record,
            session_id=worker_session_id or "",
            now=now,
        )
        runtime_capability = "available"
    elif runtime_capability == "available":
        raise ValueError("available worker capability requires a capability record")
    elif worker_session_id is not None:
        raise ValueError("worker session binding requires a capability record")
    if runtime_capability != "available" and selected_ids:
        raise ValueError("worker workstreams require verified available capability")
    if decision_override == "kept-local" and selected_ids:
        raise ValueError("kept-local work cannot select worker workstreams")

    if decomposition["required"] and not has_independent_set:
        if decision_override is not None or selected_ids:
            raise ValueError(
                "large work without two independent packets requires workstream identification"
            )
        decision = "workstream-identification-required"
        resolved_reason = "identify at least two bounded independent read-only workstreams"
        resolved_skip_reason = "insufficient-independent-work"
    elif not evaluation_required:
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
            raise ValueError("delegation requires at least two independent workstreams")
        max_parallelism = verified_capability["max_parallelism"]
        if len(selected_ids) > max_parallelism:
            raise ValueError("selected workstreams exceed verified worker parallelism")
        decision = "delegation-recommended"
        resolved_reason = reason or "verified workers can execute independent workstreams"
        resolved_skip_reason = None

    reasons = [resolved_reason]
    if has_independent_set:
        reasons.insert(0, "multiple bounded independent workstreams are available")
    evidence = {
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
    if decision_contract:
        validate_decision_evidence(evidence, decision_contract)
    return evidence


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
    worker_session_id: str | None = None,
    task_worker_packets: list[dict[str, Any]] | None = None,
    now: datetime | None = None,
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
    classification = _task_classification(
        plan,
        source_profile=resolved_source_profile,
        explicit_small_scope=requested_profile == "micro",
    )
    task_class = classification["task_class"]
    decomposition = _decomposition(
        resolved_source_profile,
        task_class,
        task_worker_packets=task_worker_packets,
    )
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
        "task_classification": classification,
        "changed_from": resolved_changed_from,
        "changed_paths": plan.changed_paths,
        "selection": selection,
        "context_packet": (
            _load_source_profile_context(
                "source-tooling",
                changed_paths=plan.changed_paths,
                selection_details=plan.selection_details,
            )
            if source_profile is None
            else _load_source_profile_context(
                source_profile,
                changed_paths=plan.changed_paths,
                selection_details=plan.selection_details,
            )
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
            worker_session_id=worker_session_id,
            now=now,
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
        "--worker-session-id",
        help="Opaque current-session binding shared with the capability record.",
    )
    parser.add_argument(
        "--worker-packet",
        action="append",
        type=Path,
        default=[],
        help="Task-specific inspect-only worker packet JSON; repeat for large work.",
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
        task_worker_packets = []
        for packet_path in args.worker_packet:
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            if not isinstance(packet, dict):
                raise ValueError(f"worker packet must contain an object: {packet_path}")
            task_worker_packets.append(packet)
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
            worker_session_id=args.worker_session_id,
            task_worker_packets=task_worker_packets,
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if args.summary:
        print(render_summary(plan), end="")
    else:
        print(json.dumps(plan, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
