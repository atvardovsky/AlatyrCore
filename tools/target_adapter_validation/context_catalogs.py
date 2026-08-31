"""Validate recursive context catalogs and semantic terms in an adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from context_catalog import (
    ContextCatalogError,
    load_codebook,
    validate_context_catalog,
)


CATALOG_ROOTS = {
    "framework": ".ai/framework/context-index.json",
    "project": ".ai/project/context-index.json",
    "assistant": ".ai/assistant/context-index.json",
}
CODEBOOK = ".ai/framework/semantics/index.json"
PACKET_TEMPLATE = ".ai/assistant/templates/context-packet.json"
DERIVED_ROUTING_REFERENCES = {
    ".ai/assistant/bootstrap-index.json",
    ".ai/support-state.json",
}


class FindingSink(Protocol):
    target: Path

    def target_path(self, relpath: str) -> Path: ...
    def load_json_object(
        self, path: Path, code_prefix: str
    ) -> dict[str, Any] | None: ...
    def error(self, code: str, message: str, path: str | None = None) -> None: ...
    def info(self, code: str, message: str, path: str | None = None) -> None: ...


def _target_references(value: Any) -> set[str]:
    references: set[str] = set()
    if isinstance(value, dict):
        for nested in value.values():
            references.update(_target_references(nested))
    elif isinstance(value, list):
        for nested in value:
            references.update(_target_references(nested))
    elif isinstance(value, str) and value.startswith(".ai/"):
        references.add(value)
    return references


def validate_context_catalog_contract(sink: FindingSink, manifest: Any) -> None:
    resolutions = {}
    indexed_paths: set[str] = set()
    semantic_refs: set[str] = set()
    for contour, relpath in CATALOG_ROOTS.items():
        root = sink.target_path(f".ai/{contour}")
        index = sink.target_path(relpath)
        if not index.is_file():
            sink.error(
                "CONTEXT_CATALOG_MISSING",
                f"{contour} recursive context index is missing",
                relpath,
            )
            continue
        try:
            resolution = validate_context_catalog(index, catalog_root=root)
        except (OSError, UnicodeError, ContextCatalogError) as exc:
            sink.error(
                "CONTEXT_CATALOG_INVALID",
                f"{contour} recursive context index is invalid: {exc}",
                relpath,
            )
            continue
        resolutions[contour] = resolution
        indexed_paths.update(f".ai/{contour}/{item.path}" for item in resolution.items)
        semantic_refs.update(
            term_id for item in resolution.items for term_id in item.semantic_refs
        )

    router_path = sink.target_path(".ai/assistant/context-router.json")
    router = sink.load_json_object(router_path, "CONTEXT_CATALOG_ROUTER")
    if router is None:
        return
    recursive = router.get("recursive_context")
    if not isinstance(recursive, dict):
        sink.error(
            "CONTEXT_CATALOG_ROUTER",
            "context router must define recursive_context",
            ".ai/assistant/context-router.json",
        )
    else:
        indexes = recursive.get("contour_indexes")
        if not isinstance(indexes, dict) or indexes != CATALOG_ROOTS:
            sink.error(
                "CONTEXT_CATALOG_ROUTER",
                "router contour indexes differ from the installed catalog roots",
                ".ai/assistant/context-router.json",
            )

    references = _target_references(router)
    if manifest is not None:
        references.update(
            scalar.value
            for scalar in manifest.scalars.values()
            if isinstance(scalar.value, str) and scalar.value.startswith(".ai/")
        )
    for relpath in sorted(references):
        if (
            relpath.endswith("/context-index.json")
            or relpath == CODEBOOK
            or relpath in DERIVED_ROUTING_REFERENCES
        ):
            continue
        path = sink.target_path(relpath)
        if path.is_file() and relpath not in indexed_paths:
            sink.error(
                "CONTEXT_CATALOG_REFERENCE_UNINDEXED",
                f"live adapter reference is absent from recursive indexes: {relpath}",
                relpath,
            )

    codebook_path = sink.target_path(CODEBOOK)
    try:
        terms = load_codebook(
            codebook_path,
            root=codebook_path.parent,
            required_terms=semantic_refs,
        )
    except (OSError, UnicodeError, ContextCatalogError) as exc:
        sink.error(
            "CONTEXT_SEMANTIC_CODEBOOK_INVALID",
            f"installed semantic codebook is invalid: {exc}",
            CODEBOOK,
        )
        terms = {}
    for term_id, term in terms.items():
        owner = term.get("canonical_owner")
        owner_path = (
            sink.target_path(f".ai/framework/{owner}")
            if isinstance(owner, str)
            else None
        )
        if owner_path is None or not owner_path.is_file():
            sink.error(
                "CONTEXT_SEMANTIC_OWNER_MISSING",
                f"semantic term {term_id} has no installed canonical owner",
                CODEBOOK,
            )

    semantic = router.get("semantic_codebook")
    preload = semantic.get("preload_terms") if isinstance(semantic, dict) else None
    preload = preload if isinstance(preload, list) else []
    bootstrap = sink.load_json_object(
        sink.target_path(".ai/assistant/bootstrap-index.json"),
        "CONTEXT_CATALOG_BOOTSTRAP",
    )
    embedded = (
        bootstrap.get("semantic_preload", {}).get("terms", [])
        if isinstance(bootstrap, dict)
        else []
    )
    embedded_ids = [
        term.get("id") for term in embedded if isinstance(term, dict)
    ]
    if embedded_ids != preload:
        sink.error(
            "CONTEXT_SEMANTIC_PRELOAD_DRIFT",
            "bootstrap semantic preload differs from the router term order",
            ".ai/assistant/bootstrap-index.json",
        )
    for embedded_term in embedded:
        if not isinstance(embedded_term, dict):
            continue
        term_id = embedded_term.get("id")
        expected = terms.get(term_id)
        if expected is None or any(
            embedded_term.get(field) != expected.get(field)
            for field in ["version", "definition"]
        ):
            sink.error(
                "CONTEXT_SEMANTIC_PRELOAD_DRIFT",
                f"bootstrap semantic term differs from installed codebook: {term_id}",
                ".ai/assistant/bootstrap-index.json",
            )

    packet = sink.load_json_object(
        sink.target_path(PACKET_TEMPLATE), "CONTEXT_PACKET_TEMPLATE"
    )
    if packet is not None:
        required_packet_fields = {
            "schema_version",
            "packet_kind",
            "profile",
            "operation",
            "task_classification",
            "selected_items",
            "semantic_terms",
            "budget",
            "receipt",
            "cost_claim",
            "limitations",
            "packet_digest",
        }
        if (
            set(packet) != required_packet_fields
            or packet.get("schema_version") != 1
            or packet.get("packet_kind") != "alatyr-context-packet"
        ):
            sink.error(
                "CONTEXT_PACKET_TEMPLATE_INVALID",
                "context packet template has an unsupported contract",
                PACKET_TEMPLATE,
            )
        receipt = packet.get("receipt")
        if not isinstance(receipt, dict):
            sink.error(
                "CONTEXT_PACKET_TEMPLATE_INVALID",
                "context packet template must include context receipt evidence",
                PACKET_TEMPLATE,
            )
        else:
            for field in [
                "receipt_kind",
                "measurement_state",
                "planned",
                "resolved",
                "observed",
                "semantic_guidance",
                "task_classification",
            ]:
                if field not in receipt:
                    sink.error(
                        "CONTEXT_PACKET_TEMPLATE_INVALID",
                        f"context packet receipt missing {field}",
                        PACKET_TEMPLATE,
                    )
        cost_claim = packet.get("cost_claim")
        if not isinstance(cost_claim, dict):
            sink.error(
                "CONTEXT_PACKET_TEMPLATE_INVALID",
                "context packet template must include cost claim classification",
                PACKET_TEMPLATE,
            )
        else:
            if cost_claim.get("exact_billing_claim") is not False:
                sink.error(
                    "CONTEXT_PACKET_TEMPLATE_INVALID",
                    "context packet exact_billing_claim must default false",
                    PACKET_TEMPLATE,
                )
            if cost_claim.get("exact_context_delivery_claim") is not False:
                sink.error(
                    "CONTEXT_PACKET_TEMPLATE_INVALID",
                    "context packet exact_context_delivery_claim must default false",
                    PACKET_TEMPLATE,
                )
        limitations = packet.get("limitations")
        if not isinstance(limitations, list) or not all(
            isinstance(item, str) and item for item in limitations
        ):
            sink.error(
                "CONTEXT_PACKET_TEMPLATE_INVALID",
                "context packet template must state context/cost limitations",
                PACKET_TEMPLATE,
            )

    if len(resolutions) == len(CATALOG_ROOTS) and terms:
        sink.info(
            "CONTEXT_CATALOG_CURRENT",
            "recursive context catalogs, semantic references, and bootstrap preload are structurally current",
        )
    sink.info(
        "CONTEXT_CATALOG_EVIDENCE_LIMIT",
        "catalog and codebook checks prove structure and identity, not model comprehension or semantic correctness",
    )
