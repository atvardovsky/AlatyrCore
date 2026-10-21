"""Pure conflict rules for opaque, credential-free runtime resource claims."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from target_validation_support import is_unresolved_value

KINDS = ("database", "fixture", "port", "directory", "service", "network")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


def resource_failures(resources: Any) -> list[str]:
    if not isinstance(resources, list) or len(resources) > 64:
        return ["resources must be a bounded array"]
    failures, identities = [], set()
    for resource in resources:
        if not isinstance(resource, dict) or set(resource) != {"kind", "id", "namespace", "access", "isolation"}:
            failures.append("resource needs kind, id, namespace, access and isolation")
            continue
        kind, identity, namespace, access, isolation = (resource[key] for key in ("kind", "id", "namespace", "access", "isolation"))
        if kind not in KINDS or not isinstance(identity, str) or not TOKEN.fullmatch(identity) or is_unresolved_value(identity):
            failures.append("resource identity must be resolved and credential-free")
            continue
        if namespace is not None and (not isinstance(namespace, str) or not TOKEN.fullmatch(namespace) or is_unresolved_value(namespace)):
            failures.append("resource namespace must be a resolved token or null")
            continue
        if access not in ("read", "write", "exclusive") or isolation not in ("shared", "verified-isolated"):
            failures.append("resource access or isolation is invalid")
            continue
        if access == "exclusive" and namespace is not None:
            failures.append("exclusive/reset access must claim the enclosing resource")
        if namespace is None and isolation == "verified-isolated":
            failures.append("verified namespace isolation requires a concrete namespace")
        key = (kind, identity, namespace)
        if key in identities:
            failures.append("duplicate resource identity and namespace")
        identities.add(key)
    return failures


def resource_conflicts(left: Any, right: Any) -> list[str]:
    failures = resource_failures(left) + resource_failures(right)
    if failures:
        raise ValueError("; ".join(failures))
    conflicts = set()
    for first in left:
        for second in right:
            if (first["kind"], first["id"]) != (second["kind"], second["id"]):
                continue
            if first["access"] == second["access"] == "read":
                continue
            separate = first["namespace"] is not None and second["namespace"] is not None and first["namespace"] != second["namespace"]
            if separate and first["isolation"] == second["isolation"] == "verified-isolated":
                continue
            conflicts.add(first["kind"] + ":" + first["id"])
    return sorted(conflicts)


def presence_resource_scopes(resources: Any) -> list[str]:
    """Conservative whole-resource identity; namespace separation is not a lock."""
    failures = resource_failures(resources)
    if failures:
        raise ValueError("; ".join(failures))
    return sorted({"resource:test-" + resource["kind"] + "-" + hashlib.sha256(
        (resource["kind"] + "\0" + resource["id"]).encode("utf-8")).hexdigest()
        for resource in resources})


def effect_resource_failures(effects: list[str], resources: list[dict[str, Any]]) -> list[str]:
    required_kinds = {"temporary-files": ("directory",), "disposable-db-writes": ("database",),
        "shared-db-writes": ("database",), "service-start": ("service", "port"),
        "package-install": ("directory",), "network": ("network", "service")}
    return [f"{effect} requires a corresponding writable resource" for effect in effects
            if not any(item["kind"] in required_kinds[effect] and item["access"] != "read" for item in resources)]


def command_resource_plan(policy: dict[str, Any], command_ids: list[str]) -> dict[str, Any]:
    if not isinstance(command_ids, list) or not command_ids or len(command_ids) > 64 or any(not isinstance(item, str) for item in command_ids) or len(set(command_ids)) != len(command_ids):
        raise ValueError("select 1 to 64 distinct command IDs")
    commands = {command["id"]: command for command in policy["commands"]}
    if any(identity not in commands for identity in command_ids):
        raise ValueError("selected command ID is not registered")
    conflicts = []
    for position, first in enumerate(command_ids):
        for second in command_ids[position + 1:]:
            shared = resource_conflicts(commands[first]["execution"]["resources"], commands[second]["execution"]["resources"])
            if shared:
                conflicts.append({"commands": [first, second], "resources": shared})
    return {"commands": command_ids, "concurrent_eligible": not conflicts, "conflicts": conflicts,
            "limitation": "Declared identities and namespace isolation require target evidence; this planner never runs commands or grants permission."}
