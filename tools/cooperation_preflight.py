#!/usr/bin/env python3
"""Compose advisory session and declared test-resource checks without writes."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from plan_test_resources import resource_plan
from session_presence_contract import scope_reference
from session_presence_store import operate


def preflight(target: Path, scopes: list[str], *, command_ids: list[str] | None = None,
              session_uid: str | None = None, source_contour: bool = False) -> dict:
    resources = resource_plan(target, command_ids) if command_ids else None
    selected = list(dict.fromkeys([*scopes, *(resources["presence_scope_refs"] if resources else [])]))
    if not selected:
        raise ValueError("select at least one scope or registered test command")
    presence = operate(target, "status", scope=selected, session_uid=session_uid, source_contour=source_contour)
    coordination = presence.get("coordination", {})
    conflicts = bool(coordination.get("reported_overlaps")) or resources is not None and not resources["concurrent_eligible"]
    uncertain = (any(scope_reference(scope)[0] == "unknown" for scope in selected)
                 or not presence["enabled"] or bool(presence.get("omitted_sessions"))
                 or bool(coordination.get("unknown_scope_peers"))
                 or bool(coordination.get("same_worktree_uncertain"))
                 or any(peer.get("freshness") != "recent" or peer.get("overlap") in {"unknown", "not-compared"}
                        for peer in presence.get("sessions", [])))
    return {"schema_version": 1, "report_kind": "alatyr-cooperation-preflight", "scope": selected,
            "decision": "coordinate-before-work" if conflicts else "unknown" if uncertain else "no-reported-conflict",
            "presence": presence, "resources": resources,
            "limitation": "Advisory reported state only, not a reservation, liveness proof, isolation guarantee, authorization or command execution. Independent clones and unreported sessions are not observed."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--scope", action="append", default=[])
    parser.add_argument("--command", action="append", default=[])
    parser.add_argument("--session-uid")
    parser.add_argument("--source-contour", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(preflight(args.target, args.scope, command_ids=args.command,
                                  session_uid=args.session_uid, source_contour=args.source_contour), indent=2))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError, RecursionError) as exc:
        print(f"FAIL: cooperation preflight: {str(exc)[:400]}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
