#!/usr/bin/env python3
"""Prepare diagram-discussion conformance prompts for assistant surfaces."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "conformance" / "operations" / "diagram-discussion.json"
SURFACES = ROOT / "conformance" / "runs" / "assistant-surfaces.json"


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def string_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{FIXTURE} must contain a non-empty string list {key}")
    return value


def surface_ids(data: dict[str, Any]) -> list[str]:
    surfaces = data.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        raise ValueError(f"{SURFACES} must contain a non-empty surfaces list")
    result: list[str] = []
    for item in surfaces:
        surface_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(surface_id, str) or not surface_id:
            raise ValueError(f"{SURFACES} contains an invalid surface ID")
        result.append(surface_id)
    return result


def render_prompt(fixture: dict[str, Any], surface_id: str) -> str:
    requirements = "\n".join(
        f"- {item}" for item in string_list(fixture, "required_for_every_surface")
    )
    fields = "\n".join(
        f"- `{item}`" for item in string_list(fixture, "required_result_fields")
    )
    allowed = ", ".join(string_list(fixture, "allowed_actions"))
    return f"""# Diagram Discussion Conformance

Assistant surface: `{surface_id}`
Operation: `{fixture['operation']}`
Allowed actions: `{allowed}`

Run this request against an already installed target adapter:

> {fixture['request']}

Do not install, update, or repair the adapter during this fixture. Do not
change repository files. Treat rendering support as unknown unless the
selected target capability entry has current evidence.
Always return a pure ASCII diagram that follows the target width and
readability contract. Native rendering or an artifact may supplement it but
must not replace it.

Required behavior:

{requirements}

Return a JSON object with these fields:

{fields}

Also report the target repository revision, loaded adapter paths, client
sections, observed bytes, estimated tokens, hidden client context, soft and
hard budget state, client version/freshness evidence, validation, and residual
risk. Shape the result from
`conformance/operations/diagram-discussion-result-template.json`. This prompt tests
runtime assistant behavior; source fixture validation alone does not prove
that the client rendered or attached anything.
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare diagram-discussion prompts for supported assistants."
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--assistant-surface", action="append", default=[])
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        fixture = load_object(FIXTURE)
        known_surfaces = surface_ids(load_object(SURFACES))
        if fixture.get("fixture_kind") != "assistant-operation-conformance":
            raise ValueError("diagram fixture kind is invalid")
        if fixture.get("operation") != "diagram-discussion":
            raise ValueError("diagram fixture operation is invalid")
        selected = args.assistant_surface or known_surfaces
        unknown = sorted(set(selected) - set(known_surfaces))
        if unknown:
            raise ValueError(f"unknown assistant surfaces: {unknown}")
        rendered = {
            surface_id: render_prompt(fixture, surface_id)
            for surface_id in selected
        }
        if any(re.search(r"\{[A-Z0-9_]+\}", text) for text in rendered.values()):
            raise ValueError("rendered prompt contains unresolved placeholders")
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.check:
        print(f"OK: prepared diagram conformance prompts for {len(rendered)} surfaces")
        return 0
    if args.output is None:
        parser.error("--output is required unless --check is used")
    args.output.mkdir(parents=True, exist_ok=True)
    for surface_id, content in rendered.items():
        path = args.output / f"{surface_id}.md"
        if path.exists() and not args.overwrite:
            print(f"FAIL: {path} exists; use --overwrite", file=sys.stderr)
            return 1
        path.write_text(content, encoding="utf-8")
    print(f"OK: wrote {len(rendered)} diagram conformance prompts to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
