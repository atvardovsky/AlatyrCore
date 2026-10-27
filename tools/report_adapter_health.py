#!/usr/bin/env python3
"""Report compact read-only health for an installed Alatyr target adapter."""

from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path
from typing import Any

from capability_catalog import load_modules
from adapter_health_views import finding_groups, tooling_comparison, work_overview

from validate_target_adapter import (
    AdapterValidatorConfig,
    BLOCKING_WARNING_CODES,
    Validator,
    findings_payload,
    load_validator_config,
)


def build_capability_advisory(
    *,
    target: Path,
    framework_source: Path | None,
    required_capabilities: list[str] | None,
) -> dict[str, Any]:
    requested = sorted(set(required_capabilities or []))
    advisory: dict[str, Any] = {
        "requested": requested,
        "missing_from_installation": [],
        "available_in_source": [],
        "unknown_to_source": [],
        "blocking": False,
        "comparison_basis": "module-ids-only",
        "limitation": "Catalog membership does not establish current contracts, target adoption or exercised evidence.",
    }
    if framework_source is None:
        if requested:
            advisory["blocking"] = True
            advisory["source_catalog_error"] = (
                "--framework-source is required for capability comparison"
            )
        return advisory

    source_catalog = framework_source / "framework" / "capabilities.json"
    target_catalog = target / ".ai" / "framework" / "capabilities.json"
    try:
        source_ids = set(load_modules(source_catalog))
    except (OSError, ValueError, json.JSONDecodeError):
        source_ids = set()
        advisory["source_catalog_error"] = str(source_catalog)
    try:
        installed_ids = set(load_modules(target_catalog))
    except (OSError, ValueError, json.JSONDecodeError):
        installed_ids = set()
        advisory["installed_catalog_error"] = str(target_catalog)
    advisory["available_in_source"] = sorted(source_ids - installed_ids)
    advisory["missing_from_installation"] = sorted(
        (set(requested) & source_ids) - installed_ids
    )
    advisory["unknown_to_source"] = sorted(set(requested) - source_ids)
    advisory["blocking"] = bool(
        advisory["missing_from_installation"] or advisory["unknown_to_source"]
    )
    return advisory


def health_payload(
    *,
    target: Path,
    framework_source: Path | None = None,
    validation_phase: str = "acceptance",
    allow_placeholders: bool = False,
    strict_warnings: bool = False,
    allow_local_paths: list[str] | None = None,
    config_path: Path | None = None,
    required_capabilities: list[str] | None = None,
    include_incident_frontier: bool = False,
    current_task_id: str | None = None,
    include_work_overview: bool = False,
) -> dict[str, Any]:
    phase = "migration-staging" if allow_placeholders else validation_phase
    config, config_findings = load_validator_config(target, config_path)
    validator = Validator(
        target,
        framework_source=framework_source,
        diff_ref=None,
        approval_records=[],
        enforce_approval_scope=False,
        change_packages=[],
        enforce_change_package=False,
        migration_diff=None,
        allow_placeholders=allow_placeholders,
        allow_local_paths=allow_local_paths or [],
        config=config,
        initial_findings=config_findings,
        validation_phase=phase,
        approval_archive_mode="changed",
    )
    findings = validator.run()
    task_view = None
    if current_task_id is not None:
        from current_task_view import current_task_view
        task_view = current_task_view(validator, current_task_id)
        if task_view["state"] == "unknown":
            validator.error("ACTIVE_TASK_BINDING", "selected task disposition is unavailable; inspect current_task diagnostics", ".ai/assistant/active-tasks.json")
    payload = findings_payload(
        findings,
        target=target.resolve(),
        strict_warnings=strict_warnings,
        validation_phase=phase,
        installation_state=validator.installation_state,
        phase_telemetry=validator.phase_telemetry,
        approval_archive_summary=validator.approval_archive_summary,
    )
    advisory = build_capability_advisory(
        target=target,
        framework_source=framework_source,
        required_capabilities=required_capabilities,
    )
    payload["capability_advisory"] = advisory
    payload["tooling_comparison"] = tooling_comparison(validator.context, Path(__file__).resolve().parents[1])
    if include_work_overview:
        payload["work_overview"] = work_overview(validator.context)
    if task_view is not None:
        payload["current_task"] = task_view
    if include_incident_frontier:
        from incident_planning import incident_frontier
        path = validator.target_path(".ai/assistant/active-tasks.json")
        read = validator.context.read_bytes_result(path, max_bytes=512 * 1024)
        try:
            index = json.loads(read.value) if read.value is not None else None
        except (ValueError, UnicodeError, RecursionError):
            index = None
        payload["incident_frontier"] = incident_frontier(index)
        payload["incident_frontier"]["index_sha256"] = hashlib.sha256(read.value).hexdigest() if read.value is not None else None
    if advisory["blocking"]:
        payload.setdefault("adapter_health", {})["state"] = "blocked"
        placeholder = payload.setdefault("placeholder_validation", {})
        placeholder["acceptance_eligible"] = False
        blockers = placeholder.setdefault("acceptance_blockers", [])
        blockers.append("required capability is unavailable in the installed adapter")
        payload["exit_code"] = 1
    return payload


def finding_line(finding: dict[str, Any]) -> str:
    code = finding.get("code", "<unknown>")
    message = finding.get("message", "")
    path = finding.get("path")
    suffix = f" [{path}]" if path else ""
    return f"- {code}: {message}{suffix}"


def render_text(payload: dict[str, Any], *, mode: str = "doctor") -> str:
    health = payload.get("adapter_health", {})
    layers = payload.get("health_layers", {})
    evidence = payload.get("evidence", {})
    counts = payload.get("counts", {})
    placeholder = payload.get("placeholder_validation", {})
    findings = [
        item for item in payload.get("findings", []) if isinstance(item, dict)
    ]
    blocking = [
        item for item in findings if item.get("level") == "error"
        or (
            item.get("level") == "warning"
            and item.get("code") in BLOCKING_WARNING_CODES
        )
    ]
    attention = [
        item for item in findings
        if item.get("level") == "warning" and item not in blocking
    ]
    repairs = health.get("repair_operations") or []
    advisory = payload.get("capability_advisory", {})
    accepted = placeholder.get("acceptance_eligible") is True

    def display(value: Any) -> str:
        return str(value) if value not in {None, ""} else "unavailable"

    lines = [
        f"Alatyr adapter health: {display(health.get('state'))}",
        f"Installation state: {display(payload.get('installation_state'))}",
        (
            "Health layers: "
            f"installation={display(layers.get('installation', {}).get('state'))} "
            f"support={display(layers.get('support', {}).get('state'))} "
            f"current_change={display(layers.get('current_change', {}).get('state'))}"
        ),
        f"Validation phase: {display(payload.get('validation_phase'))}",
        f"Acceptance eligible: {'yes' if accepted else 'no'}",
        f"Evidence basis: {display(evidence.get('basis'))}",
        f"Observed revision: {display(evidence.get('observed_revision'))}",
        f"Observed branch: {display(evidence.get('observed_branch'))}",
        (
            "Findings: "
            f"errors={counts.get('errors', 0)} "
            f"blocking_warnings={counts.get('blocking_warnings', 0)} "
            f"warnings={counts.get('warnings', 0)} "
            f"info={counts.get('info', 0)}"
        ),
        (
            "Repair operations: "
            + (
                ", ".join(repairs[:3])
                if repairs and mode == "doctor"
                else "run doctor for prioritized repair routes"
                if repairs
                else "none"
            )
        ),
        "Automatic repair performed: false",
    ]
    comparison = payload.get("tooling_comparison")
    if isinstance(comparison, dict):
        lines.append("Tooling baseline: " + comparison["state"])
        lines.append("Producer versions: " + json.dumps(comparison["producer_versions"], sort_keys=True))
        lines.append("Installed versions: " + json.dumps(comparison["installed_versions"], sort_keys=True))
        if comparison["state"] == "different-tooling-baseline":
            lines.append("Next: assess-upgrade; migration comparison does not prove corruption of the installed baseline. Existing findings still apply.")
    missing = advisory.get("missing_from_installation") or []
    unknown = advisory.get("unknown_to_source") or []
    available = advisory.get("available_in_source") or []
    if missing:
        lines.append("Required capabilities missing from installation: " + ", ".join(missing))
    if unknown:
        lines.append("Unknown required capabilities: " + ", ".join(unknown))
    if available and mode == "doctor":
        lines.append("Capabilities available after assessment/update: " + ", ".join(available))
    limitation = evidence.get("limitation")
    if isinstance(limitation, str) and limitation:
        lines.append(f"Limitation: {limitation}")
    frontier = payload.get("incident_frontier")
    if isinstance(frontier, dict):
        lines.append("Incident frontier: " + str(frontier.get("state", "unknown")))
        lines.append("Active tasks retained: " + str(len(frontier.get("retained_active", []))))
        lines.append("Frontier task IDs: " + ", ".join(frontier.get("frontier", [])[:4]))
        lines.append("Retained active ancestor IDs: " + ", ".join(frontier.get("active_ancestor_ids", [])[:4]))
        lines.append("Declared failed gates: " + ", ".join(frontier.get("declared_failed_gates", [])[:4]))
        lines.extend("Frontier issue: " + str(error)[:480] for error in frontier.get("errors", [])[:2])
        lines.append("Frontier is navigation only; all ancestor duties and canonical checks remain.")
    current = payload.get("current_task")
    if current is not None:
        lines.extend(["", "Selected task: " + str(current["task_id"]),
                      "Disposition: " + current["state"] + " (not acceptance)"])
        if "delivery" in current:
            lines.append("Recorded delivery: " + json.dumps(current["delivery"], sort_keys=True))
        outcome = current.get("incident_outcome")
        if isinstance(outcome, dict):
            original = outcome.get("original_case")
            lines.append("Original incident outcome: " + outcome["state"])
            if isinstance(original, dict):
                lines.append("Original expected outcome: " + original["expected_outcome"])
                lines.append("Original case source: " + original["source_ref"])
            lines.append("Component passes do not establish original-outcome acceptance.")
        readiness = current.get("execution_readiness", {})
        focus = current.get("execution_focus", {})
        if focus:
            lines.append("Execution focus: " + focus["state"] + " (not authorization)")
            lines.extend("Re-anchor: " + row["reason"] for row in focus.get("reanchor_signals", []))
            action = focus.get("next_action")
            if action is not None:
                lines.append("Proposed obligation: " + action["obligation_id"])
                lines.append("Completion condition: " + action["completion_condition"])
            if focus.get("recovery"):
                lines.append("Focus recovery: " + focus["recovery"])
        lines.append("Declared ready obligations: " + ", ".join(readiness.get("ready", [])))
        controls = current.get("incident_controls", {})
        lines.append("Repair review: " + controls.get("adoption", "unknown") + "; evidence: " + current["repair_evidence"]["state"])
        lines.extend("- " + item for item in current["diagnostics"][:8])
        preflight = current.get("repair_preflight")
        if isinstance(preflight, dict):
            lines.append("Related repair preflight: " + preflight["state"])
            lines.append("Next incident action: " + preflight["next_action"])
    overview = payload.get("work_overview")
    if isinstance(overview, dict):
        lines.append("Active analysis tasks: " + str(overview["analysis_tasks"]["active_count"]))
        lines.append("Reported team claims: " + str(overview["team_claims"]["reported_entries"]) + " (freshness not verified)")
        lines.append(overview["limitation"])
    if mode == "status" and findings:
        lines.append("Finding details: run doctor for prioritized findings")
        return "\n".join(lines) + "\n"

    if blocking:
        lines.append("")
        lines.append("Blocking findings:")
        groups = finding_groups(blocking)
        lines.extend(finding_line(item) + (f" ({item['count']} findings; full details in JSON)" if item["count"] > 1 else "") for item in groups[:5])
        if len(groups) > 5:
            lines.append(f"Additional blocking groups: {len(groups) - 5}")
    if attention:
        lines.append("")
        lines.append("Attention findings:")
        groups = finding_groups(attention)
        lines.extend(finding_line(item) + (f" ({item['count']} findings; full details in JSON)" if item["count"] > 1 else "") for item in groups[:5])
        if len(groups) > 5:
            lines.append(f"Additional attention groups: {len(groups) - 5}")
    if len(blocking) + len(attention) < len(findings):
        hidden = len(findings) - len(blocking) - len(attention)
        lines.append(f"Additional non-blocking findings: {hidden}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--framework-source", type=Path)
    parser.add_argument(
        "--validation-phase",
        choices=["acceptance", "migration-staging"],
        default="acceptance",
    )
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="Compatibility alias for --validation-phase migration-staging.",
    )
    parser.add_argument("--allow-local-path", action="append", default=[])
    parser.add_argument("--strict-warnings", action="store_true")
    parser.add_argument("--config", type=Path)
    parser.add_argument(
        "--required-capability",
        action="append",
        default=[],
        help="Capability required by the current task; repeat as needed.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--incident-frontier", action="store_true", help="Include an advisory bounded task-header view; does not narrow validation.")
    parser.add_argument("--current-task", help="Exact registered task ID for bound disposition and control adoption; never acceptance.")
    parser.add_argument("--work-overview", action="store_true", help="Show bounded independent task/team owner views, not liveness or acceptance.")
    parser.add_argument(
        "--mode",
        choices=["status", "doctor"],
        default="doctor",
        help="status emits compact health only; doctor includes repair routes and findings.",
    )
    args = parser.parse_args()

    payload = health_payload(
        target=args.target,
        framework_source=args.framework_source,
        validation_phase=args.validation_phase,
        allow_placeholders=args.allow_placeholders,
        strict_warnings=args.strict_warnings,
        allow_local_paths=args.allow_local_path,
        config_path=args.config,
        required_capabilities=args.required_capability,
        include_incident_frontier=args.incident_frontier,
        current_task_id=args.current_task,
        include_work_overview=args.work_overview,
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_text(payload, mode=args.mode), end="")
    return int(payload.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())
