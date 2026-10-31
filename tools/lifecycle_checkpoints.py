"""Optional lifecycle delivery; never an executor or an authorization authority."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from inspect_session_context import check_retained_context, json_object, relative_path, validate_baseline
from local_file_lock import file_lock
from support_write_transaction import read_output, replace_output, safe_output

ROOT = Path(__file__).resolve().parents[1]
POLICY = ".ai/assistant/policies/lifecycle-hooks.json"
RUNTIME = ".ai/.runtime/lifecycle-hooks"
MAX_INPUT_BYTES = 64 * 1024
MAX_REMINDERS = 8
MAX_TIMESTAMP = 253402300799  # Year 9999; bound integers before float arithmetic.
PROVIDERS = {"codex", "claude", "gemini", "cursor", "copilot", "procedural"}
EVENTS = {"request", "resume", "before-action", "after-change", "compact", "completion", "interrupt", "end"}
NATIVE_EVENTS = {
    "codex": {"UserPromptSubmit": "request", "SessionStart": "resume", "PreToolUse": "before-action",
        "PostToolUse": "after-change", "PreCompact": "compact", "PostCompact": "compact",
        "Stop": "completion", "Interrupt": "interrupt", "SessionEnd": "end"},
    "claude": {"UserPromptSubmit": "request", "SessionStart": "resume", "PreToolUse": "before-action",
        "PostToolUse": "after-change", "PreCompact": "compact", "PostCompact": "compact",
        "Stop": "completion", "SessionEnd": "end"},
    "gemini": {"BeforeAgent": "request", "SessionStart": "resume", "BeforeTool": "before-action",
        "AfterTool": "after-change", "PreCompress": "compact", "AfterAgent": "completion", "SessionEnd": "end"},
    "cursor": {"beforeSubmitPrompt": "request", "sessionStart": "resume", "preToolUse": "before-action",
        "afterFileEdit": "after-change", "preCompact": "compact", "stop": "completion", "sessionEnd": "end"},
    "copilot": {"userPromptSubmitted": "request", "sessionStart": "resume", "preToolUse": "before-action",
        "postToolUse": "after-change", "preCompact": "compact", "agentStop": "completion", "sessionEnd": "end"},
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256 or any(ord(c) < 32 for c in value):
        raise ValueError(f"{label} must be a bounded non-empty string")
    return value


def policy_failures(policy: object, *, now: float | None = None) -> list[str]:
    if not isinstance(policy, dict):
        return ["lifecycle policy must be an object"]
    required = {"schema_version", "enabled", "provider", "mode", "binding_ttl_seconds", "max_reminders", "native_evidence"}
    failures = []
    if set(policy) != required or type(policy.get("schema_version")) is not int or policy["schema_version"] != 1:
        failures.append("lifecycle policy requires exact schema-1 fields")
    if type(policy.get("enabled")) is not bool:
        failures.append("lifecycle enabled must be Boolean")
    for field, allowed in (("provider", PROVIDERS), ("mode", {"observe", "checkpoint"})):
        if not isinstance(policy.get(field), str) or policy[field] not in allowed:
            failures.append(f"lifecycle {field} is invalid")
    for field, low, high in (("binding_ttl_seconds", 1, 3600), ("max_reminders", 0, MAX_REMINDERS)):
        if type(policy.get(field)) is not int or not low <= policy[field] <= high:
            failures.append(f"lifecycle {field} must be in {low}..{high}")
    evidence = policy.get("native_evidence")
    if not isinstance(evidence, dict) or set(evidence) != {"state", "client_version", "source", "verified_at", "expires_at"}:
        failures.append("lifecycle native_evidence requires state, version, source and bounded validity")
    elif not isinstance(evidence["state"], str) or evidence["state"] not in {"unverified", "observed"}:
        failures.append("lifecycle native_evidence.state is invalid")
    elif evidence["state"] == "observed":
        try:
            for field in ("client_version", "source"):
                text = identifier(evidence[field], "native_evidence." + field)
                if text.casefold() in {"unknown", "none", "unverified"} or "{" in text:
                    raise ValueError("native evidence must be resolved")
            start, end = (timestamp(evidence[field]) for field in ("verified_at", "expires_at"))
            if not start <= (time.time() if now is None else now) < end or end - start > 30 * 86400:
                raise ValueError("native evidence is expired, future-dated or exceeds 30 days")
        except ValueError as exc:
            failures.append(str(exc))
    elif any(evidence[field] is not None for field in ("client_version", "source", "verified_at", "expires_at")):
        failures.append("unverified native evidence fields must remain null")
    if policy.get("provider") == "procedural" and policy.get("mode") != "observe":
        failures.append("procedural lifecycle delivery must remain observe-only")
    return failures


def timestamp(value: object) -> float:
    if not isinstance(value, str):
        raise ValueError("lifecycle timestamp must be an aware ISO timestamp")
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("lifecycle timestamp must be an aware ISO timestamp") from exc
    if moment.tzinfo is None:
        raise ValueError("lifecycle timestamp requires a timezone")
    try:
        return moment.timestamp()
    except (OSError, OverflowError, ValueError) as exc:
        raise ValueError("lifecycle timestamp is outside the supported range") from exc


def object_at(target: Path, relative: str, limit: int = MAX_INPUT_BYTES) -> tuple[bytes, dict]:
    relative = relative_path(relative)
    raw = read_output(target, target / relative, max_bytes=limit)
    if raw is None:
        raise ValueError(f"missing lifecycle input: {relative}")
    return raw, json_object(raw, relative)


def load_policy(target: Path) -> tuple[bytes | None, dict | None]:
    raw = read_output(target, target / POLICY, max_bytes=MAX_INPUT_BYTES)
    if raw is None:
        return None, None
    return raw, parse_policy(raw)


def parse_policy(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or len(raw) > MAX_INPUT_BYTES:
        raise ValueError("lifecycle policy exceeds 64 KiB")
    policy = json_object(raw, POLICY)
    failures = policy_failures(policy)
    if failures:
        raise ValueError("; ".join(failures))
    return policy


def selected_task(target: Path, task_id: str) -> dict:
    # Only the selected canonical view is evaluated, not Validator.run().
    from current_task_view import current_task_view
    from validate_target_adapter import Validator, load_validator_config
    config, findings = load_validator_config(target, None)
    validator = Validator(target, framework_source=ROOT, diff_ref=None,
        approval_records=[], enforce_approval_scope=False, change_packages=[],
        enforce_change_package=False, migration_diff=None, allow_placeholders=False,
        allow_local_paths=[], config=config, initial_findings=findings,
        approval_archive_mode="changed")
    result = current_task_view(validator, task_id)
    if result["state"] == "bound-recorded-disposition":
        paths = {".ai/assistant/active-tasks.json", result["model"]["path"]}
        loaded = validator.context.read_json_result(validator.target_path(result["model"]["path"])).value
        if result["task_state"] == "active" and isinstance(loaded, dict) and isinstance(loaded.get("active_projection"), dict):
            paths.add(loaded["active_projection"]["path"])
        result["checkpoint_inputs"] = {path: validator.context.content_digest(validator.target_path(path)) for path in paths}
    failures = [item.message for item in validator.findings if item.level == "error"]
    failures += ["selected task input changed: " + str(item.path) for item in validator.context.finalize()]
    failures += ["task schema changed: " + str(item.path) for item in validator.schema_context.finalize()]
    if failures or result["state"] != "bound-recorded-disposition":
        raise ValueError("selected task is unavailable, stale or invalid: " + str(failures or result["diagnostics"])[:500])
    return result


def decision(status: str, reason: str, *, block: bool = False) -> dict:
    return {"status": status, "reason": reason, "checkpoint_required": block,
        "authorization_granted": False, "acceptance_granted": False,
        "native_interception_verified": False}


def binding_current(binding: dict, policy: dict, raw_policy: bytes, now: float) -> bool:
    return (0 < binding["expires_at"] - now <= policy["binding_ttl_seconds"]
            and binding["policy_sha256"] == digest(raw_policy))


def task_context_matches(retained: dict, task: dict, policy_sha: str) -> bool:
    baseline = validate_baseline(retained.get("baseline", retained))
    inputs = {row["path"]: row["sha256"] for row in baseline["inputs"]}
    expected = {**task["checkpoint_inputs"], POLICY: policy_sha}
    return all(sha is not None and inputs.get(path) == "sha256:" + sha for path, sha in expected.items())


def validate_state(state: dict, session_id: str) -> None:
    fields = {"schema_version", "session_id", "request_id", "status", "binding", "reminders", "interrupt_sha256"}
    if (set(state) != fields or type(state.get("schema_version")) is not int or state["schema_version"] != 1
            or state.get("session_id") != session_id
            or not isinstance(state.get("status"), str) or state["status"] not in {"unbound", "bound", "review-required", "interrupted", "ended"}
            or type(state.get("reminders")) is not int or not 0 <= state["reminders"] <= MAX_REMINDERS):
        raise ValueError("invalid lifecycle session record")
    identifier(state.get("request_id"), "request_id")
    identifier(state.get("interrupt_sha256"), "interrupt_sha256")
    binding = state.get("binding")
    if binding is not None:
        if not isinstance(binding, dict) or set(binding) != {"baseline", "baseline_sha256", "task_id", "expires_at", "policy_sha256"}:
            raise ValueError("invalid reviewed lifecycle binding")
        for field in ("baseline", "baseline_sha256", "task_id", "policy_sha256"):
            identifier(binding.get(field), "binding." + field)
        if type(binding.get("expires_at")) not in (int, float) or not 0 < binding["expires_at"] <= MAX_TIMESTAMP:
            raise ValueError("invalid lifecycle binding expiry")
    if state["status"] == "bound" and binding is None:
        raise ValueError("bound lifecycle session is missing its reviewed binding")


def session_status(target: Path, session_id: str) -> dict:
    session_id = identifier(session_id, "session_id")
    raw_policy, policy = load_policy(target)
    if policy is None or not policy["enabled"]:
        return decision("disabled", "Lifecycle delivery is not adopted.")
    path = target / RUNTIME / (digest(session_id.encode()) + ".json")
    raw = read_output(target, path, max_bytes=MAX_INPUT_BYTES)
    if raw is None:
        return decision("unknown", "No session event observed; no binding may be inferred.")
    state = json_object(raw, "lifecycle session")
    validate_state(state, session_id)
    interrupt = read_output(target, path.with_suffix(".interrupted"), max_bytes=128) or b""
    status = "interrupted" if state["interrupt_sha256"] != digest(interrupt) else state["status"]
    if status == "bound" and not binding_current(state["binding"], policy, raw_policy, time.time()):
        status = "review-required"
    return {**decision(status, "Session routing only; review authorization separately."),
        "request_id": state["request_id"], "reminders": state["reminders"]}


def handle(target: Path, provider: str, event: str, payload: dict, *,
           bind: dict | None = None, now: float | None = None) -> dict:
    raw_policy, policy = load_policy(target)
    if policy is None or not policy["enabled"]:
        return decision("disabled", "No lifecycle hooks adopted; perform ordinary procedural checkpoints.")
    if provider != policy["provider"]:
        raise ValueError("lifecycle provider differs from the adopted policy")
    if event not in EVENTS:
        raise ValueError("unsupported lifecycle event")
    session_id = identifier(payload.get("session_id"), "session_id")
    if "cwd" in payload:
        Path(identifier(payload["cwd"], "cwd")).resolve().relative_to(target)
    from target_tool_compat import assert_write_compatible
    assert_write_compatible(target, tool_name="run_lifecycle_checkpoint.py")
    state_path = target / RUNTIME / (digest(session_id.encode()) + ".json")
    from target_validation_support import GitEvidenceView
    git = GitEvidenceView(target)
    for runtime in (state_path, state_path.with_suffix(".lock"), state_path.with_suffix(".interrupted")):
        relative = runtime.relative_to(target).as_posix()
        if git.is_ignored(relative) is not True or git.is_tracked(relative) is not False:
            raise ValueError("all lifecycle state, locks and revocation markers must be ignored and untracked")
    lock = safe_output(target, state_path.with_suffix(".lock"))
    lock.parent.mkdir(parents=True, exist_ok=True)
    safe_output(target, lock)
    interrupt_path = state_path.with_suffix(".interrupted")
    if event == "interrupt":
        # Independent revocation: a slow completion reader cannot hold it off.
        previous = read_output(target, interrupt_path, max_bytes=128)
        replace_output(target, interrupt_path, previous, uuid.uuid4().hex.encode())
        return decision("interrupted", "Interrupted; no automatic restart or continuation.")
    with file_lock(lock, timeout=0.25):
        current_time = time.time() if now is None else now
        interrupt = read_output(target, interrupt_path, max_bytes=128) or b""
        raw_state = read_output(target, state_path, max_bytes=MAX_INPUT_BYTES)
        state = json_object(raw_state, "lifecycle session") if raw_state else {
            "schema_version": 1, "session_id": session_id, "request_id": uuid.uuid4().hex,
            "status": "interrupted" if interrupt else "unbound", "binding": None,
            "reminders": 0, "interrupt_sha256": digest(interrupt)}
        validate_state(state, session_id)
        if event in {"request", "end"}:
            state.update(request_id=uuid.uuid4().hex, binding=None,
                status={"end": "ended"}.get(event, "unbound"), interrupt_sha256=digest(interrupt))
            result = decision(state["status"], "Review newest intent and select current context/task before state changes.")
        elif event == "resume":
            revoked = state["status"] in {"interrupted", "ended"} or state["interrupt_sha256"] != digest(interrupt)
            status = ("ended" if state["status"] == "ended" else "interrupted") if revoked else "review-required" if state["binding"] else "unbound"
            state.update(request_id=uuid.uuid4().hex, status=status,
                         binding=None if revoked else state["binding"])
            result = decision(status, "Resume restores no authority; review context and retain interruption/end boundaries.")
        elif state["interrupt_sha256"] != digest(interrupt):
            state.update(status="interrupted", binding=None)
            result = decision("interrupted", "Interrupted request remains revoked; require a new human request.", block=True)
        elif bind is not None:
            if state["status"] in {"interrupted", "ended"} or bind.get("request_id") != state["request_id"]:
                raise ValueError("reviewed binding requires the current non-interrupted request ID")
            baseline_raw, retained = object_at(target, bind["baseline"], 128 * 1024)
            task = selected_task(target, identifier(bind["task_id"], "task_id"))
            if task["task_state"] != "active":
                raise ValueError("a closed task cannot be rebound as an active execution scope")
            if not task_context_matches(retained, task, digest(raw_policy)):
                raise ValueError("reviewed baseline must include current canonical task index, selected model and projection, and lifecycle policy")
            if read_output(target, target / bind["baseline"], max_bytes=128 * 1024) != baseline_raw:
                raise ValueError("reviewed baseline changed during binding")
            state.update(status="bound", binding={"baseline": bind["baseline"],
                "baseline_sha256": digest(baseline_raw), "task_id": bind["task_id"],
                "expires_at": (time.time() if now is None else now) + policy["binding_ttl_seconds"], "policy_sha256": digest(raw_policy)})
            result = decision("bound", "Review recorded; phases, permissions and acceptance remain separately owned.")
        elif event in {"after-change", "compact"}:
            if state["status"] not in {"interrupted", "ended"}:
                state["status"] = "review-required"
            result = decision(state["status"], "Reconcile affected owners, documentation and evidence before the next mutation.")
        elif state["status"] != "bound":
            if state["binding"] is None and state["status"] not in {"interrupted", "ended"}:
                result = decision("inactive", "No registered task selected for hook delivery. Use ordinary task-scale context and authorization checks; small tasks need no model.")
            else:
                result = decision(state["status"], "A current reviewed task/context binding is required; inspect only.", block=True)
        else:
            binding = state["binding"]
            # Reject expired bindings before content I/O and recheck after it.
            if not binding_current(binding, policy, raw_policy, current_time):
                result = decision("review-required", "Lifecycle binding expired or policy changed; inspect only.", block=True)
            else:
                baseline_raw, retained = object_at(target, binding["baseline"], 128 * 1024)
                if digest(baseline_raw) != binding["baseline_sha256"]:
                    result = decision("review-required", "Selected context changed or expired; use session-continuity.", block=True)
                elif event == "before-action":
                    result = decision("current-context", "Fresh context only; classify the intended action and check current-scope authorization procedurally.")
                else:
                    view = selected_task(target, binding["task_id"])
                    if not task_context_matches(retained, view, digest(raw_policy)):
                        result = decision("review-required", "Selected task changed during evaluation; reconcile context before continuation.", block=True)
                    else:
                        ready = view.get("execution_readiness", {}).get("ready", []) if view["task_state"] == "active" else []
                        result = decision("unfinished" if ready else "handoff-review",
                            "Review the selected task's unresolved duties and original outcome. "
                            + ("Independent ready duties remain; continue only within current human authorization. " if ready else "Do not claim completion from a recorded disposition. ")
                            + "A blocker, pause, interruption or authority boundary wins; use canonical acceptance for completion.", block=bool(ready))
        active = policy["mode"] == "checkpoint" and policy["native_evidence"]["state"] == "observed"
        reminder = (event == "completion" and active and result["status"] == "unfinished"
            and state["status"] == "bound" and state["reminders"] < policy["max_reminders"]
            and payload.get("stop_hook_active") is not True)
        if reminder:
            # Reserve before delivery; a stale or interrupted attempt never refunds the budget.
            state["reminders"] += 1
        elif event == "completion" and result["status"] == "unfinished" and active:
            result["status"] = "handoff-required"
        # The binding record has no transcript, command, domain status or approval.
        encoded = (json.dumps(state, sort_keys=True) + "\n").encode()
        replace_output(target, state_path, raw_state, encoded)
        # One canonical comparison, after task evaluation and durable state writes.
        if state["status"] == "bound" and result["status"] in {"bound", "current-context", "unfinished", "handoff-review", "handoff-required"}:
            context = check_retained_context(target, target / state["binding"]["baseline"])
            final_baseline, _ = object_at(target, state["binding"]["baseline"], 128 * 1024)
            if context["status"] != "current" or digest(final_baseline) != state["binding"]["baseline_sha256"]:
                result = decision("review-required", "Selected context or reviewed baseline changed before delivery; inspect only.", block=True)
        if read_output(target, target / POLICY, max_bytes=MAX_INPUT_BYTES) != raw_policy:
            raise ValueError("lifecycle policy changed before delivery")
        if (read_output(target, interrupt_path, max_bytes=128) or b"") != interrupt:
            state.update(status="interrupted", binding=None)
            result = decision("interrupted", "Interrupted before delivery; no continuation.", block=True)
        # Check both validity windows after the last potentially blocking read.
        final_time = time.time() if now is None else now
        if policy_failures(policy, now=final_time):
            raise ValueError("lifecycle native evidence expired during evaluation; use procedural review")
        if state["status"] == "bound" and not binding_current(state["binding"], policy, raw_policy, final_time):
            result = decision("review-required", "Lifecycle binding expired during evaluation; inspect only.", block=True)
        result["emit_native_block"] = active and (
            (event == "before-action" and result["checkpoint_required"])
            or (reminder and result["status"] == "unfinished" and state["status"] == "bound"))
        result["request_id"] = state["request_id"]
        return result
