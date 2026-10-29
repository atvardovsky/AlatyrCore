#!/usr/bin/env python3
"""Capture or compare bounded active-session context without granting authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from bootstrap_index import BOOTSTRAP_PATH, SEMANTIC_INDEX_PATH, SOURCE_PATHS
from context_input_snapshot import ContextInputSnapshot, read_regular_context_bytes
from scaffold_state import validate_installation_state_record
from yaml_support import safe_load
from yaml import YAMLError


MAX_INPUTS = 256
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_BASELINE_BYTES = 128 * 1024
STATE_PATH = ".ai/assistant/installation-state.json"
TARGET_ANCHORS = frozenset({
    "AGENTS.md", BOOTSTRAP_PATH.as_posix(),
    SEMANTIC_INDEX_PATH.as_posix(), ".ai/framework/rule-registry.json", STATE_PATH,
    *(path.as_posix() for path in SOURCE_PATHS.values()),
})
OPTIONAL_TARGET_ANCHORS = frozenset({"AI_ASSISTANTS.md"})
SOURCE_ANCHORS = frozenset({
    "AGENTS.md", "VERSION", "ADAPTER_SCHEMA_VERSION", "TEMPLATE_VERSION",
    "tools/source-context/index.json", "tools/inspect_session_context.py",
})
HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")


def policy_failures(policy: dict[str, Any]) -> list[str]:
    expected = {
        "schema_version": 1, "operation": "session-context",
        "checkpoints": ["entry-or-resume", "new-request", "task-phase-change", "before-mutation-batch"],
        "selected_files": "all still-applicable context actually loaded for the task",
        "baseline": "session-memory-or-authorized-ignored-continuity-record",
        "on_change": "session-continuity",
        "nonaccepted_installation": "inspect-only-except-authorized-adaptation",
        "background_polling": False, "full_tree_scan": False, "grants_authority": False,
    }
    contract = policy.get("installed_context")
    if not isinstance(contract, dict):
        return ["continuity policy requires installed_context checkpoints"]
    return [f"installed_context requires {key}={value!r}" for key, value in expected.items()
            if type(contract.get(key)) is not type(value) or contract[key] != value]


def digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")


def relative_path(value: Any) -> str:
    if (not isinstance(value, str) or not value or "\0" in value or "\\" in value
            or PureWindowsPath(value).drive or PurePosixPath(value).is_absolute()
            or PurePosixPath(value).as_posix() != value
            or any(part in {".", ".."} for part in value.split("/"))):
        raise ValueError("context paths must be normalized target-relative paths")
    return value


def json_object(raw: bytes, label: str) -> dict[str, Any]:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate keys")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def fingerprint(record: dict[str, Any]) -> str:
    return digest(canonical({key: value for key, value in record.items() if key != "fingerprint"}))


def anchor_paths(source_contour: bool, state_path: str = STATE_PATH) -> frozenset[str]:
    return SOURCE_ANCHORS if source_contour else (TARGET_ANCHORS - {STATE_PATH}) | {relative_path(state_path)}


def validate_baseline(record: Any) -> dict[str, Any]:
    if (not isinstance(record, dict) or set(record) != {
        "schema_version", "record_kind", "target_identity", "contour", "installation_state_path", "inputs", "fingerprint"
    } or type(record.get("schema_version")) is not int or record["schema_version"] != 1
            or record.get("record_kind") != "alatyr-session-context"):
        raise ValueError("invalid session-context baseline contract")
    if not isinstance(record.get("contour"), str) or record["contour"] not in {"source", "target"}:
        raise ValueError("invalid session-context contour")
    for field in ("target_identity", "fingerprint"):
        if not isinstance(record.get(field), str) or not HASH.fullmatch(record[field]):
            raise ValueError(f"session-context {field} must be a resolved SHA-256")
    inputs = record.get("inputs")
    if not isinstance(inputs, list) or not 1 <= len(inputs) <= MAX_INPUTS:
        raise ValueError(f"session-context inputs must contain 1..{MAX_INPUTS} bindings")
    paths = []
    for item in inputs:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("invalid session-context input binding")
        paths.append(relative_path(item["path"]))
        if not isinstance(item["sha256"], str) or not HASH.fullmatch(item["sha256"]):
            raise ValueError("session-context input requires a resolved SHA-256")
    if paths != sorted(set(paths)):
        raise ValueError("session-context paths must be sorted and unique")
    state_path = record.get("installation_state_path")
    if record["contour"] == "source" and state_path != "not-applicable":
        raise ValueError("source baseline must not select a target installation")
    anchors = anchor_paths(record["contour"] == "source", state_path)
    if not anchors.issubset(paths):
        raise ValueError("session-context baseline omits required anchors")
    if record["fingerprint"] != fingerprint(record):
        raise ValueError("session-context baseline fingerprint differs from its bindings")
    if len(canonical(record)) > MAX_BASELINE_BYTES:
        raise ValueError("session-context baseline exceeds byte limit")
    return record


def capture(target: Path, paths: list[str], *, source_contour: bool = False) -> tuple[dict[str, Any], str, dict[str, int]]:
    root = target.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("target must be a directory")
    selected = [relative_path(path) for path in paths]
    if len(selected) != len(set(selected)):
        raise ValueError("context paths must not be repeated")
    total = 0
    inputs = []
    with ContextInputSnapshot(root, regular_files_only=True) as snapshot:
        state = "source-contour"
        state_path = "not-applicable"
        if not source_contour:
            manifest_raw = snapshot.read(root / ".ai/alatyr.yaml", max_bytes=MAX_FILE_BYTES)
            manifest = safe_load(manifest_raw.decode("utf-8"))
            installation = manifest.get("installation") if isinstance(manifest, dict) else None
            if not isinstance(installation, dict):
                raise ValueError("installation state route is missing")
            state_path = relative_path(installation.get("state_record"))
            state = installation.get("state")
            if not isinstance(state, str) or state not in {"scaffolded", "staged", "accepted", "degraded"}:
                raise ValueError("installation state is invalid")
        optional = set()
        if not source_contour:
            for relpath in OPTIONAL_TARGET_ANCHORS:
                try:
                    (root / relpath).lstat()
                except FileNotFoundError:
                    continue
                optional.add(relpath)
        selected = sorted(anchor_paths(source_contour, state_path) | optional | set(selected))
        if len(selected) > MAX_INPUTS:
            raise ValueError(f"session context exceeds {MAX_INPUTS} inputs")
        state_raw = None
        for relpath in selected:
            remaining = MAX_TOTAL_BYTES - total
            if remaining < 1:
                raise ValueError(f"session context exceeds {MAX_TOTAL_BYTES} bytes")
            raw = snapshot.read(root / relpath, max_bytes=min(MAX_FILE_BYTES, remaining))
            total += len(raw)
            inputs.append({"path": relpath, "sha256": digest(raw)})
            if relpath == state_path:
                state_raw = raw
        if not source_contour:
            record = json_object(state_raw, "installation state")
            failures = validate_installation_state_record(record, manifest_state=state)
            if failures:
                raise ValueError("; ".join(failures))
            for relpath in OPTIONAL_TARGET_ANCHORS:
                try:
                    (root / relpath).lstat()
                    present = True
                except FileNotFoundError:
                    present = False
                if present != (relpath in optional):
                    raise ValueError("optional bootstrap input changed during capture")
    baseline = {
        "schema_version": 1, "record_kind": "alatyr-session-context",
        "target_identity": digest(str(root).encode("utf-8")),
        "contour": "source" if source_contour else "target",
        "installation_state_path": state_path, "inputs": inputs,
    }
    baseline["fingerprint"] = fingerprint(baseline)
    validate_baseline(baseline)
    return baseline, state, {"input_files": len(inputs), "input_bytes": total,
                             "verification_reads": len(inputs)}


class Once(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        seen = getattr(namespace, "_seen", set())
        if self.dest in seen:
            parser.error(f"{option_string} may be supplied only once")
        namespace._seen = seen | {self.dest}
        setattr(namespace, self.dest, values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True, action=Once)
    parser.add_argument("--source-contour", action="store_true")
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("capture", "check"):
        child = actions.add_parser(name, allow_abbrev=False)
        child.add_argument("--context", action="append", default=[])
        child.add_argument("--output", type=Path, action=Once, help="Explicit report output; otherwise no writes.")
        if name == "check":
            binding = child.add_mutually_exclusive_group(required=True)
            binding.add_argument("--baseline", type=Path, action=Once)
            binding.add_argument("--expected", action=Once)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        prior = None
        paths = list(args.context)
        expected = getattr(args, "expected", None)
        baseline_path = getattr(args, "baseline", None)
        if baseline_path is not None:
            raw = read_regular_context_bytes(baseline_path, max_bytes=MAX_BASELINE_BYTES)
            saved = json_object(raw, "baseline")
            prior = validate_baseline(saved.get("baseline", saved))
            expected = prior["fingerprint"]
            anchors = anchor_paths(prior["contour"] == "source", prior["installation_state_path"])
            if prior["contour"] == "target":
                anchors = anchors | OPTIONAL_TARGET_ANCHORS
            paths = sorted(set(paths) | {item["path"] for item in prior["inputs"] if item["path"] not in anchors})
        if expected is not None and (not isinstance(expected, str) or not HASH.fullmatch(expected)):
            raise ValueError("expected fingerprint must be a resolved SHA-256")
        current, state, measurement = capture(args.target, paths, source_contour=args.source_contour)
        comparable = prior is None or (prior["target_identity"] == current["target_identity"]
                                      and prior["contour"] == current["contour"])
        matches = expected is not None and expected == current["fingerprint"] and comparable
        status = ("update-in-progress" if state in {"staged", "scaffolded"} else
                  "installation-degraded" if state == "degraded" else
                  "baseline-candidate" if args.action == "capture" else
                  "current" if matches else "rehydration-required")
        report = {"status": status, "fingerprint": current["fingerprint"],
                  "installation_state": state, "context_matches": matches,
                  "authorization_granted": False, "acceptance_granted": False,
                  "measurement": measurement}
        if args.action == "capture":
            report["baseline"] = current
        elif prior is not None:
            before = {item["path"]: item["sha256"] for item in prior["inputs"]}
            after = {item["path"]: item["sha256"] for item in current["inputs"]}
            report["changed_paths"] = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
            report["same_target_and_contour"] = comparable
        if baseline_path is not None and read_regular_context_bytes(
            baseline_path, max_bytes=MAX_BASELINE_BYTES
        ) != raw:
            raise ValueError("retained session-context baseline changed during comparison")
        if status not in {"current", "baseline-candidate"}:
            report["recovery"] = (
                "Peers remain inspect-only; the authorized installer/updater follows lifecycle adaptation and strict acceptance."
                if status in {"update-in-progress", "installation-degraded"} else
                "Use session-continuity before mutation; reconcile changed owners and affected plans, approvals, validation and worker evidence."
            )
        encoded = json.dumps(report, ensure_ascii=True, indent=2) + "\n"
        if "baseline" in report and len(encoded.encode("ascii")) > MAX_BASELINE_BYTES:
            raise ValueError("session-context capture report exceeds baseline byte limit")
        if args.output is not None:
            output = args.output.resolve()
            protected = {args.target.resolve() / item["path"] for item in current["inputs"]}
            if baseline_path is not None:
                protected.add(baseline_path.resolve())
            if output in protected or (output.exists() and any(output.samefile(path) for path in protected)):
                raise ValueError("report output must not overwrite context inputs or the retained baseline")
            output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as stream:
                staged = Path(stream.name)
                try:
                    stream.write(encoded.encode("ascii"))
                    stream.close()
                    if args.action == "capture":
                        os.link(staged, output)
                    else:
                        os.replace(staged, output)
                finally:
                    staged.unlink(missing_ok=True)
        visible = {key: value for key, value in report.items() if key != "baseline"}
        if args.action == "capture":
            visible["baseline_written"] = args.output is not None
        print(json.dumps(visible, ensure_ascii=True, indent=2))
        return 0 if status in {"current", "baseline-candidate"} else 1
    except (OSError, ValueError, RuntimeError, RecursionError, YAMLError) as exc:
        print(json.dumps({"status": "unavailable", "error": str(exc)[:500],
                          "recovery": "Inspect only; recover the input and reconcile through session-continuity before mutation.",
                          "authorization_granted": False, "acceptance_granted": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
