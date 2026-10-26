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
VERSION_RE = re.compile(r"\b\d+\.\d+\.\d+(?:-[a-z0-9.-]+)?(?:\+[a-z0-9.-]+)?\b", re.IGNORECASE)
ALPHA_RE = re.compile(r"\balpha\.\d+\b", re.IGNORECASE)
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
HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
EXCLUDED_HEADING_RE = re.compile(r"\b(?:previous|historical|history|examples?)\b", re.IGNORECASE)
CURRENT_HEADING_RE = re.compile(r"\bcurrent\s+(?:alatyr(?:\s*core)?\s+|installed\s+)?baseline\b", re.IGNORECASE)
FIELD_PATTERNS = (
    ("adapter_schema_version", r"\b(?:adapter\s+schema(?:\s+version)?\s*[:=]?\s*|adapter(?:\s+version)?\s*[:=]\s*|adapter\s*(?=\d))`?([^\s`,;/]+)"),
    ("template_version", r"\b(?:template\s+version\s*[:=]?\s*|template\s*[:=]\s*|template\s*(?=\d))`?([^\s`,;/]+)"),
    ("source_commit", r"\b(?:source\s+(?:commit|revision)|framework\s+commit|installed-source\s+commit|pinned\s+to)\s*[:=]?\s*`?([^\s`,;/]+)"),
)


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


def _line_claims(line: str, *, current_section: bool = False) -> list[tuple[str, str]]:
    normalized = line.strip().lstrip("- ").strip()
    normalized = normalized.replace("**", "").replace("__", "")
    lowered = normalized.casefold()
    if not current_section and not any(marker in lowered for marker in CURRENT_MARKERS):
        return []
    if re.match(r"(?:previous|historical|initial installed|history)\b", lowered):
        return []
    # Explicit historical clauses do not suppress a preceding current claim.
    normalized = re.split(r"[;(]\s*(?:previous|historical|history)\b", normalized, maxsplit=1, flags=re.IGNORECASE)[0]
    lowered = normalized.casefold()
    claims: list[tuple[str, str]] = []
    if current_section or any(marker in lowered for marker in (
        "framework version", "overall adapter state", "required surfaces checked",
        "last module-state validation", "current alatyr baseline",
    )):
        pattern = r"\b(?:framework(?:\s+version)?|alatyr(?:\s*core)?(?:\s+(?:version|baseline))?|installs?)\s*[:=]?\s*`?((?:\d+\.\d+\.\d+|alpha\.\d+)[^\s`,;/]*)"
        claims.extend(("framework_version", match.group(1).rstrip(".")) for match in re.finditer(pattern, normalized, re.IGNORECASE))
        if not claims and any(marker in lowered for marker in ("overall adapter state", "required surfaces checked", "last module-state validation", "current alatyr baseline")):
            matches = list(VERSION_RE.finditer(normalized)) or list(ALPHA_RE.finditer(normalized))
            claims.extend(("framework_version", match.group(0)) for match in matches)
    for kind, pattern in FIELD_PATTERNS:
        if current_section or kind == "source_commit" or kind.replace("_", " ") in lowered:
            claims.extend((kind, match.group(1).rstrip(".")) for match in re.finditer(pattern, normalized, re.IGNORECASE))
    if current_section:
        for kind, label in (("adapter_schema_version", "schema"), ("framework_version", "framework")):
            if re.match(rf"{label}(?:\s+version)?\s*:", normalized, re.IGNORECASE):
                if not any(found == kind for found, _ in claims):
                    claims.append((kind, normalized.split(":", 1)[1].strip(" `.*")))
    for kind, label in (("framework_version", "framework version"), ("adapter_schema_version", "adapter schema version"), ("template_version", "template version"), ("source_commit", "current framework commit"), ("source_commit", "current installed-source commit")):
        if re.match(rf"(?:current\s+)?{label}\s*:", normalized, re.IGNORECASE) and not any(found == kind for found, _ in claims):
            claims.append((kind, normalized.split(":", 1)[1].strip(" `.*")))
    return claims


def _document_claims(text: str):
    """Read bounded current sections and legacy labels, not examples/history."""
    headings: list[tuple[int, str]] = []
    fence: str | None = None
    pending: list[str] = []
    start = 0
    current = False

    def flush():
        return [(start, kind, value) for kind, value in _line_claims(" ".join(pending), current_section=current)]

    lines = text.splitlines()
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        fence_match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        heading = HEADING_RE.match(line)
        setext = number < len(lines) and bool(re.fullmatch(r" {0,3}(?:=+|-+)\s*", lines[number])) and bool(stripped)
        boundary = not stripped or heading or fence_match or setext or re.match(r"^\s*[-*+]\s", line) or any(marker in stripped.casefold() for marker in CURRENT_MARKERS)
        if boundary and pending:
            yield from flush()
            pending = []
        if fence is not None:
            if re.fullmatch(rf" {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}\s*", line):
                fence = None
            continue
        if fence_match:
            fence = fence_match.group(1)
            continue
        if heading or setext:
            level, title = (len(heading.group(1)), heading.group(2)) if heading else (1 if lines[number].lstrip().startswith("=") else 2, stripped)
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, title))
            continue
        if re.fullmatch(r" {0,3}(?:=+|-+)\s*", line):
            continue
        if any(EXCLUDED_HEADING_RE.search(title) for _, title in headings):
            continue
        if re.match(r"^\s*(?:[-*+]\s+)?(?:previous|historical|initial installed|history)\b", line, re.IGNORECASE):
            if pending:
                yield from flush()
                pending = []
            continue
        if stripped:
            if not pending:
                start = number
                current = any(CURRENT_HEADING_RE.search(title) for _, title in headings)
            pending.append(stripped)
    if pending:
        yield from flush()


def _matches_expected(kind: str, actual: str, expected: str) -> bool:
    if kind == "framework_version" and actual.casefold().startswith("alpha."):
        return expected.casefold().endswith(actual.casefold())
    if kind == "source_commit":
        return expected.casefold().startswith(actual.casefold()) or actual.casefold().startswith(
            expected.casefold()
        )
    return actual.casefold() == expected.casefold()


def validate_baseline_claims(sink: FindingSink, manifest: Any) -> None:
    if manifest is None:
        return
    expected = _expected_claims(manifest)
    checked = 0
    for relpath in _claim_surfaces(sink, manifest):
        path = sink.target_path(relpath)
        if not sink.is_target_file(path):
            continue
        checked += 1
        for line_number, kind, actual in _document_claims(sink.read_text(path)):
            expected_value = expected.get(kind)
            valid = (bool(re.fullmatch(r"\d+", actual)) if kind in {"adapter_schema_version", "template_version"}
                     else bool(COMMIT_RE.fullmatch(actual)) if kind == "source_commit"
                     else bool(VERSION_RE.fullmatch(actual) or ALPHA_RE.fullmatch(actual)))
            if not valid or not isinstance(expected_value, str) or not expected_value:
                sink.error("BASELINE_CLAIM_INVALID", f"current {kind} claim or manifest expectation is unresolved or invalid: {actual!r}", f"{relpath}:{line_number}")
            elif not _matches_expected(kind, actual, expected_value):
                sink.error("BASELINE_CLAIM_DRIFT",
                    f"current {kind.replace('_', ' ')} claim {actual} differs from manifest value {expected_value}",
                    f"{relpath}:{line_number}")
    sink.info(
        "BASELINE_CLAIMS_CHECKED",
        f"checked {checked} current-baseline claim surface(s) against the manifest",
    )


__all__ = ["validate_baseline_claims"]
