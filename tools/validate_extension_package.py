#!/usr/bin/env python3
"""Read-only structural validator for a local Alatyr extension checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from target_validation_support import parse_manifest


MANIFEST_NAME = "alatyr-extension.json"
PACKAGE_ID_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)+$")
ITEM_ID_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
    r"(?:\+[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$"
)
RULE_ID_RE = re.compile(r"^ALATYR-[A-Z0-9]+-\d{3}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
PLACEHOLDER_RE = re.compile(r"^\{[A-Z0-9_]+\}$")
EMBEDDED_PLACEHOLDER_RE = re.compile(r"\{[A-Z0-9_]+\}")
ITEM_TYPES = {
    "skill",
    "prompt",
    "gate",
    "flow",
    "template",
    "checker",
    "tool",
    "mcp",
    "bridge",
    "wrapper",
    "rule",
    "doc",
}
ALLOWED_ACTIONS = {
    "read-only",
    "docs-only",
    "adapter-only",
    "code-and-tests",
    "full-with-approval",
}
LIFECYCLE = {
    "installation": "declarative-only",
    "updates": "review-diff-and-reapprove",
    "removal": "ownership-aware",
    "arbitrary_hooks": False,
}
SKIPPED_DIRS = {".git", ".hg", ".svn", "__pycache__"}


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    path: str | None = None

    def to_json(self) -> dict[str, str]:
        result = {"level": self.level, "code": self.code, "message": self.message}
        if self.path:
            result["path"] = self.path
        return result

    def render(self) -> str:
        location = f" {self.path}" if self.path else ""
        return f"{self.level.upper()} {self.code}{location}: {self.message}"


def is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and bool(PLACEHOLDER_RE.fullmatch(value.strip()))


def has_placeholder(value: Any) -> bool:
    return isinstance(value, str) and bool(EMBEDDED_PLACEHOLDER_RE.search(value))


def non_empty_string(
    value: Any,
    label: str,
    findings: list[Finding],
    *,
    allow_placeholders: bool,
) -> str | None:
    if not isinstance(value, str) or not value.strip():
        findings.append(Finding("error", "FIELD_STRING", f"{label} must be a non-empty string"))
        return None
    if is_placeholder(value) and not allow_placeholders:
        findings.append(Finding("error", "PLACEHOLDER", f"{label} is unresolved"))
        return None
    return value.strip()


def string_list(
    value: Any,
    label: str,
    findings: list[Finding],
    *,
    allow_empty: bool = False,
    allow_placeholders: bool,
) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "a list" if allow_empty else "a non-empty list"
        findings.append(Finding("error", "FIELD_LIST", f"{label} must be {qualifier}"))
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        parsed = non_empty_string(
            item,
            f"{label}[{index}]",
            findings,
            allow_placeholders=allow_placeholders,
        )
        if parsed is not None:
            result.append(parsed)
    return result


def safe_item_path(value: str) -> bool:
    if "\\" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and len(path.parts) > 1
        and path.parts[0] == "items"
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def included_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SKIPPED_DIRS for part in relative.parts):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        result.append(path)
    return result


def package_digest(root: Path) -> tuple[str, list[dict[str, str]]]:
    digest = hashlib.sha256()
    files: list[dict[str, str]] = []
    for path in included_files(root):
        relative = path.relative_to(root).as_posix()
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
        files.append({"path": relative, "sha256": file_hash})
    return digest.hexdigest(), files


def semver_key(value: str) -> tuple[tuple[int, int, int], int, tuple[tuple[int, Any], ...]]:
    without_build = value.split("+", 1)[0]
    core_text, separator, prerelease = without_build.partition("-")
    core = tuple(int(part) for part in core_text.split("."))
    identifiers: tuple[tuple[int, Any], ...] = tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in prerelease.split(".")
        if part
    )
    return (core, 0 if separator else 1, identifiers)


def assess_compatibility(
    manifest: dict[str, Any],
    *,
    framework_version: str | None,
    adapter_schema_version: int | None,
    template_version: int | None,
    available_rule_ids: set[str] | None,
) -> dict[str, Any]:
    compatibility = manifest.get("compatibility")
    checks: list[dict[str, Any]] = []
    if not isinstance(compatibility, dict):
        return {"status": "unassessed", "checks": checks}

    def add(name: str, status: str, detail: str) -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    framework = compatibility.get("framework")
    if framework_version is None:
        add("framework", "unassessed", "target framework version not provided")
    elif not SEMVER_RE.fullmatch(framework_version) or not isinstance(framework, dict):
        add("framework", "incompatible", "target or declared framework range is invalid")
    else:
        minimum = framework.get("minimum")
        maximum = framework.get("maximum_exclusive")
        compatible = (
            isinstance(minimum, str)
            and isinstance(maximum, str)
            and bool(SEMVER_RE.fullmatch(minimum))
            and bool(SEMVER_RE.fullmatch(maximum))
            and semver_key(minimum) <= semver_key(framework_version) < semver_key(maximum)
        )
        add("framework", "compatible" if compatible else "incompatible", framework_version)

    for name, actual in [
        ("adapter_schema", adapter_schema_version),
        ("template", template_version),
    ]:
        interval = compatibility.get(name)
        if actual is None:
            add(name, "unassessed", f"target {name} version not provided")
        elif not isinstance(interval, dict):
            add(name, "incompatible", "declared compatibility range is invalid")
        else:
            minimum = interval.get("minimum")
            maximum = interval.get("maximum")
            compatible = (
                isinstance(minimum, int)
                and not isinstance(minimum, bool)
                and isinstance(maximum, int)
                and not isinstance(maximum, bool)
                and minimum <= actual <= maximum
            )
            add(name, "compatible" if compatible else "incompatible", str(actual))

    required_rules = compatibility.get("required_rule_ids")
    if available_rule_ids is None:
        add("required_rules", "unassessed", "target rule registry not provided")
    elif not isinstance(required_rules, list):
        add("required_rules", "incompatible", "required_rule_ids is invalid")
    else:
        missing = sorted(
            rule_id
            for rule_id in required_rules
            if isinstance(rule_id, str) and rule_id not in available_rule_ids
        )
        add(
            "required_rules",
            "incompatible" if missing else "compatible",
            "missing: " + ", ".join(missing) if missing else "all required rules present",
        )

    statuses = {check["status"] for check in checks}
    if "incompatible" in statuses:
        status = "incompatible"
    elif statuses == {"compatible"}:
        status = "compatible"
    elif "compatible" in statuses:
        status = "partially-assessed"
    else:
        status = "unassessed"
    return {"status": status, "checks": checks}


def validate_compatibility(
    value: Any, findings: list[Finding], *, allow_placeholders: bool
) -> None:
    if not isinstance(value, dict):
        findings.append(Finding("error", "COMPATIBILITY_SHAPE", "compatibility must be an object"))
        return
    if value.get("extension_api") != 1:
        findings.append(Finding("error", "EXTENSION_API", "compatibility.extension_api must be 1"))
    framework = value.get("framework")
    if not isinstance(framework, dict):
        findings.append(Finding("error", "FRAMEWORK_RANGE", "compatibility.framework must be an object"))
    else:
        for field in ["minimum", "maximum_exclusive"]:
            version = non_empty_string(
                framework.get(field),
                f"compatibility.framework.{field}",
                findings,
                allow_placeholders=allow_placeholders,
            )
            if version and not is_placeholder(version) and not SEMVER_RE.fullmatch(version):
                findings.append(Finding("error", "FRAMEWORK_VERSION", f"compatibility.framework.{field} is not SemVer-like"))
    for field in ["adapter_schema", "template"]:
        interval = value.get(field)
        if not isinstance(interval, dict):
            findings.append(Finding("error", "COMPATIBILITY_RANGE", f"compatibility.{field} must be an object"))
            continue
        minimum = interval.get("minimum")
        maximum = interval.get("maximum")
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
            findings.append(Finding("error", "COMPATIBILITY_MIN", f"compatibility.{field}.minimum must be a positive integer"))
        if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1:
            findings.append(Finding("error", "COMPATIBILITY_MAX", f"compatibility.{field}.maximum must be a positive integer"))
        if isinstance(minimum, int) and isinstance(maximum, int) and minimum > maximum:
            findings.append(Finding("error", "COMPATIBILITY_ORDER", f"compatibility.{field}.minimum exceeds maximum"))
    rules = string_list(
        value.get("required_rule_ids"),
        "compatibility.required_rule_ids",
        findings,
        allow_empty=True,
        allow_placeholders=allow_placeholders,
    )
    for rule_id in rules:
        if not is_placeholder(rule_id) and not RULE_ID_RE.fullmatch(rule_id):
            findings.append(Finding("error", "RULE_ID", f"invalid required rule ID {rule_id}"))


def validate_package(
    root: Path,
    *,
    allow_placeholders: bool = False,
    framework_version: str | None = None,
    adapter_schema_version: int | None = None,
    template_version: int | None = None,
    available_rule_ids: set[str] | None = None,
) -> dict[str, Any]:
    findings: list[Finding] = []
    root = root.resolve()
    manifest_path = root / MANIFEST_NAME
    manifest: dict[str, Any] = {}
    if not manifest_path.is_file():
        findings.append(Finding("error", "MANIFEST_MISSING", f"missing {MANIFEST_NAME}", MANIFEST_NAME))
    elif manifest_path.is_symlink():
        findings.append(Finding("error", "MANIFEST_SYMLINK", "manifest must not be a symlink", MANIFEST_NAME))
    else:
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                findings.append(Finding("error", "MANIFEST_SHAPE", "manifest must contain an object", MANIFEST_NAME))
            else:
                manifest = loaded
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            findings.append(Finding("error", "MANIFEST_JSON", f"cannot read manifest: {exc}", MANIFEST_NAME))

    if manifest:
        if manifest.get("schema_version") != 1:
            findings.append(Finding("error", "SCHEMA_VERSION", "schema_version must be 1"))
        if manifest.get("package_kind") != "alatyr-extension":
            findings.append(Finding("error", "PACKAGE_KIND", "package_kind must be alatyr-extension"))
        package_id = non_empty_string(
            manifest.get("id"), "id", findings, allow_placeholders=allow_placeholders
        )
        if package_id and not is_placeholder(package_id) and not PACKAGE_ID_RE.fullmatch(package_id):
            findings.append(Finding("error", "PACKAGE_ID", "id must be a lowercase namespaced package ID"))
        version = non_empty_string(
            manifest.get("version"), "version", findings, allow_placeholders=allow_placeholders
        )
        if version and not is_placeholder(version) and not SEMVER_RE.fullmatch(version):
            findings.append(Finding("error", "PACKAGE_VERSION", "version must be SemVer-like"))
        for field in ["name", "description", "license", "source_repository"]:
            non_empty_string(
                manifest.get(field), field, findings, allow_placeholders=allow_placeholders
            )
        validate_compatibility(
            manifest.get("compatibility"), findings, allow_placeholders=allow_placeholders
        )

        provided = manifest.get("provides")
        if not isinstance(provided, list) or not provided:
            findings.append(Finding("error", "PROVIDES_EMPTY", "provides must be a non-empty list"))
            provided = []
        item_ids: set[str] = set()
        item_paths: set[str] = set()
        for index, item in enumerate(provided):
            label = f"provides[{index}]"
            if not isinstance(item, dict):
                findings.append(Finding("error", "ITEM_SHAPE", f"{label} must be an object"))
                continue
            item_id = non_empty_string(
                item.get("id"), f"{label}.id", findings, allow_placeholders=allow_placeholders
            )
            if item_id and not is_placeholder(item_id):
                if not ITEM_ID_RE.fullmatch(item_id):
                    findings.append(Finding("error", "ITEM_ID", f"{label}.id is invalid"))
                if item_id in item_ids:
                    findings.append(Finding("error", "ITEM_ID_DUPLICATE", f"duplicate item ID {item_id}"))
                item_ids.add(item_id)
            item_type = non_empty_string(
                item.get("type"), f"{label}.type", findings, allow_placeholders=allow_placeholders
            )
            if item_type and not is_placeholder(item_type) and item_type not in ITEM_TYPES:
                findings.append(Finding("error", "ITEM_TYPE", f"{label}.type is invalid"))
            source_path = non_empty_string(
                item.get("path"), f"{label}.path", findings, allow_placeholders=allow_placeholders
            )
            if source_path and not (allow_placeholders and has_placeholder(source_path)):
                if not safe_item_path(source_path):
                    findings.append(Finding("error", "ITEM_PATH", f"{label}.path must remain under items/"))
                elif source_path in item_paths:
                    findings.append(Finding("error", "ITEM_PATH_DUPLICATE", f"duplicate provided path {source_path}"))
                else:
                    item_paths.add(source_path)
                    absolute = root / PurePosixPath(source_path)
                    if absolute.is_symlink():
                        findings.append(Finding("error", "ITEM_SYMLINK", "provided item must not be a symlink", source_path))
                    elif not absolute.is_file():
                        findings.append(Finding("error", "ITEM_MISSING", "provided item path does not exist", source_path))
            non_empty_string(
                item.get("purpose"), f"{label}.purpose", findings, allow_placeholders=allow_placeholders
            )
            for field in [
                "activation_triggers",
                "required_context",
                "supported_assistants",
                "requested_permissions",
                "gates",
                "validation",
            ]:
                string_list(
                    item.get(field),
                    f"{label}.{field}",
                    findings,
                    allow_placeholders=allow_placeholders,
                )
            actions = string_list(
                item.get("allowed_actions"),
                f"{label}.allowed_actions",
                findings,
                allow_placeholders=allow_placeholders,
            )
            for action in actions:
                if not is_placeholder(action) and action not in ALLOWED_ACTIONS:
                    findings.append(Finding("error", "ITEM_ACTION", f"{label} has invalid allowed action {action}"))
            non_empty_string(
                item.get("output_contract"),
                f"{label}.output_contract",
                findings,
                allow_placeholders=allow_placeholders,
            )

        bindings = manifest.get("project_bindings")
        if not isinstance(bindings, list):
            findings.append(Finding("error", "BINDINGS_SHAPE", "project_bindings must be a list"))
            bindings = []
        binding_ids: set[str] = set()
        for index, binding in enumerate(bindings):
            label = f"project_bindings[{index}]"
            if not isinstance(binding, dict):
                findings.append(Finding("error", "BINDING_SHAPE", f"{label} must be an object"))
                continue
            binding_id = non_empty_string(
                binding.get("id"), f"{label}.id", findings, allow_placeholders=allow_placeholders
            )
            if binding_id and not is_placeholder(binding_id):
                if not ITEM_ID_RE.fullmatch(binding_id):
                    findings.append(Finding("error", "BINDING_ID", f"{label}.id is invalid"))
                if binding_id in binding_ids:
                    findings.append(Finding("error", "BINDING_DUPLICATE", f"duplicate binding ID {binding_id}"))
                binding_ids.add(binding_id)
            for field in ["description", "value_type"]:
                non_empty_string(
                    binding.get(field),
                    f"{label}.{field}",
                    findings,
                    allow_placeholders=allow_placeholders,
                )
            if not isinstance(binding.get("required"), bool):
                findings.append(Finding("error", "BINDING_REQUIRED", f"{label}.required must be boolean"))

        string_list(
            manifest.get("conflicts"),
            "conflicts",
            findings,
            allow_empty=True,
            allow_placeholders=allow_placeholders,
        )
        dependencies = manifest.get("extension_dependencies")
        if dependencies != []:
            findings.append(Finding("error", "EXTENSION_DEPENDENCIES", "version 1 requires extension_dependencies to be empty"))
        if manifest.get("lifecycle") != LIFECYCLE:
            findings.append(Finding("error", "LIFECYCLE", "lifecycle must be declarative-only without arbitrary hooks"))
        string_list(
            manifest.get("validation"),
            "validation",
            findings,
            allow_placeholders=allow_placeholders,
        )

    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SKIPPED_DIRS for part in relative.parts):
            continue
        if path.is_symlink():
            findings.append(Finding("error", "PACKAGE_SYMLINK", "package symlinks are not accepted", relative.as_posix()))

    digest, files = package_digest(root)
    compatibility_result = assess_compatibility(
        manifest,
        framework_version=framework_version,
        adapter_schema_version=adapter_schema_version,
        template_version=template_version,
        available_rule_ids=available_rule_ids,
    )
    if compatibility_result["status"] == "incompatible":
        findings.append(
            Finding(
                "error",
                "TARGET_COMPATIBILITY",
                "extension compatibility does not match the selected target baseline",
            )
        )
    errors = sum(finding.level == "error" for finding in findings)
    return {
        "schema_version": 1,
        "report_kind": "alatyr-extension-package-validation",
        "package_root": str(root),
        "manifest": MANIFEST_NAME,
        "package_id": manifest.get("id", "unresolved"),
        "package_version": manifest.get("version", "unresolved"),
        "package_digest_sha256": digest,
        "digest_valid": bool(SHA256_RE.fullmatch(digest)),
        "files": files,
        "compatibility": compatibility_result,
        "provided_item_count": len(manifest.get("provides", [])) if isinstance(manifest.get("provides"), list) else 0,
        "findings": [finding.to_json() for finding in findings],
        "counts": {
            "errors": errors,
            "warnings": sum(finding.level == "warning" for finding in findings),
            "info": sum(finding.level == "info" for finding in findings),
        },
        "execution_performed": False,
        "network_access_performed": False,
        "limitations": [
            "structural validation does not prove source trustworthiness or semantic quality",
            "license text and legal compatibility are not interpreted",
            "declared commands tools MCP servers hooks and validation are not executed",
            "target bindings permissions approval and runtime compatibility require target review",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect a local Alatyr extension checkout without executing it."
    )
    parser.add_argument("--package", required=True, type=Path, help="local extension package root")
    parser.add_argument(
        "--target",
        type=Path,
        help="optional installed target repository used for compatibility assessment",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable report")
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="allow authoring-template placeholders",
    )
    args = parser.parse_args()
    if not args.package.is_dir():
        print(f"FAIL: package root is not a directory: {args.package}", file=sys.stderr)
        return 2
    framework_version: str | None = None
    adapter_schema_version: int | None = None
    template_version: int | None = None
    available_rule_ids: set[str] | None = None
    if args.target is not None:
        target = args.target.resolve()
        manifest_path = target / ".ai" / "alatyr.yaml"
        if not manifest_path.is_file():
            print(f"FAIL: target manifest is missing: {manifest_path}", file=sys.stderr)
            return 2
        try:
            target_manifest = parse_manifest(manifest_path)
            framework_version = target_manifest.scalars[("framework", "version")].value
            adapter_schema_version = int(target_manifest.scalars[("schema_version",)].value)
            template_version = int(target_manifest.scalars[("framework", "template_version")].value)
            registry_reference = target_manifest.scalars[("framework", "rule_registry")].value
            registry = json.loads((target / registry_reference).read_text(encoding="utf-8"))
            available_rule_ids = {
                rule.get("id")
                for rule in registry.get("rules", [])
                if isinstance(rule, dict) and isinstance(rule.get("id"), str)
            }
        except (KeyError, ValueError, OSError, json.JSONDecodeError) as exc:
            print(f"FAIL: cannot read target compatibility baseline: {exc}", file=sys.stderr)
            return 2
    report = validate_package(
        args.package,
        allow_placeholders=args.allow_placeholders,
        framework_version=framework_version,
        adapter_schema_version=adapter_schema_version,
        template_version=template_version,
        available_rule_ids=available_rule_ids,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for finding in report["findings"]:
            print(
                Finding(
                    finding["level"],
                    finding["code"],
                    finding["message"],
                    finding.get("path"),
                ).render(),
                file=sys.stderr if finding["level"] == "error" else sys.stdout,
            )
        status = "OK" if report["counts"]["errors"] == 0 else "FAIL"
        print(
            f"{status}: extension {report['package_id']} {report['package_version']}; "
            f"{report['provided_item_count']} item(s); digest "
            f"{report['package_digest_sha256']}; compatibility "
            f"{report['compatibility']['status']}; no execution or network access"
        )
    return 1 if report["counts"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
