"""Opt-in exact registered launches; not a general runner or authority source."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

from project_evidence import ProjectEvidence
from test_execution_contract import REPAIR_POLICY as POLICY

POLICY = ".ai/project/testing/test-first-policy.json"


def run_validation(target: Path, provider: str, payload: dict, argv: list[str], *, runner=None) -> dict:
    from lifecycle_checkpoints import handle, session_status
    action = payload.get("alatyr_action")
    if not isinstance(action, dict) or not isinstance(action.get("validation"), dict) or not action["validation"].get("execution_evidence"):
        raise ValueError("run-validation requires an action with validation.execution_evidence")
    result = handle(target, provider, "before-action", payload, procedural=True)
    if result["status"] != "request-consistent" or result["checkpoint_required"]:
        return {**result, "status": "launch-blocked", "checkpoint_required": True, "command_started": False}
    selected = result.get("validation_command")
    if not isinstance(selected, dict) or argv != selected["argv"]:
        raise ValueError("actual argv must exactly equal the target-owned registered argv; no implicit filters or shell parsing")
    from team_task_control import task_holds
    from target_adapter_validation.context import TargetRepositoryView
    completed = None
    attempted = False
    try:
        with ProjectEvidence(target) as snapshot:
            for path, expected in selected["input_sha256"].items():
                if hashlib.sha256(snapshot.exact(path)).hexdigest() != expected:
                    raise ValueError("validation input changed before launch: " + path)
            snapshot.verify()
            try:
                team = TargetRepositoryView(target)
                holds = task_holds(team, [action["task_id"]])
                if team.finalize():
                    raise ValueError("team task state changed before launch")
            except (OSError, ValueError, RuntimeError) as exc:
                return {**result, "status": "launch-blocked", "checkpoint_required": True,
                        "command_started": False, "reason": str(exc)[:300]}
            if holds:
                return {**result, "status": "launch-blocked", "checkpoint_required": True,
                        "command_started": False, "reason": holds[action["task_id"]]}
            state = session_status(target, payload["session_id"])
            if state["status"] != "bound" or state.get("request_id") != action["request_id"]:
                raise ValueError("request was interrupted, ended or expired before launch")
            # Target-owned commands retain their own fixture, resource and teardown guards.
            attempted = True
            completed = (subprocess.run if runner is None else runner)(argv, cwd=target, shell=False,
                stdin=subprocess.DEVNULL, stdout=sys.stderr, stderr=sys.stderr, check=False)
    except (OSError, ValueError, RuntimeError) as exc:
        if not attempted:
            raise
        return {**result, "status": "execution-unverified", "checkpoint_required": True,
                "command_started": True if completed is not None else None,
                "child_exit_code": completed.returncode if completed is not None else None,
                "reason": str(exc)[:500] + "; retain the attempt and diagnose before retry"}
    return {**result, "status": "command-finished", "command_started": True,
            "child_exit_code": completed.returncode, "checkpoint_required": completed.returncode != 0,
            "acceptance_granted": False, "authorization_granted": False,
            "limitation": "Exact registered child only; no automatic retry, history receipt, semantic acceptance, native interception or descendant cleanup is supplied."}
