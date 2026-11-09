#!/usr/bin/env python3
"""Deliver optional lifecycle checkpoints without executing project work."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

from inspect_session_context import Once, json_object
from lifecycle_checkpoints import (EVENTS, MAX_INPUT_BYTES, NATIVE_EVENTS, PROVIDERS,
    decision, handle, identifier, load_policy, review_request, session_status)


def normalize(provider: str, native_event: str, payload: dict) -> tuple[str, dict]:
    if provider == "procedural":
        if native_event not in EVENTS:
            raise ValueError("unknown procedural checkpoint")
        return native_event, payload
    event = NATIVE_EVENTS[provider].get(native_event)
    if event is None:
        raise ValueError("unsupported native lifecycle event; use procedural delivery")
    reported = payload.get("hook_event_name")
    if reported is not None and reported != native_event:
        raise ValueError("native payload event differs from configured event")
    if "stop_hook_active" in payload and type(payload["stop_hook_active"]) is not bool:
        raise ValueError("stop_hook_active must be Boolean")
    value = dict(payload)
    # Copilot and Cursor use different identity names; never infer a parent ID.
    names = {"copilot": ("sessionId", "session_id"), "cursor": ("conversation_id",)}.get(provider, ("session_id",))
    ids = [payload[name] for name in names if name in payload]
    if not ids or any(item != ids[0] for item in ids):
        raise ValueError("missing or conflicting native session identity")
    value["session_id"] = identifier(ids[0], "session_id")
    if provider == "cursor" and event == "completion":
        if not isinstance(payload.get("status"), str):
            raise ValueError("Cursor completion status must be a string")
        if payload["status"] in {"aborted", "error"}:
            event = "interrupt"
        elif payload.get("status") != "completed":
            raise ValueError("Cursor completion requires a known status")
    return event, value


def native_output(provider: str, native_event: str, result: dict) -> dict:
    event = NATIVE_EVENTS.get(provider, {}).get(native_event)
    if not result.get("emit_native_block"):
        return {}
    reason = "Alatyr checkpoint (not human authorization): " + result["reason"]
    if event == "completion":
        if provider == "cursor":
            return {"followup_message": reason}
        return {"decision": "deny" if provider == "gemini" else "block", "reason": reason}
    if event == "before-action":
        if provider == "copilot":
            return {"permissionDecision": "deny", "permissionDecisionReason": reason}
        if provider == "gemini":
            return {"decision": "deny", "reason": reason}
        if provider == "cursor":
            return {"permission": "deny", "user_message": reason, "agent_message": reason}
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}
    return {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, type=Path, action=Once)
    parser.add_argument("--provider", choices=sorted(PROVIDERS), default="procedural", action=Once)
    parser.add_argument("--source-contour", action="store_true", help="Use the running source repository's explicit procedural lane, not an installed adapter.")
    actions = parser.add_subparsers(dest="action", required=True)
    event = actions.add_parser("event", allow_abbrev=False)
    event.add_argument("--event", required=True, action=Once, help="Exact native event, or a procedural checkpoint name.")
    event.add_argument("--native-output", action="store_true", help="Emit provider wire JSON; diagnostics go to stderr.")
    checkpoint = actions.add_parser("checkpoint", allow_abbrev=False)
    checkpoint.add_argument("--event", choices=sorted(EVENTS), required=True, action=Once,
        help="Explicit normalized procedural delivery for the selected provider; JSON on stdin.")
    bind = actions.add_parser("bind", allow_abbrev=False)
    for field in ("session-id", "request-id", "baseline", "task-id"):
        bind.add_argument("--" + field, required=True, action=Once)
    bind.add_argument("--completion-only", action="store_true", help="Review terminal evidence without reopening execution.")
    bind.add_argument("--request-brief", action=Once, help="Retained request brief, included in the reviewed context baseline.")
    bind.add_argument("--diff-ref", action=Once, help="Source-only approved Git comparison base, resolved on binding.")
    bind.add_argument("--approval-record", action="append", default=[], help="Source-only explicit target-relative approval record; repeatable.")
    review = actions.add_parser("review", allow_abbrev=False)
    review.add_argument("--request-brief", required=True, action=Once,
        help="Read-only declared request/action check; bounded action JSON on stdin, no hook adoption required.")
    status = actions.add_parser("status", allow_abbrev=False)
    status.add_argument("--session-id", required=True, action=Once)
    setup = actions.add_parser("setup-plan", allow_abbrev=False)
    setup.add_argument("--installation-kind", choices=("new", "update"), required=True, action=Once)
    setup.add_argument("--native-setup-approved", action="store_true")
    setup.add_argument("--client-version", action=Once)
    setup.add_argument("--config-path", action=Once, help="Exact approved project-local client configuration, never global settings.")
    setup.add_argument("--interpreter", choices=("python", "python3", "py"), default="python", action=Once)
    return parser


def main() -> int:
    native_requested = "--native-output" in sys.argv[1:]
    partial = argparse.Namespace()
    parser_errors = io.StringIO()
    try:
        with contextlib.redirect_stderr(parser_errors) if native_requested else contextlib.nullcontext():
            args = build_parser().parse_args(namespace=partial)
    except SystemExit as exc:
        ordinary = getattr(partial, "action", None) in {"bind", "review", "status", "checkpoint", "setup-plan"}
        if not native_requested or exc.code != 2 or ordinary:
            if native_requested and ordinary:
                print(parser_errors.getvalue(), file=sys.stderr, end="")
            raise
        print(json.dumps(decision("unavailable", "Invalid lifecycle callback invocation; review configuration and use procedural checks.", block=True)), file=sys.stderr)
        print("{}")
        return 0
    target = None
    try:
        target = args.target.resolve(strict=True)
        options = {"source_contour": True} if args.source_contour else {}
        if args.source_contour:
            from source_adoption import assert_source_root
            assert_source_root(target)
            if args.provider != "procedural" or args.action == "setup-plan" or getattr(args, "native_output", False):
                raise ValueError("source contour supports procedural events only, not native setup/output")
        if args.action == "setup-plan":
            from lifecycle_setup import setup_plan
            result = setup_plan(target, args.provider, args.installation_kind,
                native_setup_approved=args.native_setup_approved, client_version=args.client_version,
                config_path=args.config_path, interpreter=args.interpreter)
        elif args.action == "status":
            result = session_status(target, args.session_id, **options)
        elif args.action == "bind":
            binding = {"request_id": args.request_id, "baseline": args.baseline, "task_id": args.task_id,
                       "completion_only": args.completion_only}
            if args.request_brief is not None:
                binding["request_brief"] = args.request_brief
            if args.diff_ref is not None or args.approval_record:
                if not args.source_contour:
                    raise ValueError("diff/approval binding options require the source-contour lane")
                binding.update(diff_ref=args.diff_ref, approval_records=args.approval_record)
            result = handle(target, args.provider, "before-action", {"session_id": args.session_id},
                bind=binding, **options)
        else:
            raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
            if len(raw) > MAX_INPUT_BYTES:
                raise ValueError("lifecycle event exceeds 64 KiB")
            payload = json_object(raw, "native lifecycle event")
            if args.action == "review":
                result = review_request(target, args.request_brief, payload, **options)
            else:
                event, payload = normalize("procedural" if args.action == "checkpoint" else args.provider, args.event, payload)
                result = handle(target, args.provider, event, payload, procedural=args.action == "checkpoint", **options)
        if getattr(args, "native_output", False):
            print(json.dumps(result, sort_keys=True), file=sys.stderr)
            print(json.dumps(native_output(args.provider, args.event, result), sort_keys=True))
        else:
            print(json.dumps(result, sort_keys=True))
        return 1 if result["checkpoint_required"] and not getattr(args, "native_output", False) else 0
    except (OSError, UnicodeError, ValueError, RuntimeError, RecursionError) as exc:
        result = decision("unavailable", str(exc)[:500], block=True)
        if getattr(args, "native_output", False):
            # Only a valid adopted checkpoint policy may deny a selected tool.
            # Observe-only and unknown policies must not become blocking hooks.
            try:
                _, policy = load_policy(target) if target is not None else (None, None)
                result["emit_native_block"] = bool(policy and policy["enabled"]
                    and policy["provider"] == args.provider and policy["mode"] == "checkpoint"
                    and policy["native_evidence"]["state"] == "observed"
                    and NATIVE_EVENTS.get(args.provider, {}).get(args.event) == "before-action")
            except (OSError, UnicodeError, ValueError, RuntimeError, RecursionError):
                result["emit_native_block"] = False
            print(json.dumps(result, sort_keys=True), file=sys.stderr)
            print(json.dumps(native_output(args.provider, args.event, result), sort_keys=True))
            # Stop exit 2 requests another turn in several hosts. Diagnostics
            # must not bypass the reminder ceiling or restart interrupted work.
            return 0
        else:
            print(json.dumps(result, sort_keys=True))
        # Some hosts fail open on errors. This is not a universal security gate.
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
