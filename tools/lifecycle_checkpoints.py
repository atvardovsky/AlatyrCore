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
from lifecycle_policy import (
    POLICY, MAX_INPUT_BYTES, MAX_REMINDERS, MAX_TIMESTAMP, PROVIDERS,
    identifier, policy_failures, timestamp, load_policy, parse_policy,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ".ai/.runtime/lifecycle-hooks"
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


def object_at(target: Path, relative: str, limit: int = MAX_INPUT_BYTES) -> tuple[bytes, dict]:
    relative = relative_path(relative)
    raw = read_output(target, target / relative, max_bytes=limit)
    if raw is None:
        raise ValueError(f"missing lifecycle input: {relative}")
    return raw, json_object(raw, relative)


def selected_task(target: Path, task_id: str, *, request_review: bool = False,
                  require_completion: bool = False, source_contour: bool = False) -> dict:
    # Only the selected canonical view is evaluated, not Validator.run().
    from current_task_view import current_task_view
    from validate_target_adapter import Validator, load_validator_config
    config, findings = load_validator_config(target, None)
    validator = Validator(target, framework_source=ROOT, diff_ref=None,
        approval_records=[], enforce_approval_scope=False, change_packages=[],
        enforce_change_package=False, migration_diff=None, allow_placeholders=False,
        allow_local_paths=[], config=config, initial_findings=findings,
        approval_archive_mode="changed", current_task_id=task_id)
    result = current_task_view(validator, task_id)
    if result["state"] == "bound-recorded-disposition":
        paths = {".ai/assistant/active-tasks.json", result["model"]["path"]}
        loaded = validator.context.read_json_result(validator.target_path(result["model"]["path"])).value
        if request_review:
            result["request_model"] = loaded
            result["request_contexts"] = (validator.context, validator.schema_context)
        if require_completion and result["task_state"] == "active":
            from target_adapter_validation.analysis_strategies import load_problem_model_schema, validate_selected_problem_model
            validate_selected_problem_model(validator, validator.target_path(result["model"]["path"]),
                load_problem_model_schema(validator.schema_context), require_completion=True, current_task=True)
        if result["task_state"] == "active" and isinstance(loaded, dict) and isinstance(loaded.get("active_projection"), dict):
            paths.add(loaded["active_projection"]["path"])
        if result["task_state"] == "closed":
            from target_adapter_validation.analysis_strategies import load_problem_model_schema, validate_selected_problem_model
            closure_path = result["disposition_source"]["path"]
            closure = validator.context.read_json_result(validator.target_path(closure_path)).value
            paths.add(closure_path)
            witness = closure.get("analysis_witness") if isinstance(closure, dict) else None
            projection = witness["projection"]["path"] if isinstance(witness, dict) else None
            if projection is not None:
                paths.add(projection)
            index = validator.context.read_json_result(validator.target_path(".ai/assistant/active-tasks.json")).value
            registered = next(task for task in index["tasks"] if task["task_id"] == task_id)
            validate_selected_problem_model(validator, validator.target_path(result["model"]["path"]),
                load_problem_model_schema(validator.schema_context), require_completion=True,
                archived_projection=validator.target_path(projection) if projection else None,
                original_source_path=registered["problem_model"]["path"],
                current_task=True)
            result["completion_review"] = "record-consistent" if result["delivery"]["evidence_finalization"] == "final" else "provisional"
        if isinstance(loaded, dict) and "contract_work" in loaded and result["task_state"] == "active":
            from contract_work import verify_work_artifacts
            def read_contract(path: str, limit: int) -> bytes:
                value = validator.context.read_bytes_result(validator.target_path(path), max_bytes=limit)
                if value.value is None:
                    raise ValueError(value.error or "missing work contract")
                return value.value
            for failure in verify_work_artifacts(loaded, read_contract):
                validator.error("CONTRACT_WORK_ARTIFACT", failure, result["model"]["path"])
        for path in paths:
            validator.context.content_digest(validator.target_path(path))
        result["checkpoint_inputs"] = validator.context.content_bindings()
        if source_contour:
            from source_adoption import assert_current, selected_strategy_inputs
            result["checkpoint_inputs"].update(assert_current(target))
            result["checkpoint_inputs"].update(selected_strategy_inputs(target, loaded))
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
    return not task_context_missing(retained, task, policy_sha)


def task_context_missing(retained: dict, task: dict, policy_sha: str) -> list[str]:
    baseline = validate_baseline(retained.get("baseline", retained))
    inputs = {row["path"]: row["sha256"] for row in baseline["inputs"]}
    expected = {**task["checkpoint_inputs"], POLICY: policy_sha}
    return sorted(path for path, sha in expected.items() if sha is None or inputs.get(path) != "sha256:" + sha)


def validate_state(state: dict, session_id: str, *, source_contour: bool = False) -> None:
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
        required = {"baseline", "baseline_sha256", "task_id", "expires_at", "policy_sha256"}
        if source_contour:
            required.add("source_scope")
        if (not isinstance(binding, dict) or set(binding) - {"completion_only", "request_brief"} != required
                or "completion_only" in binding and type(binding["completion_only"]) is not bool):
            raise ValueError("invalid reviewed lifecycle binding")
        if source_contour and binding["source_scope"] is not None:
            from source_scope import validate_scope
            validate_scope(binding["source_scope"])
        if "request_brief" in binding:
            value = binding["request_brief"]
            extra = {"history", "request_id", "history_inputs"}
            if (not isinstance(value, dict) or set(value) - extra != {"path", "sha256"}
                    or set(value) & extra not in (set(), extra)):
                raise ValueError("invalid lifecycle request brief binding")
            if "history" in value:
                from delivery_receipts import artifact
                artifact(value["history"], "bound delivery history")
                identifier(value["request_id"], "bound history request_id")
                paths = value["history_inputs"]
                if not isinstance(paths, list) or not 1 <= len(paths) <= 128 or any(not isinstance(path, str) for path in paths):
                    raise ValueError("bound delivery inputs require 1..128 literal paths")
                if len(set(paths)) != len(paths):
                    raise ValueError("bound delivery inputs cannot repeat paths")
                for path in paths:
                    relative_path(path)
            relative_path(value["path"])
            if not isinstance(value["sha256"], str) or len(value["sha256"]) != 64 or any(char not in "0123456789abcdef" for char in value["sha256"]):
                raise ValueError("invalid request brief SHA-256")
        for field in ("baseline", "baseline_sha256", "task_id", "policy_sha256"):
            identifier(binding.get(field), "binding." + field)
        if type(binding.get("expires_at")) not in (int, float) or not 0 < binding["expires_at"] <= MAX_TIMESTAMP:
            raise ValueError("invalid lifecycle binding expiry")
    if state["status"] == "bound" and binding is None:
        raise ValueError("bound lifecycle session is missing its reviewed binding")


def session_status(target: Path, session_id: str, *, source_contour: bool = False) -> dict:
    if source_contour:
        from source_adoption import assert_current
        assert_current(target)
    session_id = identifier(session_id, "session_id")
    raw_policy, policy = load_policy(target)
    if policy is None or not policy["enabled"]:
        return decision("disabled", "Lifecycle delivery is not adopted.")
    path = target / runtime_directory(source_contour) / (digest(session_id.encode()) + ".json")
    raw = read_output(target, path, max_bytes=MAX_INPUT_BYTES)
    if raw is None:
        return decision("unknown", "No session event observed; no binding may be inferred.")
    state = json_object(raw, "lifecycle session")
    validate_state(state, session_id, source_contour=source_contour)
    interrupt = read_output(target, path.with_suffix(".interrupted"), max_bytes=128) or b""
    status = "interrupted" if state["interrupt_sha256"] != digest(interrupt) else state["status"]
    if status == "bound" and not binding_current(state["binding"], policy, raw_policy, time.time()):
        status = "review-required"
    return {**decision(status, "Session routing only; review authorization separately."),
        "request_id": state["request_id"], "reminders": state["reminders"]}


def request_artifact(target: Path, path: str) -> tuple[bytes, dict]:
    from request_brief import MAX_BRIEF_BYTES, parse_brief
    path = relative_path(path)
    raw = read_output(target, target / path, max_bytes=MAX_BRIEF_BYTES)
    if raw is None:
        raise ValueError("missing request brief: " + path)
    return raw, parse_brief(raw)


def review_request(target: Path, brief_path: str, action: object, *,
                   request_id: str | None = None, task_id: str | None = None,
                   expected_sha256: str | None = None, native_guard: dict | None = None,
                   native_payload: dict | None = None, retained: dict | None = None,
                   policy_sha256: str | None = None, history_anchor: dict | None = None,
                   history_request_id: str | None = None, history_inputs: list[str] | None = None,
                   source_contour: bool = False, source_scope: dict | None = None) -> dict:
    from request_brief import MAX_BRIEF_BYTES, action_failures, native_file_action_failures, parse_action
    raw, brief = request_artifact(target, brief_path)
    selected_action = parse_action(action)
    if expected_sha256 is not None and digest(raw) != expected_sha256:
        raise ValueError("bound request brief changed; reconcile the newest request")
    selected_id = task_id if task_id is not None else brief["task_id"]
    selected = selected_task(target, selected_id, request_review=True,
                             require_completion=selected_action["kind"] == "complete", source_contour=source_contour)
    failures = action_failures(brief, selected_action, selected["request_model"],
        request_id=request_id if request_id is not None else brief["request_id"], task_id=selected_id)
    if source_contour:
        from source_scope import review_scope, scope_inputs
        failures.extend(review_scope(target, source_scope, selected_action, brief, selected["request_model"]))
        if source_scope is not None:
            selected["checkpoint_inputs"].update(scope_inputs(source_scope))
    from request_focus import evidence_action_review, focus_failures, request_progress
    failures.extend(focus_failures(brief, selected_action, selected["request_model"], digest(raw)))
    health, evidence_failures = evidence_action_review(brief, selected_action, selected["request_model"],
        selected.get("evidence_readiness", {"state": "not-adopted"}))
    failures.extend(evidence_failures)
    progress = request_progress(brief, selected["request_model"], health)
    required_context = set(selected["checkpoint_inputs"]) | {POLICY, brief_path}
    delivery_inputs = {}
    delivery_review = None
    delivery_history = None
    control = brief.get("delivery_control")
    if control is not None:
        from delivery_control import MAX_HISTORY_BYTES, delivery_failures, parse_history
        history_path = control["validation_history"]
        context = selected["request_contexts"][0]
        history_read = context.read_bytes_result(target / history_path, max_bytes=MAX_HISTORY_BYTES)
        if history_anchor is not None:
            delivery_inputs[history_path] = history_anchor["sha256"]
        try:
            if history_read.value is None:
                raise ValueError("missing or unreadable validation history: " + history_path)
            delivery_inputs[history_path] = digest(history_read.value)
            history = parse_history(history_read.value, brief)
            failures.extend(delivery_failures(brief, selected_action, selected["request_model"], history))
            if history["schema_version"] == 2:
                from delivery_progress import execution_review
                delivery_history = {"path": history_path, "sha256": digest(history_read.value)}
                delivery_review, delivery_failures_found = execution_review(context, target, brief, selected_action,
                    selected["request_model"], history, delivery_inputs, history_parser=parse_history,
                    history_anchor=history_anchor, history_sha256=delivery_history["sha256"],
                    anchor_request_id=history_request_id)
                failures.extend(delivery_failures_found)
                if history_anchor is None and (selected_action["phase"] != "inspect" or selected_action["kind"] == "complete"
                                               or "validation" in selected_action):
                    failures.append("schema-2 delivery work requires a retained history binding; use the bound procedural/native checkpoint")
            elif history_anchor is not None:
                failures.append("cannot drop an anchored schema-2 delivery history")
        except ValueError as exc:
            if control.get("execution_review") is None:
                raise
            recovery = selected_action["phase"] == "inspect" and selected_action["kind"] != "complete" and "validation" not in selected_action
            if not recovery:
                failures.append(str(exc))
            delivery_review = {"state": "reassessment-required", "reasons": [str(exc)],
                               "authorization_granted": False, "acceptance_granted": False}
        selected["checkpoint_inputs"].update(delivery_inputs)
    elif "validation" in selected_action:
        failures.append("validation preflight requires an adopted delivery_control")
    elif history_anchor is not None:
        failures.append("cannot drop an anchored delivery control within the same request")
    if selected["task_state"] == "closed" and selected_action["kind"] == "work":
        failures.append("closed task cannot reopen execution through request review")
    if retained is not None and not task_context_matches(retained, selected, policy_sha256):
        missing = task_context_missing(retained, selected, policy_sha256)
        recovery = (delivery_review is not None and selected_action["phase"] == "inspect"
                    and selected_action["kind"] != "complete" and "validation" not in selected_action)
        if recovery and set(missing) <= set(delivery_inputs):
            delivery_review["state"] = "reassessment-required"
            delivery_review["reasons"].append("delivery input changed since binding; reconcile before state changes")
        else:
            failures.append("selected completion/request inputs are missing or changed in retained context; recapture exact selected evidence")
    if native_guard is not None:
        failures.extend(native_file_action_failures(target, native_guard, native_payload or {}, selected_action))
    else:
        for path in selected_action["paths"]:
            safe_output(target, target / path)
    if read_output(target, target / relative_path(brief_path), max_bytes=MAX_BRIEF_BYTES) != raw:
        raise ValueError("request brief changed during review")
    for context in selected["request_contexts"]:
        if context.finalize():
            raise ValueError("selected request inputs changed during review")
    if source_contour:
        from source_adoption import assert_current
        if any(selected["checkpoint_inputs"].get(path) != sha for path, sha in assert_current(target).items()):
            raise ValueError("source controls changed during request review")
    result = decision("request-review-required" if failures else "request-consistent",
        "; ".join(failures[:8]) if failures else "Declared request, selected model and action agree; newest intent and approval still require review.", block=bool(failures))
    result.update(request_id=brief["request_id"], task_id=selected_id, failures=failures,
        request_brief={"path": brief_path, "sha256": digest(raw)},
        focus_control=brief.get("focus_control"), evidence_readiness=health, request_progress=progress,
        request_provenance="declarative-unverified", execution_interception="not-performed")
    if health["state"] == "stale-or-unavailable":
        result["reason"] += " Evidence is stale or unavailable; inspect evidence_readiness before relying on this action or answer."
    if delivery_inputs:
        result["delivery_inputs"] = delivery_inputs
    if delivery_review is not None:
        delivery_review["recovery_omissions"] = sorted(set(history_inputs or ()) - required_context)
        result["delivery_review"] = delivery_review
    if delivery_history is not None:
        result["delivery_history"] = delivery_history
    return result


def bind_request_brief(target: Path, bind: dict, state: dict, policy: dict, retained: dict, *, source_contour: bool = False) -> dict | None:
    path = bind.get("request_brief")
    prior = state.get("binding")
    required = policy.get("request_guard", {}).get("required", False) or isinstance(prior, dict) and "request_brief" in prior
    if path is None:
        if required:
            raise ValueError("request guard requires an explicit request brief; rebind cannot drop it")
        return None
    raw, brief = request_artifact(target, path)
    action = {"request_id": state["request_id"], "task_id": bind["task_id"], "kind": "answer",
              "phase": "inspect", "outcome_ids": [row["id"] for row in brief["outcomes"]], "paths": [], "effects": [],
              "brief_sha256": digest(raw)}
    prior_history = prior.get("request_brief", {}).get("history") if isinstance(prior, dict) else None
    prior_request = prior.get("request_brief", {}).get("request_id") if isinstance(prior, dict) else None
    prior_inputs = prior.get("request_brief", {}).get("history_inputs") if isinstance(prior, dict) else None
    review = review_request(target, path, action, request_id=state["request_id"], task_id=bind["task_id"],
                            history_anchor=prior_history, history_request_id=prior_request, history_inputs=prior_inputs,
                            source_contour=source_contour)
    if review["checkpoint_required"]:
        raise ValueError(review["reason"])
    if review.get("delivery_review", {}).get("state") == "reassessment-required":
        raise ValueError("reconcile delivery evidence before binding: " + "; ".join(review["delivery_review"]["reasons"][:4]))
    expected = {row["path"]: row["sha256"] for row in validate_baseline(retained.get("baseline", retained))["inputs"]}
    if expected.get(path) != "sha256:" + digest(raw) or review["request_brief"]["sha256"] != digest(raw):
        raise ValueError("reviewed baseline must retain the exact request brief")
    if any(expected.get(name) != "sha256:" + sha for name, sha in review.get("delivery_inputs", {}).items()):
        raise ValueError("reviewed baseline must retain the exact validation history")
    result = review["request_brief"]
    if "delivery_history" in review:
        result["history"] = review["delivery_history"]
        result["request_id"] = brief["request_id"]
        result["history_inputs"] = sorted(review["delivery_inputs"])
        if len(result["history_inputs"]) > 128:
            raise ValueError("delivery binding exceeds 128 selected artifacts; decompose without dropping history")
    return result


def runtime_directory(source_contour: bool) -> str:
    return ".ai/.runtime/source-lifecycle-hooks" if source_contour else RUNTIME


def handle(target: Path, provider: str, event: str, payload: dict, *,
           bind: dict | None = None, now: float | None = None, procedural: bool = False,
           source_contour: bool = False) -> dict:
    if source_contour:
        from source_adoption import assert_current, assert_source_root
        assert_source_root(target)
        if provider != "procedural":
            raise ValueError("source lifecycle delivery is procedural; native interception is unverified")
        if event not in {"interrupt", "end"}:
            assert_current(target)
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
    if not source_contour:
        assert_write_compatible(target, tool_name="run_lifecycle_checkpoint.py")
    state_path = target / runtime_directory(source_contour) / (digest(session_id.encode()) + ".json")
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
    revocation = None
    if event in {"interrupt", "request", "end"}:
        # Independent revocation: a slow completion reader cannot hold it off.
        previous = read_output(target, interrupt_path, max_bytes=128)
        revocation = uuid.uuid4().hex.encode()
        replace_output(target, interrupt_path, previous, revocation)
        if event == "interrupt":
            return decision("interrupted", "Interrupted; no automatic restart or continuation.")
    with file_lock(lock, timeout=0.25):
        current_time = time.time() if now is None else now
        interrupt = read_output(target, interrupt_path, max_bytes=128) or b""
        raw_state = read_output(target, state_path, max_bytes=MAX_INPUT_BYTES)
        state = json_object(raw_state, "lifecycle session") if raw_state else {
            "schema_version": 1, "session_id": session_id, "request_id": uuid.uuid4().hex,
            "status": "interrupted" if interrupt else "unbound", "binding": None,
            "reminders": 0, "interrupt_sha256": digest(interrupt)}
        validate_state(state, session_id, source_contour=source_contour)
        if revocation is not None and revocation != interrupt:
            state.update(status="interrupted", binding=None)
            result = decision("interrupted", "A newer request or interruption superseded this callback; no continuation.", block=True)
        elif event in {"request", "end"}:
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
        elif "request_id" in payload and payload["request_id"] != state["request_id"]:
            result = decision("review-required", "Callback belongs to an older request; do not continue it.", block=True)
        elif bind is not None:
            if state["status"] in {"interrupted", "ended"} or bind.get("request_id") != state["request_id"]:
                raise ValueError("reviewed binding requires the current non-interrupted request ID")
            baseline_raw, retained = object_at(target, bind["baseline"], 128 * 1024)
            task_options = {"request_review": True, "source_contour": True} if source_contour else {}
            task = selected_task(target, identifier(bind["task_id"], "task_id"), **task_options)
            completion_only = bind.get("completion_only", False)
            if type(completion_only) is not bool:
                raise ValueError("completion_only must be Boolean")
            if task["task_state"] != "active" and not completion_only:
                raise ValueError("a closed task cannot be rebound as an active execution scope")
            missing = task_context_missing(retained, task, digest(raw_policy))
            if missing:
                raise ValueError("reviewed baseline must include current canonical task index, selected model and projection, and lifecycle policy; capture changed/missing selected inputs: " + ", ".join(missing[:12]))
            if read_output(target, target / bind["baseline"], max_bytes=128 * 1024) != baseline_raw:
                raise ValueError("reviewed baseline changed during binding")
            request_brief = bind_request_brief(target, bind, state, policy, retained, source_contour=source_contour)
            scope = None
            if source_contour:
                from source_scope import bind_scope, scope_inputs
                _, brief = request_artifact(target, bind["request_brief"])
                prior = state.get("binding")
                scope = bind_scope(target, bind, prior.get("source_scope") if prior else None, brief, task["request_model"],
                                   previously_bound=prior is not None)
                expected = {row["path"]: row["sha256"] for row in validate_baseline(retained.get("baseline", retained))["inputs"]}
                if scope is not None and any(expected.get(path) != "sha256:" + sha for path, sha in scope_inputs(scope).items()):
                    raise ValueError("source baseline must retain the exact selected approval records")
            state.update(status="bound", binding={"baseline": bind["baseline"],
                "baseline_sha256": digest(baseline_raw), "task_id": bind["task_id"],
                "expires_at": (time.time() if now is None else now) + policy["binding_ttl_seconds"], "policy_sha256": digest(raw_policy),
                "completion_only": completion_only})
            if request_brief is not None:
                state["binding"]["request_brief"] = request_brief
            if source_contour:
                state["binding"]["source_scope"] = scope
            result = decision("bound", "Review recorded; phases, permissions and acceptance remain separately owned.")
        elif event in {"after-change", "compact"}:
            if state["status"] not in {"interrupted", "ended"}:
                state["status"] = "review-required"
            result = decision(state["status"], "Reconcile affected owners, documentation and evidence before the next mutation.")
        elif state["status"] != "bound":
            if policy.get("request_guard", {}).get("required", False) and state["status"] not in {"interrupted", "ended"}:
                result = decision("request-review-required", "Adopted request guard requires a current reviewed brief; inspect only.", block=True)
            elif state["binding"] is None and state["status"] not in {"interrupted", "ended"}:
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
                elif "request_brief" in binding and event in {"before-action", "completion"}:
                    brief = binding["request_brief"]
                    result = review_request(target, brief["path"], payload.get("alatyr_action"),
                        request_id=state["request_id"], task_id=binding["task_id"], expected_sha256=brief["sha256"],
                        native_guard=policy.get("request_guard", {"required": False, "file_tools": []}) if provider != "procedural" and not procedural and event == "before-action" else None,
                        native_payload=payload, retained=retained, policy_sha256=digest(raw_policy),
                        history_anchor=brief.get("history"), history_request_id=brief.get("request_id"),
                        history_inputs=brief.get("history_inputs"), source_contour=source_contour,
                        source_scope=binding.get("source_scope"))
                    if binding.get("completion_only") and event == "before-action":
                        result = decision("completion-only", "Terminal review cannot reopen execution.", block=True)
                    elif event == "completion" and payload["alatyr_action"]["kind"] == "work":
                        result = decision("request-review-required", "Completion callback requires answer or complete review.", block=True)
                    elif (event == "completion" and not result["checkpoint_required"]
                          and payload["alatyr_action"]["kind"] == "answer"
                          and result["request_progress"]["remaining_outcome_ids"]):
                        ready = bool(result["request_progress"]["ready_outcome_ids"])
                        result.update(decision("unfinished" if ready else "handoff-review",
                            f"Partial answer only: {len(result['request_progress']['remaining_outcome_ids'])} original outcomes remain. Review independent work and current authorization; supporting delivery is not task completion.",
                            block=ready))
                elif event == "before-action":
                    result = (decision("completion-only", "Terminal review binding cannot reopen execution; select a current active scope before mutation.", block=True)
                              if binding.get("completion_only") else
                              decision("current-context", "Fresh context only; classify the intended action and check current-scope authorization procedurally."))
                else:
                    view = selected_task(target, binding["task_id"], **({"source_contour": True} if source_contour else {}))
                    if not task_context_matches(retained, view, digest(raw_policy)):
                        result = decision("review-required", "Selected task changed during evaluation; reconcile context before continuation.", block=True)
                    else:
                        ready = view.get("execution_readiness", {}).get("ready", []) if view["task_state"] == "active" else []
                        result = decision("unfinished" if ready else "handoff-review",
                            "Review the selected task's unresolved duties and original outcome. "
                            + ("Independent ready duties remain; continue only within current human authorization. " if ready else "Do not claim completion from a recorded disposition. ")
                            + "A blocker, pause, interruption or authority boundary wins; use canonical acceptance for completion.", block=bool(ready))
                        if view.get("completion_review") == "record-consistent":
                            result = decision("completion-evidence-consistent",
                                "Selected closure and completed-model evidence are consistent. This checkpoint grants neither canonical acceptance, publication, nor current runtime readiness.")
                        result["completion_review"] = view.get("completion_review", "closure-required")
        active = not procedural and policy["mode"] == "checkpoint" and policy["native_evidence"]["state"] == "observed"
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
        if len(encoded) > MAX_INPUT_BYTES:
            raise ValueError("lifecycle state exceeds its input byte ceiling; decompose selected context")
        replace_output(target, state_path, raw_state, encoded)
        # One canonical comparison, after task evaluation and durable state writes.
        if state["status"] == "bound" and result["status"] in {"bound", "current-context", "unfinished", "handoff-review", "handoff-required", "completion-only", "completion-evidence-consistent", "request-consistent"}:
            selected_action = payload.get("alatyr_action", {})
            recovery = (event == "before-action" and result.get("delivery_review", {}).get("state") == "reassessment-required"
                        and selected_action.get("phase") == "inspect" and selected_action.get("kind") in {"answer", "work"}
                        and "validation" not in selected_action)
            omissions = result["delivery_review"].get("recovery_omissions", []) if recovery else []
            options = {"source_contour": True, "protected_inputs": tuple(assert_current(target))} if source_contour else {}
            context = (check_retained_context(target, target / state["binding"]["baseline"], inspection_omissions=omissions, **options)
                       if omissions else check_retained_context(target, target / state["binding"]["baseline"], **options))
            final_baseline, _ = object_at(target, state["binding"]["baseline"], 128 * 1024)
            if context["status"] != "current" or digest(final_baseline) != state["binding"]["baseline_sha256"]:
                delivery_diagnostics = result.get("delivery_review")
                result = decision("review-required", "Selected context or reviewed baseline changed before delivery; inspect only.", block=True)
                if delivery_diagnostics is not None:
                    result["delivery_review"] = delivery_diagnostics
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
