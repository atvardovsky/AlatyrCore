#!/usr/bin/env python3
"""Validate the compact target agent entry packet contract."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from agent_entry_packet import PACKET_PATH, build_from_target, render
from target_tool_compat import (
    generated_json_equivalent,
    generation_provenance_errors,
    source_template_provenance_errors,
)
from task_classification_contract import (
    AMBIGUITY_READ_ONLY_MARKER,
    DEFAULT_TASK_CLASS,
    SMALL_TASK_CLASS,
    TASK_CLASSES,
    TASK_CLASSIFICATION_SCHEMA_VERSION,
)


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"{path.relative_to(ROOT)} must contain an object")
    return data


def check_packet(
    packet: dict[str, Any],
    *,
    operation_index_expected: bool,
    cache_capability_expected: bool = True,
    expected_tool: str | None = "render_target_entry_packet.py",
    source_template: bool = False,
) -> list[str]:
    failures: list[str] = []
    if packet.get("schema_version") != 3:
        failures.append("entry packet schema_version must be 3")
    if packet.get("packet_kind") != "target-agent-entry-packet":
        failures.append("entry packet kind must be target-agent-entry-packet")
    if packet.get("path") != PACKET_PATH.as_posix():
        failures.append("entry packet path is invalid")
    provenance_errors = (
        source_template_provenance_errors
        if source_template
        else generation_provenance_errors
    )
    failures.extend(
        provenance_errors(packet.get("generated_by"), expected_tool=expected_tool)
    )

    required_sources = {
        "manifest",
        "context_router",
        "gate_index",
        "action_authorization_policy",
        "support_policy",
        "task_decomposition",
    }
    derived = packet.get("derived_from")
    if not isinstance(derived, dict) or not required_sources <= set(derived):
        failures.append("entry packet does not record all required source digests")
    else:
        for source_id in required_sources:
            source = derived.get(source_id)
            if (
                not isinstance(source, dict)
                or not isinstance(source.get("path"), str)
                or not isinstance(source.get("sha256"), str)
                or len(source["sha256"]) != 64
            ):
                failures.append(f"entry packet source digest is invalid: {source_id}")

    sequence = packet.get("entry_sequence")
    expected_sequence = ["host-preloaded", "bootstrap", "first-use-packet"]
    if (
        not isinstance(sequence, list)
        or [item.get("phase") for item in sequence if isinstance(item, dict)]
        != expected_sequence
    ):
        failures.append("entry packet entry_sequence is missing or unordered")
    else:
        if sequence[1].get("paths") != [".ai/assistant/bootstrap-index.json"]:
            failures.append("entry packet bootstrap phase must load bootstrap-index only")
        if sequence[2].get("paths") != [PACKET_PATH.as_posix()]:
            failures.append("entry packet first-use phase must load itself")

    routing_sources = packet.get("routing_sources")
    if not isinstance(routing_sources, dict):
        failures.append("entry packet must include compact routing_sources")
    else:
        if routing_sources.get("installed_profile_routes") != ".ai/assistant/bootstrap-index.json":
            failures.append("entry packet must route installed profiles through bootstrap")
        if routing_sources.get("full_router") != ".ai/assistant/context-router.json":
            failures.append("entry packet full-router fallback is invalid")

    cache_delivery = packet.get("cache_aware_delivery")
    if not isinstance(cache_delivery, dict):
        failures.append("entry packet must include cache_aware_delivery")
    else:
        capability_index = cache_delivery.get("provider_capability_index")
        if cache_capability_expected:
            if capability_index != ".ai/assistant/assistant-capabilities.json":
                failures.append("entry packet cache capability index is invalid")
        elif capability_index is not None:
            failures.append("kernel packet must not route an absent cache capability index")
        if cache_delivery.get("cache_hit_required") is not False:
            failures.append("entry packet must not require a cache hit")
        if cache_delivery.get("context_window_reduction") is not False:
            failures.append("entry packet must not claim context-window reduction")
        if cache_delivery.get("fallback") != "bounded-context-routing":
            failures.append("entry packet cache fallback must use bounded routing")

    classification = packet.get("task_classification")
    if not isinstance(classification, dict):
        failures.append("entry packet must include task_classification")
    else:
        if classification.get("schema_version") != TASK_CLASSIFICATION_SCHEMA_VERSION:
            failures.append("entry packet task classification schema is invalid")
        if classification.get("classification_order") != TASK_CLASSES:
            failures.append("entry packet task classification order is invalid")
        if classification.get("default_class") != DEFAULT_TASK_CLASS:
            failures.append("entry packet task classification default is invalid")
        if AMBIGUITY_READ_ONLY_MARKER not in str(
            classification.get("ambiguity_behavior", "")
        ):
            failures.append("entry packet task classification ambiguity must stay read-only")
        if classification.get("small_task_overlay") != SMALL_TASK_CLASS:
            failures.append("entry packet small-task class must route small-task overlay")
        if classification.get("expansion_policy") != (
            ".ai/assistant/context-router.json#task_classification.expansion_triggers"
        ):
            failures.append("entry packet task classification expansion policy is invalid")

    operation = packet.get("operation_routing")
    if not isinstance(operation, dict):
        failures.append("entry packet must include operation_routing")
    else:
        if operation_index_expected:
            if operation.get("index") != ".ai/assistant/operation-index.json":
                failures.append("entry packet omitted installed operation index")
        elif operation.get("index") != "not installed":
            failures.append("entry packet should mark absent operation index")

    decomposition = packet.get("task_decomposition")
    if not isinstance(decomposition, dict):
        failures.append("entry packet must include task_decomposition")
    else:
        if decomposition.get("schema_version") != 1:
            failures.append("entry packet task decomposition schema is invalid")
        if decomposition.get("policy") != ".ai/assistant/task-decomposition.json":
            failures.append("entry packet task decomposition policy path is invalid")
        if (
            decomposition.get("plan_template")
            != ".ai/assistant/templates/task-decomposition.md"
        ):
            failures.append("entry packet task decomposition plan template is invalid")
        if decomposition.get("level_range") != "L0-L7":
            failures.append("entry packet task decomposition levels are invalid")
        if "L6" not in decomposition.get("non_delegable_levels", []) or "L7" not in decomposition.get("non_delegable_levels", []):
            failures.append("entry packet must mark L6 and L7 non-delegable")
        if "non-trivial" not in str(decomposition.get("default_behavior", "")):
            failures.append("entry packet task decomposition default must name non-trivial work")
        if decomposition.get("executor_default") != "primary":
            failures.append("entry packet task decomposition executor default must be primary")

    authorization = packet.get("authorization")
    if not isinstance(authorization, dict):
        failures.append("entry packet must include authorization")
    else:
        if authorization.get("policy") != ".ai/assistant/policies/action-authorization.json":
            failures.append("entry packet authorization policy path is invalid")
        if authorization.get("current_scope_required_for") != [
            "modify",
            "commit",
            "publish",
            "live-external",
        ]:
            failures.append("entry packet current-scope phases are invalid")

    delta = packet.get("support_delta_first")
    if not isinstance(delta, dict):
        failures.append("entry packet must include support_delta_first")
    else:
        for required in [
            "tools/alatyr.py support-delta",
            "tools/alatyr.py impact",
            "tools/alatyr.py approval-check",
            ".ai/support-state.json",
        ]:
            if required not in json.dumps(delta, sort_keys=True):
                failures.append(f"entry packet support delta route missing {required}")
        if delta.get("semantic_correctness_proven") is not False:
            failures.append("entry packet support delta route must keep semantic boundary")

    lazy = packet.get("lazy_human_fallbacks")
    for fallback in [
        ".ai/assistant/context-profiles.md",
        ".ai/assistant/module-profile.md",
        ".ai/assistant/help-reference.md",
        ".ai/support-state.json",
    ]:
        if not isinstance(lazy, list) or fallback not in lazy:
            failures.append(f"entry packet missing lazy fallback {fallback}")

    reasoning = packet.get("reasoning_boundary")
    if not isinstance(reasoning, dict) or reasoning.get("logical_integrity") != "required":
        failures.append("entry packet must retain logical reasoning boundary")

    return failures


def main() -> int:
    failures: list[str] = []
    try:
        expected = render(build_from_target(TARGET))
        packet_path = TARGET / PACKET_PATH
        if not packet_path.is_file():
            failures.append(f"missing {packet_path.relative_to(ROOT)}")
        elif not generated_json_equivalent(
            expected,
            packet_path.read_text(encoding="utf-8"),
        ):
            failures.append("entry packet differs from canonical source projection")
        packet = json.loads(expected)
        failures.extend(
            check_packet(
                packet,
                operation_index_expected=True,
                source_template=True,
            )
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, AssertionError) as exc:
        failures.append(str(exc))

    try:
        with tempfile.TemporaryDirectory(prefix="alatyr-entry-packet-") as directory:
            target = Path(directory)
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/scaffold_target_structure.py",
                    "--target",
                    str(target),
                    "--profile",
                    "kernel",
                    "--write",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                failures.append(
                    f"kernel scaffold failed: {result.stderr.strip() or result.stdout.strip()}"
                )
            else:
                packet = load(target / PACKET_PATH)
                failures.extend(
                    check_packet(
                        packet,
                        operation_index_expected=False,
                        cache_capability_expected=False,
                        expected_tool="scaffold_target_structure.py",
                    )
                )
                gates = load(target / ".ai/assistant/gates/index.json")
                gate_entries = gates.get("gates")
                if not isinstance(gate_entries, dict):
                    failures.append("projected kernel gate index must contain gates")
                else:
                    if "contract-artifacts" in gate_entries:
                        failures.append("kernel gate index should omit absent contract-artifacts gate")
    except (OSError, json.JSONDecodeError, AssertionError) as exc:
        failures.append(f"kernel scaffold packet fixture failed: {exc}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: checked compact target agent entry packet and kernel projection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
