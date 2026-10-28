"""Bounded selection and closure checks for current/recent engineering tasks."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema

from target_adapter_validation.analysis_strategies import (
    load_problem_model_schema,
    validate_selected_problem_model,
)
from target_adapter_validation.values import is_resolved_string
from target_adapter_validation.consistency_map import parse_registry_fact_entries
from target_validation_support import is_target_relative_path
from task_evidence_contract import task_projection_mismatches, task_schema, task_model_header_failures, task_predecessor_failures
from architecture_review import review_failures, BoundedReviewDigests

INDEX_PATH = ".ai/assistant/active-tasks.json"
MAX_TASKS = 128
MAX_ARTIFACT_BYTES = 512 * 1024
RESULT_BYTE_LIMITS = (16 * 1024 * 1024, 64 * 1024 * 1024)


def _target_file(validator: Any, path: str | Path) -> bool:
    try:
        return validator.is_target_file(path)
    except (OSError, ValueError):
        return False


def _schema_valid(validator: Any, value: Any, name: str, source: str) -> bool:
    try:
        errors = list(task_schema(name).iter_errors(value))
    except (OSError, ValueError, jsonschema.SchemaError) as exc:
        validator.error("ACTIVE_TASK_SOURCE_SCHEMA", str(exc), source)
        return False
    for error in errors:
        validator.error("ACTIVE_TASK_SCHEMA", f"{list(error.absolute_path)}: {error.message}", source)
    return not errors


def _bound_object(validator: Any, binding: Any, label: str) -> dict[str, Any] | None:
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        validator.error("ACTIVE_TASK_BINDING", f"{label} requires path and SHA-256", INDEX_PATH)
        return None
    path, digest = binding["path"], binding["sha256"]
    if not is_resolved_string(path) or "\\" in path or not is_target_relative_path(path) or not _target_file(validator, path):
        validator.error("ACTIVE_TASK_BINDING", f"{label} path is unavailable or unsafe: {path!r}", INDEX_PATH)
        return None
    artifact = validator.target_path(path)
    if artifact.is_symlink():
        validator.error("ACTIVE_TASK_BINDING", f"{label} must be a bounded regular file", path)
        return None
    content = validator.context.read_bytes_result(artifact, max_bytes=MAX_ARTIFACT_BYTES)
    if content.value is None or digest != hashlib.sha256(content.value).hexdigest():
        validator.error("ACTIVE_TASK_DIGEST", f"{label} SHA-256 does not match its artifact", path)
        return None
    return validator.load_json_object(artifact, "ACTIVE_TASK_ARTIFACT")


def _task_model_evidence(validator: Any, task: dict[str, Any], closure: Any = None) -> tuple[Any, Any, Path | None]:
    """Closed witnesses retain the original model identity without runtime I/O."""
    binding = task.get("problem_model")
    if task.get("state") == "closed" and closure is None:
        closure = _bound_object(validator, task.get("completion_evidence"), "predecessor closure")
    witness = closure.get("analysis_witness") if isinstance(closure, dict) else None
    if witness is None:
        return _bound_object(validator, binding, "problem model"), binding, None
    if task.get("state") != "closed" or not isinstance(witness, dict) or set(witness) != {"model", "projection", "retention_review"} or not is_resolved_string(witness.get("retention_review")):
        validator.error("ACTIVE_TASK_WITNESS", "durable evidence requires a closed task and retention review", INDEX_PATH)
        return None, None, None
    task_id = task["task_id"]
    if re.fullmatch(r"[A-Za-z0-9._-]+", task_id) is None or task_id in (".", ".."):
        validator.error("ACTIVE_TASK_WITNESS", "retained task identities must be safe path tokens", INDEX_PATH)
        return None, None, None
    prefix = f".ai/assistant/task-evidence/{task_id}/"
    for name in ("model", "projection"):
        item = witness[name]
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not item["path"].startswith(prefix) or validator.git.is_ignored(item["path"]) is not False:
            validator.error("ACTIVE_TASK_WITNESS", "durable witness must be retainable below .ai/assistant/task-evidence/", INDEX_PATH)
            return None, None, None
    if not isinstance(binding, dict) or witness["model"].get("sha256") != binding.get("sha256"):
        validator.error("ACTIVE_TASK_WITNESS", "durable model must preserve the registered runtime model digest", INDEX_PATH)
        return None, None, None
    model = _bound_object(validator, witness["model"], "durable problem model")
    projection = _bound_object(validator, witness["projection"], "durable active projection")
    if projection is None:
        return None, None, None
    return model, witness["model"], validator.target_path(witness["projection"]["path"])


def validate_capture_disposition(validator: Any, value: Any, source: str, closure: dict[str, Any]) -> None:
    task_id = closure["task_id"]
    if not isinstance(value, dict):
        validator.error("TASK_EVIDENCE_DISPOSITION", "closure requires captured/skipped/blocked disposition", source)
        return
    state = value.get("state")
    if not isinstance(state, str) or state not in {"captured", "skipped", "blocked"} or not is_resolved_string(value.get("reason")):
        validator.error("TASK_EVIDENCE_DISPOSITION", "capture state and concrete reason are required", source)
        return
    ids = value.get("record_ids")
    owners = value.get("preserved_owners")
    if not isinstance(ids, list) or not all(is_resolved_string(item) for item in ids) or len(ids) != len(set(ids)):
        validator.error("TASK_EVIDENCE_DISPOSITION", "record_ids must be unique resolved strings", source)
        return
    if not isinstance(owners, list) or not all(is_resolved_string(item) and is_target_relative_path(item) and tuple(part.casefold() for part in Path(item.replace("\\", "/")).parts[:2]) != (".ai", "framework") and _target_file(validator, item) for item in owners):
        validator.error("TASK_EVIDENCE_DISPOSITION", "preserved_owners must resolve to target-owned files", source)
        return
    if state != "captured":
        materiality = value.get("materiality")
        if ids or (state == "skipped" and (materiality == "unknown" or materiality == "material" and not owners)):
            validator.error("TASK_EVIDENCE_DISPOSITION", "skipped capture preserves conclusions in owners; non-captured states cannot claim record IDs", source)
        if state == "blocked" and (not is_resolved_string(value.get("next_safe_action")) or value.get("next_safe_action") == "none"):
            validator.error("TASK_EVIDENCE_BLOCKED", "blocked capture requires a concrete next safe action", source)
        if state == "skipped" and value.get("materiality") == "material":
            registry = validator.target_path(".ai/project/source-of-truth-registry.md")
            registry_read = validator.context.read_text_result(registry)
            entries = parse_registry_fact_entries(registry_read.value or "")
            registered: dict[str, set[str]] = {}
            for entry in entries:
                for owner in entry.canonical_owner_values:
                    registered.setdefault(entry.heading_fact_type, set()).update([owner, *re.findall(r"`([^`]+)`", owner)])
            covered = set()
            for preservation in value["preservation"]:
                fact_id, fact_type, owner = preservation["fact_id"], preservation["fact_type"], preservation["owner"]
                if fact_id not in closure["changed_fact_ids"] or owner not in owners or owner not in closure["canonical_owners"] or owner not in registered.get(fact_type, set()):
                    validator.error("TASK_EVIDENCE_PRESERVATION", f"preservation mapping does not resolve a task fact to its registered owner: {preservation}", source)
                else:
                    covered.add(fact_id)
            if set(closure["changed_fact_ids"]) - covered or not covered:
                validator.error("TASK_EVIDENCE_PRESERVATION", "material skip requires preservation mappings for every changed fact", source)
        return
    if not ids:
        validator.error("TASK_EVIDENCE_UNREGISTERED", "captured evidence requires registered record IDs", source)
        return
    index_path = validator.target_path(".ai/project/engineering-evidence/index.json")
    bounded_index = validator.context.read_bytes_result(index_path, max_bytes=4 * 1024 * 1024)
    index = validator.load_json_object(index_path, "TASK_EVIDENCE_INDEX") if bounded_index.value is not None else None
    entries = index.get("records") if isinstance(index, dict) else None
    if not isinstance(entries, list):
        validator.error("TASK_EVIDENCE_UNREGISTERED", "engineering-evidence index records are unavailable", source)
        return
    for evidence_id in ids:
        matching = [entry for entry in entries if isinstance(entry, dict) and entry.get("evidence_id") == evidence_id]
        if len(matching) != 1:
            validator.error("TASK_EVIDENCE_UNREGISTERED", f"{evidence_id} must resolve exactly once in the engineering index", source)
            continue
        entry = matching[0]
        refs = entry.get("task_references")
        if not isinstance(refs, list) or task_id not in refs:
            validator.error("TASK_EVIDENCE_LINEAGE", f"{evidence_id} does not reference task {task_id}", source)
        if entry.get("status") != "validated" or entry.get("repository_binding_state") != "final":
            validator.error("TASK_EVIDENCE_UNFINALIZED", f"{evidence_id} is not validated final evidence", source)
        record_path = entry.get("record")
        if not is_resolved_string(record_path) or not is_target_relative_path(record_path) or not _target_file(validator, record_path):
            validator.error("TASK_EVIDENCE_UNCHECKED", f"{evidence_id} has no locally verifiable record; external evidence needs a local receipt", source)
            continue
        record_read = validator.context.read_bytes_result(validator.target_path(record_path), max_bytes=MAX_ARTIFACT_BYTES)
        record = validator.load_json_object(validator.target_path(record_path), "TASK_CAPTURE_RECORD") if record_read.value is not None else None
        record_task = record.get("task") if isinstance(record, dict) else None
        record_binding = record.get("repository_binding") if isinstance(record, dict) else None
        if not isinstance(record_task, dict) or record_task.get("operation_id") != closure["operation_id"]:
            validator.error("TASK_EVIDENCE_LINEAGE", f"{evidence_id} belongs to another operation", source)
        expected_binding = closure["repository_binding"]
        binding_fields = ("kind", "result_revision") + (("snapshot_sha256", "selected_paths") if isinstance(expected_binding, dict) and expected_binding.get("kind") == "selected-file-snapshot" else ())
        if not isinstance(record_binding, dict) or not isinstance(expected_binding, dict) or any(record_binding.get(field) != expected_binding.get(field) for field in binding_fields):
            validator.error("TASK_EVIDENCE_RESULT", f"{evidence_id} does not bind the closure result", source)
        # The engineering-evidence phase applies the canonical schema, projection,
        # and repository-binding checks. Do not invent a second record validator.


def validate_task_closure(validator: Any, closure: dict[str, Any], task: dict[str, Any]) -> None:
    source = task["completion_evidence"]["path"]
    task_id = task["task_id"]
    if closure.get("record_kind") != "alatyr-task-closure" or closure.get("schema_version") != 1 or closure.get("task_id") != task_id or closure.get("operation_id") != task["operation_id"]:
        validator.error("TASK_CLOSURE_IDENTITY", "closure kind, schema, and task identity must match", source)
        return
    if not _schema_valid(validator, closure, "task-closure", source):
        return
    validate_capture_disposition(validator, closure["engineering_evidence"], source, closure)
    if not is_resolved_string(closure["knowledge_review"]["reason"]):
        validator.error("TASK_KNOWLEDGE_DISPOSITION", "knowledge review needs a concrete reason", source)
    delivery = closure["delivery"]
    if delivery["implementation"] == "complete" and closure["engineering_evidence"]["state"] == "blocked":
        validator.warn("TASK_CLOSURE_BLOCKED", "implementation is complete but evidence remains blocked; this is not completed task acceptance", source)
    if validator.current_task_id == task_id and validator.validation_phase == "acceptance" and delivery["evidence_finalization"] != "final":
        validator.error("TASK_CLOSURE_NOT_FINAL", "selected current-task acceptance requires finalized evidence", source)
    if delivery["evidence_finalization"] == "final":
        if delivery["implementation"] != "complete" or closure["engineering_evidence"]["state"] == "blocked":
            validator.error("TASK_CLOSURE_FINAL", "final evidence requires complete work without evidence blockers", source)
        binding = closure["repository_binding"]
        selected_paths = binding.get("selected_paths") if isinstance(binding, dict) else None
        registration_paths = {INDEX_PATH, _normalized_path(source)}
        ambiguous_paths = isinstance(selected_paths, list) and any(isinstance(path, str) and "\\" in path for path in selected_paths)
        self_referential = isinstance(binding, dict) and binding.get("kind") == "selected-file-snapshot" and isinstance(selected_paths, list) and any(isinstance(path, str) and _normalized_path(path) in registration_paths for path in selected_paths)
        if ambiguous_paths:
            validator.error("TASK_CLOSURE_RESULT_SCOPE", "task snapshot paths require forward-slash separators on every platform", source)
        elif self_referential:
            validator.error("TASK_CLOSURE_RESULT_SCOPE", "snapshots cannot include their closure or task-registration index; use a commit/tree for index maintenance", source)
        else:
            validator.check_repository_binding(binding=binding, record_relpath=source, record_status="validated", schema_version=3, code_prefix="TASK_CLOSURE", implementation_surfaces=closure["implementation_surfaces"], verify_current=validator.current_task_id == task_id, snapshot_byte_limits=RESULT_BYTE_LIMITS)
        if validator.current_task_id == task_id:
            _validate_current_result(validator, closure, source)
            _validate_selected_architecture_review(validator, closure, source)
    elif delivery["implementation"] == "complete":
        validator.warn("TASK_CLOSURE_PROVISIONAL", "implementation is complete but evidence is not finalized; this is not final acceptance evidence", source)
    if delivery["publication"] == "published":
        _validate_publication(validator, closure, source)
    for field in task_projection_mismatches(task, closure):
        validator.error("ACTIVE_TASK_PROJECTION", f"{field} differs from closure", source)


def _validate_publication(validator: Any, closure: dict[str, Any], source: str) -> None:
    if not closure["publication_evidence"]:
        validator.error("TASK_CLOSURE_PUBLICATION", "published requires a hash-bound local observation receipt", source)
    for binding in closure["publication_evidence"]:
        receipt = _bound_object(validator, binding, "publication receipt")
        if receipt is None or not _schema_valid(validator, receipt, "publication-receipt", source):
            continue
        remote = receipt["remote_ref"]
        observed = validator.git.literal_remote_ref(remote)
        if not validator.git.is_literal_remote_ref(remote):
            validator.error("TASK_CLOSURE_PUBLICATION", "publication observation needs a literal remote-tracking ref, not revision syntax", source)
        revision = validator.git.resolve_object(receipt["observed_revision"], "commit")
        result_binding = closure["repository_binding"]
        if receipt["task_id"] != closure["task_id"] or receipt["operation_id"] != closure["operation_id"] or revision != receipt["observed_revision"]:
            validator.error("TASK_CLOSURE_PUBLICATION", "publication observation task, operation, or immutable observed revision differs", source)
        if observed != receipt["observed_revision"]:
            if validator.current_task_id == closure["task_id"]:
                validator.error("TASK_CLOSURE_PUBLICATION", "current publication observation differs from the local remote-tracking ref", source)
            else:
                validator.warn("TASK_PUBLICATION_HISTORICAL", "recorded publication is historical; the local remote-tracking ref has moved or is unavailable", source)
        matches = False
        if isinstance(result_binding, dict):
            if result_binding.get("kind") == "selected-file-snapshot":
                selected_paths = result_binding.get("selected_paths")
                if isinstance(selected_paths, list) and all(isinstance(path, str) for path in selected_paths):
                    matches = validator.git.snapshot_sha256(receipt["observed_revision"], selected_paths, byte_limits=RESULT_BYTE_LIMITS) == result_binding.get("snapshot_sha256")
            else:
                kind = "tree" if result_binding.get("kind") == "tree" else "commit"
                matches = validator.git.resolve_object(receipt["observed_revision"], kind) == result_binding.get("result_revision")
        if not matches:
            validator.error("TASK_CLOSURE_PUBLICATION", "publication observation does not bind the closure result", source)
        try:
            time = datetime.fromisoformat(receipt["observed_at"].replace("Z", "+00:00"))
            if time.tzinfo is None or time > datetime.now(timezone.utc):
                raise ValueError("invalid observation time")
        except (ValueError, OverflowError):
            validator.error("TASK_CLOSURE_PUBLICATION", "publication observation requires a valid, non-future timestamp", source)
        validator.info("TASK_PUBLICATION_EVIDENCE_LIMIT", "receipt verifies a local observed remote-tracking ref, not current live remote state or authorization", source)


def _normalized_path(value: str) -> str:
    return PurePosixPath(value.replace("\\", "/")).as_posix()


def _registration_projection(content: bytes, task_id: str) -> dict[str, Any] | None:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate registration key: {key}")
            result[key] = value
        return result

    try:
        index = json.loads(content, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError, RecursionError):
        return None
    if not task_schema("active-task-index").is_valid(index):
        return None
    matches = [task for task in index["tasks"] if task["task_id"] == task_id]
    if len(matches) != 1:
        return None
    # Closing the selected task updates only these self-referential fields.
    matches[0].pop("state")
    matches[0].pop("completion_evidence")
    return index


def _literal_bracket_surface(validator: Any, path: str, binding: dict[str, Any]) -> bool:
    if _target_file(validator, path):
        return True
    if binding.get("kind") not in {"commit", "pull-request", "tree"}:
        return False
    kind = "tree" if binding["kind"] == "tree" else "commit"
    for field, object_kind in (("result_revision", kind), ("base_revision", "commit")):
        revision = binding.get(field)
        if isinstance(revision, str) and validator.git.is_regular_file_at_ref(revision, path, object_kind=object_kind):
            return True
    return False


def _validate_current_result(validator: Any, closure: dict[str, Any], source: str) -> None:
    binding = closure["repository_binding"]
    if not isinstance(binding, dict) or not isinstance(binding.get("kind"), str):
        return
    paths = {_normalized_path(path) for path in closure["implementation_surfaces"] + closure["canonical_owners"]}
    # Literal routes may exist only in the base after a committed deletion.
    if any(not is_target_relative_path(path) or any(char in path for char in "*?") or "[" in path and not _literal_bracket_surface(validator, path, binding) for path in paths):
        validator.error("TASK_CLOSURE_RESULT_SCOPE", "current result requires exact target-relative files", source)
        return
    if _normalized_path(source) in paths:
        paths.remove(_normalized_path(source))
        validator.info("TASK_CLOSURE_REGISTRATION_METADATA", "the closure is post-result metadata, validated through its registered digest and schema rather than its own result hash", source)
    if binding["kind"] == "selected-file-snapshot":
        if INDEX_PATH in paths:
            validator.error("TASK_CLOSURE_RESULT_SCOPE", "task-index maintenance requires a commit/tree binding for stable registration fields", source)
        selected = binding.get("selected_paths")
        if not isinstance(selected, list) or not all(isinstance(path, str) for path in selected) or paths - {_normalized_path(path) for path in selected}:
            validator.error("TASK_CLOSURE_RESULT_SCOPE", "snapshot omits claimed implementation or canonical owner files", source)
        return
    if binding["kind"] not in {"commit", "pull-request", "tree"} or not isinstance(binding.get("result_revision"), str):
        return
    kind = "tree" if binding["kind"] == "tree" else "commit"
    limit, remaining = RESULT_BYTE_LIMITS
    for path in sorted(paths):
        file_limit = min(limit, remaining, MAX_ARTIFACT_BYTES if path == INDEX_PATH else limit)
        recorded, available = validator.git.bounded_file_result_at_ref(binding["result_revision"], path, file_limit, object_kind=kind)
        try:
            status = validator.context.status(Path(path))
            current = validator.context.read_bytes_result(Path(path), max_bytes=file_limit) if status.is_file else None
        except (OSError, ValueError):
            validator.error("TASK_CLOSURE_RESULT_DRIFT", f"current result path is unsafe or unreadable: {path}", source)
            continue
        remaining -= max(len(recorded) if recorded is not None else 0, len(current.value) if current is not None and current.value is not None else 0)
        absent = status.state.value == "missing"
        matches = recorded is not None and current is not None and current.value == recorded
        if path == INDEX_PATH and recorded is not None and current is not None and current.value is not None:
            projected = _registration_projection(recorded, closure["task_id"])
            matches = projected is not None and projected == _registration_projection(current.value, closure["task_id"])
        if not available or (recorded is None and not absent) or (recorded is not None and not matches):
            validator.error("TASK_CLOSURE_RESULT_DRIFT", f"current file is unavailable or differs from closure result: {path}", source)


def _validate_selected_architecture_review(validator: Any, closure: dict[str, Any], source: str) -> None:
    disposition = closure["architecture_review"]
    if not is_resolved_string(disposition["reason"]) or disposition["state"] == "blocked":
        validator.error("TASK_ARCHITECTURE_REVIEW", "final task has an unresolved architecture-review disposition", source)
        return
    catalog_path = ".ai/project/architecture/catalog.json"
    if not _target_file(validator, catalog_path):
        if disposition["state"] != "not-required":
            validator.error("TASK_ARCHITECTURE_REVIEW", "selected architecture review has no catalog", source)
        return
    catalog = validator.load_json_object(validator.target_path(catalog_path), "TASK_ARCHITECTURE_CATALOG")
    if not isinstance(catalog, dict):
        return
    items = [item for field in ("areas", "patterns") for item in (catalog.get(field) if isinstance(catalog.get(field), list) else []) if isinstance(item, dict) and is_resolved_string(item.get("id"))]
    by_id: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_id.setdefault(item["id"], []).append(item)
    owners = {_normalized_path(path) for path in closure["canonical_owners"]}
    facts = set(closure["changed_fact_ids"])
    related = set()
    for item in items:
        review = item.get("source_review")
        if not isinstance(review, dict):
            continue
        paths = {_normalized_path(binding["path"]) for binding in review.get("inputs", []) if isinstance(binding, dict) and isinstance(binding.get("path"), str)} if isinstance(review.get("inputs"), list) else set()
        reviewed_facts = {fact for fact in review.get("changed_fact_ids", []) if isinstance(fact, str)} if isinstance(review.get("changed_fact_ids"), list) else set()
        if owners & paths or facts & reviewed_facts:
            related.add(item["id"])
    selected = set(disposition["item_ids"])
    if related - selected or disposition["state"] == "not-required" and selected:
        validator.error("TASK_ARCHITECTURE_REVIEW", "related architecture items require an explicit selected review", source)
    if disposition["state"] == "reviewed" and not selected:
        validator.error("TASK_ARCHITECTURE_REVIEW", "reviewed requires selected catalog item IDs", source)
    digests = BoundedReviewDigests(validator.context)
    for item_id in sorted(selected):
        matching = by_id.get(item_id, [])
        if len(matching) != 1 or catalog.get("schema_version") != 2:
            validator.error("TASK_ARCHITECTURE_REVIEW", f"{item_id} lacks source-bound schema-2 review evidence", source)
            continue
        item = matching[0]
        review = item.get("source_review")
        failures = review_failures(review, digests)
        if failures or not isinstance(review, dict) or review.get("state") == "revalidation-required":
            validator.error("TASK_ARCHITECTURE_REVIEW", f"{item_id} requires revalidation: {failures}", source)


def validate_active_tasks(validator: Any) -> None:
    """Select registered work without walking ignored runtime or archive folders."""
    try:
        index_read = validator.context.read_bytes_result(validator.target_path(INDEX_PATH), max_bytes=MAX_ARTIFACT_BYTES)
    except (OSError, ValueError):
        validator.error("ACTIVE_TASK_INDEX_LIMIT", "active-task index path is unsafe or unreadable", INDEX_PATH)
        return
    if index_read.value is None:
        validator.error("ACTIVE_TASK_INDEX_LIMIT", f"active-task index must be readable, stable, and at most {MAX_ARTIFACT_BYTES} bytes", INDEX_PATH)
        return
    index = validator.load_json_object(validator.target_path(INDEX_PATH), "ACTIVE_TASK_INDEX")
    if index is None:
        return
    if not _schema_valid(validator, index, "active-task-index", INDEX_PATH):
        return
    tasks = index.get("tasks")
    if type(index.get("schema_version")) is not int or index.get("schema_version") != 1 or index.get("index_kind") != "target-active-task-index" or not isinstance(tasks, list) or len(tasks) > MAX_TASKS:
        validator.error("ACTIVE_TASK_INDEX_CONTRACT", f"index requires schema 1 and at most {MAX_TASKS} tasks", INDEX_PATH)
        return
    seen: set[str] = set()
    seen_closures: set[str] = set()
    model_schema = None
    selected_task = getattr(validator, "current_task_id", None)
    if getattr(validator, "require_task_acceptance", False):
        selected = [task for task in tasks if task.get("task_id") == selected_task]
        if len(selected) != 1 or selected[0].get("state") != "closed":
            validator.error("TASK_ACCEPTANCE_CLOSURE", "current-task acceptance requires one closed selected task", INDEX_PATH)
    if selected_task is not None and not any(task.get("task_id") == selected_task for task in tasks):
        validator.error("ACTIVE_TASK_UNREGISTERED", f"current task {selected_task!r} is absent from the task index", INDEX_PATH)
    changed = validator.git.changed_files(validator.diff_ref) if validator.validation_scope == "changed" else None
    previous_tasks = {}
    if changed is not None and validator.diff_ref:
        change_set = validator.git.change_set(validator.diff_ref)
        previous_bytes = validator.git.bounded_file_at_ref(change_set.base_revision, INDEX_PATH, MAX_ARTIFACT_BYTES) if change_set else None
        try:
            previous_index = json.loads(previous_bytes) if previous_bytes else None
            previous_tasks = {task["task_id"]: task for task in previous_index["tasks"] if isinstance(task, dict) and isinstance(task.get("task_id"), str)} if isinstance(previous_index, dict) and isinstance(previous_index.get("tasks"), list) else {}
        except (ValueError, UnicodeError, RecursionError):
            validator.warn("ACTIVE_TASK_BASELINE_UNAVAILABLE", "baseline headers cannot be read; historical selection cannot be narrowed", INDEX_PATH)
    task_by_id = {task["task_id"]: task for task in tasks}
    for task_id, previous in previous_tasks.items():
        if previous.get("state") == "active" and task_id not in task_by_id:
            validator.error("ACTIVE_TASK_REMOVED", f"active task {task_id} requires a terminal closure before retirement", INDEX_PATH)
    for message in task_predecessor_failures(tasks):
        validator.error("ACTIVE_TASK_PREDECESSOR", message, INDEX_PATH)
    for task in tasks:
        if not isinstance(task, dict) or not is_resolved_string(task.get("task_id")):
            validator.error("ACTIVE_TASK_ENTRY", "task entries require a resolved task_id", INDEX_PATH)
            continue
        task_id = task["task_id"]
        if task_id in seen:
            validator.error("ACTIVE_TASK_DUPLICATE", f"duplicate task_id: {task_id}", INDEX_PATH)
        seen.add(task_id)
        state, scale = task.get("state"), task.get("task_class")
        previous = previous_tasks.get(task_id)
        expected_class = getattr(validator, "current_task_class", None) or "standard-task"
        if task_id == selected_task and scale != expected_class:
            validator.error("ACTIVE_TASK_CLASS", f"selected task class {scale} differs from caller binding {expected_class}", INDEX_PATH)
        if isinstance(previous, dict) and previous.get("task_class") != "small-task" and scale == "small-task":
            validator.error("ACTIVE_TASK_CLASS", "a previously non-trivial task cannot drop its model through a class downgrade", INDEX_PATH)
        if isinstance(previous, dict) and previous.get("incident_family_id") not in (None, "none") and previous["incident_family_id"] != task.get("incident_family_id"):
            validator.error("ACTIVE_TASK_MODEL_LINEAGE", "an existing incident task cannot erase or replace its family identity", INDEX_PATH)
        closure_binding = task.get("completion_evidence")
        if isinstance(closure_binding, dict):
            closure_path = closure_binding["path"]
            if closure_path in seen_closures:
                validator.error("ACTIVE_TASK_DUPLICATE", f"closure is reused: {closure_path}", INDEX_PATH)
            seen_closures.add(closure_path)
        if state == "closed" and changed is not None and previous == task and task_id != selected_task and isinstance(closure_binding, dict) and closure_binding["path"] not in changed:
            model_binding = task.get("problem_model")
            witness_changed = any(path.startswith(f".ai/assistant/task-evidence/{task_id}/") for path in changed)
            if not witness_changed and (not isinstance(model_binding, dict) or model_binding["path"] not in changed):
                continue
        if not isinstance(state, str) or state not in {"active", "closed"} or not isinstance(scale, str) or scale not in {"small-task", "standard-task", "large-or-resumable", "protected-or-sensitive"}:
            validator.error("ACTIVE_TASK_ENTRY", "task state or class is invalid", INDEX_PATH)
            continue
        model_binding = task.get("problem_model")
        closure = _bound_object(validator, task.get("completion_evidence"), f"{task_id} closure") if state == "closed" else None
        if task_id == selected_task and isinstance(closure, dict):
            validator.task_closure_checked = True
        delivery = closure.get("delivery") if isinstance(closure, dict) else None
        require_completion = isinstance(delivery, dict) and delivery.get("evidence_finalization") == "final"
        if scale != "small-task" or model_binding is not None:
            model, selected_binding, archived_projection = _task_model_evidence(validator, task, closure)
            if model is not None:
                model_schema = model_schema or load_problem_model_schema()
                path = validator.target_path(selected_binding["path"])
                if state == "closed" and archived_projection is None:
                    validator.error("ACTIVE_TASK_WITNESS", "closed non-small tasks require durable model and projection witnesses", INDEX_PATH)
                validated_model = validate_selected_problem_model(validator, path, model_schema, require_completion=require_completion,
                    archived_projection=archived_projection, original_source_path=model_binding["path"], current_task=task_id == selected_task)
                if task_id == selected_task and isinstance(validated_model, dict):
                    from target_adapter_validation.repair_review import validate_task_repair_review
                    validate_task_repair_review(validator, task, validated_model, completion=require_completion)
                for code, message in task_model_header_failures(task, validated_model if isinstance(validated_model, dict) else {}):
                    if code == "ACTIVE_TASK_MODEL_LINEAGE":
                        validator.error("ACTIVE_TASK_MODEL_LINEAGE", message, INDEX_PATH)
                    else:
                        validator.error("ACTIVE_TASK_PROJECTION", message, INDEX_PATH)
                incident = validated_model.get("incident") if isinstance(validated_model, dict) else None
                if isinstance(incident, dict) and incident.get("mode") == "none" and task["predecessor_task_ids"]:
                    validator.error("ACTIVE_TASK_PREDECESSOR", "non-incident model cannot claim incident predecessor tasks", INDEX_PATH)
                for predecessor in task["predecessor_task_ids"]:
                    if predecessor in task_by_id and task_by_id[predecessor]["incident_family_id"] != task["incident_family_id"]:
                        validator.error("ACTIVE_TASK_PREDECESSOR", "predecessor task belongs to another incident family", INDEX_PATH)
                if isinstance(incident, dict):
                    predecessor_models = set()
                    for predecessor in task["predecessor_task_ids"]:
                        header = task_by_id.get(predecessor)
                        prior_model = _task_model_evidence(validator, header)[0] if isinstance(header, dict) else None
                        if not isinstance(prior_model, dict) or not isinstance(prior_model.get("model_id"), str):
                            validator.error("ACTIVE_TASK_PREDECESSOR", "predecessor requires model evidence, not only a matching family header", INDEX_PATH)
                            continue
                        predecessor_models.add(prior_model["model_id"])
                        if task_id == selected_task:
                            if not isinstance(prior_model.get("proof_obligations"), list) or any(not isinstance(item, dict) for item in prior_model["proof_obligations"]):
                                validator.error("ACTIVE_TASK_PREDECESSOR", "predecessor proof obligations are malformed", INDEX_PATH)
                                continue
                            inherited_review = any(item.get("id") == "repair-evidence-review" and item.get("required") is True for item in prior_model.get("proof_obligations", []))
                            retained_review = any(item.get("id") == "repair-evidence-review" and item.get("required") is True for item in validated_model.get("proof_obligations", []))
                            if inherited_review and not retained_review:
                                validator.error("ACTIVE_TASK_PREDECESSOR", "incident successors must retain the required repair-evidence-review obligation", INDEX_PATH)
                        prior_incident = prior_model.get("incident")
                        current_iteration = incident.get("corrective_iteration")
                        prior_iteration = prior_incident.get("corrective_iteration") if isinstance(prior_incident, dict) else None
                        if type(current_iteration) is not int or type(prior_iteration) is not int or prior_iteration >= current_iteration or prior_incident.get("family_id") != incident.get("family_id"):
                            validator.error("ACTIVE_TASK_PREDECESSOR", "predecessor family or iteration does not precede current work", INDEX_PATH)
                    declared = incident.get("predecessor_model_ids")
                    if not isinstance(declared, list) or not all(isinstance(item, str) for item in declared) or set(declared) != predecessor_models:
                        validator.error("ACTIVE_TASK_PREDECESSOR", "predecessor tasks and model identities differ; retain required lineage headers", INDEX_PATH)
        if state == "closed":
            if closure is not None:
                validate_task_closure(validator, closure, task)
        elif task.get("completion_evidence") is not None:
            validator.error("ACTIVE_TASK_ENTRY", "active work cannot claim a closed-task receipt", INDEX_PATH)
        elif task_id == selected_task and validator.validation_phase == "acceptance":
            validator.error("ACTIVE_TASK_NOT_CLOSED", "selected current-task acceptance requires a closure receipt", INDEX_PATH)
    validator.info("ACTIVE_TASK_COVERAGE", f"checked {len(tasks)} registered current/recent tasks; unregistered history and runtime files were not scanned", INDEX_PATH)
