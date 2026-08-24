"""Build and validate the compact installed-adapter bootstrap projection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


BOOTSTRAP_PATH = Path(".ai/assistant/bootstrap-index.json")
SOURCE_PATHS = {
    "manifest": Path(".ai/alatyr.yaml"),
    "project_map": Path(".ai/README.md"),
    "context_router": Path(".ai/assistant/context-router.json"),
}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _string(value: Any, default: str = "unknown") -> str:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return default


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _route_projection(entries: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(entries, dict):
        return {}
    projected: dict[str, dict[str, Any]] = {}
    for route_id, entry in entries.items():
        if not isinstance(route_id, str) or not isinstance(entry, dict):
            continue
        route: dict[str, Any] = {}
        for source, target in [
            ("use_when", "signals"),
            ("descriptor", "descriptor"),
            ("required_module", "required_module"),
            ("operation_candidates", "operations"),
        ]:
            value = entry.get(source)
            if isinstance(value, str) and value:
                route[target] = value
            elif isinstance(value, list):
                values = _string_list(value)
                if values:
                    route[target] = values
        projected[route_id] = route
    return projected


def build_bootstrap_index(
    manifest_text: str,
    project_map_text: str,
    router_text: str,
) -> dict[str, Any]:
    """Return a deterministic routing projection from canonical target sources."""

    manifest = yaml.safe_load(manifest_text)
    router = json.loads(router_text)
    if not isinstance(manifest, dict):
        raise ValueError(".ai/alatyr.yaml must contain a mapping")
    if not isinstance(router, dict):
        raise ValueError("context router must contain an object")

    framework = manifest.get("framework")
    installation = manifest.get("installation")
    modules = manifest.get("modules")
    operation_routing = router.get("operation_routing")
    framework = framework if isinstance(framework, dict) else {}
    installation = installation if isinstance(installation, dict) else {}
    modules = modules if isinstance(modules, dict) else {}
    operation_routing = operation_routing if isinstance(operation_routing, dict) else {}

    return {
        "schema_version": 1,
        "index_kind": "target-bootstrap-index",
        "derived_from": {
            name: {"path": path.as_posix(), "sha256": _sha256(text)}
            for (name, path), text in zip(
                SOURCE_PATHS.items(),
                [manifest_text, project_map_text, router_text],
            )
        },
        "installation": {
            "framework_version": _string(framework.get("version")),
            "adapter_schema_version": _string(manifest.get("schema_version")),
            "template_version": _string(framework.get("template_version")),
            "support_profile": _string(installation.get("support_profile")),
            "framework_pack": _string(framework.get("pack")),
        },
        "project_map": SOURCE_PATHS["project_map"].as_posix(),
        "context_router": SOURCE_PATHS["context_router"].as_posix(),
        "routing_order": _string_list(router.get("routing_order")),
        "profiles": _route_projection(router.get("profile_index")),
        "intent_overlays": _route_projection(router.get("intent_overlays")),
        "task_scale_overlays": _route_projection(router.get("task_scale_overlays")),
        "area_overlays": _route_projection(router.get("area_overlays")),
        "project_knowledge_routing": _string(
            router.get("project_knowledge_routing", {}).get("descriptor")
            if isinstance(router.get("project_knowledge_routing"), dict)
            else None,
            "not installed",
        ),
        "operation_index": _string(operation_routing.get("index"), "not installed"),
        "operation_catalog": _string(
            operation_routing.get("catalog"), "not installed"
        ),
        "gate_index": ".ai/assistant/gates/index.json",
        "enabled_modules": _string_list(modules.get("enabled")),
        "known_gaps": _string_list(manifest.get("known_gaps")),
        "expansion_policy": _string(
            router.get("context_budgets", {}).get("on_exceed")
            if isinstance(router.get("context_budgets"), dict)
            else None
        ),
    }


def build_from_target(target: Path) -> dict[str, Any]:
    texts: dict[str, str] = {}
    for name, relpath in SOURCE_PATHS.items():
        path = target / relpath
        if not path.is_file():
            raise ValueError(f"bootstrap source is missing: {relpath.as_posix()}")
        texts[name] = path.read_text(encoding="utf-8")
    return build_bootstrap_index(
        texts["manifest"], texts["project_map"], texts["context_router"]
    )


def render(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True) + "\n"
