"""Preview canonical team-record edits; apply only non-authority metadata."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

from cli_inputs import json_object
from path_spec import logical_path
from team_task_control import execution_hold, read_team_tasks

METADATA = {"next_action", "notes", "residual_risks"}
REVISION = {"record_revision", "expected_revision"}
INDEX = ".ai/assistant/team/active-work-index.json"
MAX_BYTES = 512 * 1024


def _read(view, name):
    path = view.target / logical_path(name)
    if path.resolve() != path:
        raise ValueError("task update inputs must be exact regular paths")
    read = view.read_bytes_result(path, max_bytes=MAX_BYTES, aggregate_max_bytes=10 * 1024 * 1024)
    if read.value is None:
        raise ValueError("task update input is missing or oversized: " + name)
    return read


def _validate_overlay(validator, manifest, overlays):
    from target_adapter_validation.team_collaboration import validate_team_collaboration

    context = validator.capability_validation_context()
    remaining = set(overlays)

    def load(path, code):
        original = context.load_json_object(path, code)
        if original is None or path not in overlays:
            return original
        remaining.discard(path)
        return overlays[path]

    validate_team_collaboration(replace(context, load_target_json_object=load), manifest)
    for path in sorted(remaining):
        validator.error("TEAM_TASK_UPDATE_NOT_VALIDATED",
                        "canonical team validator did not read this draft surface", context.rel(path))


def prepare(target, point_id, draft, expected_sha256):
    from validate_target_adapter import AdapterValidatorConfig, Validator
    from target_validation_support import parse_manifest

    if re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
        raise ValueError("task update requires the exact current SHA-256")
    validator = Validator(target, framework_source=None, diff_ref=None, approval_records=[],
        enforce_approval_scope=False, change_packages=[], enforce_change_package=False,
        migration_diff=None, allow_placeholders=False, allow_local_paths=[], config=AdapterValidatorConfig())
    view = validator.context
    record = read_team_tasks(view).get(point_id)
    if record is None:
        raise ValueError("selected canonical team point is unavailable")
    name, current = record
    original = _read(view, name)
    if original.digest != expected_sha256:
        raise ValueError("task record changed; inspect the latest bytes before retrying")
    observed = _read(view, draft)
    candidate = json_object(observed.value, "candidate team record")
    if name == draft or candidate.get("id") != point_id:
        raise ValueError("draft must be a distinct file with the same point ID")
    changed = sorted(key for key in current.keys() | candidate.keys()
                     if (key in current) != (key in candidate)
                     or json.dumps(current.get(key), sort_keys=True) != json.dumps(candidate.get(key), sort_keys=True))
    revision = current.get("record_revision")
    next_revision = candidate.get("record_revision")
    valid_revision = (type(revision) is int and revision >= 0 and
                      type(next_revision) is int and next_revision == revision + 1 and
                      type(candidate.get("expected_revision")) is int and candidate["expected_revision"] == next_revision)
    manifest_path = view.target / ".ai/alatyr.yaml"
    manifest = parse_manifest(view.text_source(manifest_path))
    entry = manifest.scalars.get(("team_collaboration", "active_work_index"))
    index_name = entry.value if entry else INDEX
    index_raw = _read(view, index_name)
    index = json_object(index_raw.value, "team active-work index")
    projection = copy.deepcopy(index)
    entries = projection.get("entries")
    if not isinstance(entries, list) or len(entries) > 128 or any(not isinstance(row, dict) for row in entries):
        raise ValueError("active-work index requires bounded record entries")
    matches = [row for row in entries if row.get("task_id") == point_id]
    if len(matches) > 1 or any(row.get("task_record") != name or row.get("record_revision") != revision
                               or row.get("status") != current.get("status") for row in matches):
        raise ValueError("selected active-work entry does not match the current task")
    for row in matches:
        row["record_revision"] = next_revision
    _validate_overlay(validator, manifest, {view.target / name: candidate,
                                           view.target / index_name: projection})
    from target_adapter_validation.local_paths import scan_local_paths
    portability = scan_local_paths(observed.value.decode("utf-8"), ".json", str(view.target))
    if portability.failures or portability.matches:
        validator.error("LOCAL_PATH_LEAKAGE", "draft contains machine-local paths or cannot be scanned completely", draft)
    if view.finalize() or not validator.git.finalize():
        raise ValueError("task update inputs changed during review")
    errors = [row for row in validator.findings if row.level == "error"]
    groups = Counter(row.code for row in errors)
    protected = sorted(set(changed) - METADATA - REVISION)
    metadata_valid = ("notes" not in candidate or isinstance(candidate["notes"], str)
                      and len(candidate["notes"]) <= 32768)
    ready = (not errors and not protected and valid_revision and metadata_valid
             and set(changed) & METADATA and not execution_hold(current))
    targets = {view.target / name: (original.value, observed.value)}
    if projection != index:
        targets[view.target / index_name] = (index_raw.value, (json.dumps(projection, indent=2, ensure_ascii=True) + "\n").encode())
    report = {"schema_version": 1, "report_kind": "alatyr-team-task-update",
              "state": "ready-for-metadata-review" if ready else "blocked",
              "task_id": point_id, "changed_fields": changed, "protected_fields": protected,
              "hold": execution_hold(current), "revision_valid": valid_revision,
              "metadata_valid": metadata_valid, "error_count": len(errors),
              "error_groups": dict(groups.most_common(20)), "error_groups_omitted": max(0, len(groups) - 20),
              "examples": [row.to_json() for row in errors[:5]], "draft_sha256": observed.digest,
              "paths": [p.relative_to(view.target).as_posix() for p in targets],
              "write_performed": False, "authorization_granted": False, "acceptance_granted": False,
              "next_action": "review the protected change separately or apply the exact metadata draft, then finalize generated support and refresh registry evidence"}
    return report, targets


def update(target, point_id, draft, expected_sha256, *, write=False, draft_sha256=None):
    if not write:
        return prepare(target, point_id, draft, expected_sha256)[0]
    from support_write_transaction import SupportTransaction, support_writer_lock
    from target_tool_compat import assert_write_compatible
    assert_write_compatible(target, tool_name="team_task_update.py")
    with support_writer_lock(target):
        report, targets = prepare(target, point_id, draft, expected_sha256)
        if report["state"] != "ready-for-metadata-review" or report["draft_sha256"] != draft_sha256:
            raise ValueError("write requires a valid unheld metadata draft and its reviewed SHA-256")
        transaction = SupportTransaction(target)
        try:
            transaction.apply({path: pair[1] for path, pair in targets.items()},
                              expected_inputs={path: pair[0] for path, pair in targets.items()})
            transaction.verify_owned()
        except (OSError, ValueError):
            if transaction.rollback():
                raise ValueError("task update rollback preserved concurrent edits; reconcile the reported paths")
            raise
        return {**report, "state": "metadata-written-support-refresh-required", "write_performed": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--point", required=True)
    parser.add_argument("--draft", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--draft-sha256")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        report = update(args.target.resolve(), args.point, args.draft, args.expected_sha256,
                        write=args.write, draft_sha256=args.draft_sha256)
        print(json.dumps(report, indent=2))
        return 1 if report["state"] == "blocked" else 0
    except (OSError, ValueError, RuntimeError, UnicodeError) as exc:
        print(f"FAIL: team task update: {str(exc)[:400]}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
