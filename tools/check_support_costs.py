#!/usr/bin/env python3
"""Validate standing support-cost reporting and guardrails."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from report_support_costs import (
    assistant_surface_summary,
    build_installed_report,
    build_scaffold_report,
    module_costs,
)


ROOT = Path(__file__).resolve().parents[1]
MAX_PROFILE_WORDS = {
    "kernel": 95_000,
    "core": 105_000,
    "standard": 125_000,
    "full": 200_000,
}
PROFILE_ORDER = ["kernel", "core", "standard", "full"]


def require_runtime_scope(
    failures: list[str], report: dict[str, object], label: str
) -> None:
    scopes = report.get("cost_scopes")
    if not isinstance(scopes, dict):
        failures.append(f"{label} report is missing cost_scopes")
        return
    runtime = scopes.get("runtime_context")
    if not isinstance(runtime, dict):
        failures.append(f"{label} report is missing runtime_context cost scope")
        return
    if runtime.get("standing_support_cost_is_not_runtime_context") is not True:
        failures.append(
            f"{label} runtime cost scope must state that standing support cost "
            "is not runtime context"
        )


def main() -> int:
    failures: list[str] = []
    cached_assistant_surfaces = assistant_surface_summary()
    cached_module_costs = module_costs()
    reports = {
        profile: build_scaffold_report(
            profile,
            assistant_surface_report=cached_assistant_surfaces,
            optional_module_cost_report=cached_module_costs,
        )
        for profile in PROFILE_ORDER
    }
    default_report = reports["kernel"]
    recommendation = default_report.get("profile_recommendation", {})
    if default_report.get("profile") != "kernel":
        failures.append("default support-cost report must start from kernel profile")
    if recommendation.get("default") != "kernel":
        failures.append("support-cost recommendation must name kernel as default")
    if recommendation.get("escalation_order") != PROFILE_ORDER:
        failures.append("support-cost recommendation escalation order is invalid")
    if "cheapest sufficient profile" not in str(recommendation.get("policy", "")):
        failures.append("support-cost recommendation must name cheapest sufficient profile")
    require_runtime_scope(failures, default_report, "kernel scaffold")
    selected_projection = default_report.get("cost_scopes", {}).get(
        "selected_support_projection"
    )
    if not isinstance(selected_projection, dict):
        failures.append("scaffold report is missing selected_support_projection")
    elif selected_projection.get("files") != default_report["combined_support"]["files"]:
        failures.append("selected support projection file count is out of sync")
    managed_inventory = default_report.get("cost_scopes", {}).get(
        "complete_managed_inventory"
    )
    if not isinstance(managed_inventory, dict):
        failures.append("scaffold report is missing complete_managed_inventory")
    elif managed_inventory.get("present") is not True:
        failures.append("template managed inventory must be present")
    words = {
        profile: report["combined_support"]["words"]
        for profile, report in reports.items()
    }
    files = {
        profile: report["combined_support"]["files"]
        for profile, report in reports.items()
    }
    if not all(
        files[left] < files[right]
        for left, right in zip(PROFILE_ORDER, PROFILE_ORDER[1:])
    ):
        failures.append(f"support profile file counts are not monotonic: {files}")
    if not all(
        words[left] < words[right]
        for left, right in zip(PROFILE_ORDER, PROFILE_ORDER[1:])
    ):
        failures.append(f"support profile word counts are not monotonic: {words}")
    for profile, maximum in MAX_PROFILE_WORDS.items():
        if words[profile] > maximum:
            failures.append(
                f"{profile} standing support words exceed guardrail "
                f"{maximum}: {words[profile]}"
            )

    core = reports["core"]
    if core["operation_surface"]["projected_operation_count"] != 0:
        failures.append("core support cost must not include projected operations")
    standard = reports["standard"]
    if standard["operation_surface"]["projected_operation_count"] <= 0:
        failures.append("standard support cost must include projected operations")
    surfaces = reports["full"]["assistant_surfaces"]
    if surfaces["known_surfaces"] < 10:
        failures.append("assistant surface registry unexpectedly shrank")
    if (
        surfaces["unique_capability_payloads_without_identity"]
        > surfaces["capability_template_files"]
    ):
        failures.append("assistant capability payload summary is invalid")

    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "target"
        target.mkdir()
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "scaffold_target_structure.py"),
                "--target",
                str(target),
                "--profile",
                "core",
                "--write",
            ],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            failures.append(
                "core scaffold support-cost smoke setup failed: "
                + (result.stderr.strip() or result.stdout.strip())
            )
        else:
            installed = build_installed_report(target)
            require_runtime_scope(failures, installed, "installed")
            installed_scope = installed.get("cost_scopes", {}).get(
                "installed_support_files"
            )
            if not isinstance(installed_scope, dict):
                failures.append("installed report is missing installed_support_files")
            elif installed_scope.get("files") != installed["support_surfaces"]["files"]:
                failures.append("installed support file scope is out of sync")
            installed_inventory = installed.get("cost_scopes", {}).get(
                "managed_inventory"
            )
            if not isinstance(installed_inventory, dict):
                failures.append("installed report is missing managed_inventory")
            elif installed_inventory.get("present") is not True:
                failures.append("installed report did not find managed inventory")
            if not installed["support_policy_present"]:
                failures.append("installed support-cost report did not find support policy")
            installed_files = installed["support_surfaces"]["files"]
            if installed_files != files["core"]:
                failures.append(
                    "installed core support file count differs from source projection: "
                    f"{installed_files} != {files['core']}"
                )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: checked standing support-cost reports "
        f"kernel={files['kernel']} core={files['core']} "
        f"standard={files['standard']} full={files['full']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
