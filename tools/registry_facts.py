"""Shared registry representation; declarations are not verified project facts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from registry_ownership import OwnerDeclaration, owner_declarations

REGISTRY_PATH = ".ai/project/source-of-truth-registry.md"
REGISTRY_ENTRY_HEADING_RE = re.compile(r"^### Fact Type: `([^`]+)`\s*$", re.MULTILINE)
COMPACT_FIELDS = {
    "Applicability state": ("Authority", "applicability", "ap"),
    "Authority state": ("Authority", "state", "st"),
    "Decision source": ("Authority", "decision_source", "ds"),
    "Evidence revision": ("Authority", "evidence_revision", "er"),
    "Last reviewed": ("Authority", "reviewed", "at"),
    "Gap severity": ("Authority", "gap", "gs"),
    "Consistency level": ("Routing", "consistency_level", "cl"),
    "Project area": ("Routing", "project_area", "pa"),
    "Consistency map node": ("Routing", "consistency_node", "cn"),
    "Relationship coverage": ("Routing", "relationship_coverage", "rc"),
}
COMPACT_PAIR_RE = re.compile(r"(?:^|;\s*)([a-z_]+)=`([^`]*)`")


def _unquote(value: str) -> str | None:
    value = value.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    return value or None


def markdown_scalar(block: str, name: str) -> str | None:
    match = re.search(rf"^{re.escape(name)}:[ \t]*(.*?)[ \t]*$", block, re.MULTILINE)
    if match is None:
        return None
    return _unquote(match.group(1))


def compact_markdown_scalar(block: str, group: str, *keys: str) -> str | None:
    line = re.search(rf"^{re.escape(group)}:[ \t]*(.*?)[ \t]*$", block, re.MULTILINE)
    if line is None:
        return None
    for key in keys:
        match = re.search(rf"(?:^|;\s*){re.escape(key)}=`([^`]*)`", line.group(1))
        if match is not None:
            return match.group(1).strip() or None
    return None


@dataclass(frozen=True)
class RegistryFactEntry:
    heading_fact_type: str
    declared_fact_type: str | None
    map_node_id: str | None
    canonical_owner_values: tuple[str, ...]
    line: int
    owner_declarations: tuple[OwnerDeclaration, ...] = ()
    fields: dict[str, str | None] = field(default_factory=dict)
    block: str = ""
    conflicts: tuple[str, ...] = ()


def parse_registry_fact_entries(text: str) -> list[RegistryFactEntry]:
    matches = list(REGISTRY_ENTRY_HEADING_RE.finditer(text))
    entries = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end():end]
        values: dict[str, list[str]] = {}
        compact_values: dict[tuple[str, str], list[str]] = {}
        owners = []
        for line in block.splitlines():
            name, separator, value = line.partition(":")
            if not separator:
                continue
            values.setdefault(name, []).append(value)
            if name in {"Authority", "Routing"}:
                for key, compact in COMPACT_PAIR_RE.findall(value.strip()):
                    compact_values.setdefault((name, key), []).append(compact.strip())
            if name.lower().endswith("owner") and value.strip():
                owners.append(value.strip().strip("`"))
        fields = {"Fact type": _unquote(values["Fact type"][0]) if "Fact type" in values else None}
        conflicts = []
        for name, (group, *keys) in COMPACT_FIELDS.items():
            declarations = values.get(name, [])
            long = _unquote(declarations[0]) if declarations else None
            compact_declarations = [value for key in keys for value in compact_values.get((group, key), [])]
            compact = compact_declarations[0] or None if compact_declarations else None
            fields[name] = long or compact
            if len(declarations) > 1 or len(values.get(group, [])) > 1 or len(compact_declarations) > 1 or (
                    long is not None and compact is not None and long != compact):
                conflicts.append(name)
        if len(values.get("Fact type", [])) > 1:
            conflicts.append("Fact type")
        entries.append(RegistryFactEntry(
            heading_fact_type=match.group(1).strip(), declared_fact_type=fields["Fact type"],
            map_node_id=fields["Consistency map node"], canonical_owner_values=tuple(owners),
            line=text.count("\n", 0, match.start()) + 1,
            owner_declarations=owner_declarations(block, text.count("\n", 0, match.end()) + 1),
            fields=fields, block=block.strip(), conflicts=tuple(conflicts)))
    return entries


def resolved(value: Any) -> bool:
    from target_validation_support import is_placeholder, is_unresolved_value
    return isinstance(value, str) and bool(value) and not is_placeholder(value) and not is_unresolved_value(value)


def registry_route_health(entry: RegistryFactEntry) -> dict[str, Any]:
    """Use declared coverage, never opaque node IDs, to describe routing gaps."""
    fields = entry.fields
    node = fields.get("Consistency map node")
    coverage = fields.get("Relationship coverage")
    token = coverage.partition(":")[0].strip().casefold() if isinstance(coverage, str) else ""
    unavailable = {"", "not-applicable", "deferred", "disabled", "not-installed", "missing", "unknown", "not-evaluated", "unmapped"}
    return {
        "applicability": fields.get("Applicability state"),
        "authority": fields.get("Authority state"),
        "decision_source": fields.get("Decision source"),
        "evidence_revision": fields.get("Evidence revision"),
        "reviewed_at": fields.get("Last reviewed"),
        "relationship_coverage": coverage,
        "consistency_node": node,
        "mapping": "unavailable" if token in unavailable or not resolved(node) or not resolved(coverage) else "declared-not-verified",
        "source_freshness": "not-established-by-registry-metadata",
        "semantic_review": "not-established-by-registry-metadata",
        "declaration_conflicts": list(entry.conflicts),
    }
