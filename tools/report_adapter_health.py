#!/usr/bin/env python3
"""Report compact read-only health for an installed Alatyr target adapter."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from capability_catalog import load_modules

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
    if mode == "status" and findings:
        lines.append("Finding details: run doctor for prioritized findings")
        return "\n".join(lines) + "\n"

    if blocking:
        lines.append("")
        lines.append("Blocking findings:")
        lines.extend(finding_line(item) for item in blocking[:5])
    if attention:
        lines.append("")
        lines.append("Attention findings:")
        lines.extend(finding_line(item) for item in attention[:5])
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
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_text(payload, mode=args.mode), end="")
    return int(payload.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())
