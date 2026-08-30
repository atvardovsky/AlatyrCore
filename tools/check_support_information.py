#!/usr/bin/env python3
"""Validate support-state, impact-routing, and generation source contracts."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import jsonschema

from framework_packaging import resolve_framework_files
from support_state import build_support_state, validate_policy


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain an object")
    return value


def main() -> int:
    failures: list[str] = []
    schemas = [
        "alatyr-support-policy.schema.json",
        "alatyr-support-state.schema.json",
        "alatyr-consistency-map.schema.json",
        "alatyr-consistency-map-shard.schema.json",
        "alatyr-relationship-candidates.schema.json",
        "alatyr-support-generation.schema.json",
    ]
    try:
        for name in schemas:
            jsonschema.Draft7Validator.check_schema(load(ROOT / "schemas" / name))
        policy = load(TARGET / ".ai/project/support-policy.json")
        validate_policy(policy)
        jsonschema.validate(
            policy,
            load(ROOT / "schemas/alatyr-support-policy.schema.json"),
        )
    except (OSError, ValueError, AssertionError, jsonschema.SchemaError, jsonschema.ValidationError) as exc:
        failures.append(f"support schema or policy contract is invalid: {exc}")

    required_paths = [
        "framework/support-information.md",
        "templates/target/.ai/project/support-policy.json",
        "templates/target/.ai/support-state.json",
        "templates/target/.ai/project/consistency/areas/_template.json",
        "templates/target/.ai/project/consistency/relationship-candidates.json",
        "templates/target/.ai/assistant/consistency-reverse-index.json",
        "templates/target/.ai/project/support-generation/registry.json",
        "templates/target/.ai/assistant/support-generation-index.json",
        "templates/target/.ai/assistant/flows/support-generation.flow.md",
        "templates/target/.ai/assistant/gates/support-generation.md",
    ]
    for relpath in required_paths:
        if not (ROOT / relpath).is_file():
            failures.append(f"missing support-information surface: {relpath}")

    try:
        rules = load(ROOT / "framework/rule-registry.json")["rules"]
        support_rule = next(
            item for item in rules if item.get("id") == "ALATYR-SUPPORT-001"
        )
        if support_rule.get("canonical_source") != "framework/support-information.md":
            failures.append("ALATYR-SUPPORT-001 canonical owner drifted")
        core_pack_files = resolve_framework_files("core")
        if "support-information.md" not in core_pack_files:
            failures.append("core framework pack omits ALATYR-SUPPORT-001")
        capabilities = load(ROOT / "framework/capabilities.json")["modules"]
        if "support-generation" not in capabilities:
            failures.append("support-generation capability is missing")
        commands = {
            item.get("name") for item in load(ROOT / "tools/tool_commands.json")["commands"]
        }
        for name in [
            "snapshot-support",
            "support-diff",
            "support-delta",
            "change-cost",
            "impact",
            "generate-support",
        ]:
            if name not in commands:
                failures.append(f"tool command manifest omits {name}")
    except (OSError, KeyError, StopIteration, TypeError, AssertionError) as exc:
        failures.append(f"support registry integration is invalid: {exc}")

    try:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            shutil.copytree(TARGET / ".ai", target / ".ai")
            for entrypoint in ["AGENTS.md", "AI_ASSISTANTS.md"]:
                shutil.copy2(TARGET / entrypoint, target / entrypoint)
            subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            generated = build_support_state(target)
            jsonschema.validate(
                generated,
                load(ROOT / "schemas/alatyr-support-state.schema.json"),
            )
            if not generated["files"]:
                failures.append("generated support state is unexpectedly empty")
    except (OSError, subprocess.CalledProcessError, ValueError, jsonschema.ValidationError) as exc:
        failures.append(f"support-state fixture failed: {exc}")

    try:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            (target / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=target, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.email=alatyr@example.invalid",
                    "-c",
                    "user.name=Alatyr Check",
                    "commit",
                    "-qm",
                    "base",
                ],
                cwd=target,
                check=True,
            )
            (target / "AGENTS.md").write_text(
                "# Agent Instructions\n\nSupport change.\n",
                encoding="utf-8",
            )
            (target / "src").mkdir()
            (target / "src/example.py").write_text(
                "print('product change')\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/report_change_cost.py"),
                    "--target",
                    str(target),
                    "--diff-ref",
                    "HEAD",
                    "--json",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                failures.append(f"change-cost fixture failed: {result.stderr.strip()}")
            else:
                report = json.loads(result.stdout)
                summary = report.get("summary", {})
                files = summary.get("files", {}) if isinstance(summary, dict) else {}
                if files.get("support") != 1 or files.get("product") != 1:
                    failures.append("change-cost did not split support/product files")
                if report.get("report_kind") != "target-change-cost":
                    failures.append("change-cost report kind is invalid")
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        failures.append(f"change-cost fixture failed: {exc}")

    try:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            (target / ".ai/project").mkdir(parents=True)
            (target / ".ai/project/support-policy.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "policy_kind": "target-support-policy",
                        "managed_roots": [".ai"],
                        "optional_entrypoints": ["AGENTS.md"],
                        "exclusions": [
                            {
                                "pattern": ".ai/support-state.json",
                                "reason": "self exclusion",
                            }
                        ],
                        "classifications": [
                            {
                                "id": "adapter",
                                "classification": "exact-contract",
                                "patterns": [".ai/**", "AGENTS.md"],
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (target / ".ai/project/rule.md").write_text("rule\n", encoding="utf-8")
            (target / "AGENTS.md").write_text("agent\n", encoding="utf-8")
            state = build_support_state(target)
            (target / ".ai/support-state.json").write_text(
                json.dumps(state, indent=2) + "\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "."], cwd=target, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.email=alatyr@example.invalid",
                    "-c",
                    "user.name=Alatyr Check",
                    "commit",
                    "-qm",
                    "base",
                ],
                cwd=target,
                check=True,
            )
            (target / ".ai/project/rule.md").write_text("changed\n", encoding="utf-8")
            (target / "src").mkdir()
            (target / "src/example.py").write_text("print('x')\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/report_support_delta.py"),
                    "--target",
                    str(target),
                    "--diff-ref",
                    "HEAD",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                failures.append(f"support-delta fixture failed: {result.stderr.strip()}")
            else:
                report = json.loads(result.stdout)
                if report.get("report_kind") != "target-support-delta":
                    failures.append("support-delta report kind is invalid")
                if not isinstance(report.get("delta_digest"), str) or not report[
                    "delta_digest"
                ].startswith("sha256:"):
                    failures.append("support-delta omitted deterministic delta digest")
                summary = report.get("changed_path_summary")
                if not isinstance(summary, dict) or not isinstance(
                    summary.get("digest"), str
                ):
                    failures.append("support-delta omitted changed-path digest")
                if ".ai/project/rule.md" not in report.get("changed_support_paths", []):
                    failures.append("support-delta omitted changed support path")
                if "src/example.py" not in report.get("changed_product_paths", []):
                    failures.append("support-delta omitted changed product path")
                if "framework/support-information.md" in json.dumps(report):
                    failures.append("support-delta should not load portable prose directly")
    except (OSError, subprocess.CalledProcessError, ValueError, json.JSONDecodeError) as exc:
        failures.append(f"support-delta fixture failed: {exc}")

    lifecycle = (ROOT / "tools/check_lifecycle_conformance.py").read_text(encoding="utf-8")
    renderer = (ROOT / "tools/render_context_catalogs.py").read_text(encoding="utf-8")
    if "path.write_bytes(content.encode(\"utf-8\"))" not in lifecycle:
        failures.append("lifecycle context refresh is not byte-stable on Windows")
    if "path.write_bytes(text.encode(\"utf-8\"))" not in renderer:
        failures.append("context catalog renderer is not byte-stable on Windows")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: support information, impact, generation, and Windows digest contracts agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
