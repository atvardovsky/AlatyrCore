#!/usr/bin/env python3
"""Materialize bounded source-context views from canonical repository files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from target_validation_support import is_target_relative_path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = "tools/source-context/index.json"


def contained_source_path(root: Path, relpath: str) -> Path:
    if not is_target_relative_path(relpath):
        raise ValueError("source path must be an exact repository-relative path")
    path = root / relpath
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ValueError("source selection must not traverse symlinks")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("source selection escapes its repository")
    return path


def encoded(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n"


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate source JSON field: {key}")
        result[key] = value
    return result


def source_json(text: str) -> dict[str, Any]:
    def invalid_constant(value: str) -> None:
        raise ValueError(f"invalid source JSON constant: {value}")
    data = json.loads(text, object_pairs_hook=unique_object, parse_constant=invalid_constant)
    if not isinstance(data, dict):
        raise ValueError("indexed source must contain an object")
    return data


def heading_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def markdown_sections(text: str) -> dict[str, list[str]]:
    lines = text.splitlines(keepends=True)
    headings: list[tuple[int, int, str]] = []
    fence: tuple[str, int] | None = None
    for number, line in enumerate(lines):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1] and not line[marker.end():].strip():
                fence = None
            continue
        match = re.match(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if fence is None and match:
            headings.append((number, len(match[1]), heading_id(match[2])))
    sections: dict[str, list[str]] = {}
    for position, (start, depth, name) in enumerate(headings):
        end = next((line for line, level, _ in headings[position + 1:] if level <= depth), len(lines))
        sections.setdefault(name, []).append("".join(lines[start:end]))
    return sections


def selectable_values(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        return [name for name, sections in markdown_sections(text).items() if len(sections) == 1]
    data = source_json(text)
    if len({"checks", "rules", "stages", "entries"}.intersection(data)) != 1:
        raise ValueError("source must have one unambiguous record collection")
    for key in ("checks", "rules", "stages", "entries"):
        if key not in data:
            continue
        records = data.get(key)
        if not isinstance(records, dict if key == "stages" else list):
            raise ValueError(f"invalid {key} collection type")
        if isinstance(records, dict):
            return list(records)
        if isinstance(records, list):
            if key == "entries":
                if any(not isinstance(item, dict) or not isinstance(item.get("owner_refs"), list) or
                       any(not isinstance(owner, str) for owner in item["owner_refs"]) for item in records):
                    raise ValueError("source index owner_refs must be string lists")
                return list(dict.fromkeys(owner for item in records for owner in item.get("owner_refs", [])))
            return [item["id"] for item in records if isinstance(item, dict) and isinstance(item.get("id"), str)]
    raise ValueError("indexed context has no supported record collection")


def project_file(root: Path, relpath: str, values: list[str]) -> dict[str, Any]:
    if not is_target_relative_path(relpath) or not isinstance(values, list) or not values or any(not isinstance(v, str) or not v for v in values):
        raise ValueError("source selection requires a safe path and exact nonempty selectors")
    path = contained_source_path(root, relpath)
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    values = list(dict.fromkeys(values))
    if path.suffix == ".md":
        sections = markdown_sections(text)
        if any(len(sections.get(value, [])) != 1 for value in values):
            raise ValueError(f"unknown or ambiguous source section: {values}")
        content = "\n".join(sections[value][0] for value in values)
    else:
        data = source_json(text)
        if len({"checks", "rules", "stages", "entries"}.intersection(data)) != 1:
            raise ValueError("source must have one unambiguous record collection")
        selected = None
        for key in ("checks", "rules", "stages", "entries"):
            if key not in data:
                continue
            records = data.get(key)
            if not isinstance(records, dict if key == "stages" else list):
                raise ValueError(f"invalid {key} collection type")
            if isinstance(records, dict):
                if not set(values) <= records.keys():
                    raise ValueError(f"unknown {key} selector: {values}")
                selected = {key: {value: records[value] for value in values}}
                if key == "stages" and isinstance(data.get("contracts"), dict):
                    stage_values = selected[key].values()
                    if any(not isinstance(stage, dict) for stage in stage_values):
                        raise ValueError("selected installer stage must be an object")
                    fields = {"outputs": "required_outputs", "evidence": "required_evidence", "completion_checks": "completion_checks"}
                    selected["contracts"] = {
                        kind: {name: data["contracts"][kind][name] for name in dict.fromkeys(
                            name for stage in stage_values for name in stage.get(field, [])
                        )} for kind, field in fields.items()
                    }
                break
            if isinstance(records, list):
                if any(not isinstance(item, dict) for item in records):
                    raise ValueError(f"invalid {key} record")
                ids = [item.get("id") for item in records]
                if any(not isinstance(value, str) for value in ids) or len(ids) != len(set(ids)):
                    raise ValueError(f"ambiguous {key} identities")
                if key == "entries":
                    if any(not isinstance(item.get("owner_refs"), list) or
                           any(not isinstance(owner, str) for owner in item["owner_refs"]) for item in records):
                        raise ValueError("source index owner_refs must be string lists")
                    chosen = [item for item in records if set(values).intersection(item.get("owner_refs", []))]
                    found = {owner for item in chosen for owner in item.get("owner_refs", [])}
                else:
                    chosen = [item for item in records if item["id"] in values]
                    found = {item["id"] for item in chosen}
                if not set(values) <= found:
                    raise ValueError(f"unknown {key} selector: {values}")
                selected = {key: chosen}
                break
        if selected is None:
            raise ValueError("source has no supported indexed collection")
        for key in ("schema_version", "canonical_rule", "checkpoint_contract", "session_reentry"):
            if key in data:
                selected[key] = data[key]
        content = encoded(selected)
    return {"path": relpath, "selectors": values, "source_sha256": hashlib.sha256(raw).hexdigest(),
            "projection_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(), "content": content,
            "authority": "routing-only; canonical owners and dependencies remain required"}


def bootstrap_outputs(root: Path = ROOT) -> dict[str, str]:
    router = source_json((root / "tools/source_context_router.json").read_text(encoding="utf-8"))
    if type(router.get("schema_version")) is not int or router["schema_version"] != 1 or router.get("router_kind") != "alatyr-source-context-router":
        raise ValueError("source router schema or kind is invalid")
    profiles = router.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("source router requires profile objects")
    if any(not isinstance(name, str) or re.fullmatch(r"[a-z][a-z0-9-]*", name) is None or
           not isinstance(profile, dict) or not isinstance(profile.get("check_profile"), str)
           for name, profile in profiles.items()):
        raise ValueError("source profiles require safe stable IDs, objects and check profile names")
    common = {key: value for key, value in router.items() if key != "profiles"}
    outputs = {}
    for name, profile in profiles.items():
        outputs[f"tools/source-context/profiles/{name}.json"] = encoded({
            "schema_version": 1, "source_profile": name, "canonical_source": "tools/source_context_router.json",
            **profile,
        })
    common["profiles"] = {name: {
        "path": f"tools/source-context/profiles/{name}.json", "check_profile": profile["check_profile"],
        "content_sha256": hashlib.sha256(outputs[f"tools/source-context/profiles/{name}.json"].encode()).hexdigest(),
    } for name, profile in profiles.items()}
    outputs[BOOTSTRAP] = encoded(common)
    return outputs


def compact_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Project presentation only; retain the canonical plan for machine checks."""
    context = plan["context_packet"]
    sources: dict[str, dict[str, Any]] = {}
    for item in context["selected_items"]:
        target = sources.setdefault(item["path"], {"path": item["path"], "reasons": []})
        target["reasons"] = list(dict.fromkeys([*target["reasons"], *item["reason"]]))
        if "content_ref" in item:
            target["content_ref"] = item["content_ref"]
    return {
        "schema_version": 1, "report_kind": "alatyr-source-plan-agent-view",
        "full_receipt_sha256": hashlib.sha256(encoded(plan).encode()).hexdigest(),
        "full_receipt": "same invocation without --compact; this view is not acceptance evidence",
        "source_profile": plan["source_profile"], "task_classification": plan["task_classification"],
        "context_readiness": context["readiness"], "selected_sources": list(sources.values()),
        "context_projections": context["context_projections"], "owner_fallbacks": context["owner_fallbacks"],
        "unrouted_requested_paths": context["unrouted_requested_paths"],
        "unresolved_routes": [item for item in context["omitted_candidates"]
                              if item.get("unresolved_selectors") or item.get("unresolved_owner_rule_ids") or item.get("unresolved_paths")],
        "context_budget": {key: value for key, value in context["context_budget"].items() if key not in {"planned", "resolved"}},
        "check_plan": plan["check_plan"], "validation_profiles": plan["validation_profiles"],
        "check_selection_reasons": plan["selection"],
        "delegation": plan["delegation_assessment"],
        "reuse": {"reusable_check_ids": plan["reuse"]["reusable_check_ids"], "evidence": "candidates only; not executed or accepted"},
        "quality_boundary": plan["quality_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        outputs = bootstrap_outputs(ROOT)
        changed = [name for name, text in outputs.items() if not (ROOT / name).is_file() or (ROOT / name).read_bytes() != text.encode("utf-8")]
        if args.write:
            for name in changed:
                path = contained_source_path(ROOT, name)
                if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != ROOT):
                    raise ValueError("source context output must not traverse symlinks")
            for name in changed:
                path = ROOT / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(outputs[name].encode("utf-8"))
        print(encoded({"changed_paths": changed, "write": args.write}), end="")
        return int(bool(changed) and not args.write)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"FAIL: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
