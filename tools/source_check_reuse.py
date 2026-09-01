"""Hash-bound reuse helpers for AlatyrCore source-check results."""

from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path
from typing import Any

from source_state import SourceEntry


FINGERPRINT_CONTRACT = "alatyr-source-check-inputs-v1"


def _digest_payload(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def check_input_fingerprint(
    check: dict[str, Any],
    snapshot: dict[str, SourceEntry],
) -> dict[str, Any]:
    """Return a deterministic digest of the source inputs declared by one check."""

    patterns = list(dict.fromkeys([*check["contract_inputs"], *check["implementation_paths"]]))
    entries = [
        {
            "path": relpath,
            "kind": entry.kind,
            "mode": entry.mode,
            "digest": entry.digest,
        }
        for relpath, entry in sorted(snapshot.items())
        if any(fnmatch.fnmatch(relpath, pattern) for pattern in patterns)
    ]
    payload = {
        "contract": FINGERPRINT_CONTRACT,
        "check_id": check["id"],
        "patterns": patterns,
        "entries": entries,
    }
    return {
        **payload,
        "matched_path_count": len(entries),
        "sha256": _digest_payload(payload),
    }


def load_reuse_report(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 2:
        raise ValueError("--reuse-report must point to a source-check report schema 2")
    if data.get("report_kind") != "alatyr-source-check-run":
        raise ValueError("--reuse-report must point to an alatyr-source-check-run report")
    return data


def _previous_checks(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    checks = report.get("checks")
    if not isinstance(checks, list):
        return {}
    return {
        check["id"]: check
        for check in checks
        if isinstance(check, dict) and isinstance(check.get("id"), str)
    }


def reuse_decisions(
    *,
    selected: list[dict[str, Any]],
    previous_report: dict[str, Any] | None,
    current_source: dict[str, Any],
    current_environment: dict[str, Any],
    input_fingerprints: dict[str, dict[str, Any]],
    commands_by_id: dict[str, list[str]],
) -> dict[str, dict[str, Any]]:
    """Explain whether each selected check can reuse a previous passed result."""

    decisions: dict[str, dict[str, Any]] = {}
    previous_checks = _previous_checks(previous_report or {})
    previous_source = (
        previous_report.get("source", {}) if isinstance(previous_report, dict) else {}
    )
    previous_environment = (
        previous_report.get("environment", {}) if isinstance(previous_report, dict) else {}
    )
    for check in selected:
        check_id = check["id"]
        previous = previous_checks.get(check_id)
        reason = "no reuse report"
        reusable = False
        if previous_report is not None and previous is None:
            reason = "previous report has no matching check"
        elif previous is not None and previous.get("status") not in {"passed", "reused-pass"}:
            reason = "previous check did not pass"
        elif previous is not None and previous.get("timed_out") is True:
            reason = "previous check timed out"
        elif previous is not None and previous_source.get("manifest_sha256") != current_source.get("manifest_sha256"):
            reason = "check manifest digest changed"
        elif previous is not None and previous_environment.get("platform") != current_environment.get("platform"):
            reason = "platform changed"
        elif previous is not None and previous_environment.get("python") != current_environment.get("python"):
            reason = "python runtime changed"
        elif previous is not None and previous.get("command") != commands_by_id.get(check_id):
            reason = "check command changed"
        elif previous is not None and previous.get("input_fingerprint", {}).get("sha256") != input_fingerprints[check_id]["sha256"]:
            reason = "check input fingerprint changed"
        elif previous is not None:
            reason = "previous passed result is hash-bound to current inputs"
            reusable = True
        decisions[check_id] = {
            "reusable": reusable,
            "reason": reason,
            "previous_status": previous.get("status") if previous else None,
            "input_fingerprint": input_fingerprints[check_id],
        }
    return decisions
