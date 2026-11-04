"""Explicit phase/role context selection; canonical budget and owner closure stay shared."""

from __future__ import annotations

from typing import Callable

PHASE_REQUIREMENTS = {
    "large-or-resumable": {"create": (False, False), "resume": (True, False)},
    "delegated-execution": {"planning": (False, False), "dispatch": (True, True),
                            "convergence": (True, False)},
}


def select_phase_context(selectors: tuple[str, ...], instances: tuple[str, ...], role: str | None,
                         router: dict, load: Callable, select: Callable) -> list[dict]:
    if (not isinstance(router, dict) or any(not isinstance(values, (list, tuple))
            or any(not isinstance(p, str) or not p for p in values) for values in (selectors, instances))
            or len(selectors) > 2 or len(instances) > 64
            or len(instances) != len(set(instances))
            or role is not None and (not isinstance(role, str) or not role)):
        raise ValueError("phase selectors, instances and role must be bounded resolved values")
    if not selectors:
        if instances or role is not None:
            raise ValueError("phase instances and worker roles require an explicit overlay phase")
        return []
    phases = {}
    for selector in selectors:
        name, separator, phase = selector.partition(":")
        if not separator or not phase or name in phases:
            raise ValueError("overlay phases must be unique OVERLAY:PHASE selectors")
        phases[name] = phase
    if set(phases) - PHASE_REQUIREMENTS.keys():
        raise ValueError("unknown phase-aware task overlay")
    overlays = router.get("task_scale_overlays")
    if not isinstance(overlays, dict):
        raise ValueError("task-scale overlay routing is unavailable")
    evidence = []
    for name, phase in sorted(phases.items()):
        requirements = PHASE_REQUIREMENTS[name].get(phase)
        if requirements is None:
            raise ValueError(f"unsupported delivery phase: {name}:{phase}")
        entry = overlays.get(name)
        if not isinstance(entry, dict) or not isinstance(entry.get("descriptor"), str):
            raise ValueError(f"phase overlay descriptor is unavailable: {name}")
        path = entry["descriptor"]
        descriptor = load(path)
        if (descriptor.get("descriptor_kind") != "target-task-scale-overlay" or type(descriptor.get("schema_version")) is not int or descriptor["schema_version"] != 1
                or descriptor.get("overlay", descriptor.get("id")) != name):
            raise ValueError("unsupported phase overlay descriptor")
        variants = descriptor.get("phase_context")
        variant = variants.get(phase) if isinstance(variants, dict) else None
        if not isinstance(variant, dict) or set(variant) != {"required_context", "requires_instance", "requires_role"}:
            raise ValueError(f"unknown or malformed overlay phase: {name}:{phase}")
        paths = variant["required_context"]
        if (not isinstance(paths, list) or not paths or any(not isinstance(p, str) or not p for p in paths)
                or type(variant["requires_instance"]) is not bool or type(variant["requires_role"]) is not bool):
            raise ValueError("phase context requires resolved paths and Boolean evidence requirements")
        if (variant["requires_instance"], variant["requires_role"]) != requirements:
            raise ValueError("phase descriptor contradicts canonical instance/role prerequisites")
        if variant["requires_instance"] and not instances:
            raise ValueError("resume/dispatch/convergence requires explicitly selected current instance evidence")
        if variant["requires_role"] and role is None:
            raise ValueError("delegated dispatch requires one exact enabled worker role")
        select(path)
        for required in paths:
            select(required)
        evidence.append({"overlay": name, "phase": phase, "descriptor": path})
    if role is not None:
        if phases.get("delegated-execution") != "dispatch":
            raise ValueError("worker role selection requires delegated-execution:dispatch")
        catalog = load(".ai/assistant/workers/role-catalog.json")
        if (type(catalog.get("schema_version")) is not int or catalog["schema_version"] != 2
                or catalog.get("catalog_kind") != "target-worker-role-catalog"):
            raise ValueError("unsupported worker role catalog envelope")
        roles = catalog.get("roles")
        if not isinstance(roles, list):
            raise ValueError("worker role catalog requires a role list")
        matches = [r for r in roles if isinstance(r, dict) and r.get("id") == role]
        if len(matches) != 1 or matches[0].get("state") != "enabled":
            raise ValueError("selected worker role is missing, ambiguous, disabled, or unresolved")
        selected = matches[0]
        if (not isinstance(selected.get("prompt"), str) or not selected["prompt"]
                or type(selected.get("max_files")) is not int or selected["max_files"] <= 0
                or type(selected.get("max_context_words")) is not int or selected["max_context_words"] <= 0):
            raise ValueError("selected worker role requires a prompt and resolved positive limits")
        if (not isinstance(selected.get("action_ceiling"), str)
                or selected["action_ceiling"] not in {"read-only", "docs-only", "adapter-only", "code-and-tests"}
                or not isinstance(selected.get("write_mode"), str) or selected["write_mode"] not in {"none", "bounded"}):
            raise ValueError("selected worker role action/write ceilings are unresolved")
        if selected["action_ceiling"] == "read-only" and selected["write_mode"] != "none":
            raise ValueError("read-only worker role cannot declare writes")
        select(selected["prompt"])
        evidence.append({"selected_role": role, "catalog": ".ai/assistant/workers/role-catalog.json",
                         "effective_role": {key: selected[key] for key in ("prompt", "action_ceiling", "write_mode", "max_files", "max_context_words")}})
    for path in instances:
        select(path)
    return evidence
