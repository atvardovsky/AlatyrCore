"""Fail-closed, hash-bound reuse helpers for source-check results."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from path_spec import PathDialect, PathSpec
from source_check_manifest import transitive_local_tool_dependencies
from source_state import SourceEntry


FINGERPRINT_CONTRACT = "alatyr-source-check-inputs-v3"
REUSE_CONTRACT = "alatyr-source-check-reuse-v1"
RUN_IDENTITY_CONTRACT = "alatyr-source-check-run-identity-v1"
CHECK_CACHE_IDENTITY_CONTRACT = "alatyr-source-check-cache-identity-v1"


def canonical_digest(value: Any) -> str:
    """Return a stable digest for JSON-compatible execution evidence."""

    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class SourceSnapshotIndex:
    """Immutable run-scoped source index with cached pattern matches."""

    def __init__(self, snapshot: dict[str, SourceEntry]) -> None:
        self._entries = tuple(sorted(snapshot.items()))
        self._by_path = dict(self._entries)
        self._pattern_matches: dict[str, tuple[str, ...]] = {}
        self.sha256 = canonical_digest(
            {
                "contract": "alatyr-source-snapshot-v1",
                "entries": [
                    {
                        "path": relpath,
                        "kind": entry.kind,
                        "mode": entry.mode,
                        "digest": entry.digest,
                    }
                    for relpath, entry in self._entries
                ],
            }
        )

    def matching_paths(self, pattern: str) -> tuple[str, ...]:
        cached = self._pattern_matches.get(pattern)
        if cached is not None:
            return cached
        if not any(character in pattern for character in "*?["):
            matched = (pattern,) if pattern in self._by_path else ()
        else:
            spec = PathSpec(pattern, PathDialect.SOURCE_HOST_V1)
            matched = tuple(
                relpath
                for relpath, _entry in self._entries
                if spec.matches(relpath)
            )
        self._pattern_matches[pattern] = matched
        return matched

    def fingerprint(self, check: dict[str, Any]) -> dict[str, Any]:
        transitive_dependencies = transitive_local_tool_dependencies(
            check["command"][0]
        )
        patterns = list(
            dict.fromkeys(
                [
                    *check["contract_inputs"],
                    *check["implementation_paths"],
                    *sorted(transitive_dependencies),
                ]
            )
        )
        matched_paths = sorted(
            {
                relpath
                for pattern in patterns
                for relpath in self.matching_paths(pattern)
            }
        )
        entries = [
            {
                "path": relpath,
                "kind": self._by_path[relpath].kind,
                "mode": self._by_path[relpath].mode,
                "digest": self._by_path[relpath].digest,
            }
            for relpath in matched_paths
        ]
        unsupported_inputs = [
            entry["path"] for entry in entries if entry["kind"] != "file"
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
            "reuse_eligible": not unsupported_inputs,
            "unsupported_inputs": unsupported_inputs,
            "sha256": canonical_digest(payload),
        }


def check_input_fingerprint(
    check: dict[str, Any],
    snapshot: dict[str, SourceEntry] | SourceSnapshotIndex,
) -> dict[str, Any]:
    """Return a deterministic digest of one check's declared source inputs."""

    index = (
        snapshot
        if isinstance(snapshot, SourceSnapshotIndex)
        else SourceSnapshotIndex(snapshot)
    )
    return index.fingerprint(check)


def environment_fingerprint(environment: dict[str, Any]) -> dict[str, Any]:
    """Bind reuse to the complete environment contract recorded by the runner."""

    payload = {
        "contract": "alatyr-source-check-environment-v1",
        "environment": environment,
    }
    return {**payload, "sha256": canonical_digest(payload)}


def check_cache_identity(
    *,
    check: dict[str, Any],
    command: list[str],
    input_fingerprint: dict[str, Any],
    environment: dict[str, Any],
    run_identity: dict[str, Any],
) -> dict[str, Any]:
    """Bind one check result to only the execution inputs it can observe."""

    selection = check.get("_selection", {})
    payload = {
        "contract": CHECK_CACHE_IDENTITY_CONTRACT,
        "check_id": check["id"],
        "command": command,
        "input_fingerprint_sha256": input_fingerprint.get("sha256"),
        "environment_sha256": environment_fingerprint(environment)["sha256"],
        "selection": {
            "profile": selection.get("profile"),
            "changed_paths": selection.get("changed_paths", []),
            "matched_changed_paths": selection.get("matched_changed_paths", []),
            "reasons": selection.get("reasons", []),
        },
        "changed_from": run_identity.get("changed_from"),
        "baseline": run_identity.get("baseline"),
        "child_capacity": check.get("_child_capacity", 1),
    }
    return {**payload, "sha256": canonical_digest(payload)}


def cached_check_decision(
    *,
    record: dict[str, Any] | None,
    identity: dict[str, Any],
    input_fingerprint: dict[str, Any],
) -> dict[str, Any]:
    """Validate one disposable cached pass without trusting its file name."""

    reusable = (
        isinstance(record, dict)
        and record.get("contract") == "alatyr-source-check-result-cache-v1"
        and record.get("identity") == identity
        and record.get("status") == "passed"
        and record.get("timed_out") is False
    )
    return {
        "reusable": reusable and input_fingerprint.get("reuse_eligible") is True,
        "reason": (
            "content-addressed executed pass matches this check input closure"
            if reusable and input_fingerprint.get("reuse_eligible") is True
            else "no matching content-addressed executed pass"
        ),
        "previous_status": record.get("status") if isinstance(record, dict) else None,
        "input_fingerprint": input_fingerprint,
        "reuse_source": "per-check-cache",
    }


def load_reuse_report(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") not in {2, 3}:
        raise ValueError("--reuse-report must point to a source-check report schema 2 or 3")
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


def _report_reuse_rejection(
    report: dict[str, Any],
    *,
    current_run_identity: dict[str, Any] | None,
    current_environment: dict[str, Any],
) -> str | None:
    contract = report.get("reuse_contract")
    if not isinstance(contract, dict) or contract.get("contract") != REUSE_CONTRACT:
        return "previous report is timing-only under the legacy reuse contract"
    if current_run_identity is None:
        return "current execution identity is unavailable"
    if contract.get("completed") is not True:
        return "previous run was incomplete"
    if contract.get("successful") is not True:
        return "previous run was not successful"
    checks = report.get("checks")
    run_identity = contract.get("run_identity")
    if not isinstance(checks, list) or not isinstance(run_identity, dict):
        return "previous run completion evidence is invalid"
    expected_check_ids = run_identity.get("selected_check_ids")
    observed_check_ids = [
        item.get("id") for item in checks if isinstance(item, dict)
    ]
    if (
        not isinstance(expected_check_ids, list)
        or observed_check_ids != expected_check_ids
        or len(observed_check_ids) != len(checks)
    ):
        return "previous run completion evidence is invalid"
    if any(
        item.get("status") not in {"passed", "reused-pass"}
        or item.get("timed_out") is True
        for item in checks
        if isinstance(item, dict)
    ):
        return "previous run was not successful"
    write_scope = report.get("source_write_scope")
    if (
        not isinstance(write_scope, dict)
        or write_scope.get("declared") != "none"
        or write_scope.get("preserved") is not True
        or write_scope.get("changes") != []
    ):
        return "previous run did not preserve source write scope"
    previous_environment = report.get("environment")
    if not isinstance(previous_environment, dict):
        return "previous execution environment evidence is invalid"
    previous_environment_sha256 = environment_fingerprint(previous_environment)[
        "sha256"
    ]
    if contract.get("environment_sha256") != previous_environment_sha256:
        return "previous execution environment evidence is inconsistent"
    if previous_environment_sha256 != environment_fingerprint(current_environment)[
        "sha256"
    ]:
        return "execution environment changed"
    current_identity_digest = canonical_digest(current_run_identity)
    if contract.get("run_identity_sha256") != current_identity_digest:
        return "execution scope or resolved ref identity changed"
    if contract.get("run_identity") != current_run_identity:
        return "execution identity evidence is inconsistent"
    return None


def reuse_decisions(
    *,
    selected: list[dict[str, Any]],
    previous_report: dict[str, Any] | None,
    current_source: dict[str, Any],
    current_environment: dict[str, Any],
    input_fingerprints: dict[str, dict[str, Any]],
    commands_by_id: dict[str, list[str]],
    current_run_identity: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Explain whether each selected check can reuse an executed passed result."""

    decisions: dict[str, dict[str, Any]] = {}
    report = previous_report or {}
    previous_checks = _previous_checks(report)
    previous_source = report.get("source", {}) if isinstance(report, dict) else {}
    report_rejection = (
        _report_reuse_rejection(
            report,
            current_run_identity=current_run_identity,
            current_environment=current_environment,
        )
        if previous_report is not None
        else "no reuse report"
    )
    current_identity_digest = (
        canonical_digest(current_run_identity)
        if current_run_identity is not None
        else None
    )
    for check in selected:
        check_id = check["id"]
        previous = previous_checks.get(check_id)
        fingerprint = input_fingerprints[check_id]
        reason = report_rejection or "previous report has no matching check"
        reusable = False
        if report_rejection is not None:
            pass
        elif previous is None:
            reason = "previous report has no matching check"
        elif fingerprint.get("reuse_eligible") is not True:
            reason = "current check inputs include unsupported non-file paths"
        elif previous.get("status") != "passed":
            reason = "previous check was not an executed pass"
        elif previous.get("timed_out") is True:
            reason = "previous check timed out"
        elif previous.get("result_provenance") != {
            "kind": "executed",
            "run_identity_sha256": current_identity_digest,
        }:
            reason = "previous check lacks direct executed-result provenance"
        elif previous_source.get("manifest_sha256") != current_source.get(
            "manifest_sha256"
        ):
            reason = "check manifest digest changed"
        elif previous.get("command") != commands_by_id.get(check_id):
            reason = "check command changed"
        elif (
            previous.get("input_fingerprint", {}).get("sha256")
            != fingerprint["sha256"]
        ):
            reason = "check input fingerprint changed"
        else:
            reason = (
                "previous executed pass is bound to the current execution identity"
            )
            reusable = True
        decisions[check_id] = {
            "reusable": reusable,
            "reason": reason,
            "previous_status": previous.get("status") if previous else None,
            "input_fingerprint": fingerprint,
        }
    return decisions
