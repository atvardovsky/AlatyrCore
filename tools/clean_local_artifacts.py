#!/usr/bin/env python3
"""Report or remove old entries from AlatyrCore's ignored tmp directory."""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "tmp"


@dataclass(frozen=True)
class Candidate:
    path: Path
    bytes: int
    newest_mtime: float


def entry_stats(path: Path) -> tuple[int, float]:
    if path.is_symlink() or path.is_file():
        stat = path.lstat()
        return stat.st_size, stat.st_mtime
    total = 0
    newest = path.stat().st_mtime
    for child in path.rglob("*"):
        try:
            stat = child.lstat()
        except FileNotFoundError:
            continue
        newest = max(newest, stat.st_mtime)
        if child.is_file() or child.is_symlink():
            total += stat.st_size
    return total, newest


def collect_candidates(root: Path, cutoff: float) -> list[Candidate]:
    if not root.is_dir():
        return []
    candidates: list[Candidate] = []
    for path in sorted(root.iterdir()):
        size, newest = entry_stats(path)
        if newest < cutoff:
            candidates.append(Candidate(path=path, bytes=size, newest_mtime=newest))
    return candidates


def remove_candidate(candidate: Candidate) -> None:
    path = candidate.path
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--older-than-days",
        type=int,
        default=7,
        help="Select top-level tmp entries whose newest content is older than this age.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Remove selected entries. The default is a read-only report.",
    )
    args = parser.parse_args()
    if args.older_than_days < 0:
        parser.error("--older-than-days must be non-negative")

    cutoff = time.time() - args.older_than_days * 86400
    candidates = collect_candidates(ARTIFACT_ROOT, cutoff)
    total = sum(candidate.bytes for candidate in candidates)
    action = "REMOVE" if args.apply else "WOULD REMOVE"
    for candidate in candidates:
        print(
            f"{action}: {candidate.path.relative_to(ROOT).as_posix()} "
            f"({candidate.bytes} bytes)"
        )
        if args.apply:
            remove_candidate(candidate)
    mode = "removed" if args.apply else "selected"
    print(f"OK: {mode} {len(candidates)} entries totaling {total} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
