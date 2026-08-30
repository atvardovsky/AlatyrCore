"""Compatibility and provenance helpers for target-mutating source tools."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from target_validation_support import is_placeholder, load_manifest_object


ROOT = Path(__file__).resolve().parents[1]
SOURCE_TEMPLATE_TARGET = ROOT / "templates" / "target"


def source_revision(source_root: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def dirty_paths(root: Path, *, limit: int = 50) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    paths: list[str] = []
    for line in result.stdout.splitlines():
        value = line[3:] if len(line) > 3 else line.strip()
        value = value.strip()
        if value:
            paths.append(value)
        if len(paths) >= limit:
            break
    return paths


def worktree_state(root: Path) -> str:
    paths = dirty_paths(root, limit=1)
    return "dirty" if paths else "clean"


def file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def source_versions(source_root: Path = ROOT) -> dict[str, str]:
    return {
        "framework_version": (source_root / "VERSION").read_text(encoding="utf-8").strip(),
        "adapter_schema_version": (
            source_root / "ADAPTER_SCHEMA_VERSION"
        ).read_text(encoding="utf-8").strip(),
        "template_version": (
            source_root / "TEMPLATE_VERSION"
        ).read_text(encoding="utf-8").strip(),
    }


def source_template_target(target: Path, *, source_root: Path = ROOT) -> bool:
    """Return true for committed target templates in this source repository."""

    try:
        return target.resolve() == (source_root / "templates" / "target").resolve()
    except OSError:
        return False


def target_versions(target: Path) -> dict[str, str]:
    manifest = load_manifest_object(target / ".ai" / "alatyr.yaml")
    framework = manifest.get("framework")
    framework = framework if isinstance(framework, dict) else {}
    return {
        "framework_version": str(framework.get("version", "")),
        "adapter_schema_version": str(manifest.get("schema_version", "")),
        "template_version": str(framework.get("template_version", "")),
    }


def unresolved_version(value: str) -> bool:
    return not value or is_placeholder(value)


def assert_write_compatible(
    target: Path,
    *,
    tool_name: str,
    migration_staging: bool = False,
    source_root: Path = ROOT,
) -> None:
    """Reject target writes when the running source and target contract differ."""

    current = source_versions(source_root)
    installed = target_versions(target)
    mismatches = [
        f"{key}: target={installed[key] or '<missing>'} source={current[key]}"
        for key in sorted(current)
        if not unresolved_version(installed[key]) and installed[key] != current[key]
    ]
    if mismatches and not migration_staging:
        raise ValueError(
            f"{tool_name} refuses to write with mismatched Alatyr versions; "
            "run an explicit migration-staging operation first: "
            + "; ".join(mismatches)
        )


def generation_provenance(
    target: Path,
    *,
    tool_name: str,
    source_root: Path = ROOT,
) -> dict[str, Any]:
    manifest_path = target / ".ai" / "alatyr.yaml"
    versions = source_versions(source_root)
    if source_template_target(target, source_root=source_root):
        return {
            "schema_version": 1,
            "provenance_kind": "source-template",
            "tool": tool_name,
            "source_revision": "source-template",
            "source_worktree_state": "clean",
            "source_dirty_paths": [],
            "target_manifest": ".ai/alatyr.yaml",
            "target_manifest_digest": file_sha256(manifest_path)
            if manifest_path.is_file()
            else "unavailable",
            "target_worktree_state": "clean",
            "target_dirty_paths": [],
            **versions,
        }
    return {
        "schema_version": 1,
        "tool": tool_name,
        "source_revision": source_revision(source_root),
        "source_worktree_state": worktree_state(source_root),
        "source_dirty_paths": dirty_paths(source_root),
        "target_manifest": ".ai/alatyr.yaml",
        "target_manifest_digest": file_sha256(manifest_path)
        if manifest_path.is_file()
        else "unavailable",
        "target_worktree_state": worktree_state(target),
        "target_dirty_paths": dirty_paths(target),
        **versions,
    }


def generation_provenance_from_manifest_text(
    target: Path,
    *,
    tool_name: str,
    manifest_text: str,
    source_root: Path = ROOT,
) -> dict[str, Any]:
    if source_template_target(target, source_root=source_root):
        return {
            "schema_version": 1,
            "provenance_kind": "source-template",
            "tool": tool_name,
            "source_revision": "source-template",
            "source_worktree_state": "clean",
            "source_dirty_paths": [],
            "target_manifest": ".ai/alatyr.yaml",
            "target_manifest_digest": text_sha256(manifest_text),
            "target_worktree_state": "clean",
            "target_dirty_paths": [],
            **source_versions(source_root),
        }
    provenance = generation_provenance(
        target,
        tool_name=tool_name,
        source_root=source_root,
    )
    provenance["target_manifest_digest"] = text_sha256(manifest_text)
    return provenance


DYNAMIC_GENERATED_BY_FIELDS = {
    "source_revision",
    "source_worktree_state",
    "source_dirty_paths",
    "target_worktree_state",
    "target_dirty_paths",
}


def normalized_generated_json(value: dict[str, Any]) -> dict[str, Any]:
    """Return a comparison-safe copy of a generated JSON object."""

    normalized = copy.deepcopy(value)
    normalized.pop("generated_by", None)
    return normalized


def generated_json_equivalent(expected: str, actual: str) -> bool:
    try:
        expected_object = json.loads(expected)
        actual_object = json.loads(actual)
    except json.JSONDecodeError:
        return expected == actual
    if not isinstance(expected_object, dict) or not isinstance(actual_object, dict):
        return expected_object == actual_object
    return normalized_generated_json(expected_object) == normalized_generated_json(
        actual_object
    )


def generation_provenance_errors(
    value: Any,
    *,
    expected_tool: str | None = None,
) -> list[str]:
    if not isinstance(value, dict):
        return ["generated_by must be an object"]
    required = {
        "schema_version",
        "tool",
        "source_revision",
        "source_worktree_state",
        "source_dirty_paths",
        "target_manifest",
        "target_manifest_digest",
        "target_worktree_state",
        "target_dirty_paths",
        "framework_version",
        "adapter_schema_version",
        "template_version",
    }
    missing = sorted(required - set(value))
    errors = [f"generated_by missing {field}" for field in missing]
    if value.get("schema_version") != 1:
        errors.append("generated_by.schema_version must be 1")
    if expected_tool is not None and value.get("tool") != expected_tool:
        errors.append(
            f"generated_by.tool must be {expected_tool}, got {value.get('tool')}"
        )
    if value.get("source_worktree_state") not in {"clean", "dirty"}:
        errors.append("generated_by.source_worktree_state must be clean or dirty")
    if value.get("target_worktree_state") not in {"clean", "dirty"}:
        errors.append("generated_by.target_worktree_state must be clean or dirty")
    for field in ["source_dirty_paths", "target_dirty_paths"]:
        paths = value.get(field)
        if not isinstance(paths, list) or not all(
            isinstance(path, str) and path for path in paths
        ):
            errors.append(f"generated_by.{field} must be a string list")
    return errors


def source_template_provenance_errors(
    value: Any,
    *,
    expected_tool: str | None = None,
) -> list[str]:
    """Validate stable provenance for committed source template artifacts."""

    errors = generation_provenance_errors(value, expected_tool=expected_tool)
    if not isinstance(value, dict):
        return errors
    if value.get("provenance_kind") != "source-template":
        errors.append("generated_by.provenance_kind must be source-template")
    if value.get("source_revision") != "source-template":
        errors.append("generated_by.source_revision must be source-template")
    if value.get("source_dirty_paths") != []:
        errors.append("generated_by.source_dirty_paths must be empty in source templates")
    if value.get("target_dirty_paths") != []:
        errors.append("generated_by.target_dirty_paths must be empty in source templates")
    if value.get("source_worktree_state") != "clean":
        errors.append("generated_by.source_worktree_state must be clean in source templates")
    if value.get("target_worktree_state") != "clean":
        errors.append("generated_by.target_worktree_state must be clean in source templates")
    return errors
