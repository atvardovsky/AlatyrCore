#!/usr/bin/env python3
"""Validate and render target-adapter contract compatibility metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from target_adapter_validation.contract_compatibility import (
    CATALOG_PATH,
    load_contract_compatibility,
)
from yaml_support import safe_load


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "target-adapter-contract-compatibility.md"
ADAPTER_SCHEMA = ROOT / "schemas" / "alatyr-adapter.schema.json"
TARGET_MANIFEST = ROOT / "templates" / "target" / ".ai" / "alatyr.yaml"


def nested(value: Any, dotted_path: str) -> Any:
    current = value
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return value


def validate(catalog: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    contracts = catalog.get("contracts")
    if not isinstance(contracts, dict) or not contracts:
        return ["compatibility catalog requires contracts"]

    adapter_schema = load_object(ADAPTER_SCHEMA)
    manifest = safe_load(TARGET_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        return ["target manifest template must contain a mapping"]

    for contract_id, contract in sorted(contracts.items()):
        if not isinstance(contract, dict):
            failures.append(f"{contract_id} must be an object")
            continue
        manifest_key = contract.get("manifest_key")
        contract_version = contract.get("manifest_contract_version")
        if not isinstance(manifest_key, str) or not isinstance(contract_version, int):
            failures.append(f"{contract_id} requires manifest key and integer version")
            continue
        if nested(manifest, manifest_key) != contract_version:
            failures.append(
                f"{contract_id} target manifest {manifest_key} differs from "
                f"compatibility version {contract_version}"
            )
        schema_contract = nested(
            adapter_schema,
            "properties." + manifest_key.replace(".contract_version", "")
            + ".properties.contract_version.const",
        )
        if schema_contract != contract_version:
            failures.append(
                f"{contract_id} adapter schema contract version differs from "
                f"{contract_version}"
            )

        artifacts = contract.get("artifacts")
        if not isinstance(artifacts, dict) or not artifacts:
            failures.append(f"{contract_id} requires artifacts")
            continue
        for artifact_id, artifact in sorted(artifacts.items()):
            label = f"{contract_id}.{artifact_id}"
            if not isinstance(artifact, dict):
                failures.append(f"{label} must be an object")
                continue
            current = artifact.get("current")
            supported = artifact.get("supported")
            limited = artifact.get("migration_limited")
            if (
                not isinstance(current, int)
                or not isinstance(supported, list)
                or not supported
                or any(not isinstance(value, int) for value in supported)
                or len(set(supported)) != len(supported)
                or supported != sorted(supported)
            ):
                failures.append(f"{label} has invalid current or supported versions")
                continue
            if current not in supported:
                failures.append(f"{label} current version is not supported")
            if (
                not isinstance(limited, list)
                or any(value not in supported or value == current for value in limited)
                or len(set(limited)) != len(limited)
            ):
                failures.append(f"{label} has invalid migration-limited versions")

            for path_field in ("schema", "template"):
                relpath = artifact.get(path_field)
                if relpath is None:
                    continue
                if not isinstance(relpath, str) or not (ROOT / relpath).is_file():
                    failures.append(f"{label}.{path_field} is missing: {relpath}")
            template_path = artifact.get("template")
            if isinstance(template_path, str) and (ROOT / template_path).is_file():
                template = load_object(ROOT / template_path)
                if template.get("schema_version") != current:
                    failures.append(
                        f"{label} template schema_version differs from current {current}"
                    )
            schema_path = artifact.get("schema")
            if isinstance(schema_path, str) and (ROOT / schema_path).is_file():
                schema = load_object(ROOT / schema_path)
                declared = nested(schema, "properties.schema_version")
                declared_versions = (
                    declared.get("enum") if isinstance(declared, dict) else None
                )
                if declared_versions != supported:
                    failures.append(
                        f"{label} schema versions {declared_versions} differ from "
                        f"supported {supported}"
                    )

            minimums = artifact.get("minimum_index_by_record")
            if minimums is not None:
                expected_keys = {str(value) for value in supported}
                if not isinstance(minimums, dict) or set(minimums) != expected_keys:
                    failures.append(
                        f"{label} minimum-index mapping must cover every supported version"
                    )
                elif any(
                    not isinstance(value, int) for value in minimums.values()
                ):
                    failures.append(f"{label} minimum-index values must be integers")
    return failures


def render(catalog: dict[str, Any]) -> str:
    lines = [
        "# Target Adapter Contract Compatibility",
        "",
        "This generated source-maintainer reference projects the canonical",
        "compatibility data in",
        "`tools/target_adapter_validation/contract-compatibility.json`.",
        "It does not replace portable framework rules or target-owned project facts.",
        "",
    ]
    for contract_id, contract in sorted(catalog["contracts"].items()):
        lines.extend(
            [
                f"## {contract_id}",
                "",
                f"Manifest key: `{contract['manifest_key']}`.",
                f"Current contract version: `{contract['manifest_contract_version']}`.",
                "",
            ]
        )
        for artifact_id, artifact in sorted(contract["artifacts"].items()):
            supported = ", ".join(f"`{value}`" for value in artifact["supported"])
            limited = artifact["migration_limited"]
            limited_text = (
                ", ".join(f"`{value}`" for value in limited) if limited else "none"
            )
            lines.extend(
                [
                    f"Artifact: `{artifact_id}`",
                    f"Current version: `{artifact['current']}`.",
                    f"Supported versions: {supported}.",
                    f"Migration-limited versions: {limited_text}.",
                    "",
                ]
            )
    lines.extend(
        [
            "Regenerate this reference with:",
            "",
            "```sh",
            "python3 tools/render_target_contract_compatibility.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when output is stale")
    args = parser.parse_args()

    try:
        catalog = load_contract_compatibility()
        failures = validate(catalog)
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    content = render(catalog)
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != content:
            print(f"FAIL: stale generated output {OUTPUT.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print(
            "OK: checked target adapter compatibility for "
            f"{len(catalog['contracts'])} contracts"
        )
        return 0

    OUTPUT.write_text(content, encoding="utf-8")
    print(f"Rendered {OUTPUT.relative_to(ROOT)} from {CATALOG_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
