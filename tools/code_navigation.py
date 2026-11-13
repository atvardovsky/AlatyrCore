"""Validate passive host navigation evidence without invoking a code engine."""

from __future__ import annotations

import hashlib
from typing import Any

from project_evidence import ProjectEvidence
from target_adapter_validation.values import is_resolved_string

MAX_MATCHES = 128
MAX_BINDINGS = 8


def navigation_evidence(data: Any, question: str, selected: set[str], evidence: ProjectEvidence) -> dict:
    required = {"schema_version", "report_kind", "query", "backend", "match_kind",
                "coverage", "source_bindings", "matches", "limitations"}
    if not isinstance(data, dict) or set(data) != required:
        raise ValueError("navigation report requires exactly: " + ", ".join(sorted(required)))
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("navigation schema_version must be 1")
    if data["report_kind"] != "code-navigation-evidence":
        raise ValueError("navigation report_kind must be code-navigation-evidence")
    if not isinstance(data["query"], str) or data["query"] != question:
        raise ValueError("navigation query must exactly match the selected question")
    if not is_resolved_string(data["backend"]) or len(data["backend"]) > 128:
        raise ValueError("navigation backend requires a concrete bounded tool identity")
    kind = data["match_kind"]
    if not isinstance(kind, str) or kind not in {"symbol-reference", "text-match"}:
        raise ValueError("navigation match_kind must be symbol-reference or text-match")
    if data["coverage"] != "selected-files":
        raise ValueError("navigation coverage must remain selected-files, never repository-complete")
    limitations = data["limitations"]
    if (not isinstance(limitations, list) or len(limitations) > 8
            or any(not is_resolved_string(value) or len(value) > 512 for value in limitations)):
        raise ValueError("navigation limitations require at most eight bounded concrete strings")
    bindings = data["source_bindings"]
    if not isinstance(bindings, list) or not 1 <= len(bindings) <= MAX_BINDINGS:
        raise ValueError(f"navigation requires 1..{MAX_BINDINGS} source bindings")
    bound = {}
    for row in bindings:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise ValueError("navigation bindings require path and sha256")
        path, expected = row["path"], row["sha256"]
        if not isinstance(path, str) or path not in selected or path in bound:
            raise ValueError("navigation bindings must be unique explicitly selected source paths")
        if (not isinstance(expected, str) or len(expected) != 64
                or any(value not in "0123456789abcdef" for value in expected)):
            raise ValueError("navigation bindings require lowercase SHA-256")
        raw = evidence.exact(path)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"navigation source is stale: {path}")
        bound[path] = raw.decode("utf-8").splitlines()
    matches = data["matches"]
    if not isinstance(matches, list) or len(matches) > MAX_MATCHES:
        raise ValueError(f"navigation matches must contain at most {MAX_MATCHES} rows")
    seen = set()
    for row in matches:
        if not isinstance(row, dict) or set(row) != {"path", "line"}:
            raise ValueError("navigation matches require path and line")
        path, line = row["path"], row["line"]
        if not isinstance(path, str) or path not in bound:
            raise ValueError("navigation match path lacks a current selected source binding")
        if type(line) is not int or not 1 <= line <= len(bound[path]):
            raise ValueError("navigation match line must identify an existing source line")
        if (path, line) in seen:
            raise ValueError("navigation match locations must be unique")
        seen.add((path, line))
    return {
        "backend": data["backend"], "match_kind": kind, "matches": matches,
        "source_bindings": bindings, "coverage": "selected-files",
        "resolution": "tool-reported-symbol-references" if kind == "symbol-reference" else "textual-candidates",
        "provenance": "captured-not-authenticated", "source_identity": "verified",
        "complete_call_graph": False, "absence_proven": False,
        "limitations": [*limitations, "Bound bytes and locations do not verify symbol resolution or complete callers."],
    }
