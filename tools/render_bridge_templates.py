#!/usr/bin/env python3
"""Render Alatyr source bridge templates from a manifest.

This is a source-repository maintenance helper. It is not an installation
mechanism and must not be copied into target repositories as a required
command.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tools" / "bridge_template_manifest.json"


class BridgeTemplateError(Exception):
    """Raised when the bridge template manifest is invalid."""


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BridgeTemplateError(f"missing bridge template manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BridgeTemplateError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise BridgeTemplateError(f"{path} must contain a JSON object")
    if data.get("schema_version") != 1:
        raise BridgeTemplateError(f"{path} schema_version must be 1")
    templates = data.get("templates")
    if not isinstance(templates, list) or not templates:
        raise BridgeTemplateError(f"{path} must contain a non-empty templates list")

    seen_paths: set[str] = set()
    for index, template in enumerate(templates):
        if not isinstance(template, dict):
            raise BridgeTemplateError(f"template {index} must be an object")
        relpath = template.get("path")
        lines = template.get("lines")
        if not isinstance(relpath, str) or not relpath:
            raise BridgeTemplateError(f"template {index} must have a path")
        if relpath in seen_paths:
            raise BridgeTemplateError(f"duplicate bridge template path: {relpath}")
        seen_paths.add(relpath)
        if not relpath.startswith("templates/target/"):
            raise BridgeTemplateError(
                f"bridge template path must be under templates/target: {relpath}"
            )
        if not isinstance(lines, list) or not lines:
            raise BridgeTemplateError(f"{relpath} must contain non-empty lines")
        if not all(isinstance(line, str) for line in lines):
            raise BridgeTemplateError(f"{relpath} lines must all be strings")

    return data


def render_templates(data: dict[str, Any]) -> dict[str, str]:
    rendered: dict[str, str] = {}
    for template in data["templates"]:
        rendered[template["path"]] = "\n".join(template["lines"]) + "\n"
    return rendered


def check_templates(rendered: dict[str, str]) -> list[str]:
    failures: list[str] = []
    for relpath, expected in rendered.items():
        path = ROOT / relpath
        if not path.is_file():
            failures.append(f"missing bridge template: {relpath}")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            failures.append(
                f"{relpath} differs from tools/bridge_template_manifest.json"
            )
    return failures


def write_templates(rendered: dict[str, str]) -> list[str]:
    written: list[str] = []
    for relpath, content in rendered.items():
        path = ROOT / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        path.write_text(content, encoding="utf-8")
        written.append(relpath)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check or render Alatyr source bridge templates."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Rewrite tracked source bridge templates from the manifest.",
    )
    args = parser.parse_args()

    try:
        manifest = load_manifest()
        rendered = render_templates(manifest)
    except BridgeTemplateError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.write:
        written = write_templates(rendered)
        if written:
            print("Updated bridge templates:")
            for relpath in written:
                print(f"- {relpath}")
        else:
            print("OK: bridge templates already match manifest")
        return 0

    failures = check_templates(rendered)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print(
            "Run `python3 tools/render_bridge_templates.py --write` to refresh "
            "source bridge templates.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: checked {len(rendered)} generated bridge templates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
