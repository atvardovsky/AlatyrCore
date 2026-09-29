"""Validate current baseline claims against the target manifest."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Protocol


DEFAULT_CLAIM_SURFACES = (
    ".ai/assistant/lifecycle.md",
    ".ai/assistant/maturity-profile.md",
    ".ai/assistant/module-profile.md",
)
LEGACY_PUBLIC_CLAIM_SURFACES = ("docs/ALATYR_CORE.md",)
VERSION_RE = re.compile(r"\b0\.1\.0-alpha\.\d+\b", re.IGNORECASE)
ALPHA_RE = re.compile(r"\balpha\.\d+\b", re.IGNORECASE)
INTEGER_RE = re.compile(r"\b\d+\b")
COMMIT_RE = re.compile(r"\b[0-9a-f]{7,64}\b", re.IGNORECASE)
CURRENT_MARKERS = (
    "current framework version",
    "framework version",
    "adapter schema version",
    "template version",
    "current framework commit",
    "current installed-source commit",
    "overall adapter state",
    "required surfaces checked",
    "last module-state validation",
    "current alatyr baseline",
)
HISTORICAL_MARKERS = ("previous", "historical", "initial installed", "history")


class FindingSink(Protocol):
    def target_path(self, relpath: str) -> Path: ...
    def is_target_file(self, path: str | Path) -> bool: ...
    def read_text(self, path: Path) -> str: ...
    def error(self, code: str, message: str, path: str | None = None) -> None: ...
    def info(self, code: str, message: str, path: str | None = None) -> None: ...


def _manifest_value(manifest: Any, key: tuple[str, ...]) -> str | None:
    if manifest is None:
        return None
    scalar = manifest.scalars.get(key)
    return scalar.value if scalar is not None else None


def _claim_surfaces(sink: FindingSink, manifest: Any) -> list[str]:
    configured = []
    if manifest is not None:
        configured = [
            scalar.value
            for scalar in manifest.lists.get(
                ("validation", "baseline_claim_surfaces"), []
            )
            if isinstance(scalar.value, str) and scalar.value
        ]
    candidates = [*DEFAULT_CLAIM_SURFACES, *configured]
    if any(sink.is_target_file(sink.target_path(path)) for path in LEGACY_PUBLIC_CLAIM_SURFACES):
        candidates.extend(LEGACY_PUBLIC_CLAIM_SURFACES)
    return list(dict.fromkeys(candidates))


def _expected_claims(manifest: Any) -> dict[str, str | None]:
    source_commit = _manifest_value(manifest, ("framework", "source_commit"))
    if source_commit is None:
        source_commit = _manifest_value(manifest, ("framework", "baseline"))
    return {
        "framework_version": _manifest_value(manifest, ("framework", "version")),
        "adapter_schema_version": _manifest_value(manifest, ("schema_version",)),
        "template_version": _manifest_value(manifest, ("framework", "template_version")),
        "source_commit": source_commit,
    }


def _line_claims(line: str) -> list[tuple[str, str]]:
    normalized = line.strip().lstrip("- ").strip()
    lowered = normalized.casefold()
    if not any(marker in lowered for marker in CURRENT_MARKERS):
        return []
    if any(marker in lowered for marker in HISTORICAL_MARKERS):
        return []
    claims: list[tuple[str, str]] = []
    if "adapter schema version" in lowered:
        match = INTEGER_RE.search(normalized.split(":", 1)[-1])
        if match:
            claims.append(("adapter_schema_version", match.group(0)))
    if "template version" in lowered:
        match = INTEGER_RE.search(normalized.split(":", 1)[-1])
        if match:
            claims.append(("template_version", match.group(0)))
    if "framework version" in lowered or "overall adapter state" in lowered:
        match = VERSION_RE.search(normalized)
        if match:
            claims.append(("framework_version", match.group(0)))
        else:
            alpha = ALPHA_RE.search(normalized)
            if alpha:
                claims.append(("framework_version", alpha.group(0)))
    if "required surfaces checked" in lowered or "last module-state validation" in lowered:
        alpha = ALPHA_RE.search(normalized)
        if alpha:
            claims.append(("framework_version", alpha.group(0)))
    if "current framework commit" in lowered or "current installed-source commit" in lowered:
        match = COMMIT_RE.search(normalized.split(":", 1)[-1])
        if match:
            claims.append(("source_commit", match.group(0)))
    return claims


def _matches_expected(kind: str, actual: str, expected: str) -> bool:
    if kind == "framework_version" and actual.casefold().startswith("alpha."):
        return expected.casefold().endswith(actual.casefold())
    if kind == "source_commit":
        return expected.casefold().startswith(actual.casefold()) or actual.casefold().startswith(
            expected.casefold()
        )
    return actual.casefold() == expected.casefold()


def validate_baseline_claims(sink: FindingSink, manifest: Any) -> None:
    expected = _expected_claims(manifest)
    if not all(expected.values()):
        return
    checked = 0
    for relpath in _claim_surfaces(sink, manifest):
        path = sink.target_path(relpath)
        if not sink.is_target_file(path):
            continue
        checked += 1
        for line_number, line in enumerate(sink.read_text(path).splitlines(), start=1):
            for kind, actual in _line_claims(line):
                expected_value = expected.get(kind)
                if expected_value is None or _matches_expected(kind, actual, expected_value):
                    continue
                sink.error(
                    "BASELINE_CLAIM_DRIFT",
                    f"current {kind.replace('_', ' ')} claim {actual} differs from "
                    f"manifest value {expected_value}",
                    f"{relpath}:{line_number}",
                )
    sink.info(
        "BASELINE_CLAIMS_CHECKED",
        f"checked {checked} current-baseline claim surface(s) against the manifest",
    )


__all__ = ["validate_baseline_claims"]
