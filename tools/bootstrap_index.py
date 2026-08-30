"""Build and validate the compact installed-adapter bootstrap projection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from context_catalog import load_codebook
from target_tool_compat import generation_provenance


BOOTSTRAP_PATH = Path(".ai/assistant/bootstrap-index.json")
SOURCE_PATHS = {
    "manifest": Path(".ai/alatyr.yaml"),
    "project_map": Path(".ai/README.md"),
    "context_router": Path(".ai/assistant/context-router.json"),
}
SEMANTIC_INDEX_PATH = Path(".ai/framework/semantics/index.json")
SOURCE_SEMANTIC_INDEX = Path(__file__).resolve().parents[1] / "framework" / "semantics" / "index.json"


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
    *,
    semantic_index_text: str | None = None,
    semantic_terms: dict[str, dict[str, Any]] | None = None,
    generated_by: dict[str, Any] | None = None,
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

    derived_from = {
        name: {"path": path.as_posix(), "sha256": _sha256(text)}
        for (name, path), text in zip(
            SOURCE_PATHS.items(),
            [manifest_text, project_map_text, router_text],
        )
    }
    if semantic_index_text is not None:
        derived_from["semantic_codebook"] = {
            "path": SEMANTIC_INDEX_PATH.as_posix(),
            "sha256": _sha256(semantic_index_text),
        }
    recursive_context = router.get("recursive_context")
    recursive_context = recursive_context if isinstance(recursive_context, dict) else {}
    semantic_codebook = router.get("semantic_codebook")
    semantic_codebook = semantic_codebook if isinstance(semantic_codebook, dict) else {}
    context_packet = router.get("context_packet")
    context_packet = context_packet if isinstance(context_packet, dict) else {}
    agent_entry_packet = router.get("agent_entry_packet")
    agent_entry_packet = agent_entry_packet if isinstance(agent_entry_packet, dict) else {}
    preload_ids = _string_list(semantic_codebook.get("preload_terms"))
    ordered_semantic_ids = [
        term_id for term_id in preload_ids if term_id in (semantic_terms or {})
    ]
    ordered_semantic_ids.extend(
        term_id
        for term_id in (semantic_terms or {})
        if term_id not in ordered_semantic_ids
    )

    return {
        "schema_version": 1,
        "index_kind": "target-bootstrap-index",
        "generated_by": generated_by or {},
        "derived_from": derived_from,
        "installation": {
            "framework_version": _string(framework.get("version")),
            "adapter_schema_version": _string(manifest.get("schema_version")),
            "template_version": _string(framework.get("template_version")),
            "support_profile": _string(installation.get("support_profile")),
            "framework_pack": _string(framework.get("pack")),
        },
        "project_map": SOURCE_PATHS["project_map"].as_posix(),
        "context_router": SOURCE_PATHS["context_router"].as_posix(),
        "recursive_context": {
            "contour_indexes": recursive_context.get("contour_indexes", {}),
            "max_depth": recursive_context.get("max_depth", "unknown"),
            "on_failure": _string(recursive_context.get("on_failure")),
        },
        "semantic_preload": {
            "index": _string(semantic_codebook.get("index"), SEMANTIC_INDEX_PATH.as_posix()),
            "codebook_schema_version": semantic_codebook.get("schema_version", "unknown"),
            "terms": [
                {
                    "id": term_id,
                    "version": term.get("version"),
                    "definition": term.get("definition"),
                    "canonical_owner": f".ai/framework/{term.get('canonical_owner')}",
                }
                for term_id in ordered_semantic_ids
                for term in [(semantic_terms or {})[term_id]]
            ],
            "fallback": _string(semantic_codebook.get("fallback")),
        },
        "context_packet": {
            "schema_version": context_packet.get("schema_version", "unknown"),
            "template": _string(context_packet.get("template")),
            "receipt_required_for": _string_list(context_packet.get("receipt_required_for")),
        },
        "agent_entry_packet": {
            "schema_version": agent_entry_packet.get("schema_version", "unknown"),
            "path": _string(agent_entry_packet.get("path")),
            "load_after": _string(agent_entry_packet.get("load_after")),
        },
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
    installed_index = target / SEMANTIC_INDEX_PATH
    semantic_index = installed_index if installed_index.is_file() else SOURCE_SEMANTIC_INDEX
    semantic_terms = load_codebook(semantic_index, root=semantic_index.parent)
    return build_bootstrap_index(
        texts["manifest"],
        texts["project_map"],
        texts["context_router"],
        semantic_index_text=semantic_index.read_text(encoding="utf-8"),
        semantic_terms=semantic_terms,
        generated_by=generation_provenance(
            target,
            tool_name="render_target_bootstrap_index.py",
        ),
    )


def render(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True) + "\n"
