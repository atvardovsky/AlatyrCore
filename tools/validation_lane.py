"""Bounded local coordination for opt-in expensive registered validation."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid

from cli_inputs import json_object
from delivery_receipts import sha256
from local_file_lock import file_lock
from request_values import fields, integer
from session_presence_store import git_identity, safe_hub
from support_write_transaction import read_output, replace_output, safe_output
from validation_lane_policy import MAX_BYTES, STATES, case_ids

OUTCOMES = {"running", "discovery-failed", "execution-failed", "unverified", "finished", "cleanup-failed"}


def _encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()


def _digest(value):
    return hashlib.sha256(_encode(value)).hexdigest()


def _ledger(hub, path, identity, limits):
    raw = read_output(hub, path, max_bytes=MAX_BYTES)
    if raw is None:
        return raw, {"schema_version": 1, "objective": identity, "limits": list(limits), "attempts": []}
    value = fields(json_object(raw, "validation history"), {"schema_version", "objective", "limits", "attempts"},
                   "validation lane history")
    old = value["limits"]
    if (type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["objective"] != identity
            or not isinstance(old, list) or len(old) != 2):
        raise ValueError("validation lane history is bound to a different objective or format")
    integer(old[0], "retained attempt limit", 1, 32)
    integer(old[1], "retained time limit", 1, 86400)
    attempts = value["attempts"]
    if not isinstance(attempts, list) or len(attempts) > 32:
        raise ValueError("validation lane history exceeded its attempt limit")
    ids = set()
    for row in attempts:
        fields(row, {"id", "material", "binding", "status", "seconds", "artifact_sha256", "case_sha256"},
               "validation lane attempt")
        key = row["id"]
        if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{32}", key) or key in ids:
            raise ValueError("validation lane history requires distinct attempt IDs")
        ids.add(key)
        if not isinstance(row["status"], str) or row["status"] not in OUTCOMES:
            raise ValueError("invalid validation lane attempt state")
        integer(row["seconds"], "retained attempt seconds", 1, 86400)
        sha256(row["material"], "retained material")
        sha256(row["binding"], "retained exact binding")
        for name in ("artifact_sha256", "case_sha256"):
            if row[name] is not None:
                sha256(row[name], name)
    value["limits"] = [min(a, b) for a, b in zip(old, limits)]
    return raw, value


def _retry_reason(attempts, material, retry):
    if not attempts:
        if retry:
            return "retry cannot bind an absent prior attempt"
        return None
    last = attempts[-1]
    if retry is None or retry["previous_attempt"] != last["id"]:
        return "repeat needs a reviewed diagnosis that binds the latest lane attempt"
    if retry["reason"] == "changed-input" and material == last["material"]:
        return "changed-input retry requires different material, not a new request or wrapper label"
    if last["status"] in {"running", "unverified", "cleanup-failed"} and not (
            retry["reason"] == "execution-repair" and retry["cleanup_confirmed"]):
        return "prior launch or cleanup is unresolved; verify the owned child and resources are stopped"
    if retry["reason"] == "execution-repair" and last["status"] == "finished":
        return "execution-repair requires a failed or interrupted attempt"
    if sum(row["status"] != "finished" for row in attempts) >= 2 and not retry["independent_review"]:
        return "repeated lane failures require a distinct independent review"
    return None


def _probe(argv, target, environment, deadline, expected):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("validation lane exhausted its time before discovery")
    # The target-owned probe must be small and read-only. Do not buffer its logs in memory.
    with tempfile.TemporaryFile() as output_file:
        result = subprocess.run(argv, cwd=target, env=environment, stdin=subprocess.DEVNULL,
                                stdout=output_file, stderr=sys.stderr, check=False, timeout=min(30, remaining))
        output_file.seek(0)
        raw = output_file.read(MAX_BYTES + 1)
    if result.returncode or len(raw) > MAX_BYTES:
        raise ValueError("read-only discovery or artifact verification failed")
    output = fields(json_object(raw, "validation probe output"), {"schema_version", "cases"}, "validation probe output")
    if type(output["schema_version"]) is not int or output["schema_version"] != 1:
        raise ValueError("validation probe requires schema 1")
    if set(case_ids(output["cases"], "discovered cases")) != set(expected):
        raise ValueError("discovery does not match the exact approved case selection")


def _cases(hub, path, expected):
    raw = read_output(hub, path, max_bytes=MAX_BYTES)
    value = fields(json_object(raw or b"", "case result"), {"schema_version", "cases", "cleanup"}, "case result")
    results = value["cases"]
    if (type(value["schema_version"]) is not int or value["schema_version"] != 1
            or not isinstance(results, dict) or set(results) != set(expected)
            or any(not isinstance(status, str) or status not in STATES for status in results.values())
            or value["cleanup"] not in ("passed", "failed", "not-applicable")):
        raise ValueError("case receipt must account for every selected case and the cleanup disposition")
    return value, hashlib.sha256(raw).hexdigest()


def _receipt(target, spec):
    data = read_output(target, target / spec["receipt"], max_bytes=MAX_BYTES)
    return hashlib.sha256(data).hexdigest() if data is not None else None


def _result(base, identity, state, *, blocked=True, started=False, **details):
    return {**base, "status": state, "checkpoint_required": blocked, "command_started": started,
            "validation_objective": identity, "authorization_granted": False, "acceptance_granted": False,
            "limitation": "Execution observations only; native test evidence, coverage and owner acceptance remain separate.",
            **details}


def _execute(hub, path, raw, history, target, lane, argv, result, recheck, verify, runner):
    identity = lane["objective"]
    attempts = history["attempts"]
    environment = dict(os.environ)
    environment.pop("ALATYR_VALIDATION_CASE_RESULT", None)
    artifact = lane["artifact"]
    material = _digest([lane["material_inputs"], sorted(lane["cases"])])
    binding = _digest([str(target), argv, lane["probe_argv"], material, lane["inputs"],
                       lane["policy_sha256"], artifact, _digest(environment)])
    current = _receipt(target, artifact) if artifact else None
    estimated = lane["estimate"]
    deadline = time.monotonic() + estimated
    last = attempts[-1] if attempts else None
    if (current and last and last["status"] == "finished" and last["binding"] == binding
            and last["artifact_sha256"] == current):
        recheck()
        _probe(artifact["argv"], target, environment, deadline, [])
        recheck()
        if _receipt(target, artifact) != current:
            raise ValueError("artifact receipt changed during verification")
        return _result(result, identity, "artifact-available", blocked=False, attempt_id=last["id"],
                       artifact={"path": artifact["receipt"], "sha256": current}, tests_reused=False)
    reason = _retry_reason(attempts, material, lane["retry"])
    if reason:
        return _result(result, identity, "launch-blocked", reason=reason, previous_attempt=last["id"] if last else None)
    if current:
        raise ValueError("existing artifact receipt is not qualified; reconcile or move it before rebuilding")
    maximum, time_limit = history["limits"]
    if len(attempts) >= maximum or sum(row["seconds"] for row in attempts) + estimated > time_limit:
        raise ValueError("validation objective cumulative attempt or time budget exhausted; reassess with the owner")
    recheck()
    attempt = {"id": uuid.uuid4().hex, "material": material, "binding": binding, "status": "running", "seconds": estimated,
               "artifact_sha256": None, "case_sha256": None}
    attempts.append(attempt)
    reserved = _encode(history)
    replace_output(hub, path, raw, reserved)
    outcome, started, code, details = "discovery-failed", False, None, {}
    start = time.monotonic()
    try:
        _probe(lane["probe_argv"], target, environment, deadline, lane["cases"])
        recheck()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("validation lane exhausted its time before launch")
        case_path = safe_output(hub, hub / (attempt["id"] + ".cases.json"))
        if lane["cases"]:
            environment["ALATYR_VALIDATION_CASE_RESULT"] = str(case_path)
        started = True
        outcome = "unverified"
        completed = runner(argv, cwd=target, env=environment, shell=False, stdin=subprocess.DEVNULL,
                           stdout=sys.stderr, stderr=sys.stderr, check=False, timeout=remaining)
        code = completed.returncode
        verify()
        outcome = "execution-failed" if code else "finished"
        if lane["cases"]:
            output, digest = _cases(hub, case_path, lane["cases"])
            attempt["case_sha256"] = digest
            cases = output["cases"]
            counts = {state: sum(value == state for value in cases.values()) for state in sorted(STATES)}
            details.update(case_counts=counts, cleanup=output["cleanup"], case_sha256=digest,
                           unresolved_cases=[key for key in lane["cases"] if cases[key] != "passed"][:8])
            if output["cleanup"] == "failed":
                outcome = "cleanup-failed"
            elif counts["failed"] or counts["not-run"]:
                outcome = "execution-failed"
        if artifact and outcome == "finished":
            outcome = "unverified"
            digest = _receipt(target, artifact)
            if digest is None:
                raise ValueError("successful build must produce its new artifact receipt")
            _probe(artifact["argv"], target, environment, deadline, [])
            verify()
            if _receipt(target, artifact) != digest:
                raise ValueError("artifact receipt changed during verification")
            attempt["artifact_sha256"] = digest
            details["artifact"] = {"path": artifact["receipt"], "sha256": digest}
            outcome = "finished"
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
        outcome = "unverified" if started or isinstance(exc, (subprocess.TimeoutExpired, KeyboardInterrupt)) else "discovery-failed"
        details["reason"] = ("owned validation timed out or was interrupted; verify cleanup before retry"
                             if isinstance(exc, (subprocess.TimeoutExpired, KeyboardInterrupt)) else str(exc)[:400])
    finally:
        attempt["status"] = outcome
        attempt["seconds"] = min(86400, max(1, math.ceil(time.monotonic() - start)))
        try:
            replace_output(hub, path, reserved, _encode(history))
        except (OSError, ValueError, RuntimeError) as exc:
            outcome = "unverified"
            details["reason"] = "attempt journal could not be finalized; reconcile the retained reservation: " + str(exc)[:250]
    return _result(result, identity, "command-finished" if outcome == "finished" else outcome,
                   blocked=outcome != "finished", started=started, attempt_id=attempt["id"],
                   child_exit_code=code, duration_seconds=attempt["seconds"], **details)


def run_lane(target, lane, argv, result, recheck, verify, runner):
    """One cooperating expensive child per Git common directory; no host-wide lock."""
    identity = lane["objective"]
    try:
        _, presence, _ = git_identity(target)
        hub = presence.with_name("alatyr-validation-lanes")
        safe_hub(hub, create=True)
        path = hub / (identity + ".json")
        with file_lock(safe_output(hub, hub / "heavy.lock"), timeout=0.05):
            raw, history = _ledger(hub, path, identity, lane["limits"])
            return _execute(hub, path, raw, history, target, lane, argv, result, recheck, verify, runner)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        return _result(result, identity, "launch-blocked", reason=str(exc)[:400])
