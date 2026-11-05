"""Bounded request/action consistency, not conversational authority or dispatch."""

from __future__ import annotations

import re
from pathlib import Path

from inspect_session_context import json_object, relative_path


MAX_BRIEF_BYTES = 16384
MAX_BRIEF_WORDS = 1200
MAX_ROWS = 32
PHASES = frozenset({"inspect", "modify", "commit", "publish", "live-external"})
WINDOWS_DEVICES = frozenset({"con", "prn", "aux", "nul", "conin$", "conout$",
                            *[f"{prefix}{number}" for prefix in ("com", "lpt") for number in range(1, 10)]})


def text(value: object, label: str, limit: int = 1024) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > limit
            or any(ord(char) < 32 for char in value)
            or value.casefold() in {"unknown", "none", "unresolved"}
            or re.search(r"\{[A-Z][A-Z0-9_]*\}", value)):
        raise ValueError(f"{label} requires bounded resolved text")
    return value


def strings(value: object, label: str, *, minimum: int = 0) -> list[str]:
    if not isinstance(value, list) or not minimum <= len(value) <= MAX_ROWS:
        raise ValueError(f"{label} requires {minimum}..{MAX_ROWS} entries")
    result = [text(item, label) for item in value]
    if len(set(result)) != len(result):
        raise ValueError(f"{label} cannot contain duplicates")
    return result


def fields(value: object, required: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError(f"{label} requires exact fields: {', '.join(sorted(required))}")
    return value


def request_path(value: object) -> str:
    path = relative_path(text(value, "request path"))
    for part in path.split("/"):
        device = part.split(".")[0].rstrip(" ").casefold().translate(str.maketrans({"\u00b9": "1", "\u00b2": "2", "\u00b3": "3"}))
        if (part.endswith((" ", ".")) or any(char in part for char in '*?[]:<>|"')
                or device in WINDOWS_DEVICES):
            raise ValueError("request paths must be portable literal paths without device, alias or stream names")
    return path


def parse_brief(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or len(raw) > MAX_BRIEF_BYTES:
        raise ValueError(f"request brief exceeds {MAX_BRIEF_BYTES} bytes")
    try:
        document = json_object(raw, "request brief")
    except RecursionError as exc:
        raise ValueError("request brief nesting exceeds parser limits") from exc
    brief = fields(document, {
        "schema_version", "record_kind", "request_id", "task_id", "source_ref",
        "objective", "outcomes", "constraints", "non_goals", "requested_order",
        "authorized_phases", "write_scope", "effect_scope",
    }, "request brief")
    if type(brief["schema_version"]) is not int or brief["schema_version"] != 1 or brief["record_kind"] != "alatyr-request-brief":
        raise ValueError("request brief requires schema 1 and alatyr-request-brief kind")
    for key in ("request_id", "task_id", "source_ref", "objective"):
        text(brief[key], "request brief." + key)
    phases = strings(brief["authorized_phases"], "authorized_phases", minimum=1)
    if not set(phases) <= PHASES or "inspect" not in phases:
        raise ValueError("authorized_phases requires inspect and exact action phase names")
    for key in ("constraints", "non_goals", "requested_order", "effect_scope"):
        strings(brief[key], key)
    scopes = brief["write_scope"]
    if not isinstance(scopes, list) or len(scopes) > MAX_ROWS:
        raise ValueError("write_scope requires bounded path entries")
    if "modify" in phases and not scopes:
        raise ValueError("modify ceiling requires an explicit write_scope")
    seen = set()
    for row in scopes:
        fields(row, {"path", "recursive"}, "write_scope entry")
        request_path(row["path"])
        if type(row["recursive"]) is not bool:
            raise ValueError("write_scope requires literal paths and Boolean recursive")
        identity = (row["path"], row["recursive"])
        if identity in seen:
            raise ValueError("write_scope contains duplicate entries")
        seen.add(identity)
    outcomes = brief["outcomes"]
    if not isinstance(outcomes, list) or not 1 <= len(outcomes) <= MAX_ROWS:
        raise ValueError("outcomes requires bounded nonempty entries")
    ids = set()
    for row in outcomes:
        fields(row, {"id", "statement", "rejection_case", "proof_obligation_ids"}, "outcome")
        for key in ("id", "statement", "rejection_case"):
            text(row[key], "outcome." + key)
        if row["id"] in ids:
            raise ValueError("outcomes contains duplicate IDs")
        ids.add(row["id"])
        strings(row["proof_obligation_ids"], "proof_obligation_ids", minimum=1)
    from analysis_strategy_contract import structured_word_count
    if structured_word_count(brief) > MAX_BRIEF_WORDS:
        raise ValueError(f"request brief exceeds {MAX_BRIEF_WORDS} words")
    return brief


def guard_policy(value: object) -> dict:
    guard = fields(value, {"required", "file_tools"}, "request_guard")
    if type(guard["required"]) is not bool or not isinstance(guard["file_tools"], list) or len(guard["file_tools"]) > MAX_ROWS:
        raise ValueError("request_guard requires Boolean required and bounded file_tools")
    names = set()
    for row in guard["file_tools"]:
        fields(row, {"tool_name", "path_field"}, "file_tools entry")
        for key in ("tool_name", "path_field"):
            text(row[key], "file_tools." + key, 256)
        if row["path_field"] not in {"path", "file_path", "filename"}:
            raise ValueError("file_tools.path_field must select a supported single-file path field")
        if row["tool_name"] in names:
            raise ValueError("file_tools cannot repeat tool names")
        names.add(row["tool_name"])
    return guard


def parse_action(value: object) -> dict:
    action = fields(value, {"request_id", "task_id", "kind", "phase", "outcome_ids", "paths", "effects"}, "request action")
    for key in ("request_id", "task_id"):
        text(action[key], "action." + key)
    if not isinstance(action["kind"], str) or action["kind"] not in {"work", "answer", "complete"}:
        raise ValueError("action.kind must be work, answer or complete")
    if not isinstance(action["phase"], str) or action["phase"] not in PHASES:
        raise ValueError("action.phase requires an exact action phase")
    if action["kind"] != "work" and action["phase"] != "inspect":
        raise ValueError("answers and completion reviews must use inspect")
    strings(action["outcome_ids"], "action.outcome_ids", minimum=1)
    for key in ("paths", "effects"):
        strings(action[key], "action." + key)
    for path in action["paths"]:
        request_path(path)
    if action["phase"] == "modify" and not action["paths"]:
        raise ValueError("modify requires actual affected paths")
    if action["phase"] in {"inspect", "modify"} and action["effects"]:
        raise ValueError("inspection/file modification cannot contain Git/publication/live effects")
    if action["phase"] in {"commit", "publish", "live-external"} and not action["effects"]:
        raise ValueError("Git/publication/live phases require explicit effect identities")
    return action


def action_failures(brief: dict, action: dict, model: dict, *, request_id: str,
                    task_id: str) -> list[str]:
    """Inputs are validated by their canonical parsers before dependent operations."""
    failures = []
    if brief["request_id"] != request_id or action["request_id"] != request_id:
        failures.append("request identity is stale or differs from the selected request")
    if brief["task_id"] != task_id or action["task_id"] != task_id:
        failures.append("task identity differs from the request brief")
    if brief["objective"] != model["objective"]:
        failures.append("selected model objective differs from the request brief")
    outcomes = {row["id"]: row for row in brief["outcomes"]}
    proofs = {row["id"]: row for row in model["proof_obligations"]}
    for outcome in outcomes.values():
        for key in outcome["proof_obligation_ids"]:
            if key not in proofs or proofs[key]["required"] is not True:
                failures.append(f"outcome {outcome['id']} requires a known required proof obligation: {key}")
    if not set(action["outcome_ids"]) <= outcomes.keys():
        failures.append("action does not map to declared requested outcomes")
    if action["phase"] not in brief["authorized_phases"]:
        failures.append("action phase exceeds the declared current-request ceiling")
    if action["phase"] != "inspect":
        for path in action["paths"]:
            if not any(path == row["path"] or row["recursive"] and path.startswith(row["path"] + "/") for row in brief["write_scope"]):
                failures.append(f"action path is outside the declared write scope: {path}")
    if not set(action["effects"]) <= set(brief["effect_scope"]):
        failures.append("action effects exceed the declared request scope")
    if action["kind"] == "complete":
        for outcome in outcomes.values():
            missing = [key for key in outcome["proof_obligation_ids"] if key not in proofs or proofs[key]["status"] != "passed"]
            if missing:
                failures.append(f"requested outcome {outcome['id']} remains unverified: {', '.join(missing)}")
    return failures


def native_file_action_failures(target: Path, guard: dict, payload: dict, action: dict) -> list[str]:
    """Only explicitly mapped single-file mutators; no shell/interpreter inference."""
    name, arguments = payload.get("tool_name"), payload.get("tool_input")
    if not isinstance(name, str) or not isinstance(arguments, dict):
        return ["native action requires a reviewed file-tool mapping; unknown tools need procedural review"]
    mapping = next((row for row in guard["file_tools"] if row["tool_name"] == name), None)
    if mapping is None:
        return ["native tool has no reviewed single-file mutation mapping"]
    if set(arguments) - {mapping["path_field"], "content", "old_string", "new_string", "replace_all"}:
        return ["native file-tool input contains unsupported command, multi-file or extra fields"]
    value = arguments.get(mapping["path_field"])
    if not isinstance(value, str) or not value or len(value) > 4096:
        return ["native file-tool path is missing, malformed or oversized"]
    try:
        path = Path(value)
        if path.is_absolute():
            value = path.relative_to(target).as_posix()
        request_path(value)
        from support_write_transaction import safe_output
        safe_output(target, target / value)
    except (OSError, ValueError, RuntimeError):
        return ["native file-tool path is not a safe target-relative file"]
    if action["kind"] != "work" or action["phase"] != "modify" or action["paths"] != [value] or action["effects"]:
        return ["declared action differs from the actual mapped file-tool input"]
    return []
