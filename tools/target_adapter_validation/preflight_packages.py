"""Resolve indexed active/selected incident inputs before generating projections."""

from __future__ import annotations

from change_package_contract import ACTIVE_CHANGE_PACKAGE_STATUSES, CHANGE_PACKAGE_STATUSES


def validate_package_prerequisites(validator):
    path = validator.target_path(".ai/assistant/change-packages/index.json")
    entries = []
    if validator.is_target_file(path):
        index = validator.load_json_object(path, "PACKAGE_INDEX")
        if index is not None:
            entries = validator.indexed_change_package_entries(index)
    paths = list(validator.change_packages)
    known = {validator.rel(path) for path in paths}
    for entry in entries:
        record = entry.get("record")
        if entry.get("status") in ACTIVE_CHANGE_PACKAGE_STATUSES and isinstance(record, str) and record not in known:
            paths.append(validator.target_path(record))
            known.add(record)
    for package in validator.resolve_change_packages(paths):
        data = validator.load_json_object(package, "PACKAGE")
        if data is not None:
            if not isinstance(data.get("status"), str) or data["status"] not in CHANGE_PACKAGE_STATUSES:
                validator.error("PACKAGE_STATUS", "package status must be a canonical string", validator.rel(package))
                continue
            validator.validate_package_incident_continuity(data, validator.rel(package),
                status=data.get("status"), indexed_entries=entries, authoring_only=True)
