#!/usr/bin/env python3
"""Check bridge and prepared-run contracts for every assistant surface."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
SURFACES = ROOT / "conformance" / "runs" / "assistant-surfaces.json"
BRIDGES = ROOT / "tools" / "bridge_template_manifest.json"


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    return data


def main() -> int:
    failures: list[str] = []
    try:
        surface_data = load(SURFACES)
        bridge_data = load(BRIDGES)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    surfaces = surface_data.get("surfaces", [])
    bridge_paths = {
        item["path"][len("templates/target/") :]
        for item in bridge_data.get("templates", [])
        if isinstance(item, dict)
        and isinstance(item.get("path"), str)
        and item["path"].startswith("templates/target/")
    }
    known_paths = bridge_paths | {"AGENTS.md"}
    seen_ids: set[str] = set()
    seen_aliases: set[str] = set()

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        for surface in surfaces:
            if not isinstance(surface, dict):
                failures.append("assistant surface entries must be objects")
                continue
            surface_id = surface.get("id")
            if not isinstance(surface_id, str) or not surface_id:
                failures.append("assistant surface id must be a string")
                continue
            if surface_id in seen_ids:
                failures.append(f"duplicate assistant surface id: {surface_id}")
            seen_ids.add(surface_id)
            aliases = surface.get("aliases")
            if not isinstance(aliases, list) or not aliases:
                failures.append(f"assistant surface {surface_id} has no aliases")
                aliases = []
            for alias in aliases:
                if not isinstance(alias, str) or not alias:
                    failures.append(f"assistant surface {surface_id} has invalid alias")
                elif alias in seen_aliases or alias in seen_ids:
                    failures.append(f"duplicate assistant surface alias: {alias}")
                else:
                    seen_aliases.add(alias)

            paths = surface.get("bridge_paths")
            if not isinstance(paths, list) or not paths:
                failures.append(f"assistant surface {surface_id} has no bridge paths")
                paths = []
            for relpath in paths:
                if relpath not in known_paths:
                    failures.append(
                        f"assistant surface {surface_id} has untracked bridge {relpath}"
                    )
                    continue
                path = TARGET / relpath
                if not path.is_file():
                    failures.append(f"assistant surface bridge is missing: {relpath}")
                    continue
                text = path.read_text(encoding="utf-8")
                for required in [
                    "AGENTS.md",
                    ".ai/alatyr.yaml",
                    ".ai/README.md",
                    ".ai/assistant/context-router.json",
                    ".ai/assistant/help.md",
                    ".ai/assistant/flows/operation-routing.flow.md",
                ]:
                    if relpath == "AGENTS.md" and required == "AGENTS.md":
                        continue
                    if required not in text:
                        failures.append(
                            f"assistant surface {surface_id} bridge {relpath} "
                            f"does not route {required}"
                        )
                if "preloaded" not in text.lower():
                    failures.append(
                        f"assistant surface {surface_id} bridge {relpath} "
                        "does not preserve preloaded bootstrap"
                    )

            output = base / surface_id
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/prepare_conformance_run.py",
                    "--output",
                    str(output),
                    "--assistant-surface",
                    surface_id,
                    "--source-commit",
                    "surface-contract",
                    "--fixture",
                    "frontend-app-minimal",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                failures.append(f"could not prepare conformance run for {surface_id}")
                continue
            prompt = output / "prompts" / "frontend-app-minimal.md"
            prompt_text = prompt.read_text(encoding="utf-8")
            for required in [
                f"Assistant surface: `{surface_id}`",
                "assistant-run-report-template.json",
                "not target validation",
                "`context_cost_evidence`",
                "`logical_integrity_evidence`",
            ]:
                if required not in prompt_text:
                    failures.append(
                        f"prepared prompt for {surface_id} missing {required}"
                    )
            if "do not invent validation commands" not in prompt_text.lower():
                failures.append(
                    f"prepared prompt for {surface_id} missing validation safety rule"
                )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: checked compact bridges and prepared conformance runs for "
        f"{len(seen_ids)} assistant surfaces"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
