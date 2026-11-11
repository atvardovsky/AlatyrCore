"""Bounded request/action consistency, not conversational authority or dispatch."""

from __future__ import annotations

from pathlib import Path

from inspect_session_context import json_object
from request_values import MAX_ROWS, WINDOWS_DEVICES, fields, request_path, strings, text


MAX_BRIEF_BYTES = 16384
MAX_BRIEF_WORDS = 1200
PHASES = frozenset({"inspect", "modify", "commit", "publish", "live-external"})


def parse_brief(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or len(raw) > MAX_BRIEF_BYTES:
        raise ValueError(f"request brief exceeds {MAX_BRIEF_BYTES} bytes")
    try:
        document = json_object(raw, "request brief")
    except RecursionError as exc:
        raise ValueError("request brief nesting exceeds parser limits") from exc
    required = {
        "schema_version", "record_kind", "request_id", "task_id", "source_ref",
        "objective", "outcomes", "constraints", "non_goals", "requested_order",
        "authorized_phases", "write_scope", "effect_scope",
    }
    if document.get("schema_version") in (2, 3):
        required.add("delivery_control")
    if document.get("schema_version") == 3:
        required.add("focus_control")
        required.update(set(document) & {"terminal_control"})
    brief = fields(document, required, "request brief")
    if type(brief["schema_version"]) is not int or brief["schema_version"] not in (1, 2, 3) or brief["record_kind"] != "alatyr-request-brief":
        raise ValueError("request brief requires schema 1, 2 or 3 and alatyr-request-brief kind")
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
    if brief.get("delivery_control") is not None:
        from delivery_control import parse_control
        parse_control(brief["delivery_control"], ids)
    from request_focus import parse_focus_control
    parse_focus_control(brief.get("focus_control"))
    if brief.get("terminal_control") is not None:
        from action_prerequisites import parse_terminal_control
        parse_terminal_control(brief["terminal_control"], brief)
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
    required = {"request_id", "task_id", "kind", "phase", "outcome_ids", "paths", "effects"}
    if isinstance(value, dict):
        required.update(set(value) & {"validation", "brief_sha256", "obligation_ids"})
    action = fields(value, required, "request action")
    for key in ("request_id", "task_id"):
        text(action[key], "action." + key)
    from request_focus import parse_focus_action
    parse_focus_action(action)
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
    if "validation" in action:
        from delivery_control import parse_validation
        parse_validation(action["validation"])
        if action["kind"] != "work" or action["phase"] != "inspect" or action["paths"] or action["effects"]:
            raise ValueError("validation review requires an inspect work action without file or external mutations")
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
    if "outcome_checks" in model.get("analysis_evidence", {}):
        from outcome_evidence import request_outcome_failures
        failures.extend(request_outcome_failures(brief, model))
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
    if "validation" in action or action["kind"] != "work" or action["phase"] != "modify" or action["paths"] != [value] or action["effects"]:
        return ["declared action differs from the actual mapped file-tool input"]
    return []
