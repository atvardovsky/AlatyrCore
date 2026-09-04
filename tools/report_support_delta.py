#!/usr/bin/env python3
"""Report changed support surfaces and route follow-up review delta-first."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from path_spec import PathDialect, PathSpec
from support_state import (
    STATE_PATH,
    SupportStateError,
    build_support_state,
    load_policy,
    load_state,
    state_differences,
)
from target_validation_support import git_changed_files


SUPPORT_OWNER_HINTS = {
    "framework": ".ai/framework/context-index.json",
    "project": ".ai/project/context-index.json",
    "assistant": ".ai/assistant/context-index.json",
    "adapter-root": ".ai/README.md",
    "entrypoints": "AGENTS.md",
}
HEAVY_FALLBACKS = {
    ".ai/assistant/context-profiles.md",
    ".ai/assistant/module-profile.md",
    ".ai/assistant/help-reference.md",
    STATE_PATH,
}


def _digest_payload(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _matches(path: str, pattern: str) -> bool:
    return PathSpec(pattern, PathDialect.SUPPORT_TREE_V1).matches(path)


def _normalize_path(value: str) -> str:
    return PurePosixPath(value.replace("\\", "/")).as_posix()


def _is_support_path(relpath: str, policy: dict[str, Any]) -> bool:
    managed_roots = [
        value for value in policy.get("managed_roots", []) if isinstance(value, str)
    ]
    optional = {
        value
        for value in policy.get("optional_entrypoints", [])
        if isinstance(value, str)
    }
    return (
        relpath == STATE_PATH
        or relpath in optional
        or any(_matches(relpath, root + "/**") for root in managed_roots)
    )


def _file_group(state: dict[str, Any]) -> dict[str, str]:
    groups: dict[str, str] = {}
    for item in state.get("files", []):
        if isinstance(item, dict):
            path = item.get("path")
            group = item.get("group")
            if isinstance(path, str) and isinstance(group, str):
                groups[path] = group
    return groups


def _support_groups(
    differences: list[dict[str, Any]],
    recorded: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, list[str]]:
    before = _file_group(recorded)
    after = _file_group(current)
    grouped: dict[str, list[str]] = {}
    for difference in differences:
        path = difference.get("path")
        if not isinstance(path, str):
            continue
        group = after.get(path) or before.get(path) or "adapter-root"
        grouped.setdefault(group, []).append(path)
    return {group: sorted(paths) for group, paths in sorted(grouped.items())}


def _changed_paths(target: Path, diff_ref: str | None) -> list[str]:
    if diff_ref is None:
        return []
    paths = git_changed_files(target, diff_ref)
    if paths is None:
        raise ValueError(f"cannot resolve Git diff from {diff_ref}")
    return [_normalize_path(path) for path in paths]


def build_report(target: Path, diff_ref: str | None) -> dict[str, Any]:
    target = target.resolve()
    policy = load_policy(target)
    recorded = load_state(target)
    current = build_support_state(target, policy)
    support_differences = [
        difference.__dict__ for difference in state_differences(recorded, current)
    ]
    git_paths = _changed_paths(target, diff_ref)
    git_support = sorted(path for path in git_paths if _is_support_path(path, policy))
    git_product = sorted(path for path in git_paths if path not in set(git_support))
    support_paths = sorted(
        {
            *git_support,
            *[
                item["path"]
                for item in support_differences
                if isinstance(item.get("path"), str)
            ],
        }
    )
    changed_groups = _support_groups(support_differences, recorded, current)
    owner_hints = sorted(
        {
            SUPPORT_OWNER_HINTS.get(group, ".ai/README.md")
            for group in changed_groups
        }
    )
    heavy_changed = sorted(path for path in support_paths if path in HEAVY_FALLBACKS)

    delta_identity = {
        "diff_ref": diff_ref,
        "baseline_digest": recorded.get("root_digest"),
        "current_digest": current.get("root_digest"),
        "changed_support_paths": support_paths,
        "changed_product_paths": git_product,
        "support_differences": support_differences,
    }

    return {
        "schema_version": 1,
        "report_kind": "target-support-delta",
        "target": str(target),
        "diff_ref": diff_ref,
        "delta_digest": _digest_payload(delta_identity),
        "baseline_digest": recorded.get("root_digest"),
        "current_digest": current.get("root_digest"),
        "support_state_current": recorded.get("root_digest") == current.get("root_digest")
        and recorded.get("policy_digest") == current.get("policy_digest"),
        "changed_path_summary": {
            "support_count": len(support_paths),
            "product_count": len(git_product),
            "support_difference_count": len(support_differences),
            "digest": _digest_payload(
                {
                    "changed_support_paths": support_paths,
                    "changed_product_paths": git_product,
                    "support_differences": support_differences,
                }
            ),
        },
        "changed_support_paths": support_paths,
        "changed_product_paths": git_product,
        "support_differences": support_differences,
        "changed_support_groups": changed_groups,
        "candidate_owner_context": owner_hints,
        "heavy_fallbacks_changed": heavy_changed,
        "next_review_steps": [
            "load candidate owner context only for changed support groups",
            "run plan_support_impact.py when a consistency map exists or changed facts are known",
            "re-derive semantic facts and invariants manually; do not infer them from hashes",
            "refresh .ai/support-state.json last after accepted adapter/support updates",
        ],
        "reasoning_boundary": "This report identifies changed support surfaces and candidate review owners; it does not prove semantic correctness or complete impact.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--diff-ref")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = build_report(args.target, args.diff_ref)
    except (OSError, SupportStateError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(rendered.encode("utf-8"))
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
