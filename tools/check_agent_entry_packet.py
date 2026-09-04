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
    TARGET_REQUIRED_EXPANSION_TRIGGERS,
    TASK_CLASSES,
    TASK_CLASSIFICATION_SCHEMA_VERSION,
    missing_required_values,
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
    if packet.get("schema_version") != 1:
        failures.append("entry packet schema_version must be 1")
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

    recommendation = packet.get("profile_recommendation")
    if not isinstance(recommendation, dict):
        failures.append("entry packet must include profile_recommendation")
    else:
        if recommendation.get("default_install_profile") != "kernel":
            failures.append("entry packet must recommend kernel by default")
        if recommendation.get("escalation_order") != [
            "kernel",
            "core",
            "standard",
            "full",
        ]:
            failures.append("entry packet profile escalation order is invalid")
        if "cheapest sufficient profile" not in str(
            recommendation.get("decision_policy", "")
        ):
            failures.append("entry packet recommendation must name cheapest sufficient profile")

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

    profile_routes = packet.get("profile_routes")
    if not isinstance(profile_routes, dict) or "code-local" not in profile_routes:
        failures.append("entry packet must include bounded profile routes")
    else:
        code = profile_routes["code-local"]
        if not isinstance(code, dict):
            failures.append("code-local packet route must be an object")
        else:
            for field in ["required_context", "default_gate_paths", "final_evidence"]:
                values = code.get(field)
                if not isinstance(values, list) or not values:
                    failures.append(f"code-local packet route missing {field}")

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
        classes = classification.get("classes")
        if not isinstance(classes, dict) or SMALL_TASK_CLASS not in classes:
            failures.append("entry packet task classification must expose small-task")
        else:
            small = classes[SMALL_TASK_CLASS]
            if (
                not isinstance(small, dict)
                or small.get("task_scale_overlay") != SMALL_TASK_CLASS
            ):
                failures.append("entry packet small-task class must route small-task overlay")
        triggers = classification.get("expansion_triggers")
        if not isinstance(triggers, list) or missing_required_values(
            triggers, TARGET_REQUIRED_EXPANSION_TRIGGERS
        ):
            failures.append("entry packet task classification expansion triggers are incomplete")

    operation = packet.get("operation_routing")
    if not isinstance(operation, dict):
        failures.append("entry packet must include operation_routing")
    else:
        routes = operation.get("operation_routes")
        if operation_index_expected:
            if not isinstance(routes, dict) or "adapter-health" not in routes:
                failures.append("entry packet omitted installed operation routes")
        elif routes != {}:
            failures.append("entry packet should omit operation routes when index is absent")

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
        if decomposition.get("level_order") != [
            "L0",
            "L1",
            "L2",
            "L3",
            "L4",
            "L5",
            "L6",
            "L7",
        ]:
            failures.append("entry packet task decomposition levels are invalid")
        if "L6" not in decomposition.get("non_delegable_levels", []) or "L7" not in decomposition.get("non_delegable_levels", []):
            failures.append("entry packet must mark L6 and L7 non-delegable")
        if "non-trivial" not in str(decomposition.get("default_behavior", "")):
            failures.append("entry packet task decomposition default must name non-trivial work")
        executor = decomposition.get("executor_selection")
        if not isinstance(executor, dict) or executor.get("default") != "primary":
            failures.append("entry packet task decomposition executor default must be primary")

    authorization = packet.get("authorization")
    if not isinstance(authorization, dict):
        failures.append("entry packet must include authorization")
    else:
        modes = authorization.get("allowed_action_modes")
        for mode in [
            "read-only",
            "docs-only",
            "adapter-only",
            "code-and-tests",
            "full-with-approval",
        ]:
            if not isinstance(modes, dict) or mode not in modes:
                failures.append(f"entry packet missing allowed action mode {mode}")
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
        if "never prove semantic correctness" not in str(delta.get("routing_policy", "")):
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

    if "Logical integrity" not in str(packet.get("reasoning_boundary", "")):
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
                    for route in packet.get("profile_routes", {}).values():
                        if isinstance(route, dict):
                            for gate_path in route.get("default_gate_paths", []):
                                if isinstance(gate_path, str) and not (target / gate_path).is_file():
                                    failures.append(
                                        f"kernel packet routes missing gate path {gate_path}"
                                    )
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
