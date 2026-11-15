"""Validate declared economical choices; never infer prices or model quality."""

from __future__ import annotations

from typing import Any
import re

from target_validation_support import is_placeholder, is_unresolved_value


TASK_CLASSES = {"mechanical", "bounded-code", "semantic"}
FIELDS = {"schema_version", "packet_id", "node_id", "capability_sha256", "task_class", "options",
          "exclusions", "selected_option", "selection_mode", "rationale", "max_cost_rank", "observed"}
OPTION_FIELDS = {"id", "model", "reasoning", "cost_rank", "eligible_for", "availability", "authorized", "evidence_ref", "selection_modes"}


def _object(value: Any, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(label + " has missing or unexpected fields")
    return value


def _text(value: Any, label: str) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > 2048
            or is_placeholder(value) or is_unresolved_value(value)):
        raise ValueError(label + " must be a resolved bounded string")
    return value


def _enum(value: Any, choices: set[str], label: str) -> str:
    result = _text(value, label)
    if result not in choices:
        raise ValueError(label + " is unsupported")
    return result


def _rank(value: Any, label: str) -> int:
    if type(value) is not int or not 0 <= value <= 10000:
        raise ValueError(label + " must be an integer from 0 through 10000")
    return value


def review_selection(value: Any, *, packet_id: str, node_id: str, capability_sha256: str,
                     execution_state: str, choose: bool = False) -> dict:
    record = _object(value, FIELDS, "worker model selection")
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise ValueError("worker model selection schema_version must be 1")
    for key, expected in (("packet_id", packet_id), ("node_id", node_id), ("capability_sha256", capability_sha256)):
        if _text(record[key], key) != expected:
            raise ValueError("worker model selection " + key + " differs from its assignment")
    if not re.fullmatch(r"[0-9a-f]{64}", record["capability_sha256"]):
        raise ValueError("worker model selection capability binding must be a SHA-256")
    task_class = _enum(record["task_class"], TASK_CLASSES, "task_class")
    _enum(record["selection_mode"], {"explicit-model", "inherit", "client-default"}, "selection_mode")
    _text(record["rationale"], "rationale")
    options = record["options"]
    if not isinstance(options, list) or not 1 <= len(options) <= 16:
        raise ValueError("model options must contain 1..16 declared alternatives")
    indexed = {}
    for raw in options:
        option = _object(raw, OPTION_FIELDS, "model option")
        identity = _text(option["id"], "model option id")
        if identity in indexed:
            raise ValueError("duplicate model option id")
        for key in ("model", "reasoning", "evidence_ref"):
            _text(option[key], "model option " + key)
        _rank(option["cost_rank"], "model option cost_rank")
        eligible = option["eligible_for"]
        if (not isinstance(eligible, list) or not eligible or
                any(not isinstance(item, str) or item not in TASK_CLASSES for item in eligible) or
                len(set(eligible)) != len(eligible)):
            raise ValueError("model option eligible_for must name unique supported task classes")
        _enum(option["availability"], {"available", "unavailable", "unknown"}, "model availability")
        modes = option["selection_modes"]
        if (not isinstance(modes, list) or not modes or any(not isinstance(mode, str) or
                mode not in {"explicit-model", "inherit", "client-default"} for mode in modes) or len(set(modes)) != len(modes)):
            raise ValueError("model option requires verified unique selection_modes")
        if type(option["authorized"]) is not bool:
            raise ValueError("model option authorized must be Boolean")
        indexed[identity] = option
    exclusions = record["exclusions"]
    if not isinstance(exclusions, list) or len(exclusions) > len(options):
        raise ValueError("model exclusions must be a bounded list")
    excluded = set()
    for raw in exclusions:
        row = _object(raw, {"option_id", "reason", "evidence_ref"}, "model exclusion")
        identity = _text(row["option_id"], "excluded option")
        if identity not in indexed or identity in excluded:
            raise ValueError("model exclusion is unknown or duplicated")
        _enum(row["reason"], {"observed-quality-failure", "policy-restriction", "runtime-unavailable"}, "model exclusion reason")
        _text(row["evidence_ref"], "model exclusion evidence")
        excluded.add(identity)
    ceiling = record["max_cost_rank"]
    if ceiling is not None:
        _rank(ceiling, "max_cost_rank")
    eligible = [o for key, o in indexed.items() if key not in excluded and o["authorized"] and
                o["availability"] == "available" and task_class in o["eligible_for"] and
                record["selection_mode"] in o["selection_modes"] and
                (ceiling is None or o["cost_rank"] <= ceiling)]
    if not eligible:
        raise ValueError("no authorized, verified-available model option satisfies this task and cost ceiling; review fallback")
    cheapest = min(o["cost_rank"] for o in eligible)
    identity = record["selected_option"]
    if choose and identity is None:
        identity = next(o["id"] for o in eligible if o["cost_rank"] == cheapest)
    selected = indexed.get(_text(identity, "selected_option"))
    if selected not in eligible:
        raise ValueError("selected worker model is unavailable, unauthorized, excluded, unsuitable or above its ceiling")
    if selected["cost_rank"] != cheapest:
        raise ValueError("selected worker model is more costly than an eligible alternative; provide evidence-backed exclusions")
    observed = _object(record["observed"], {"state", "model", "reasoning", "evidence_ref"}, "observed model")
    state = _enum(observed["state"], {"verified", "unverified"}, "observed model state")
    if state == "verified":
        _text(observed["evidence_ref"], "observed model evidence")
        for key in ("model", "reasoning"):
            if _text(observed[key], "observed " + key) != selected[key]:
                raise ValueError("observed worker " + key + " differs from the selected option")
    elif any(observed[key] is not None for key in ("model", "reasoning", "evidence_ref")):
        raise ValueError("unverified model observation cannot claim an observed identity")
    elif ceiling is not None and execution_state in {"RUNNING", "DONE"}:
        raise ValueError("a bounded-cost execution requires verified actual model and reasoning evidence")
    return {"record": {**record, "selected_option": identity}, "selected": selected,
            "verification": state, "cost_basis": "target-declared-relative-rank-not-observed-billing",
            "authorization_granted": False, "acceptance_granted": False}
