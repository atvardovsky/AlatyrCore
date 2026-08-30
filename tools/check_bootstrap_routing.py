#!/usr/bin/env python3
"""Validate compact bootstrap generation and routed target gate contracts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from agent_entry_packet import (
    PACKET_PATH,
    build_from_target as build_entry_packet,
    render as render_entry_packet,
)
from bootstrap_index import BOOTSTRAP_PATH, build_from_target, render
from context_catalog import word_count
from target_tool_compat import generated_json_equivalent, generation_provenance_errors


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
ROUTER_PATH = TARGET / ".ai/assistant/context-router.json"
GATE_INDEX_PATH = TARGET / ".ai/assistant/gates/index.json"
FULL_CHECKLIST = ".ai/assistant/gates/checklist.md"


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    return data


def main() -> int:
    failures: list[str] = []
    try:
        router = load_object(ROUTER_PATH)
        gates = load_object(GATE_INDEX_PATH)
        expected = render(build_from_target(TARGET))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot load bootstrap routing contracts: {exc}", file=sys.stderr)
        return 1

    bootstrap_path = TARGET / BOOTSTRAP_PATH
    if not bootstrap_path.is_file():
        failures.append(f"missing generated bootstrap index: {BOOTSTRAP_PATH.as_posix()}")
    elif not generated_json_equivalent(
        expected,
        bootstrap_path.read_text(encoding="utf-8"),
    ):
        failures.append("bootstrap index differs from its canonical source projection")
    else:
        bootstrap_index = load_object(bootstrap_path)
        failures.extend(
            generation_provenance_errors(
                bootstrap_index.get("generated_by"),
                expected_tool="render_target_bootstrap_index.py",
            )
        )
        entry_packet = bootstrap_index.get("agent_entry_packet")
        if (
            not isinstance(entry_packet, dict)
            or entry_packet.get("path") != PACKET_PATH.as_posix()
            or entry_packet.get("load_after") != BOOTSTRAP_PATH.as_posix()
        ):
            failures.append("bootstrap index does not route the agent entry packet")

    packet_path = TARGET / PACKET_PATH
    try:
        expected_packet = render_entry_packet(build_entry_packet(TARGET))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(f"cannot derive agent entry packet: {exc}")
        expected_packet = ""
    if not packet_path.is_file():
        failures.append(f"missing generated agent entry packet: {PACKET_PATH.as_posix()}")
    elif expected_packet and not generated_json_equivalent(
        expected_packet,
        packet_path.read_text(encoding="utf-8"),
    ):
        failures.append("agent entry packet differs from its canonical source projection")

    bootstrap = router.get("bootstrap_context")
    if bootstrap != [BOOTSTRAP_PATH.as_posix()]:
        failures.append("router bootstrap_context must contain only bootstrap-index.json")
    budget = router.get("context_budgets", {}).get("bootstrap", {})
    soft_max = budget.get("soft_max_words") if isinstance(budget, dict) else None
    static_words = word_count(TARGET / "AGENTS.md") + word_count(bootstrap_path)
    if not isinstance(soft_max, int) or static_words > soft_max:
        failures.append(
            f"static bootstrap uses {static_words} words and exceeds soft limit {soft_max}"
        )

    if gates.get("schema_version") != 1 or gates.get("index_kind") != "target-gate-index":
        failures.append("gate index has an unsupported contract")
    gate_entries = gates.get("gates")
    gate_entries = gate_entries if isinstance(gate_entries, dict) else {}
    gate_paths: dict[str, str] = {}
    for gate_id, entry in gate_entries.items():
        path = entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(path, str) or not (TARGET / path).is_file():
            failures.append(f"gate {gate_id} points to a missing target path: {path}")
            continue
        gate_paths[gate_id] = path

    profile_defaults = gates.get("profile_defaults")
    profile_defaults = profile_defaults if isinstance(profile_defaults, dict) else {}
    profile_index = router.get("profile_index")
    profile_index = profile_index if isinstance(profile_index, dict) else {}
    for profile_id, index_entry in profile_index.items():
        descriptor = index_entry.get("descriptor") if isinstance(index_entry, dict) else None
        if not isinstance(descriptor, str):
            failures.append(f"profile {profile_id} has no descriptor")
            continue
        profile = load_object(TARGET / descriptor)
        required = profile.get("required_context")
        required = required if isinstance(required, list) else []
        conditional = profile.get("conditional_context")
        conditional = conditional if isinstance(conditional, list) else []
        conditional_paths = {
            entry.get("path")
            for entry in conditional
            if isinstance(entry, dict)
            and isinstance(entry.get("path"), str)
            and isinstance(entry.get("when"), str)
            and entry["when"]
        }
        routed_context = set(required) | conditional_paths
        if FULL_CHECKLIST in required:
            failures.append(f"profile {profile_id} loads the full checklist eagerly")
        defaults = profile_defaults.get(profile_id)
        if not isinstance(defaults, list) or not defaults:
            failures.append(f"profile {profile_id} has no default gate route")
            continue
        expected_gate_paths = {gate_paths.get(gate_id) for gate_id in defaults}
        missing = sorted(
            path for path in expected_gate_paths if path and path not in routed_context
        )
        if missing:
            failures.append(f"profile {profile_id} omits routed gates: {missing}")
        unknown = sorted(gate_id for gate_id in defaults if gate_id not in gate_paths)
        if unknown:
            failures.append(f"profile {profile_id} references unknown gates: {unknown}")

    docs = load_object(TARGET / profile_index["docs-local"]["descriptor"])
    if ".ai/framework/testing-guidance.md" in docs.get("required_context", []):
        failures.append("docs-local must not load testing guidance eagerly")
    code = load_object(TARGET / profile_index["code-local"]["descriptor"])
    if ".ai/framework/testing-guidance.md" in code.get("required_context", []):
        failures.append("code-local must keep general testing guidance conditional")

    with tempfile.TemporaryDirectory(prefix="alatyr-bootstrap-") as directory:
        target = Path(directory)
        result = subprocess.run(
            [
                sys.executable,
                "tools/scaffold_target_structure.py",
                "--target",
                str(target),
                "--profile",
                "core",
                "--write",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            failures.append(f"core scaffold failed: {result.stderr.strip() or result.stdout.strip()}")
        elif not (target / BOOTSTRAP_PATH).is_file():
            failures.append("core scaffold did not generate bootstrap-index.json")
        elif not (target / PACKET_PATH).is_file():
            failures.append("core scaffold did not generate entry-packet.json")
        else:
            try:
                scaffold_expected = render(build_from_target(target))
                scaffold_packet_expected = render_entry_packet(build_entry_packet(target))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                failures.append(f"scaffold bootstrap sources are invalid: {exc}")
            else:
                if not generated_json_equivalent(
                    scaffold_expected,
                    (target / BOOTSTRAP_PATH).read_text(encoding="utf-8"),
                ):
                    failures.append("core scaffold bootstrap is not deterministic")
                if not generated_json_equivalent(
                    scaffold_packet_expected,
                    (target / PACKET_PATH).read_text(encoding="utf-8"),
                ):
                    failures.append("core scaffold entry packet is not deterministic")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: compact bootstrap, routed gates, profile defaults, and core scaffold agree "
        f"({static_words} static words)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
