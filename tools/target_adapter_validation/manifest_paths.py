"""Manifest path comparison helpers for target-adapter validators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from target_validation_support import PathKey


@dataclass(frozen=True)
class ManifestPathMismatch:
    key: PathKey
    expected: str


def manifest_path_mismatches(
    manifest: Any, expected: Mapping[PathKey, str]
) -> list[ManifestPathMismatch]:
    """Return missing or mismatched scalar path claims without emitting findings."""

    mismatches: list[ManifestPathMismatch] = []
    for key, expected_value in expected.items():
        scalar = manifest.scalars.get(key)
        if scalar is None or scalar.value != expected_value:
            mismatches.append(ManifestPathMismatch(key, expected_value))
    return mismatches
