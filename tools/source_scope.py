"""Source lifecycle bindings around the canonical approval/diff validator."""

from __future__ import annotations

from pathlib import Path

from request_values import fields, request_path, text
from source_adoption import MAX_BYTES, sha, source_object
from source_context_selection import source_json
from target_validation_support import GitEvidenceView, scope_entries_cover


def validate_scope(value: dict) -> dict:
    fields(value, {"diff_base", "approval_records"}, "source scope binding")
    base = text(value["diff_base"], "resolved source diff base")
    if len(base) not in {40, 64} or any(char not in "0123456789abcdef" for char in base):
        raise ValueError("source diff base must be a resolved commit identity")
    records = value["approval_records"]
    if not isinstance(records, dict) or not 1 <= len(records) <= 32:
        raise ValueError("source scope requires 1..32 explicit approval bindings")
    for path, digest in records.items():
        request_path(path)
        if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("source approval binding requires an exact SHA-256")
    return value


def scope_inputs(value: dict) -> dict[str, str]:
    return validate_scope(value)["approval_records"]


def bind_scope(root: Path, bind: dict, prior: dict | None, brief: dict, model: dict, *, previously_bound: bool = False) -> dict | None:
    base, paths = bind.get("diff_ref"), bind.get("approval_records", [])
    needed = set(brief["authorized_phases"]) - {"inspect"}
    if base is None and not paths:
        if needed or prior is not None:
            raise ValueError("state-changing source work requires explicit diff-ref and approval-record bindings")
        return None
    if (not base or not isinstance(paths, list) or not 1 <= len(paths) <= 32
            or any(not isinstance(path, str) for path in paths) or len(set(paths)) != len(paths)):
        raise ValueError("source scope requires one diff-ref and distinct explicit approval records")
    resolved = GitEvidenceView(root).resolve_ref(text(base, "source diff ref"))
    if resolved is None:
        raise ValueError("source diff base cannot be resolved")
    records = {}
    for path in paths:
        raw, record = source_object(root, request_path(path))
        if (not isinstance(record.get("operation"), dict)
                or record["operation"].get("id") != model["operation_id"]
                or not isinstance(record.get("approval"), dict)
                or record["approval"].get("source_or_message") != brief["source_ref"]):
            raise ValueError("source approval must bind the selected operation and current request source: " + path)
        records[path] = sha(raw)
    result = validate_scope({"diff_base": resolved, "approval_records": records})
    if previously_bound and prior is None:
        raise ValueError("same-request read-only binding cannot acquire mutation scope; review a new human request")
    if prior is not None and result != validate_scope(prior):
        raise ValueError("same-request rebind cannot replace its diff base or approval scope; review a new human request")
    return result


def review_scope(root: Path, scope: dict | None, action: dict, brief: dict, model: dict) -> list[str]:
    if action["phase"] == "inspect" and action["kind"] != "complete":
        return []
    if scope is None:
        # Read-only completion needs no code-change approval.
        return [] if set(brief["authorized_phases"]) == {"inspect"} else ["source action requires retained approval/diff bindings"]
    validate_scope(scope)
    from validate_target_adapter import AdapterValidatorConfig, Validator
    validator = Validator(root, framework_source=None, diff_ref=scope["diff_base"],
        approval_records=[root / path for path in scope["approval_records"]],
        enforce_approval_scope=True, change_packages=[], enforce_change_package=False,
        migration_diff=None, allow_placeholders=False, allow_local_paths=[],
        config=AdapterValidatorConfig(), approval_archive_mode="none",
        validation_phase="migration-staging")
    failures = []
    for path, expected in scope["approval_records"].items():
        # The canonical validator must consume the bound snapshot, not a later
        # independently reopened file which happens to occupy the same path.
        value = validator.context.read_bytes_result(validator.target_path(path), max_bytes=MAX_BYTES)
        if value.value is None or sha(value.value) != expected:
            failures.append("source approval changed since binding: " + path)
            continue
        record = source_json(value.value.decode("utf-8"))
        if (not isinstance(record.get("approval"), dict)
                or record["approval"].get("source_or_message") != brief["source_ref"]
                or not isinstance(record.get("operation"), dict)
                or record["operation"].get("id") != model["operation_id"]):
            failures.append("source approval no longer binds current request/operation: " + path)
        excluded = record.get("scope", {}).get("excluded_actions", []) if isinstance(record.get("scope"), dict) else []
        if isinstance(excluded, list) and action["phase"] in excluded:
            failures.append("source approval excludes action phase: " + action["phase"])
    if failures:
        return failures
    # Missing Git evidence must not become a harmless archive/scope warning.
    initial = validator.git.change_set(scope["diff_base"])
    if initial is None:
        return ["actual source change set is unavailable"]
    validator.check_approval_scope()
    scopes = [validator.load_approval_scope(root / path) for path in scope["approval_records"]]
    if any(row is None for row in scopes):
        failures.append("source approval scope is unavailable")
    else:
        for path in action["paths"]:
            if (any(scope_entries_cover(path, row.excluded) for row in scopes)
                    or not any(scope_entries_cover(path, row.allowed) for row in scopes)):
                failures.append("proposed source path exceeds approval scope: " + path)
    consumed = validator.context.content_bindings()
    if any(consumed.get(path) != digest for path, digest in scope["approval_records"].items()):
        failures.append("canonical scope validation did not consume the bound approval bytes")
    failures.extend(item.code + ": " + item.message for item in validator.findings if item.level == "error")
    failures.extend("source scope input changed: " + str(item.path) for item in validator.context.finalize())
    current = GitEvidenceView(root).change_set(scope["diff_base"])
    if current != initial:
        failures.append("actual source change set changed during scope review")
    return failures
