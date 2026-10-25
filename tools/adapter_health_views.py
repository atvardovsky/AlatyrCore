"""Bounded derived health views; no acceptance, repair or registry ownership."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from target_adapter_validation.context import TargetRepositoryView
from target_validation_support import is_target_relative_path, is_unresolved_value, parse_manifest


VERSION_PATHS = {"framework": "VERSION", "adapter_schema": "ADAPTER_SCHEMA_VERSION", "template": "TEMPLATE_VERSION"}


def tooling_comparison(view: TargetRepositoryView, source: Path) -> dict[str, Any]:
    producer = TargetRepositoryView(source.resolve())
    versions = {}
    for key, name in VERSION_PATHS.items():
        read = producer.read_bytes_result(producer.target / name, max_bytes=1024)
        try:
            value = read.value.decode("utf-8").strip() if read.value is not None else None
        except UnicodeError:
            value = None
        versions[key] = value if value and not is_unresolved_value(value) else None
    installed = {key: None for key in VERSION_PATHS}
    pin = None
    path = view.target / ".ai/alatyr.yaml"
    read = view.read_bytes_result(path, max_bytes=512 * 1024)
    if read.value is not None:
        try:
            manifest = parse_manifest(view.text_source(path))
        except (ValueError, UnicodeError):
            manifest = None
        if manifest is not None and not manifest.parse_failures:
            for key, location in (("framework", ("framework", "version")), ("adapter_schema", ("schema_version",)), ("template", ("framework", "template_version"))):
                scalar = manifest.scalars.get(location)
                installed[key] = scalar.value if scalar is not None and not is_unresolved_value(scalar.value) else None
            scalar = manifest.scalars.get(("framework", "source_commit")) or manifest.scalars.get(("framework", "baseline"))
            pin = scalar.value if scalar is not None else None
    known = all(value is not None for value in (*versions.values(), *installed.values()))
    state = ("same-declared-versions" if versions == installed else "different-tooling-baseline") if known else "unknown"
    return {"state": state, "producer_versions": versions, "installed_versions": installed,
            "installed_baseline": pin, "next_action": "assess-upgrade" if state == "different-tooling-baseline" else "inspect-findings",
            "acceptance_granted": False, "findings_waived": False,
            "limitation": "Declared versions only, not installed-content integrity or semantic compatibility. Newer-tool comparisons are migration evidence, not proof the older baseline was corrupt."}


def finding_groups(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    for index, item in enumerate(findings):
        key = (item["level"], item["code"], item.get("path"))
        group = groups.setdefault(key, {"level": key[0], "code": key[1], "path": key[2],
                                        "message": item["message"], "count": 0, "finding_indexes": []})
        group["count"] += 1
        group["finding_indexes"].append(index)
    return list(groups.values())


def _overview_index(view: TargetRepositoryView, path: str, field: str) -> tuple[dict[str, Any] | None, str | None]:
    if not is_target_relative_path(path):
        return None, "owner path is unsafe"
    read = view.read_bytes_result(view.target / path, max_bytes=512 * 1024)
    if read.value is None:
        return None, "owner index is unavailable"
    result = view.read_json_result(view.target / path)
    data = result.value
    if result.error or not isinstance(data, dict) or not isinstance(data.get(field), list) or len(data[field]) > 128:
        return None, "owner index is malformed or exceeds 128 entries"
    if any(not isinstance(row, dict) for row in data[field]):
        return None, "owner index entries must be objects"
    return data, None


def work_overview(view: TargetRepositoryView) -> dict[str, Any]:
    task_path = ".ai/assistant/active-tasks.json"
    team_path = ".ai/assistant/team/active-work-index.json"
    manifest_path = view.target / ".ai/alatyr.yaml"
    routing_error = None
    if view.read_bytes_result(manifest_path, max_bytes=512 * 1024).value is not None:
        try:
            manifest = parse_manifest(view.text_source(manifest_path))
        except (ValueError, UnicodeError):
            manifest = None
        if manifest is None or manifest.parse_failures:
            routing_error = "team owner routing is unavailable from the malformed manifest"
        else:
            scalar = manifest.scalars.get(("team_collaboration", "active_work_index"))
            if scalar is not None:
                team_path = scalar.value
    tasks, task_error = _overview_index(view, task_path, "tasks")
    team, team_error = (None, routing_error) if routing_error else _overview_index(view, team_path, "entries")
    active = None
    if tasks is not None:
        from incident_planning import incident_frontier
        frontier = incident_frontier(tasks)
        if frontier["state"] == "derived":
            active = len(frontier["retained_active"])
        else:
            task_error = "task headers are invalid; active count is unknown"
    return {"state": "reported-owner-views", "authority": "none", "acceptance_granted": False,
            "analysis_tasks": {"path": task_path, "active_count": active, "diagnostic": task_error},
            "team_claims": {"path": team_path, "reported_entries": len(team["entries"]) if team is not None else None,
                            "recorded_at": team.get("generated_at") if team is not None and isinstance(team.get("generated_at"), str) and len(team["generated_at"]) <= 128 else None,
                            "freshness": "not-verified", "diagnostic": team_error},
            "sessions": {"state": "not-observed", "next_action": "cooperation-preflight"},
            "limitation": "Independent owners, not a merged registry. Empty team claims do not mean no active tasks; dates and headers do not establish current liveness or coordination."}
