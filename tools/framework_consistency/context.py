"""Shared immutable inputs for framework-consistency check groups."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckContext:
    root: Path
    framework_files: tuple[str, ...]
    bridge_files: tuple[str, ...]
    required_bridge_refs: tuple[str, ...]

    def read_text(self, relpath: str) -> str:
        return (self.root / relpath).read_text(encoding="utf-8")

    def line_count(self, relpath: str) -> int:
        return len(self.read_text(relpath).splitlines())

    def assistant_surfaces(self) -> list[dict[str, object]]:
        data = json.loads(
            (self.root / "conformance" / "runs" / "assistant-surfaces.json").read_text(
                encoding="utf-8"
            )
        )
        surfaces = data.get("surfaces")
        if not isinstance(surfaces, list):
            raise ValueError("assistant-surfaces.json must contain a surfaces list")
        return [surface for surface in surfaces if isinstance(surface, dict)]

    def git_ignored_no_index(self, relpaths: list[str]) -> set[str]:
        if not relpaths:
            return set()
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "-z", "--stdin"],
            cwd=self.root,
            input="\0".join(relpaths) + "\0",
            capture_output=True,
            text=True,
        )
        if result.returncode not in {0, 1}:
            raise RuntimeError(result.stderr.strip() or "git check-ignore failed")
        return set(filter(None, result.stdout.split("\0")))
