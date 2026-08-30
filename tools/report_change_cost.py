#!/usr/bin/env python3
"""Report support/product change cost for a target repository diff."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from target_validation_support import git_changed_files, is_protected_surface


def git_paths(target: Path, *arguments: str) -> list[str] | None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "-z", *arguments],
        cwd=target,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    return [
        value.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        for value in result.stdout.split(b"\0")
        if value
    ]


def git_untracked_paths(target: Path) -> list[str] | None:
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=target,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    return [
        value.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        for value in result.stdout.split(b"\0")
        if value
    ]


def changed_paths(target: Path, diff_ref: str | None) -> list[str] | None:
    changed: set[str] = set()
    if diff_ref:
        paths = git_changed_files(target, diff_ref)
        if paths is None:
            return None
        changed.update(paths)
    for arguments in [(), ("--cached",)]:
        paths = git_paths(target, *arguments)
        if paths is None:
            return None
        changed.update(paths)
    untracked = git_untracked_paths(target)
    if untracked is None:
        return None
    changed.update(untracked)
    return sorted(changed)


def git_numstat(target: Path, *arguments: str) -> dict[str, dict[str, int]] | None:
    result = subprocess.run(
        ["git", "diff", "--numstat", "-z", *arguments],
        cwd=target,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    values = result.stdout.split(b"\0")
    totals: dict[str, dict[str, int]] = {}
    index = 0
    while index < len(values):
        header = values[index]
        index += 1
        if not header:
            continue
        parts = header.decode("utf-8", errors="replace").split("\t")
        if len(parts) < 3:
            continue
        added_text, deleted_text, path = parts[0], parts[1], parts[2]
        if path == "":
            if index >= len(values):
                break
            path = values[index].decode("utf-8", errors="surrogateescape")
            index += 1
        if added_text == "-" or deleted_text == "-":
            added = deleted = 0
        else:
            try:
                added = int(added_text)
                deleted = int(deleted_text)
            except ValueError:
                added = deleted = 0
        normalized = path.replace("\\", "/")
        current = totals.setdefault(normalized, {"added": 0, "deleted": 0})
        current["added"] += added
        current["deleted"] += deleted
    return totals


def count_untracked_lines(target: Path, paths: list[str]) -> dict[str, dict[str, int]]:
    totals: dict[str, dict[str, int]] = {}
    for relpath in paths:
        path = target / relpath
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data:
            totals[relpath] = {"added": 0, "deleted": 0}
            continue
        totals[relpath] = {"added": data.count(b"\n") + (0 if data.endswith(b"\n") else 1), "deleted": 0}
    return totals


def line_changes(target: Path, diff_ref: str | None, paths: list[str]) -> dict[str, dict[str, int]]:
    totals: dict[str, dict[str, int]] = {}
    include_index_and_worktree = True
    if diff_ref:
        base = git_numstat(target, f"{diff_ref}...HEAD")
        if base is None:
            base = git_numstat(target, diff_ref)
            include_index_and_worktree = False
        if base is not None:
            for path, change in base.items():
                totals[path] = change.copy()
    if include_index_and_worktree:
        for arguments in [(), ("--cached",)]:
            diff = git_numstat(target, *arguments) or {}
            for path, change in diff.items():
                current = totals.setdefault(path, {"added": 0, "deleted": 0})
                current["added"] += change["added"]
                current["deleted"] += change["deleted"]
    elif diff_ref:
        diff = git_numstat(target, diff_ref) or {}
        for path, change in diff.items():
            current = totals.setdefault(path, {"added": 0, "deleted": 0})
            current["added"] = max(current["added"], change["added"])
            current["deleted"] = max(current["deleted"], change["deleted"])
    untracked = sorted(set(paths) - set(totals))
    for path, change in count_untracked_lines(target, untracked).items():
        totals[path] = change
    return totals


def summarize(paths: list[str], changes: dict[str, dict[str, int]]) -> dict[str, Any]:
    support_paths = [path for path in paths if is_protected_surface(path)]
    product_paths = [path for path in paths if not is_protected_surface(path)]
    support_lines = sum(
        changes.get(path, {}).get("added", 0) + changes.get(path, {}).get("deleted", 0)
        for path in support_paths
    )
    product_lines = sum(
        changes.get(path, {}).get("added", 0) + changes.get(path, {}).get("deleted", 0)
        for path in product_paths
    )
    total_lines = support_lines + product_lines
    total_files = len(paths)
    return {
        "files": {
            "total": total_files,
            "support": len(support_paths),
            "product": len(product_paths),
        },
        "line_changes": {
            "total": total_lines,
            "support": support_lines,
            "product": product_lines,
        },
        "ratios": {
            "support_file_percent": round((len(support_paths) / total_files) * 100, 2)
            if total_files
            else 0.0,
            "product_file_percent": round((len(product_paths) / total_files) * 100, 2)
            if total_files
            else 0.0,
            "support_line_percent": round((support_lines / total_lines) * 100, 2)
            if total_lines
            else 0.0,
            "product_line_percent": round((product_lines / total_lines) * 100, 2)
            if total_lines
            else 0.0,
        },
        "support_paths": support_paths,
        "product_paths": product_paths,
    }


def render_text(report: dict[str, Any]) -> str:
    files = report["summary"]["files"]
    lines = report["summary"]["line_changes"]
    ratios = report["summary"]["ratios"]
    output = [
        "Target change cost",
        f"Target: {report['target']}",
        f"Diff ref: {report['diff_ref'] or 'working tree only'}",
        "",
        f"Files: {files['total']} total, {files['support']} support, {files['product']} product",
        f"Line changes: {lines['total']} total, {lines['support']} support, {lines['product']} product",
        (
            "Support/product file ratio: "
            f"{ratios['support_file_percent']}% / {ratios['product_file_percent']}%"
        ),
        (
            "Support/product line ratio: "
            f"{ratios['support_line_percent']}% / {ratios['product_line_percent']}%"
        ),
        "",
        "Reasoning boundary: deterministic counts classify surfaces; agents still perform semantic integrity review.",
    ]
    return "\n".join(output) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--diff-ref")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    target = args.target.resolve()
    paths = changed_paths(target, args.diff_ref)
    if paths is None:
        print("FAIL: cannot resolve changed paths", file=sys.stderr)
        return 1
    changes = line_changes(target, args.diff_ref, paths)
    report = {
        "schema_version": 1,
        "report_kind": "target-change-cost",
        "target": str(target),
        "diff_ref": args.diff_ref,
        "changed_paths": paths,
        "per_path_line_changes": changes,
        "summary": summarize(paths, changes),
        "limitations": [
            "Line counts are diff-based estimates and may omit binary-file size.",
            "Surface classification is structural; it does not replace semantic review.",
        ],
    }
    rendered = (
        json.dumps(report, indent=2, ensure_ascii=True) + "\n"
        if args.json
        else render_text(report)
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(rendered.encode("utf-8"))
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
