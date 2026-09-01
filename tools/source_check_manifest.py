"""Reusable helpers for source-check manifest contract validation."""

from __future__ import annotations

import ast
import fnmatch
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_PROFILES = {"micro", "quick", "fast", "full", "change", "platform", "release"}
ALLOWED_WRITE_SCOPES = {"none"}
ALLOWED_PLATFORMS = {"all", "linux", "macos", "windows"}
ALLOWED_RESOURCE_CLASSES = {"light", "standard", "heavy"}
TOOL_DEPENDENCY_CACHE: dict[str, frozenset[str]] = {}


def valid_manifest_path(value: str) -> bool:
    """Accept portable repository-relative literal or glob path declarations."""

    path = Path(value)
    return (
        bool(value)
        and "\\" not in value
        and not path.is_absolute()
        and ".." not in path.parts
        and "." not in path.parts
    )


def validate_path_list(check_id: str, field: str, value: Any) -> list[str]:
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and valid_manifest_path(item) for item in value
    ):
        raise ValueError(f"{check_id}.{field} is invalid")
    if len(value) != len(set(value)):
        raise ValueError(f"{check_id}.{field} contains duplicate paths")
    return value


def validate_optional_path_list(check_id: str, field: str, value: Any) -> list[str]:
    if value is None:
        return []
    return validate_path_list(check_id, field, value)


def load_manifest(
    manifest_path: Path | None = None,
    *,
    root: Path = ROOT,
) -> list[dict[str, Any]]:
    manifest = manifest_path or root / "tools" / "check_manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("schema_version") != 2 or data.get("manifest_kind") != (
        "alatyr-source-checks"
    ):
        raise ValueError("unsupported source check manifest")
    defaults = data.get("defaults")
    checks = data.get("checks")
    if not isinstance(defaults, dict) or not isinstance(checks, list) or not checks:
        raise ValueError("check manifest must define defaults and checks")

    normalized: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, raw in enumerate(checks):
        if not isinstance(raw, dict):
            raise ValueError(f"checks[{index}] must be an object")
        check = {**defaults, **raw}
        check_id = check.get("id")
        command = check.get("command")
        profiles = check.get("profiles")
        platforms = check.get("platforms")
        if "owned_paths" in check:
            raise ValueError(f"{check_id}.owned_paths is obsolete; use contract_inputs")
        contract_inputs = validate_path_list(
            check_id, "contract_inputs", check.get("contract_inputs")
        )
        implementation_paths = validate_path_list(
            check_id, "implementation_paths", check.get("implementation_paths")
        )
        trigger_paths = validate_path_list(
            check_id, "trigger_paths", check.get("trigger_paths")
        )
        dependencies = check.get("depends_on")
        if not isinstance(check_id, str) or not check_id or check_id in ids:
            raise ValueError(f"checks[{index}] has invalid or duplicate id")
        if not isinstance(command, list) or not command or not all(
            isinstance(value, str) and value for value in command
        ):
            raise ValueError(f"{check_id}.command must contain strings")
        script = command[0]
        if (
            not script.startswith("tools/")
            or Path(script).is_absolute()
            or ".." in Path(script).parts
        ):
            raise ValueError(f"{check_id}.command has unsafe script path")
        if not (root / script).is_file():
            raise ValueError(f"{check_id}.command script does not exist: {script}")
        if (
            not isinstance(profiles, list)
            or not profiles
            or not set(profiles) <= ALLOWED_PROFILES
        ):
            raise ValueError(f"{check_id}.profiles is invalid")
        micro_trigger_paths = validate_optional_path_list(
            check_id, "micro_trigger_paths", check.get("micro_trigger_paths")
        )
        if "micro" in profiles and not micro_trigger_paths:
            raise ValueError(
                f"{check_id}.micro_trigger_paths is required for micro profile checks"
            )
        if (
            not isinstance(platforms, list)
            or not platforms
            or not set(platforms) <= ALLOWED_PLATFORMS
        ):
            raise ValueError(f"{check_id}.platforms is invalid")
        if check.get("write_scope") not in ALLOWED_WRITE_SCOPES:
            raise ValueError(f"{check_id}.write_scope is invalid")
        if script not in implementation_paths:
            raise ValueError(
                f"{check_id}.implementation_paths must include its command script"
            )
        overlap = sorted(set(contract_inputs) & set(implementation_paths))
        if overlap:
            raise ValueError(
                f"{check_id} declarations overlap between contract_inputs and "
                f"implementation_paths: {overlap}"
            )
        undeclared_triggers = sorted(
            set(contract_inputs + implementation_paths) - set(trigger_paths)
        )
        if undeclared_triggers:
            raise ValueError(
                f"{check_id}.trigger_paths must include every contract or "
                f"implementation input: {undeclared_triggers}"
            )
        timeout_seconds = check.get("timeout_seconds")
        if (
            not isinstance(timeout_seconds, int)
            or isinstance(timeout_seconds, bool)
            or timeout_seconds <= 0
        ):
            raise ValueError(f"{check_id}.timeout_seconds is invalid")
        if check.get("resource_class") not in ALLOWED_RESOURCE_CLASSES:
            raise ValueError(f"{check_id}.resource_class is invalid")
        if not isinstance(check.get("always_for_changed", False), bool):
            raise ValueError(f"{check_id}.always_for_changed must be boolean")
        if not isinstance(dependencies, list) or not all(
            isinstance(value, str) and value for value in dependencies
        ):
            raise ValueError(f"{check_id}.depends_on is invalid")
        ids.add(check_id)
        check["contract_inputs"] = contract_inputs
        check["implementation_paths"] = implementation_paths
        check["trigger_paths"] = trigger_paths
        check["micro_trigger_paths"] = micro_trigger_paths
        check["always_for_changed"] = check.get("always_for_changed", False)
        normalized.append(check)

    by_id = {check["id"]: check for check in normalized}
    for check in normalized:
        unknown = sorted(set(check["depends_on"]) - set(by_id))
        if unknown:
            raise ValueError(f"{check['id']} has unknown dependencies: {unknown}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(check_id: str) -> None:
        if check_id in visiting:
            raise ValueError(f"check dependency cycle includes {check_id}")
        if check_id in visited:
            return
        visiting.add(check_id)
        for dependency in by_id[check_id]["depends_on"]:
            visit(dependency)
        visiting.remove(check_id)
        visited.add(check_id)

    for check_id in by_id:
        visit(check_id)
    return normalized


def matches(check: dict[str, Any], path: str) -> bool:
    """Whether a path is declared as a checked contract or implementation input."""

    candidates = [*check["contract_inputs"], *check["implementation_paths"]]
    return any(fnmatch.fnmatch(path, pattern) for pattern in candidates)


def routes(check: dict[str, Any], path: str) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in check["trigger_paths"])


def micro_routes(check: dict[str, Any], path: str) -> bool:
    """Whether a path is explicitly allowed to use this check in micro mode."""

    return any(
        fnmatch.fnmatch(path, pattern) for pattern in check.get("micro_trigger_paths", [])
    )


@dataclass(frozen=True)
class SourcePathIndex:
    """Repository source paths used to resolve manifest declarations once."""

    paths: frozenset[str]

    @classmethod
    def from_paths(cls, paths: list[str]) -> "SourcePathIndex":
        indexed: set[str] = set()
        for path in paths:
            normalized = Path(path).as_posix()
            if not normalized or normalized == ".":
                continue
            indexed.add(normalized)
            parent = Path(normalized).parent
            while parent.as_posix() not in {"", "."}:
                indexed.add(parent.as_posix())
                parent = parent.parent
        return cls(frozenset(indexed))

    @classmethod
    def from_root(cls, root: Path = ROOT) -> "SourcePathIndex":
        result = subprocess.run(
            ["git", "ls-files", "-c", "-o", "--exclude-standard", "-z"],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            message = result.stderr.decode("utf-8", errors="replace").strip()
            raise ValueError(message or "cannot enumerate source paths")
        paths = [
            path
            for path in result.stdout.decode(
                "utf-8", errors="surrogateescape"
            ).split("\0")
            if path
        ]
        return cls.from_paths(paths)

    def matches_declaration(self, pattern: str) -> bool:
        if any(character in pattern for character in "*?["):
            return any(fnmatch.fnmatch(path, pattern) for path in self.paths)
        return pattern in self.paths


def declared_implementation_path(check: dict[str, Any], path: str) -> bool:
    return any(
        fnmatch.fnmatch(path, pattern) for pattern in check["implementation_paths"]
    )


def direct_local_tool_dependencies(script: str) -> set[str]:
    """Find direct imports that resolve to repository-local tools modules.

    This deliberately validates only imports that Python can resolve from the
    checked-in `tools/` tree. Dynamic imports and runtime-computed data paths
    remain a maintainer declaration responsibility.
    """

    cached = TOOL_DEPENDENCY_CACHE.get(script)
    if cached is not None:
        return set(cached)

    path = ROOT / script
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=script)
    dependencies: set[str] = set()
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules = [alias.name.split(".", 1)[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules = [node.module.split(".", 1)[0]]
        for module in modules:
            module_file = ROOT / "tools" / f"{module}.py"
            module_package = ROOT / "tools" / module
            if module_file.is_file():
                dependencies.add(module_file.relative_to(ROOT).as_posix())
            elif (module_package / "__init__.py").is_file():
                dependencies.add(module_package.relative_to(ROOT).as_posix() + "/**")
    TOOL_DEPENDENCY_CACHE[script] = frozenset(dependencies)
    return dependencies


def declaration_matches_source(
    path: str, source_index: SourcePathIndex | None = None
) -> bool:
    """Reject stale exact paths and glob declarations that match no source file."""

    index = source_index or SourcePathIndex.from_root(ROOT)
    return index.matches_declaration(path)


def broad_trigger_patterns(check: dict[str, Any]) -> list[str]:
    patterns: list[str] = []
    for pattern in check["trigger_paths"]:
        if pattern == "**":
            patterns.append(pattern)
            continue
        if pattern.endswith("/**"):
            prefix = pattern[:-3].rstrip("/")
            if len(Path(prefix).parts) <= 2:
                patterns.append(pattern)
    return patterns
