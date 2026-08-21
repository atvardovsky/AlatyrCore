#!/usr/bin/env python3
"""Inspect a passive Alatyr dependency knowledge export without execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import jsonschema


MANIFEST_NAME = "alatyr-dependency.json"
SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "schemas"
    / "alatyr-dependency-knowledge.schema.json"
)
REQUIRED_PROHIBITIONS = {
    "assistant-bridges",
    "prompts",
    "skills",
    "gates",
    "tools",
    "permissions",
    "lifecycle-hooks",
    "executable-commands",
}
EXPORT_TYPES = {
    "public-contract",
    "architecture",
    "vocabulary",
    "configuration",
    "migration",
    "validation-guidance",
}
AUTHORITIES = {
    "upstream-canonical",
    "upstream-derived",
    "observed",
    "third-party",
}
STABILITIES = {"stable", "experimental", "deprecated", "internal"}
APPLICABILITY = {"active", "inactive", "conditional"}
RELATIONSHIPS = {"public-contract", "optional", "peer", "plugin", "integration"}
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]*$")


def is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and "{" in value and "}" in value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolved_string(value: Any, allow_placeholders: bool) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and (allow_placeholders or not is_placeholder(value))
    )


def validate_export(
    source: Path,
    *,
    allow_placeholders: bool = False,
    verify_files: bool = True,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    def add(code: str, message: str, location: str = MANIFEST_NAME) -> None:
        findings.append({"code": code, "message": message, "location": location})

    root = source.resolve()
    manifest_path = root / MANIFEST_NAME if root.is_dir() else root
    root = manifest_path.parent.resolve()
    if not manifest_path.is_file():
        add("MANIFEST_MISSING", f"missing {MANIFEST_NAME}", str(manifest_path))
        return findings
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        add("MANIFEST_INVALID", f"cannot parse manifest: {exc}")
        return findings
    if not isinstance(data, dict):
        add("MANIFEST_SHAPE", "manifest must contain an object")
        return findings

    if not allow_placeholders:
        try:
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            validator = jsonschema.Draft7Validator(schema)
        except (OSError, UnicodeError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
            add("SCHEMA_UNAVAILABLE", f"cannot load dependency knowledge schema: {exc}")
            return findings
        for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
            location = ".".join(str(part) for part in error.path) or MANIFEST_NAME
            add("SCHEMA_CONTRACT", error.message, location)

    if data.get("schema_version") != 1:
        add("SCHEMA_VERSION", "schema_version must be 1")
    if data.get("package_kind") != "alatyr-dependency-knowledge":
        add("PACKAGE_KIND", "package_kind must be alatyr-dependency-knowledge")
    if data.get("knowledge_api") != 1:
        add("KNOWLEDGE_API", "knowledge_api must be 1")

    package = data.get("package")
    if not isinstance(package, dict):
        add("PACKAGE_SHAPE", "package must be an object")
        package = {}
    for field in ["ecosystem", "name", "version", "source", "license"]:
        if not resolved_string(package.get(field), allow_placeholders):
            add("PACKAGE_FIELD", f"package.{field} must be resolved")
    if package.get("release_profile") not in {"consumer", "full-source"}:
        add("RELEASE_PROFILE", "package.release_profile must be consumer or full-source")

    compatibility = data.get("compatibility")
    required_capabilities = (
        compatibility.get("required_capabilities")
        if isinstance(compatibility, dict)
        else None
    )
    if not isinstance(required_capabilities, list) or "dependency-knowledge:v1" not in required_capabilities:
        add("CAPABILITY", "compatibility must require dependency-knowledge:v1")

    if data.get("export_root") != "exports":
        add("EXPORT_ROOT", "export_root must be exports")
    exports = data.get("exports")
    if not isinstance(exports, list) or not exports:
        add("EXPORTS", "exports must be a non-empty list")
        exports = []

    export_ids: set[str] = set()
    for index, item in enumerate(exports):
        location = f"{MANIFEST_NAME}:exports[{index}]"
        if not isinstance(item, dict):
            add("EXPORT_SHAPE", "export must be an object", location)
            continue
        export_id = item.get("id")
        if not resolved_string(export_id, allow_placeholders) or (
            not is_placeholder(export_id) and not ID_RE.fullmatch(export_id)
        ):
            add("EXPORT_ID", "export id must be a stable namespaced identifier", location)
        elif export_id in export_ids:
            add("EXPORT_ID_DUPLICATE", f"duplicate export id {export_id}", location)
        else:
            export_ids.add(export_id)
        if item.get("type") not in EXPORT_TYPES and not (
            allow_placeholders and is_placeholder(item.get("type"))
        ):
            add("EXPORT_TYPE", "export type is invalid", location)
        if item.get("authority") not in AUTHORITIES and not (
            allow_placeholders and is_placeholder(item.get("authority"))
        ):
            add("EXPORT_AUTHORITY", "export authority is invalid", location)
        if item.get("stability") not in STABILITIES and not (
            allow_placeholders and is_placeholder(item.get("stability"))
        ):
            add("EXPORT_STABILITY", "export stability is invalid", location)
        if not resolved_string(item.get("summary"), allow_placeholders):
            add("EXPORT_SUMMARY", "export summary must be resolved", location)
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence or not all(
            resolved_string(value, allow_placeholders) for value in evidence
        ):
            add("EXPORT_EVIDENCE", "export evidence must contain references", location)

        applicability = item.get("applicability")
        if not isinstance(applicability, dict):
            add("APPLICABILITY", "applicability must be an object", location)
        else:
            state = applicability.get("state")
            if state not in APPLICABILITY and not (
                allow_placeholders and is_placeholder(state)
            ):
                add("APPLICABILITY_STATE", "applicability state is invalid", location)
            conditions = applicability.get("conditions")
            if not isinstance(conditions, list) or not all(
                resolved_string(value, allow_placeholders) for value in conditions
            ):
                add("APPLICABILITY_CONDITIONS", "conditions must be a list of declarative strings", location)

        relpath = item.get("path")
        if not resolved_string(relpath, allow_placeholders):
            add("EXPORT_PATH", "export path must be resolved", location)
            continue
        if allow_placeholders and is_placeholder(relpath):
            continue
        path = Path(relpath)
        if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "exports":
            add("EXPORT_PATH", "export path must remain below exports/", location)
            continue
        candidate = root / path
        try:
            resolved_candidate = candidate.resolve(strict=verify_files)
        except OSError as exc:
            add("EXPORT_FILE", f"cannot resolve export file: {exc}", relpath)
            continue
        try:
            resolved_candidate.relative_to((root / "exports").resolve())
        except ValueError:
            add("EXPORT_ESCAPE", "export path escapes the export root", relpath)
            continue
        current = root
        symlinked = False
        for part in path.parts:
            current = current / part
            if current.is_symlink():
                symlinked = True
                break
        if symlinked:
            add("EXPORT_SYMLINK", "export path must not traverse a symlink", relpath)
        if verify_files and not candidate.is_file():
            add("EXPORT_FILE", "export path must reference an existing file", relpath)
            continue
        expected_digest = item.get("content_digest")
        if not isinstance(expected_digest, str) or not DIGEST_RE.fullmatch(expected_digest):
            add("EXPORT_DIGEST", "content_digest must be lowercase SHA-256", location)
        elif verify_files and candidate.is_file() and sha256(candidate) != expected_digest:
            add("EXPORT_DIGEST_MISMATCH", "content_digest does not match export file", relpath)

    dependencies = data.get("public_dependencies")
    if not isinstance(dependencies, list):
        add("PUBLIC_DEPENDENCIES", "public_dependencies must be a list")
    else:
        for index, item in enumerate(dependencies):
            location = f"{MANIFEST_NAME}:public_dependencies[{index}]"
            if not isinstance(item, dict):
                add("PUBLIC_DEPENDENCY_SHAPE", "dependency reference must be an object", location)
                continue
            for field in ["package", "version_constraint"]:
                if not resolved_string(item.get(field), allow_placeholders):
                    add("PUBLIC_DEPENDENCY_FIELD", f"{field} must be resolved", location)
            if item.get("relationship") not in RELATIONSHIPS and not (
                allow_placeholders and is_placeholder(item.get("relationship"))
            ):
                add("PUBLIC_DEPENDENCY_RELATIONSHIP", "relationship is invalid", location)
            required_ids = item.get("required_export_ids")
            if not isinstance(required_ids, list) or not all(
                resolved_string(value, allow_placeholders) for value in required_ids
            ):
                add("PUBLIC_DEPENDENCY_EXPORTS", "required_export_ids must be a list", location)

    prohibited = data.get("prohibited_surfaces")
    if not isinstance(prohibited, list) or not REQUIRED_PROHIBITIONS <= set(prohibited):
        add("PROHIBITED_SURFACES", "all passive export prohibitions must be declared")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect one local passive dependency knowledge export without execution."
    )
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--allow-placeholders", action="store_true")
    parser.add_argument("--no-file-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    findings = validate_export(
        args.source,
        allow_placeholders=args.allow_placeholders,
        verify_files=not args.no_file_check,
    )
    if args.json:
        print(json.dumps({"valid": not findings, "findings": findings}, indent=2))
    else:
        for finding in findings:
            print(
                f"ERROR {finding['code']} {finding['location']}: {finding['message']}",
                file=sys.stderr,
            )
        if not findings:
            print("Dependency knowledge export structure is valid; semantic trust is not proven.")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
