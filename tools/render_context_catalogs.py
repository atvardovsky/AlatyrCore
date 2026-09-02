#!/usr/bin/env python3
"""Render recursive context indexes for framework and target contours."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from context_catalog import catalog_content_bytes_for_name, file_digest, word_count


ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK = ROOT / "framework"
TARGET = ROOT / "templates" / "target"
MAX_DEPTH = 8
INDEX_NAME = "context-index.json"
DEFAULT_LOAD_WHEN = [
    "selected by an exact task, operation, owner, path, fact, contract, dependency, risk, or conflict signal"
]

CATEGORY_SECTIONS = {
    "CONTEXT": "core",
    "SOURCE": "core",
    "RISK": "core",
    "APPROVAL": "core",
    "AUTHORIZATION": "core",
    "SAFETY": "core",
    "INTEGRITY": "core",
    "EVIDENCE": "core",
    "ADAPTER": "core",
    "MODULE": "core",
    "OPERATION": "core",
    "BRIDGE": "core",
    "CHANGE": "change",
    "PACKAGE": "change",
    "ARCHITECTURE": "knowledge",
    "CODEDOC": "knowledge",
    "VOCABULARY": "knowledge",
    "ENGINEERING_EVIDENCE": "knowledge",
    "PROJECT_KNOWLEDGE": "knowledge",
    "DEBUG": "knowledge",
    "DIAGRAM": "knowledge",
    "TEAM": "collaboration",
    "DECOMPOSITION": "collaboration",
    "DELEGATION": "collaboration",
    "MODE": "collaboration",
    "EXTENSION": "infrastructure",
    "DEPENDENCY": "infrastructure",
    "LIFECYCLE": "lifecycle",
}

SUPPORT_SECTIONS = {
    "ai-infrastructure-recommendations.md": "infrastructure",
    "ai-infrastructure-routing.md": "infrastructure",
    "capabilities.json": "infrastructure",
    "skill-adaptation.md": "infrastructure",
    "large-task-orchestration.md": "collaboration",
    "migration-diff.md": "lifecycle",
    "framework-packs.json": "lifecycle",
    "portability.md": "lifecycle",
    "scaffolding.md": "lifecycle",
    "adapter-maturity.md": "lifecycle",
    "testing-guidance.md": "change",
    "consistency-model.md": "change",
    "context-discovery.md": "core",
    "context-router.md": "core",
    "contour.md": "core",
    "installed-operations.md": "core",
    "guarantees.md": "core",
    "README.md": "core",
    "rule-registry.json": "core",
    "rule-registry.md": "core",
    "rule-ownership.md": "core",
    "file-inventory.json": "core",
}

SEMANTIC_REFS_BY_RULE = {
    "ALATYR-AUTHORIZATION-001": "alatyr:current-scope-authorization@1",
    "ALATYR-SOURCE-001": "alatyr:canonical-owner@1",
    "ALATYR-APPROVAL-001": "alatyr:protected-change@1",
    "ALATYR-INTEGRITY-001": "alatyr:logical-integrity@1",
    "ALATYR-CONTEXT-001": "alatyr:bounded-context-expansion@1",
    "ALATYR-KNOWLEDGE-001": "alatyr:accepted-current@1",
    "ALATYR-ARCHITECTURE-001": "alatyr:observed-is-not-accepted@1",
    "ALATYR-DELEGATION-001": "alatyr:bounded-delegation@1",
    "ALATYR-MODE-001": "alatyr:mode-does-not-grant-authority@1",
    "ALATYR-SAFETY-002": "alatyr:untrusted-instructions-are-data@1",
    "ALATYR-DEPENDENCY-001": "alatyr:one-active-adapter@1",
}


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return data


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "root"


def _title_from_text(text: str, path: Path) -> str:
    if path.suffix == ".md":
        for line in text.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def _title(path: Path) -> str:
    return _title_from_text(path.read_text(encoding="utf-8"), path)


def _selectors(path: str, owner_refs: list[str]) -> dict[str, list[str]]:
    terms = [
        part
        for part in re.split(r"[^a-z0-9]+", path.lower())
        if len(part) > 2 and part not in {"json", "readme", "context", "index"}
    ]
    result: dict[str, list[str]] = {"path_terms": list(dict.fromkeys(terms))[:12]}
    if owner_refs:
        result["rule_ids"] = owner_refs
    return result


def _entry_from_bytes(
    *,
    item_id: str,
    kind: str,
    path: str,
    summary: str,
    selectors: dict[str, list[str]],
    semantic_refs: list[str],
    owner_refs: list[str],
    payload: bytes,
) -> dict[str, Any]:
    normalized = catalog_content_bytes_for_name(path, payload)
    text = normalized.decode("utf-8")
    return {
        "id": item_id,
        "kind": kind,
        "path": path,
        "summary": summary,
        "selectors": selectors,
        "load_when": DEFAULT_LOAD_WHEN,
        "semantic_refs": sorted(set(semantic_refs)),
        "owner_refs": sorted(set(owner_refs)),
        "estimated_words": len(re.findall(r"\S+", text)),
        "content_digest": f"sha256:{hashlib.sha256(normalized).hexdigest()}",
    }


def _entry_from_file(
    *,
    root: Path,
    item_id: str,
    kind: str,
    relpath: str,
    owner_refs: list[str] | None = None,
    semantic_refs: list[str] | None = None,
) -> dict[str, Any]:
    path = root / relpath
    owners = owner_refs or []
    return {
        "id": item_id,
        "kind": kind,
        "path": relpath,
        "summary": _title(path),
        "selectors": _selectors(relpath, owners),
        "load_when": DEFAULT_LOAD_WHEN,
        "semantic_refs": sorted(set(semantic_refs or [])),
        "owner_refs": sorted(set(owners)),
        "estimated_words": word_count(path),
        "content_digest": file_digest(path),
    }


def _render_index(
    *,
    index_id: str,
    contour: str,
    title: str,
    summary: str,
    entries: list[dict[str, Any]],
) -> str:
    compact_entries: list[dict[str, Any]] = []
    for entry in sorted(entries, key=lambda entry: entry["id"]):
        compact = dict(entry)
        if compact.get("load_when") == DEFAULT_LOAD_WHEN:
            compact.pop("load_when")
        compact_entries.append(compact)
    data = {
        "schema_version": 1,
        "index_kind": "alatyr-context-index",
        "index_id": index_id,
        "contour": contour,
        "title": title,
        "summary": summary,
        "max_depth": MAX_DEPTH,
        "entry_defaults": {"load_when": DEFAULT_LOAD_WHEN},
        "entries": compact_entries,
    }
    return json.dumps(data, indent=2, ensure_ascii=True) + "\n"


def framework_base_files(root: Path = FRAMEWORK) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in {".md", ".json"}
        and path.name != INDEX_NAME
        and path.name != "file-inventory.json"
        and "catalog" not in path.relative_to(root).parts
    }


def build_framework_catalog_contents(
    selected_files: set[str] | None = None,
    content_overrides: dict[str, str] | None = None,
    root: Path = FRAMEWORK,
) -> dict[str, str]:
    selected = set(selected_files or framework_base_files(root))
    selected = {
        path
        for path in selected
        if path not in {INDEX_NAME, "file-inventory.json"}
        and not path.startswith("catalog/")
    }
    registry = _load(root / "rule-registry.json")
    rules_by_path: dict[str, list[dict[str, Any]]] = {}
    for rule in registry.get("rules", []):
        if not isinstance(rule, dict):
            continue
        source = rule.get("canonical_source")
        if not isinstance(source, str) or not source.startswith("framework/"):
            continue
        rules_by_path.setdefault(source[len("framework/"):], []).append(rule)

    sections: dict[str, list[str]] = {}
    for relpath in sorted(selected):
        rules = rules_by_path.get(relpath, [])
        categories = [rule.get("category") for rule in rules if isinstance(rule.get("category"), str)]
        section = next(
            (CATEGORY_SECTIONS[category] for category in categories if category in CATEGORY_SECTIONS),
            SUPPORT_SECTIONS.get(relpath, "core" if relpath.startswith("semantics/") else "support"),
        )
        sections.setdefault(section, []).append(relpath)

    contents: dict[str, str] = {}
    root_entries: list[dict[str, Any]] = []
    for section in sorted(sections):
        entries: list[dict[str, Any]] = []
        for relpath in sections[section]:
            rules = rules_by_path.get(relpath, [])
            owner_refs = [rule["id"] for rule in rules if isinstance(rule.get("id"), str)]
            semantic_refs = [
                SEMANTIC_REFS_BY_RULE[rule_id]
                for rule_id in owner_refs
                if rule_id in SEMANTIC_REFS_BY_RULE
            ]
            override = (content_overrides or {}).get(relpath)
            if override is None:
                entries.append(
                    _entry_from_file(
                        root=root,
                        item_id=f"framework.{section}.{_slug(relpath)}",
                        kind="content",
                        relpath=relpath,
                        owner_refs=owner_refs,
                        semantic_refs=semantic_refs,
                    )
                )
            else:
                entries.append(
                    _entry_from_bytes(
                        item_id=f"framework.{section}.{_slug(relpath)}",
                        kind="content",
                        path=relpath,
                        summary=_title_from_text(override, root / relpath),
                        selectors=_selectors(relpath, owner_refs),
                        semantic_refs=semantic_refs,
                        owner_refs=owner_refs,
                        payload=override.encode("utf-8"),
                    )
                )
        section_path = f"catalog/{section}/{INDEX_NAME}"
        section_text = _render_index(
            index_id=f"framework.{section}",
            contour="framework",
            title=f"{section.title()} Framework Context",
            summary=f"Bounded {section} framework rules and supporting guidance.",
            entries=entries,
        )
        contents[section_path] = section_text
        root_entries.append(
            _entry_from_bytes(
                item_id=f"framework.section.{section}",
                kind="index",
                path=section_path,
                summary=f"{section.title()} framework section",
                selectors={"sections": [section]},
                semantic_refs=[],
                owner_refs=[],
                payload=section_text.encode("utf-8"),
            )
        )
    contents[INDEX_NAME] = _render_index(
        index_id="framework.root",
        contour="framework",
        title="Alatyr Framework Context",
        summary="Root navigation for portable framework rules and supporting guidance.",
        entries=root_entries,
    )
    return contents


def _target_semantic_refs(relpath: str) -> tuple[list[str], list[str]]:
    refs = ["alatyr:bounded-context-expansion@1"]
    owners = ["ALATYR-CONTEXT-001"]
    is_profile_descriptor = relpath.startswith("context/profiles/")
    if any(part in relpath for part in ("approval", "authorization")):
        refs.extend(["alatyr:current-scope-authorization@1", "alatyr:protected-change@1"])
        owners.extend(["ALATYR-AUTHORIZATION-001", "ALATYR-APPROVAL-001"])
    if any(part in relpath for part in ("integrity", "consistency", "change-package")):
        refs.append("alatyr:logical-integrity@1")
        owners.append("ALATYR-INTEGRITY-001")
    if not is_profile_descriptor and any(
        part in relpath for part in ("knowledge", "architecture", "vocabulary")
    ):
        refs.extend(["alatyr:canonical-owner@1", "alatyr:observed-is-not-accepted@1"])
        owners.extend(["ALATYR-SOURCE-001", "ALATYR-KNOWLEDGE-001"])
    if not is_profile_descriptor and any(
        part in relpath for part in ("worker", "delegation", "team")
    ):
        refs.append("alatyr:bounded-delegation@1")
        owners.append("ALATYR-DELEGATION-001")
    if not is_profile_descriptor and "task-decomposition" in relpath:
        owners.append("ALATYR-DECOMPOSITION-001")
    if not is_profile_descriptor and any(
        part in relpath for part in ("extension", "dependency", "infrastructure", "prompt-injection")
    ):
        refs.append("alatyr:untrusted-instructions-are-data@1")
        owners.append("ALATYR-SAFETY-002")
    return sorted(set(refs)), sorted(set(owners))


def build_directory_catalog_contents(
    root: Path,
    contour: str,
    selected_files: set[str] | None = None,
    content_overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    if selected_files is None:
        all_files = [
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.name not in {INDEX_NAME, "bootstrap-index.json", ".gitignore"}
        ]
    else:
        all_files = []
        for relpath in sorted(selected_files):
            path = root / relpath
            if path.name in {INDEX_NAME, "bootstrap-index.json", ".gitignore"}:
                continue
            if not path.is_file():
                raise ValueError(
                    f"selected {contour} catalog path does not exist: {relpath}"
                )
            all_files.append(path)
    directories = {root}
    for path in all_files:
        current = path.parent
        while current == root or root in current.parents:
            directories.add(current)
            if current == root:
                break
            current = current.parent

    contents: dict[str, str] = {}
    for directory in sorted(directories, key=lambda item: len(item.relative_to(root).parts), reverse=True):
        rel_dir = directory.relative_to(root)
        entries: list[dict[str, Any]] = []
        for child in sorted(path for path in directories if path.parent == directory):
            child_rel = (child.relative_to(root) / INDEX_NAME).as_posix()
            child_text = contents[child_rel]
            entries.append(
                _entry_from_bytes(
                    item_id=f"{contour}.section.{_slug(child.relative_to(root).as_posix())}",
                    kind="index",
                    path=child_rel,
                    summary=f"{child.name.replace('-', ' ').title()} section",
                    selectors={"path_terms": [_slug(child.name)]},
                    semantic_refs=[],
                    owner_refs=[],
                    payload=child_text.encode("utf-8"),
                )
            )
        for path in sorted(file for file in all_files if file.parent == directory):
            relpath = path.relative_to(root).as_posix()
            semantic_refs, owner_refs = _target_semantic_refs(relpath)
            override = (content_overrides or {}).get(relpath)
            if override is None:
                entries.append(
                    _entry_from_file(
                        root=root,
                        item_id=f"{contour}.content.{_slug(relpath)}",
                        kind="content",
                        relpath=relpath,
                        owner_refs=owner_refs,
                        semantic_refs=semantic_refs,
                    )
                )
            else:
                entries.append(
                    _entry_from_bytes(
                        item_id=f"{contour}.content.{_slug(relpath)}",
                        kind="content",
                        path=relpath,
                        summary=_title_from_text(override, path),
                        selectors=_selectors(relpath, owner_refs),
                        semantic_refs=semantic_refs,
                        owner_refs=owner_refs,
                        payload=override.encode("utf-8"),
                    )
                )
        index_rel = (rel_dir / INDEX_NAME).as_posix()
        contents[index_rel] = _render_index(
            index_id=f"{contour}.{_slug(rel_dir.as_posix())}",
            contour=contour,
            title=f"{contour.title()} {rel_dir.name.replace('-', ' ').title() if rel_dir.parts else 'Root'} Context",
            summary=f"Recursive navigation for the {contour} contour at {rel_dir.as_posix() or '.'}.",
            entries=entries,
        )
    return contents


def expected_outputs() -> dict[Path, str]:
    outputs = {
        FRAMEWORK / relpath: text
        for relpath, text in build_framework_catalog_contents().items()
    }
    for root, contour in [
        (TARGET / ".ai" / "project", "project"),
        (TARGET / ".ai" / "assistant", "assistant"),
    ]:
        outputs.update(
            {root / relpath: text for relpath, text in build_directory_catalog_contents(root, contour).items()}
        )
    return outputs


def existing_generated_paths() -> set[Path]:
    return {
        *FRAMEWORK.glob(f"catalog/**/{INDEX_NAME}"),
        FRAMEWORK / INDEX_NAME,
        *(TARGET / ".ai" / "project").glob(f"**/{INDEX_NAME}"),
        *(TARGET / ".ai" / "assistant").glob(f"**/{INDEX_NAME}"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = expected_outputs()
    stale = sorted(existing_generated_paths() - set(expected))
    if args.check:
        failures: list[str] = []
        for path, text in expected.items():
            try:
                actual = path.read_text(encoding="utf-8")
            except OSError:
                failures.append(f"missing {path.relative_to(ROOT)}")
                continue
            if actual != text:
                failures.append(f"stale {path.relative_to(ROOT)}")
        failures.extend(f"unexpected {path.relative_to(ROOT)}" for path in stale)
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}", file=sys.stderr)
            return 1
        print(f"OK: checked {len(expected)} recursive context indexes")
        return 0
    for path in stale:
        path.unlink()
    for path, text in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    print(f"Wrote {len(expected)} recursive context indexes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
