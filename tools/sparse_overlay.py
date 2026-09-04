"""Content-addressed decisions for sparse, non-destructive file projection."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OverlayDecision:
    """Describe whether one desired projection differs from its target surface."""

    path: Path
    changed: bool
    current_digest: str | None
    desired_digest: str


def sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def overlay_decision(path: Path, desired: bytes) -> OverlayDecision:
    """Compare one target file without assigning deletion or ownership semantics."""

    desired_digest = sha256_bytes(desired)
    try:
        current = path.read_bytes()
    except FileNotFoundError:
        return OverlayDecision(path, True, None, desired_digest)
    current_digest = sha256_bytes(current)
    return OverlayDecision(
        path,
        current_digest != desired_digest,
        current_digest,
        desired_digest,
    )


def sparse_overlay(
    desired_files: dict[Path, bytes],
) -> tuple[OverlayDecision, ...]:
    """Return deterministic decisions for a desired managed-file projection."""

    return tuple(
        overlay_decision(path, desired_files[path]) for path in sorted(desired_files)
    )
