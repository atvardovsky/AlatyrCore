#!/usr/bin/env python3
"""Render the target-validator finding catalog from validator source calls."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate_target_adapter.py"
MODULES = ROOT / "tools" / "target_adapter_validation"
PROJECT_KNOWLEDGE = ROOT / "tools" / "project_knowledge.py"
JSON_OUTPUT = MODULES / "finding-codes.json"
MARKDOWN_OUTPUT = ROOT / "docs" / "target-adapter-validator-findings.md"
CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]+$")
LEVELS = {"error", "warn", "info"}


def source_paths() -> list[Path]:
    return [VALIDATOR, PROJECT_KNOWLEDGE, *sorted(MODULES.glob("*.py"))]


def literal_code(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value if CODE_PATTERN.fullmatch(node.value) else None
    return None


def json_object_loader_prefix(node: ast.Call, relpath: str) -> str | None:
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "load_json_object":
        return None
    prefix_node: ast.AST | None = node.args[1] if len(node.args) > 1 else None
    if prefix_node is None:
        for keyword in node.keywords:
            if keyword.arg == "code_prefix":
                prefix_node = keyword.value
                break
    if not (
        isinstance(prefix_node, ast.Constant)
        and isinstance(prefix_node.value, str)
        and CODE_PATTERN.fullmatch(prefix_node.value)
    ):
        raise ValueError(
            f"{relpath}:{node.lineno} load_json_object requires a literal finding-code prefix"
        )
    return prefix_node.value


def collect() -> dict[str, Any]:
    entries: dict[str, dict[str, set[str]]] = {}
    for path in source_paths():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relpath = path.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            loader_prefix = json_object_loader_prefix(node, relpath)
            if loader_prefix is not None:
                for suffix in ("INVALID_JSON", "INVALID_SHAPE"):
                    code = f"{loader_prefix}_{suffix}"
                    entry = entries.setdefault(
                        code, {"levels": set(), "sources": set()}
                    )
                    entry["levels"].add("error")
                    entry["sources"].add(relpath)
            finding_constructor = (
                isinstance(node.func, ast.Name) and node.func.id == "KnowledgeFinding"
            )
            code_arg = (
                node.args[1]
                if finding_constructor and len(node.args) > 1
                else node.args[0]
            )
            code = literal_code(code_arg)
            if code is None:
                continue
            level = "dynamic"
            if finding_constructor:
                raw_level = node.args[0]
                if isinstance(raw_level, ast.Constant) and raw_level.value in LEVELS:
                    level = "warning" if raw_level.value == "warn" else str(raw_level.value)
            elif isinstance(node.func, ast.Attribute) and node.func.attr in LEVELS:
                level = "warning" if node.func.attr == "warn" else node.func.attr
            elif isinstance(node.func, ast.Name) and node.func.id == "report":
                level = "configured"
            entry = entries.setdefault(code, {"levels": set(), "sources": set()})
            entry["levels"].add(level)
            entry["sources"].add(relpath)

    families: dict[str, int] = {}
    for code in entries:
        family = code.split("_", 1)[0]
        families[family] = families.get(family, 0) + 1

    return {
        "schema_version": 1,
        "catalog_kind": "target-adapter-validator-findings",
        "generated_from": [path.relative_to(ROOT).as_posix() for path in source_paths()],
        "families": [
            {"id": family, "code_count": count}
            for family, count in sorted(families.items())
        ],
        "finding_codes": [
            {
                "code": code,
                "levels": sorted(values["levels"]),
                "sources": sorted(values["sources"]),
            }
            for code, values in sorted(entries.items())
        ],
    }


def render_markdown(catalog: dict[str, Any]) -> str:
    lines = [
        "# Target Adapter Validator Findings",
        "",
        "This generated reference lists stable finding identifiers emitted by the",
        "portable target-adapter validator. A finding describes structural evidence;",
        "it does not prove project semantics or replace logical integrity review.",
        "",
        "Regenerate both catalog surfaces with:",
        "",
        "```sh",
        "python3 tools/render_target_validator_findings.py",
        "```",
        "",
        f"Catalog entries: {len(catalog['finding_codes'])}",
        "",
        "## Families",
        "",
    ]
    for family in catalog["families"]:
        lines.append(f"- `{family['id']}`: {family['code_count']} codes.")
    lines.extend(
        [
            "",
        "## Codes",
        "",
        ]
    )
    for entry in catalog["finding_codes"]:
        levels = ", ".join(entry["levels"])
        sources = ", ".join(f"`{source}`" for source in entry["sources"])
        lines.extend(
            [
                f"- `{entry['code']}`",
                f"  Level: {levels}. Source: {sources}.",
            ]
        )
    lines.extend(
        [
            "",
            "The machine-readable catalog is",
            "`tools/target_adapter_validation/finding-codes.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when outputs are stale")
    args = parser.parse_args()

    try:
        catalog = collect()
    except (OSError, SyntaxError, ValueError) as exc:
        print(f"FAIL: cannot derive target-validator findings: {exc}", file=sys.stderr)
        return 1
    rendered_json = json.dumps(catalog, indent=2) + "\n"
    rendered_markdown = render_markdown(catalog)
    outputs = [(JSON_OUTPUT, rendered_json), (MARKDOWN_OUTPUT, rendered_markdown)]

    if args.check:
        stale = [
            path
            for path, content in outputs
            if not path.is_file() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            for path in stale:
                print(
                    f"FAIL: stale generated output {path.relative_to(ROOT)}",
                    file=sys.stderr,
                )
            return 1
        print(f"OK: checked {len(catalog['finding_codes'])} target-validator finding codes")
        return 0

    for path, content in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"Rendered {len(catalog['finding_codes'])} target-validator finding codes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
