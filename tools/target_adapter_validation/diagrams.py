"""Discussion-diagram capability validation."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from target_validation_support import UNRESOLVED_WORDS, dotted
from target_adapter_validation.assistant_capabilities import (
    CAPABILITY_INDEX_KIND,
    CAPABILITY_INDEX_SCHEMA_VERSION,
    SURFACE_CAPABILITY_KIND,
    SURFACE_CAPABILITY_SCHEMA_VERSION,
    capability_record_path,
)
from target_adapter_validation.capability import FunctionCapabilityModule
from target_adapter_validation.files import missing_target_files
from target_adapter_validation.manifest_paths import manifest_path_mismatches
from target_adapter_validation.values import is_string_list


REQUIRED_PATHS = (
    ".ai/assistant/flows/diagram-discussion.flow.md",
    ".ai/assistant/templates/diagram-presentation.md",
    ".ai/assistant/templates/ascii-diagram.md",
    ".ai/assistant/assistant-capabilities.json",
    ".ai/assistant/bridge-capability-matrix.md",
    ".ai/framework/ascii-diagrams.md",
)

REQUIRED_CAPABILITY_FIELDS = {
    "route",
    "native_inline_syntaxes",
    "artifact_presentation",
    "readable_fallback",
    "verified_at",
    "expires_at",
    "review_triggers",
    "client_version",
    "evidence",
}


def validate_discussion_diagrams(validator: Any, manifest: Any) -> None:
    self = validator
    if not self.module_validation_enabled(
        "diagrams",
        "DIAGRAM_MODULE_UNDECLARED",
        "DIAGRAM_MODULE_STATE_MISSING",
        "diagrams",
    ):
        return

    _validate_required_files(self)
    _validate_manifest_paths(self, manifest)
    _validate_operation_catalog(self)
    _validate_router(self)
    matrix_matches, capability_surfaces = _validate_capability_index_and_matrix(self)
    _validate_surface_capabilities(self, matrix_matches, capability_surfaces)
    _validate_contract_text(self)


DISCUSSION_DIAGRAMS_MODULE = FunctionCapabilityModule(
    "check_discussion_diagrams", validate_discussion_diagrams
)


def _validate_required_files(self: Any) -> None:
    for relpath in missing_target_files(self, REQUIRED_PATHS):
        self.error(
            "DIAGRAM_REQUIRED_FILE_MISSING",
            "enabled diagrams module is missing a discussion contract",
            relpath,
        )


def _validate_manifest_paths(self: Any, manifest: Any) -> None:
    if manifest is None:
        return
    expected_manifest = {
        ("operations", "diagram_discussion"): REQUIRED_PATHS[0],
        ("operations", "diagram_presentation"): REQUIRED_PATHS[1],
        ("bridges", "capabilities"): REQUIRED_PATHS[3],
    }
    for mismatch in manifest_path_mismatches(manifest, expected_manifest):
        self.error(
            "DIAGRAM_MANIFEST_PATH",
            f"{dotted(mismatch.key)} must be {mismatch.expected} when diagrams are enabled",
            ".ai/alatyr.yaml",
        )


def _validate_operation_catalog(self: Any) -> None:
    catalog = self.load_json_object(
        self.target_path(".ai/assistant/operation-catalog.json"),
        "OPERATION_CATALOG",
    )
    operations = catalog.get("operations") if isinstance(catalog, dict) else None
    operation = None
    if isinstance(operations, list):
        operation = next(
            (
                item
                for item in operations
                if isinstance(item, dict)
                and item.get("id") == "diagram-discussion"
            ),
            None,
        )
    if not isinstance(operation, dict):
        self.error(
            "DIAGRAM_OPERATION_MISSING",
            "enabled diagrams module requires diagram-discussion operation",
            ".ai/assistant/operation-catalog.json",
        )
        return

    if operation.get("required_module") != "diagrams":
        self.error(
            "DIAGRAM_OPERATION_MODULE",
            "diagram-discussion must require the diagrams module",
            ".ai/assistant/operation-catalog.json",
        )
    if operation.get("flow") != REQUIRED_PATHS[0]:
        self.error(
            "DIAGRAM_OPERATION_FLOW",
            f"diagram-discussion must route to {REQUIRED_PATHS[0]}",
            ".ai/assistant/operation-catalog.json",
        )
    if operation.get("allowed_actions") != ["read-only", "docs-only"]:
        self.error(
            "DIAGRAM_OPERATION_ACTIONS",
            "diagram-discussion must allow only read-only and docs-only",
            ".ai/assistant/operation-catalog.json",
        )


def _validate_router(self: Any) -> None:
    router = self.load_json_object(
        self.target_path(".ai/assistant/context-router.json"), "ROUTER"
    )
    intent_overlays = (
        router.get("intent_overlays") if isinstance(router, dict) else None
    )
    diagram_overlay = (
        intent_overlays.get("diagram-request")
        if isinstance(intent_overlays, dict)
        else None
    )
    routed = isinstance(diagram_overlay, dict) and diagram_overlay.get(
        "operation_candidates"
    ) == ["diagram-discussion"]
    if not routed:
        self.error(
            "DIAGRAM_OPERATION_UNROUTED",
            "enabled diagram-discussion has no diagram-request intent overlay",
            ".ai/assistant/context-router.json",
        )


def _validate_capability_index_and_matrix(
    self: Any,
) -> tuple[list[re.Match[str]], dict[str, str]]:
    matrix_relpath = ".ai/assistant/bridge-capability-matrix.md"
    matrix_text = self.read_text(self.target_path(matrix_relpath))
    matches = list(
        re.finditer(
            r"^### Assistant Surface: `([^`]+)`\s*$",
            matrix_text,
            flags=re.MULTILINE,
        )
    )
    if not matches:
        self.error(
            "DIAGRAM_BRIDGE_CAPABILITY_MISSING",
            "enabled diagrams module has no assistant capability entries",
            matrix_relpath,
        )

    capability_relpath = ".ai/assistant/assistant-capabilities.json"
    capabilities = self.load_json_object(
        self.target_path(capability_relpath), "ASSISTANT_CAPABILITIES"
    )
    capability_surfaces = (
        capabilities.get("surfaces") if isinstance(capabilities, dict) else None
    )
    if isinstance(capabilities, dict):
        if capabilities.get("schema_version") != CAPABILITY_INDEX_SCHEMA_VERSION:
            self.error(
                "DIAGRAM_CAPABILITY_SCHEMA",
                "capability index schema_version should be "
                f"{CAPABILITY_INDEX_SCHEMA_VERSION}",
                capability_relpath,
            )
        if capabilities.get("capability_kind") != CAPABILITY_INDEX_KIND:
            self.error(
                "DIAGRAM_CAPABILITY_KIND",
                f"capability_kind should be {CAPABILITY_INDEX_KIND}",
                capability_relpath,
            )
    if not isinstance(capability_surfaces, dict) or not capability_surfaces:
        self.error(
            "DIAGRAM_CAPABILITY_SURFACES",
            "enabled diagrams require assistant capability surface entries",
            capability_relpath,
        )
        return matches, {}

    return matches, {
        key: value
        for key, value in capability_surfaces.items()
        if isinstance(key, str) and isinstance(value, str)
    }


def _validate_surface_capabilities(
    self: Any,
    matches: list[re.Match[str]],
    capability_surfaces: dict[str, str],
) -> None:
    matrix_relpath = ".ai/assistant/bridge-capability-matrix.md"
    matrix_text = self.read_text(self.target_path(matrix_relpath))
    capability_relpath = ".ai/assistant/assistant-capabilities.json"
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(matrix_text)
        block = matrix_text[match.end():end]
        surface_id = match.group(1)
        surface_relpath = capability_record_path(surface_id)
        expected_reference = "Diagram capability record: " f"`{surface_relpath}`"
        if expected_reference not in block:
            self.error(
                "DIAGRAM_BRIDGE_CAPABILITY_FIELD",
                f"assistant surface {surface_id} has no compact capability reference",
                matrix_relpath,
            )
        if capability_surfaces.get(surface_id) != surface_relpath:
            self.error(
                "DIAGRAM_CAPABILITY_INDEX_PATH",
                f"assistant surface {surface_id} must route to {surface_relpath}",
                capability_relpath,
            )
            continue
        _validate_surface_record(self, surface_id, surface_relpath)

    matrix_surface_ids = {match.group(1) for match in matches}
    extra_capabilities = sorted(set(capability_surfaces) - matrix_surface_ids)
    if extra_capabilities:
        self.error(
            "DIAGRAM_CAPABILITY_SURFACE_DRIFT",
            f"capability projection has surfaces absent from bridge matrix: {extra_capabilities}",
            capability_relpath,
        )


def _validate_surface_record(
    self: Any, surface_id: str, surface_relpath: str
) -> None:
    surface = self.load_json_object(
        self.target_path(surface_relpath), "ASSISTANT_SURFACE_CAPABILITIES"
    )
    if surface is None:
        return
    if surface.get("schema_version") != SURFACE_CAPABILITY_SCHEMA_VERSION:
        self.error(
            "DIAGRAM_SURFACE_CAPABILITY_SCHEMA",
            "surface capability schema_version should be "
            f"{SURFACE_CAPABILITY_SCHEMA_VERSION}",
            surface_relpath,
        )
    if surface.get("capability_kind") != SURFACE_CAPABILITY_KIND:
        self.error(
            "DIAGRAM_SURFACE_CAPABILITY_KIND",
            "surface capability kind is invalid",
            surface_relpath,
        )
    if surface.get("assistant_surface") != surface_id:
        self.error(
            "DIAGRAM_SURFACE_CAPABILITY_ID",
            f"surface capability identity should be {surface_id}",
            surface_relpath,
        )

    diagram = surface.get("diagram_discussion")
    if not isinstance(diagram, dict):
        self.error(
            "DIAGRAM_CAPABILITY_MISSING",
            f"assistant surface {surface_id} has no diagram_discussion capability",
            surface_relpath,
        )
        return

    missing_fields = sorted(REQUIRED_CAPABILITY_FIELDS - set(diagram))
    if missing_fields:
        self.error(
            "DIAGRAM_CAPABILITY_FIELDS",
            f"assistant surface {surface_id} is missing {missing_fields}",
            surface_relpath,
        )
    if diagram.get("route") not in {"supported", "unsupported", "unknown"}:
        self.error(
            "DIAGRAM_CAPABILITY_ROUTE",
            f"assistant surface {surface_id} route must be supported, unsupported, or unknown",
            surface_relpath,
        )
    if diagram.get("artifact_presentation") not in {
        "link",
        "attachment",
        "both",
        "unsupported",
        "unknown",
    }:
        self.error(
            "DIAGRAM_CAPABILITY_ARTIFACT",
            f"assistant surface {surface_id} artifact_presentation has an invalid enum",
            surface_relpath,
        )

    _validate_surface_lists(self, surface_id, surface_relpath, diagram)
    _validate_surface_evidence(self, surface_id, surface_relpath, diagram)
    _validate_surface_freshness(self, surface_id, surface_relpath, diagram)


def _validate_surface_lists(
    self: Any, surface_id: str, surface_relpath: str, diagram: dict[str, Any]
) -> None:
    syntaxes = diagram.get("native_inline_syntaxes")
    if not is_string_list(syntaxes):
        self.error(
            "DIAGRAM_CAPABILITY_SYNTAXES",
            f"assistant surface {surface_id} native_inline_syntaxes must be a string list",
            surface_relpath,
        )
    review_triggers = diagram.get("review_triggers")
    if not is_string_list(review_triggers):
        self.error(
            "DIAGRAM_CAPABILITY_REVIEW_TRIGGERS",
            f"assistant surface {surface_id} review_triggers must be a string list",
            surface_relpath,
        )


def _validate_surface_evidence(
    self: Any, surface_id: str, surface_relpath: str, diagram: dict[str, Any]
) -> None:
    for field in [
        "readable_fallback",
        "verified_at",
        "expires_at",
        "client_version",
        "evidence",
    ]:
        value = diagram.get(field)
        if not isinstance(value, str) or not value.strip():
            self.error(
                "DIAGRAM_CAPABILITY_EVIDENCE",
                f"assistant surface {surface_id} {field} must be recorded",
                surface_relpath,
            )
    for field in ["readable_fallback", "evidence"]:
        value = diagram.get(field)
        if isinstance(value, str) and value.strip().casefold() in UNRESOLVED_WORDS:
            self.error(
                "DIAGRAM_CAPABILITY_EVIDENCE",
                f"assistant surface {surface_id} {field} is unresolved",
                surface_relpath,
            )
    if diagram.get("readable_fallback") != "ascii":
        self.error(
            "DIAGRAM_CAPABILITY_ASCII_FALLBACK",
            f"assistant surface {surface_id} readable_fallback must be ascii",
            surface_relpath,
        )
    client_version = diagram.get("client_version")
    if isinstance(client_version, str) and client_version.casefold() in {
        "unknown",
        "n/a",
    }:
        self.error(
            "DIAGRAM_CAPABILITY_CLIENT_VERSION",
            f"assistant surface {surface_id} client_version needs a value or unknown: reason",
            surface_relpath,
        )


def _validate_surface_freshness(
    self: Any, surface_id: str, surface_relpath: str, diagram: dict[str, Any]
) -> None:
    verified_at = diagram.get("verified_at")
    if isinstance(verified_at, str) and not (
        re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T[^\s]+)?", verified_at)
        or verified_at.casefold().startswith("unknown:")
    ):
        self.error(
            "DIAGRAM_CAPABILITY_FRESHNESS",
            f"assistant surface {surface_id} verified_at must be an ISO date/time or unknown: reason",
            surface_relpath,
        )

    expires_at = diagram.get("expires_at")
    if not isinstance(expires_at, str):
        return
    expiry_is_date = re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T[^\s]+)?", expires_at)
    expiry_is_trigger = expires_at.casefold().startswith(
        ("review-trigger:", "unknown:")
    )
    if not expiry_is_date and not expiry_is_trigger:
        self.error(
            "DIAGRAM_CAPABILITY_EXPIRY",
            f"assistant surface {surface_id} expires_at needs an ISO date or review-trigger: reason",
            surface_relpath,
        )
    elif expiry_is_date:
        expiry = datetime.strptime(expires_at[:10], "%Y-%m-%d").date()
        if expiry < datetime.now(timezone.utc).date():
            self.warn(
                "DIAGRAM_CAPABILITY_EXPIRED",
                f"assistant surface {surface_id} capability evidence expired",
                surface_relpath,
            )


def _validate_contract_text(self: Any) -> None:
    flow_text = self.read_text(self.target_path(REQUIRED_PATHS[0]))
    presentation_text = self.read_text(self.target_path(REQUIRED_PATHS[1]))
    required_snippets = [
        (
            REQUIRED_PATHS[0],
            flow_text,
            [
                "`read-only`",
                "current assistant surface record",
                "portable ASCII view",
                "hard maximum of 100 columns",
                "stable diagram ID",
                "Classify data sensitivity",
            ],
        ),
        (
            REQUIRED_PATHS[1],
            presentation_text,
            [
                "Presentation mode:",
                "Portable ASCII presentation:",
                "ASCII readability check:",
                "Diagram ID:",
                "Data classification:",
                "External renderer or network action:",
                "is not project source of truth",
            ],
        ),
        (
            REQUIRED_PATHS[2],
            self.read_text(self.target_path(REQUIRED_PATHS[2])),
            [
                "Hard maximum width: `100`",
                "printable 7-bit ASCII plus line feeds",
                "Longest line at most 100 columns",
            ],
        ),
    ]
    for relpath, text, snippets in required_snippets:
        for snippet in snippets:
            if snippet not in text:
                self.error(
                    "DIAGRAM_CONTRACT_INCOMPLETE",
                    f"discussion contract is missing {snippet}",
                    relpath,
                )
