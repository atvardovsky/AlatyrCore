#!/usr/bin/env python3
"""Validate source contracts for portable session continuity."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
CONTINUITY_FILES = {
    ".ai/assistant/policies/session-continuity.json",
    ".ai/assistant/context/task-scales/session-continuity.json",
    ".ai/assistant/flows/session-continuity.flow.md",
    ".ai/assistant/gates/session-continuity.md",
    ".ai/assistant/templates/session-continuity-packet.json",
}


def load_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return value


def main() -> int:
    failures: list[str] = []
    try:
        schema = load_object(
            ROOT / "schemas/alatyr-session-continuity-packet.schema.json"
        )
        jsonschema.Draft7Validator.check_schema(schema)
        policy = load_object(
            TARGET / ".ai/assistant/policies/session-continuity.json"
        )
        if policy.get("schema_version") != 3:
            failures.append("continuity policy schema_version must be 3")
        if policy.get("packet_schema") != "alatyr-session-continuity-packet-v3":
            failures.append("continuity policy must use packet schema v3")
        if policy.get("canonical_rule") != "ALATYR-CONTINUITY-001":
            failures.append("continuity policy must route to its canonical rule")
        if policy.get("runtime_directory") != ".ai/.runtime/continuity":
            failures.append("continuity policy runtime directory is invalid")
        resume = policy.get("resume")
        if not isinstance(resume, dict) or resume.get("full_corpus_reload") is not False:
            failures.append("continuity policy must prohibit automatic full-corpus reload")
        if not isinstance(resume, dict) or resume.get(
            "restore_publish_or_live_external"
        ) is not False:
            failures.append("continuity policy must not restore publish or live authority")
        analysis_state = resume.get("analysis_state") if isinstance(resume, dict) else None
        if not isinstance(analysis_state, list) or not {
            "problem-model path and digest",
            "active-projection path, digest, and source-model digest",
            "active-projection measured size",
        }.issubset(set(analysis_state)):
            failures.append("continuity policy must preserve bounded analysis state")

        support_policy = load_object(TARGET / ".ai/project/support-policy.json")
        exclusions = support_policy.get("exclusions")
        patterns = {
            entry.get("pattern")
            for entry in exclusions or []
            if isinstance(entry, dict)
        }
        if ".ai/.runtime/**" not in patterns:
            failures.append("support policy must exclude ephemeral runtime records")

        scaffold = load_object(ROOT / "tools/scaffold_profiles.json")
        kernel = scaffold.get("profiles", {}).get("kernel", {})
        kernel_files = set(kernel.get("template_files", [])) if isinstance(kernel, dict) else set()
        missing_kernel = sorted(CONTINUITY_FILES - kernel_files)
        if missing_kernel:
            failures.append(f"kernel scaffold omits continuity files: {missing_kernel}")

        catalog = load_object(TARGET / ".ai/assistant/operation-catalog.json")
        operations = catalog.get("operations")
        aliases = (
            [
                alias
                for operation in operations
                if isinstance(operation, dict)
                for alias in operation.get("aliases", [])
                if isinstance(alias, str)
            ]
            if isinstance(operations, list)
            else []
        )
        if len(aliases) != len(set(aliases)):
            failures.append("operation aliases must remain unique")
        if "resume Alatyr task" in aliases:
            failures.append("generic resume must not route directly to large-task")
        continuity_operation = next(
            (
                operation
                for operation in operations or []
                if isinstance(operation, dict)
                and operation.get("id") == "session-continuity"
            ),
            None,
        )
        if not isinstance(continuity_operation, dict):
            failures.append("operation catalog omits session-continuity")

        generic = load_object(
            TARGET / ".ai/assistant/assistant-capabilities/generic.json"
        )
        compaction = generic.get("context_compaction")
        if not isinstance(compaction, dict) or compaction.get(
            "fallback"
        ) != "session-continuity":
            failures.append("generic assistant capability omits continuity fallback")

        installer_router = load_object(ROOT / "installer/context-router.json")
        reentry = installer_router.get("session_reentry")
        if (
            not isinstance(reentry, dict)
            or reentry.get("canonical_rule") != "ALATYR-CONTINUITY-001"
            or reentry.get("full_corpus_reload") is not False
            or "newest-request action authorization" not in reentry.get("verify", [])
        ):
            failures.append("installer session reentry contract is incomplete")

        for entrypoint in [ROOT / "AGENTS.md", TARGET / "AGENTS.md"]:
            if "ALATYR-CONTINUITY-001" not in entrypoint.read_text(encoding="utf-8"):
                failures.append(
                    f"{entrypoint.relative_to(ROOT)} omits the continuity rule"
                )
    except (OSError, ValueError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: session continuity source contracts are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
