#!/usr/bin/env python3
"""Validate workspace-mode rule, target template, routing, and safety contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return value


def require(path: Path, snippets: list[str], failures: list[str]) -> None:
    text = " ".join(path.read_text(encoding="utf-8").split())
    for snippet in snippets:
        if " ".join(snippet.split()) not in text:
            failures.append(f"{path.relative_to(ROOT)} missing {snippet}")


def main() -> int:
    failures: list[str] = []
    paths = {
        "rule": ROOT / "framework/workspace-modes.md",
        "index": TARGET / ".ai/project/workspace-modes/README.md",
        "catalog": TARGET / ".ai/project/workspace-modes/catalog.json",
        "root": TARGET / ".ai/project/workspace-modes/root/context.json",
        "mode": TARGET / ".ai/project/workspace-modes/modes/_template/mode.json",
        "intent": TARGET / ".ai/assistant/context/intents/workspace-mode-request.json",
        "flow": TARGET / ".ai/assistant/flows/workspace-mode.flow.md",
        "gate": TARGET / ".ai/assistant/gates/workspace-mode.md",
        "suggestion": TARGET / ".ai/assistant/templates/workspace-mode-suggestion.md",
        "preflight": TARGET / ".ai/assistant/templates/workspace-mode-preflight.md",
        "manifest": TARGET / ".ai/alatyr.yaml",
        "modules": TARGET / ".ai/assistant/module-profile.md",
        "operations": TARGET / ".ai/assistant/operation-catalog.json",
        "router": TARGET / ".ai/assistant/context-router.json",
        "help": TARGET / ".ai/assistant/help.md",
        "install": ROOT / "INSTALL.md",
        "install_flow": ROOT / "installer/assistant-installation.flow.md",
        "readiness": ROOT / "installer/readiness-checklist.md",
        "plan": ROOT / "installer/installation-plan-template.md",
        "validator": ROOT / "tools/validate_target_adapter.py",
    }
    for path in paths.values():
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    data: dict[str, dict[str, Any]] = {}
    for name in ["catalog", "root", "mode", "intent", "operations", "router"]:
        try:
            data[name] = load(paths[name])
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"{paths[name].relative_to(ROOT)} invalid JSON: {exc}")

    require(
        paths["rule"],
        [
            "ALATYR-MODE-001",
            "## Three Independent Facts",
            "Every actual mode has its own directory",
            "Suggestions remain `proposed`",
            "Automatically select only one accepted mode",
            "A mode cannot activate nested adapters",
            "It does not grant approval, write scope, permissions, authority, tool access",
        ],
        failures,
    )
    require(
        paths["flow"],
        [
            "propose zero or more modes",
            "Ask the user when multiple modes match",
            "Load only the selected `mode.json`",
            "Do not guess a mode",
        ],
        failures,
    )
    require(
        paths["gate"],
        [
            "Dependency and scaffold adapters remain passive or provenance-only",
            "Suggestions remain proposed",
            "Mode constraints do not grant write scope",
            "Structural checks cannot prove",
        ],
        failures,
    )
    for name in ["install", "install_flow", "readiness", "plan"]:
        require(paths[name], ["workspace mode"], failures)

    mode = data.get("mode", {})
    constraints = mode.get("constraints")
    no_grant_fields = {
        "grants_write_scope",
        "grants_approval",
        "grants_permissions",
        "grants_authority",
        "grants_tools",
        "activates_nested_adapters",
        "bypasses_gates",
    }
    if not isinstance(constraints, dict) or any(
        constraints.get(field) is not False for field in no_grant_fields
    ):
        failures.append("mode template must explicitly disable every grant surface")

    catalog = data.get("catalog", {})
    selection = catalog.get("selection")
    suggestions = catalog.get("suggestions")
    if not isinstance(selection, dict) or selection.get("ambiguity_behavior") != "ask-user":
        failures.append("catalog must ask the user on selection ambiguity")
    if not isinstance(suggestions, dict) or suggestions.get("automatic_acceptance") is not False:
        failures.append("catalog must prohibit automatic suggestion acceptance")

    capabilities = load(ROOT / "framework/capabilities.json")
    module = capabilities.get("modules", {}).get("workspace-modes")
    if not isinstance(module, dict) or module.get("check_ids") != ["workspace-modes"]:
        failures.append("framework capabilities missing workspace-modes check closure")

    operations = data.get("operations", {}).get("operations", [])
    operation = next(
        (item for item in operations if isinstance(item, dict) and item.get("id") == "workspace-mode"),
        None,
    )
    if not isinstance(operation, dict) or operation.get("required_module") != "workspace-modes":
        failures.append("operation catalog does not gate workspace-mode by module")
    router = data.get("router", {})
    route = router.get("intent_overlays", {}).get("workspace-mode-request")
    if not isinstance(route, dict) or route.get("operation_candidates") != ["workspace-mode"]:
        failures.append("context router does not select workspace-mode operation")
    mode_routing = router.get("workspace_mode_routing")
    if (
        not isinstance(mode_routing, dict)
        or mode_routing.get("ambiguity_behavior") != "ask-user-and-remain-read-only"
    ):
        failures.append("context router lacks safe workspace-mode ambiguity behavior")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("Workspace-mode contracts are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
