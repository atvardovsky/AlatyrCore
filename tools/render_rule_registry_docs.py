#!/usr/bin/env python3
"""Render human rule-registry surfaces from the machine-readable registry."""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "framework" / "rule-registry.json"
REGISTRY_DOC = ROOT / "framework" / "rule-registry.md"
OWNERSHIP_DOC = ROOT / "framework" / "rule-ownership.md"


def load_registry() -> dict[str, Any]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("rule registry must be an object")
    if not isinstance(data.get("rules"), list):
        raise ValueError("rule registry must contain rules")
    if not isinstance(data.get("category_owners"), list):
        raise ValueError("rule registry must contain category_owners")
    return data


def wrapped(prefix: str, value: str) -> list[str]:
    return textwrap.wrap(
        value,
        width=79,
        initial_indent=prefix,
        subsequent_indent="",
        break_long_words=False,
        break_on_hyphens=False,
    )


def render_registry(data: dict[str, Any]) -> str:
    categories = [owner["category"] for owner in data["category_owners"]]
    lines = [
        "# Rule Registry",
        "",
        "This file is generated from `framework/rule-registry.json`. Edit the JSON",
        "registry and the canonical owner document, then run",
        "`python3 tools/render_rule_registry_docs.py`.",
        "",
        "Rule IDs let target adapters and migration records reference stable process",
        "contracts without copying complete policy text. Canonical semantics remain in",
        "the `canonical_source` owner named by each registry entry. Category routing",
        "owners group related rules but do not replace those semantic owners.",
        "`framework/rule-ownership.md` renders both mappings from this registry for",
        "maintainers and tools; it is not an independent policy source.",
        "",
        "## Rule ID Format",
        "",
        "```text",
        "ALATYR-<CATEGORY>-<NNN>",
        "```",
        "",
        "Registered categories:",
        "",
        *[f"- `{category}`" for category in categories],
        "",
        "Do not reuse an ID for a different meaning. Record material rule changes in",
        "the changelog and release migration note.",
        "",
        "## Registry Entries",
        "",
    ]
    for rule in data["rules"]:
        source = rule["canonical_source"]
        target_source = f".ai/{source}"
        lines.extend(
            [
                f"Rule ID: `{rule['id']}`",
                f"Canonical source: `{target_source}`",
                *wrapped("Commitment: ", rule["summary"]),
                *wrapped("Applies to: ", ", ".join(rule["applies_to"]) + "."),
                *wrapped("Enforcement: ", rule["enforcement"] + "."),
                "",
            ]
        )
    lines.extend(
        [
            "## Use In Target Adapters",
            "",
            "Target adapters may reference rule IDs in migration notes, approval",
            "records, recheck reports, module profiles, bridge capability records,",
            "checker rules, and local deviations. Record the affected rule ID whenever",
            "a target adapter intentionally narrows a portable rule.",
            "",
        ]
    )
    return "\n".join(lines)


def render_ownership(data: dict[str, Any]) -> str:
    lines = [
        "# Rule Ownership",
        "",
        "This file is generated from `framework/rule-registry.json`. Per-rule canonical",
        "owners define rule semantics. Category routing owners group related rules for",
        "maintainers and tools but do not become additional semantic owners.",
        "Derived documents should reference the owner or rule ID and avoid copying",
        "the complete policy language.",
        "",
        "## Ownership Rules",
        "",
        "- Change the canonical owner document before changing a rule summary.",
        "- Keep installer, template, bridge, and help wording as short references.",
        "- Keep owner front matter aligned with registered IDs and dependencies.",
        "- Record material contract changes in the changelog and migration evidence.",
        "",
        "## Category Routing Owners",
        "",
    ]
    for owner in data["category_owners"]:
        target_owner = f".ai/{owner['owner']}"
        lines.extend(
            [
                f"Category: `{owner['category']}`",
                f"Routing owner: `{target_owner}`",
                "Rule IDs: " + ", ".join(f"`{item}`" for item in owner["rule_ids"]),
                *wrapped("Derived surfaces: ", ", ".join(owner["derived_surfaces"]) + "."),
                "",
            ]
        )
    lines.extend(
        [
            "## Rule Canonical Owners",
            "",
        ]
    )
    for rule in data["rules"]:
        target_source = f".ai/{rule['canonical_source']}"
        lines.extend(
            [
                f"Rule: `{rule['id']}`",
                f"Canonical owner: `{target_source}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Change Protocol",
            "",
            "1. Update the owning framework document and its `alatyr_doc` metadata.",
            "2. Update `framework/rule-registry.json`.",
            "3. Regenerate this file and `framework/rule-registry.md`.",
            "4. Update affected installer, target, checker, and conformance surfaces.",
            "5. Keep assistant bridges as pointers.",
            "6. Record behavioral changes in `CHANGELOG.md` and migration evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated docs are stale")
    args = parser.parse_args()
    try:
        data = load_registry()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    outputs = [
        (REGISTRY_DOC, render_registry(data)),
        (OWNERSHIP_DOC, render_ownership(data)),
    ]
    if args.check:
        stale = [
            path
            for path, content in outputs
            if not path.is_file() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            for path in stale:
                print(f"FAIL: stale generated rule surface {path.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print("OK: checked generated rule registry and ownership documentation")
        return 0


    for path, content in outputs:
        path.write_text(content, encoding="utf-8")
    print("Rendered rule registry and ownership documentation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
