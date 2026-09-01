#!/usr/bin/env python3
"""Plan the smallest quality-preserving AlatyrCore source work route."""

from __future__ import annotations

import argparse
import json
import sys
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


def _load_source_tooling_context() -> dict[str, Any]:
    router = json.loads(SOURCE_ROUTER.read_text(encoding="utf-8"))
    profiles = router.get("profiles", {})
    profile = profiles.get("source-tooling", {}) if isinstance(profiles, dict) else {}
    return {
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
    command = ["python3", "tools/check_all.py", "--profile", effective_profile]
    if effective_profile in {"micro", "fast"} and changed_from:
        command.extend(["--changed-from", changed_from])
    if from_ref:
        command.extend(["--from-ref", from_ref])
    if reuse_report:
        command.extend(["--reuse-report", str(reuse_report)])
    command.extend(["--report", "tmp/source-check-plan-result.json"])
    return command


def _task_class(effective_profile: str, selected_count: int) -> str:
    if effective_profile == "micro":
        return "small-task"
    if effective_profile in {"quick", "fast"} and selected_count <= 8:
        return "standard-task"
    return "large-or-resumable"


def build_plan(
    *,
    requested_profile: str,
    changed_from: str | None,
    from_ref: str | None,
    reuse_report_path: Path | None,
    platform: str | None = None,
) -> dict[str, Any]:
    checks = load_manifest()
    selected_profile = "micro" if requested_profile == "auto" else requested_profile
    resolved_changed_from = resolve_changed_from(selected_profile, changed_from)
    baseline = effective_baseline(selected_profile, resolved_changed_from, from_ref)
    plan = select_check_plan(
        checks,
        selected_profile,
        resolved_changed_from,
        platform=platform,
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
    return {
        "schema_version": 1,
        "report_kind": "alatyr-source-minimum-work-plan",
        "scope": "source-repository",
        "requested_profile": requested_profile,
        "effective_profile": plan.effective_profile,
        "task_class": _task_class(plan.effective_profile, len(selected)),
        "changed_from": resolved_changed_from,
        "changed_paths": plan.changed_paths,
        "selection": selection,
        "context_packet": _load_source_tooling_context(),
        "check_plan": {
            "selected_check_ids": [check["id"] for check in selected],
            "selected_check_count": len(selected),
            "heavy_check_ids": heavy_checks,
            "command": _recommended_command(
                effective_profile=plan.effective_profile,
                changed_from=resolved_changed_from,
                from_ref=from_ref,
                reuse_report=reuse_report_path,
            ),
        },
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
        f"Task class: {plan['task_class']}",
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
    lines.append("Recommended command:")
    lines.append(" ".join(check_plan["command"]))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=["auto", "micro", "quick", "fast", "full", "change", "platform", "release"],
        default="auto",
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
        changed_from = args.changed_from
        if args.profile == "auto" and changed_from is None:
            changed_from = default_changed_from()
        plan = build_plan(
            requested_profile=args.profile,
            changed_from=changed_from,
            from_ref=args.from_ref,
            reuse_report_path=args.reuse_report,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if args.summary:
        print(render_summary(plan), end="")
    else:
        print(json.dumps(plan, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
