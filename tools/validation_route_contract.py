"""Typed references to existing validation operations, never command inference."""

from __future__ import annotations

from typing import Any

CONTRACT_PATH = ".ai/assistant/validation-contract.json"
ROUTE_ROLES = {"inspection": "adapter-health", "completion": "current-change"}


def validation_route_failures(route: Any, contract: Any) -> list[str]:
    if not isinstance(route, dict) or set(route) != set(ROUTE_ROLES):
        return ["validation_entrypoints must bind exactly inspection and completion"]
    failures = []
    entries = contract.get("entrypoints") if isinstance(contract, dict) else None
    if not isinstance(entries, dict):
        return ["validation route requires the existing validation contract entrypoints"]
    for role, expected in ROUTE_ROLES.items():
        name = route.get(role)
        if not isinstance(name, str) or name != expected:
            failures.append(f"{role} must reference {expected}, not {name!r}")
            continue
        entry = entries.get(name)
        if not isinstance(entry, dict):
            failures.append(f"{role} references missing entrypoint {name}")
            continue
        eligible = role == "completion"
        if not isinstance(entry.get("command"), str) or not entry["command"].strip():
            failures.append(f"{role} requires a concrete command prefix")
        if entry.get("final_evidence_eligible") is not eligible:
            failures.append(f"{role} entrypoint {name} has incompatible final-evidence eligibility")
        coverage = entry.get("coverage")
        if eligible and (not isinstance(coverage, str) or coverage not in {"canonical-delegate", "target-equivalent"}):
            failures.append("completion cannot rely on auxiliary or manual-only validation")
    return failures
