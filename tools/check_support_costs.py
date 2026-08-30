#!/usr/bin/env python3
"""Validate standing support-cost reporting and guardrails."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from report_support_costs import build_installed_report, build_scaffold_report


ROOT = Path(__file__).resolve().parents[1]
MAX_PROFILE_WORDS = {
    "kernel": 95_000,
    "core": 105_000,
    "standard": 125_000,
    "full": 200_000,
}
PROFILE_ORDER = ["kernel", "core", "standard", "full"]


def main() -> int:
    failures: list[str] = []
    reports = {
        profile: build_scaffold_report(profile)
        for profile in PROFILE_ORDER
    }
    default_report = build_scaffold_report()
    recommendation = default_report.get("profile_recommendation", {})
    if default_report.get("profile") != "kernel":
        failures.append("default support-cost report must start from kernel profile")
    if recommendation.get("default") != "kernel":
        failures.append("support-cost recommendation must name kernel as default")
    if recommendation.get("escalation_order") != PROFILE_ORDER:
        failures.append("support-cost recommendation escalation order is invalid")
    if "cheapest sufficient profile" not in str(recommendation.get("policy", "")):
        failures.append("support-cost recommendation must name cheapest sufficient profile")
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
