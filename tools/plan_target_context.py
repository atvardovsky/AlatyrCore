#!/usr/bin/env python3
"""Plan bounded read-only context for one installed Alatyr target task."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from context_planning import ContextPlanRequest, plan_target_context


def _inside_target(path: Path, target: Path) -> bool:
    resolved = path.resolve()
    target = target.resolve()
    return resolved == target or target in resolved.parents


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--operation", required=True)
    parser.add_argument("--changed-path", action="append", default=[])
    parser.add_argument("--fact-id", action="append", default=[])
    parser.add_argument("--assistant-surface")
    parser.add_argument("--max-words", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    request = ContextPlanRequest(
        target=args.target,
        profile=args.profile,
        operation=args.operation,
        changed_paths=tuple(args.changed_path),
        fact_ids=tuple(args.fact_id),
        assistant_surface=args.assistant_surface,
        max_words=args.max_words,
    )
    result = plan_target_context(request)
    if args.output and _inside_target(args.output, args.target):
        result = {
            "schema_version": 1,
            "plan_kind": "target-context-plan",
            "status": "invalid-request",
            "read_only": True,
            "upgrade_required": False,
            "errors": [
                {
                    "code": "OUTPUT_INSIDE_TARGET",
                    "message": (
                        "read-only target planning cannot write output inside "
                        "the target repository"
                    ),
                    "details": {"output": args.output.as_posix()},
                }
            ],
            "context_packet": None,
        }
        canonical = json.dumps(
            result, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        result["plan_digest"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
    rendered = json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
    if args.output and result.get("status") != "invalid-request":
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(rendered.encode("utf-8"))
        except OSError as exc:
            print(f"FAIL: cannot write context plan: {exc}", file=sys.stderr)
            return 1
    else:
        print(rendered, end="")
    return 0 if result.get("status") == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
