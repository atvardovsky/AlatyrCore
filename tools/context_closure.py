#!/usr/bin/env python3
"""Validate a measured context-closure receipt for a context-bearing update."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
KIND = "alatyr-context-closure"
DEFAULT_THRESHOLD = 0.10
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_OMISSIONS = 512
MAX_MESSAGE = 240
EPOCH_EVENTS = {"framework-update", "compaction"}
CAPABILITY_FIELDS = {
    "route",
    "automatic_compaction",
    "manual_compaction",
    "manual_trigger",
    "pre_boundary_signal",
    "post_boundary_signal",
    "summary_inspection",
    "project_instruction_reload",
    "fallback",
}


class ClosureError(ValueError):
    """Invalid input; the closure cannot be evaluated."""


def _read_json(value: str, label: str) -> tuple[dict[str, Any], Path]:
    path = Path(value).expanduser()
    if path.is_symlink():
        raise ClosureError(f"{label} must not be a symlink")
    try:
        info = path.stat()
    except OSError as exc:
        raise ClosureError(f"{label} is unavailable") from exc
    if not stat.S_ISREG(info.st_mode):
        raise ClosureError(f"{label} must be a regular file")
    if info.st_size > MAX_JSON_BYTES:
        raise ClosureError(f"{label} exceeds {MAX_JSON_BYTES} bytes")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise ClosureError(f"{label} is not valid JSON") from exc
    if not isinstance(data, dict):
        raise ClosureError(f"{label} must contain an object")
    return data, path


def _measure(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ClosureError(f"{label} must be an object")
    result: dict[str, Any] = {}
    for field in ("words", "characters", "resolved_files"):
        item = value.get(field, 0)
        if type(item) is not int or item < 0:
            raise ClosureError(f"{label}.{field} must be a non-negative integer")
        result[field] = item
    for field in ("missing_paths", "resolved_paths"):
        items = value.get(field, [])
        if not isinstance(items, list) or any(
            not isinstance(item, str) or not item for item in items
        ):
            raise ClosureError(f"{label}.{field} must be a string list")
        result[field] = items
    return result


def _report(value: dict[str, Any], label: str) -> dict[str, Any]:
    first = _measure(value.get("first_use"), f"{label}.first_use")
    operational = _measure(
        value.get("operational_entry", value.get("first_use")),
        f"{label}.operational_entry",
    )
    profiles_value = value.get("profiles", {})
    if not isinstance(profiles_value, dict):
        raise ClosureError(f"{label}.profiles must be an object")
    profiles = {
        name: _measure(item, f"{label}.profiles.{name}")
        for name, item in profiles_value.items()
        if isinstance(name, str) and name
    }
    return {"first_use": first, "operational_entry": operational, "profiles": profiles}


def _delta(before: int, after: int) -> float:
    if before == 0:
        return 0.0 if after == 0 else 1.0
    return (after - before) / before


def _check(code: str, passed: bool, **details: Any) -> dict[str, Any]:
    result = {"code": code, "status": "pass" if passed else "fail"}
    result.update(details)
    return result


def _compare(
    code: str,
    label: str,
    before: dict[str, Any],
    after: dict[str, Any],
    threshold: float,
    checks: list[dict[str, Any]],
    failures: list[str],
) -> None:
    for field in ("words", "characters"):
        delta = _delta(before[field], after[field])
        passed = delta <= threshold
        checks.append(
            _check(
                f"{code}_{field.upper()}", passed, label=label,
                before=before[field], after=after[field], delta=round(delta, 4),
            )
        )
        if not passed:
            failures.append(
                f"{code}_{field.upper()}: {label} {field} grew by {delta:.1%}"
            )


def _omissions(value: str | None) -> dict[str, str]:
    if value is None:
        return {}
    data, _ = _read_json(value, "omissions")
    items = data.get("items")
    if not isinstance(items, list) or len(items) > MAX_OMISSIONS:
        raise ClosureError("omissions items are invalid")
    result: dict[str, str] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict) or set(item) != {"path", "reason"}:
            raise ClosureError(f"omissions[{index}] has an invalid shape")
        path, reason = item.get("path"), item.get("reason")
        if not isinstance(path, str) or not path or not isinstance(reason, str) or not reason:
            raise ClosureError(f"omissions[{index}] fields must be non-empty strings")
        result[path] = reason[:MAX_MESSAGE]
    return result


def _status(value: dict[str, Any]) -> dict[str, Any]:
    state = value.get("state")
    if state not in {"current", "absent", "unavailable"}:
        raise ClosureError("ledger status state is invalid")
    pending = value.get("compaction_pending", False)
    if type(pending) is not bool:
        raise ClosureError("ledger status compaction_pending must be boolean")
    epoch_state = value.get("epoch_state", "absent")
    if epoch_state not in {"current", "absent", "invalid"}:
        raise ClosureError("ledger status epoch_state is invalid")
    result = {
        "state": state,
        "generation": value.get("generation"),
        "epoch": value.get("epoch"),
        "epoch_state": epoch_state,
        "compaction_pending": pending,
    }
    if result["generation"] is not None and (
        type(result["generation"]) is not int or result["generation"] < 0
    ):
        raise ClosureError("ledger status generation is invalid")
    if result["epoch"] is not None and (
        type(result["epoch"]) is not int or result["epoch"] < 0
    ):
        raise ClosureError("ledger status epoch is invalid")
    return result


def _epoch(value: dict[str, Any]) -> dict[str, Any]:
    required = {"schema_version", "session_id", "epoch", "event", "source", "observed_at"}
    if set(value) != required or value.get("schema_version") != 1:
        raise ClosureError("epoch has an invalid shape")
    if not isinstance(value.get("session_id"), str) or not value["session_id"]:
        raise ClosureError("epoch session_id is invalid")
    epoch_value = value.get("epoch")
    if type(epoch_value) is not int or epoch_value < 0:
        raise ClosureError("epoch number is invalid")
    if value.get("event") not in EPOCH_EVENTS:
        raise ClosureError("epoch event must be framework-update or compaction")
    for field in ("source", "observed_at"):
        if not isinstance(value.get(field), str) or not value[field]:
            raise ClosureError(f"epoch {field} is invalid")
    return {
        "epoch": epoch_value,
        "event": value["event"],
        "source": value["source"],
    }


def _capability(value: str, surface: str | None, root: Path) -> dict[str, Any]:
    data, path = _read_json(value, "capability")
    if "surfaces" in data:
        surfaces = data.get("surfaces")
        if not isinstance(surfaces, dict) or not surface:
            raise ClosureError("--surface is required for a capability index")
        reference = surfaces.get(surface)
        if not isinstance(reference, str) or not reference:
            raise ClosureError(f"capability surface is missing: {surface}")
        if Path(reference).is_absolute() or ".." in Path(reference).parts:
            raise ClosureError("capability surface path must be target-relative")
        data, path = _read_json(str(root / reference), f"capability {surface}")
    compaction = data.get("context_compaction")
    if not isinstance(compaction, dict):
        raise ClosureError("capability context_compaction is missing")
    missing = CAPABILITY_FIELDS - set(compaction)
    if missing:
        raise ClosureError(
            "capability context_compaction misses " + ", ".join(sorted(missing))
        )
    if compaction.get("fallback") != "session-continuity":
        raise ClosureError("capability context_compaction fallback must be session-continuity")
    if any("{" in str(value) or "}" in str(value) for value in compaction.values()):
        raise ClosureError("capability context_compaction contains unresolved placeholders")
    return {
        "surface": surface,
        "post_boundary_signal": compaction.get("post_boundary_signal"),
        "fallback": compaction.get("fallback"),
        "route": compaction.get("route"),
    }


def _result(
    *, checks: list[dict[str, Any]], failures: list[str], threshold: float,
    omissions: dict[str, str], ledger: dict[str, Any] | None,
    epoch: dict[str, Any] | None, capability: dict[str, Any] | None,
    ttl_seconds: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "status": "passed" if not failures else "blocked",
        "threshold": threshold,
        "checks": checks,
        "failures": failures,
        "omissions": [
            {"path": path, "reason": reason} for path, reason in sorted(omissions.items())
        ],
        "ledger": ledger,
        "epoch": epoch,
        "capability": capability,
        "ttl_seconds": ttl_seconds,
        "authority": "none",
        "authority_granted": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--capability", required=True)
    parser.add_argument("--surface")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--ledger-status")
    parser.add_argument("--epoch-file")
    parser.add_argument("--omissions")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--ttl-seconds", type=int, default=0)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--write", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if not 0 <= args.threshold < 1:
            raise ClosureError("--threshold must be from 0 to less than 1")
        if type(args.ttl_seconds) is not int or args.ttl_seconds < 0:
            raise ClosureError("--ttl-seconds must be a non-negative integer")
        if args.output is not None and not args.write:
            raise ClosureError("--output requires --write")
        root = args.root.expanduser().resolve()
        if not root.is_dir():
            raise ClosureError("--root is not a directory")

        before_value, _ = _read_json(args.before, "before report")
        after_value, _ = _read_json(args.after, "after report")
        before = _report(before_value, "before")
        after = _report(after_value, "after")
        omissions = _omissions(args.omissions)
        ledger = _status(_read_json(args.ledger_status, "ledger status")[0]) if args.ledger_status else None
        epoch = _epoch(_read_json(args.epoch_file, "epoch")[0]) if args.epoch_file else None
        capability = _capability(args.capability, args.surface, root)

        checks: list[dict[str, Any]] = []
        failures: list[str] = []
        _compare("FIRST_USE", "first_use", before["first_use"], after["first_use"], args.threshold, checks, failures)
        _compare("OPERATIONAL", "operational_entry", before["operational_entry"], after["operational_entry"], args.threshold, checks, failures)
        for name in sorted(set(before["profiles"]) & set(after["profiles"])):
            _compare(
                f"PROFILE_{name.upper().replace('-', '_')}", f"profile {name}",
                before["profiles"][name], after["profiles"][name],
                args.threshold, checks, failures,
            )

        removed_profiles = sorted(set(before["profiles"]) - set(after["profiles"]))
        removed_paths = sorted(
            set(before["first_use"]["resolved_paths"])
            - set(after["first_use"]["resolved_paths"])
        )
        for name in removed_profiles:
            key = f"profile:{name}"
            passed = key in omissions
            checks.append(_check("PROFILE_REMOVED", passed, profile=name))
            if not passed:
                failures.append(f"PROFILE_REMOVED: {name} disappeared")
        for path in removed_paths:
            passed = path in omissions
            checks.append(_check("COVERAGE_PATH_REMOVED", passed, path=path))
            if not passed:
                failures.append(f"COVERAGE_PATH_REMOVED: {path} disappeared")

        missing = [
            f"first_use:{path}" for path in after["first_use"]["missing_paths"]
        ] + [
            f"operational_entry:{path}" for path in after["operational_entry"]["missing_paths"]
        ] + [
            f"profile {name}:{path}"
            for name, profile in after["profiles"].items()
            for path in profile["missing_paths"]
        ]
        checks.append(_check("MISSING_PATHS", not missing, paths=missing[:32]))
        if missing:
            failures.append("MISSING_PATHS: " + ", ".join(missing[:8]))

        compaction_evidence = bool(epoch) or bool(ledger and ledger["epoch_state"] == "current")
        if ledger is not None:
            ledger_ok = (
                ledger["state"] != "unavailable"
                and not ledger["compaction_pending"]
                and ledger["epoch_state"] != "invalid"
            )
            checks.append(_check("LEDGER_STATE", ledger_ok, state=ledger["state"]))
            if not ledger_ok:
                failures.append("LEDGER_STATE: ledger is unavailable, pending, or invalid")
        if epoch is not None and ledger is not None:
            same = ledger["epoch"] == epoch["epoch"] or (
                type(ledger["generation"]) is int and ledger["generation"] >= epoch["epoch"]
            )
            checks.append(_check("EPOCH_STATUS_MATCH", same, epoch=epoch["epoch"], generation=ledger["generation"]))
            if not same:
                failures.append("EPOCH_STATUS_MATCH: epoch and ledger generation differ")

        if not compaction_evidence and args.ttl_seconds == 0:
            checks.append(_check("COMPACTION_EVIDENCE", False, epoch=False, ttl_seconds=0))
            failures.append("COMPACTION_EVIDENCE: provide an epoch, current ledger, or TTL fallback")
        else:
            checks.append(
                _check(
                    "COMPACTION_EVIDENCE", True,
                    epoch=compaction_evidence, ttl_seconds=args.ttl_seconds,
                )
            )

        supported = str(capability.get("post_boundary_signal", "")).lower()
        if supported == "supported" and epoch is None:
            checks.append(_check("CAPABILITY_EPOCH_REQUIRED", False, post_boundary_signal="supported"))
            failures.append("CAPABILITY_EPOCH_REQUIRED: supported boundary signal needs an epoch")
        else:
            checks.append(
                _check(
                    "CAPABILITY_EPOCH_REQUIRED", True,
                    post_boundary_signal=supported or "unknown",
                )
            )

        result = _result(
            checks=checks, failures=failures, threshold=args.threshold,
            omissions=omissions, ledger=ledger, epoch=epoch,
            capability=capability, ttl_seconds=args.ttl_seconds,
        )
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output is not None:
            output = args.output.expanduser()
            if output.is_symlink() or (output.exists() and not output.is_file()):
                raise ClosureError("--output must be a regular file")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0 if not failures else 1
    except (OSError, ClosureError, ValueError) as exc:
        print(f"FAIL: context closure: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
