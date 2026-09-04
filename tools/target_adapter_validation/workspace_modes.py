"""Workspace-mode capability validation."""

from __future__ import annotations

import re
from typing import Any

from target_validation_support import dotted, is_target_relative_path
from target_adapter_validation.action_modes import ALLOWED_ACTION_MODES
from target_adapter_validation.capability import FunctionCapabilityModule
from target_adapter_validation.files import missing_target_files
from target_adapter_validation.manifest_paths import manifest_path_mismatches
from target_adapter_validation.values import is_resolved_string, is_string_list


REQUIRED_PATHS = (
    ".ai/framework/workspace-modes.md",
    ".ai/project/workspace-modes/README.md",
    ".ai/project/workspace-modes/catalog.json",
    ".ai/project/workspace-modes/root/README.md",
    ".ai/project/workspace-modes/root/context.json",
    ".ai/project/workspace-modes/modes/_template/README.md",
    ".ai/project/workspace-modes/modes/_template/mode.json",
    ".ai/assistant/context/intents/workspace-mode-request.json",
    ".ai/assistant/flows/workspace-mode.flow.md",
    ".ai/assistant/gates/workspace-mode.md",
    ".ai/assistant/templates/workspace-mode-suggestion.md",
    ".ai/assistant/templates/workspace-mode-preflight.md",
)

EXPECTED_MANIFEST = {
    ("workspace_modes", "index"): REQUIRED_PATHS[1],
    ("workspace_modes", "catalog"): REQUIRED_PATHS[2],
    ("workspace_modes", "root_context"): REQUIRED_PATHS[4],
    ("workspace_modes", "modes"): ".ai/project/workspace-modes/modes",
    ("workspace_modes", "mode_template"): REQUIRED_PATHS[6],
    ("workspace_modes", "intent"): REQUIRED_PATHS[7],
    ("workspace_modes", "flow"): REQUIRED_PATHS[8],
    ("workspace_modes", "gate"): REQUIRED_PATHS[9],
    ("workspace_modes", "suggestion"): REQUIRED_PATHS[10],
    ("workspace_modes", "preflight"): REQUIRED_PATHS[11],
    ("operations", "workspace_mode"): REQUIRED_PATHS[8],
    ("operations", "workspace_mode_preflight"): REQUIRED_PATHS[11],
}

MODE_KINDS = {
    "application-development",
    "framework-development",
    "library-development",
    "skeleton-development",
    "dependency-integration",
    "dependency-contribution",
    "skeleton-migration",
    "workspace-coordination",
    "custom",
}
MODE_STATES = {"proposed", "accepted", "disabled", "deprecated", "blocked"}
RELATIONSHIP_TYPES = {
    "workspace-root",
    "workspace-member",
    "dependency",
    "scaffold-origin",
    "vendored-source",
}
ADAPTER_ROLES = {"active", "passive", "provenance-only"}
OWNERSHIP_VALUES = {"target", "upstream", "mixed"}


def validate_workspace_modes(validator: Any, manifest: Any) -> None:
    self = validator
    if _missing_required_files(self):
        return

    _validate_manifest_paths(self, manifest)
    catalog_relpath = REQUIRED_PATHS[2]
    root_relpath = REQUIRED_PATHS[4]
    catalog = self.load_json_object(
        self.target_path(catalog_relpath), "WORKSPACE_MODE_CATALOG"
    )
    root_context = self.load_json_object(
        self.target_path(root_relpath), "WORKSPACE_MODE_ROOT_CONTEXT"
    )
    if catalog is None or root_context is None:
        return

    workspace_id = _validate_catalog(self, catalog, catalog_relpath)
    root_state = _validate_root_context(self, root_context, root_relpath)
    accepted_ids = _validate_modes(
        self,
        catalog,
        catalog_relpath,
        root_state,
        workspace_id,
    )
    _validate_default_mode(self, catalog, accepted_ids, catalog_relpath)
    _validate_operation_and_router(self, catalog_relpath, root_relpath)
    self.info(
        "WORKSPACE_MODE_EVIDENCE_LIMIT",
        "workspace-mode structural checks do not prove strategic correctness, complete workspace discovery, ownership truth, semantic consistency, or assistant compliance",
    )


WORKSPACE_MODES_MODULE = FunctionCapabilityModule(
    "check_workspace_modes", validate_workspace_modes
)


def _target_path_list(
    self: Any,
    value: Any,
    code: str,
    label: str,
    source: str,
    *,
    non_empty: bool = False,
    require_exists: bool = False,
) -> list[str]:
    if not isinstance(value, list) or (non_empty and not value):
        self.error(code, f"{label} must be a {'non-empty ' if non_empty else ''}list", source)
        return []
    result: list[str] = []
    for entry in value:
        if not is_resolved_string(entry) or not is_target_relative_path(entry):
            self.error(code, f"{label} must contain target-relative resolved paths", source)
            continue
        if require_exists and not self.target_path(entry).exists():
            self.error(code, f"{label} points to missing target evidence {entry}", source)
            continue
        result.append(entry)
    return result


def _missing_required_files(self: Any) -> bool:
    missing = missing_target_files(self, REQUIRED_PATHS)
    for relpath in missing:
        self.error(
            "WORKSPACE_MODE_REQUIRED_FILE_MISSING",
            "enabled workspace-modes module is missing a contract",
            relpath,
        )
    return bool(missing)


def _validate_manifest_paths(self: Any, manifest: Any) -> None:
    if manifest is None:
        return
    for mismatch in manifest_path_mismatches(manifest, EXPECTED_MANIFEST):
        self.error(
            "WORKSPACE_MODE_MANIFEST_PATH",
            f"{dotted(mismatch.key)} must be {mismatch.expected} when workspace modes are enabled",
            ".ai/alatyr.yaml",
        )


def _validate_catalog(self: Any, catalog: dict[str, Any], catalog_relpath: str) -> str | None:
    if (
        catalog.get("schema_version") != 1
        or catalog.get("catalog_kind") != "target-workspace-mode-catalog"
    ):
        self.error(
            "WORKSPACE_MODE_CATALOG_SCHEMA",
            "catalog schema or kind is invalid",
            catalog_relpath,
        )
    if catalog.get("state") not in {"enabled", "required"}:
        self.error(
            "WORKSPACE_MODE_CATALOG_STATE",
            "enabled module requires enabled or required catalog state",
            catalog_relpath,
        )
    for field in ["owner", "decision_authority"]:
        if not is_resolved_string(catalog.get(field)):
            self.error(
                "WORKSPACE_MODE_CATALOG_OWNER",
                f"catalog {field} must be resolved",
                catalog_relpath,
            )
    if catalog.get("root_context") != REQUIRED_PATHS[4]:
        self.error(
            "WORKSPACE_MODE_ROOT_REFERENCE",
            "catalog root_context path is invalid",
            catalog_relpath,
        )
    _validate_selection(self, catalog, catalog_relpath)
    _validate_suggestions(self, catalog, catalog_relpath)
    return _validate_workspace(self, catalog, catalog_relpath)


def _validate_workspace(
    self: Any, catalog: dict[str, Any], catalog_relpath: str
) -> str | None:
    workspace = catalog.get("workspace")
    if not isinstance(workspace, dict):
        self.error(
            "WORKSPACE_MODE_WORKSPACE",
            "catalog workspace must be an object",
            catalog_relpath,
        )
        return None

    workspace_id = workspace.get("id") if is_resolved_string(workspace.get("id")) else None
    if workspace_id is None:
        self.error(
            "WORKSPACE_MODE_WORKSPACE",
            "workspace id must be resolved",
            catalog_relpath,
        )
    if workspace.get("kind") not in {
        "application",
        "framework",
        "library",
        "skeleton",
        "tool",
        "monorepo",
        "mixed",
    }:
        self.error("WORKSPACE_MODE_WORKSPACE", "workspace kind is invalid", catalog_relpath)
    if workspace.get("root") != "." or workspace.get("adapter_role") != "active":
        self.error(
            "WORKSPACE_MODE_ACTIVE_ROOT",
            "catalog workspace must identify the selected root '.' and active adapter",
            catalog_relpath,
        )
    _target_path_list(
        self,
        workspace.get("evidence"),
        "WORKSPACE_MODE_WORKSPACE_EVIDENCE",
        "workspace.evidence",
        catalog_relpath,
        non_empty=True,
        require_exists=True,
    )
    return workspace_id


def _validate_selection(self: Any, catalog: dict[str, Any], catalog_relpath: str) -> None:
    selection = catalog.get("selection")
    if not isinstance(selection, dict):
        self.error("WORKSPACE_MODE_SELECTION", "selection must be an object", catalog_relpath)
        selection = {}
    expected_selection = {
        "automatic_selection": "accepted-unambiguous-only",
        "ambiguity_behavior": "ask-user",
        "no_match_behavior": "root-read-only",
        "persistence": "per-task",
        "local_preference_allowed": False,
        "show_preflight_before_changes": True,
    }
    for field, expected in expected_selection.items():
        if selection.get(field) != expected:
            self.error(
                "WORKSPACE_MODE_SELECTION_POLICY",
                f"selection.{field} must be {expected!r}",
                catalog_relpath,
            )


def _validate_suggestions(self: Any, catalog: dict[str, Any], catalog_relpath: str) -> None:
    suggestions = catalog.get("suggestions")
    if not isinstance(suggestions, dict):
        self.error(
            "WORKSPACE_MODE_SUGGESTIONS",
            "suggestions must be an object",
            catalog_relpath,
        )
        return
    for field in ["after_installation", "after_framework_update", "after_workspace_change"]:
        if suggestions.get(field) is not True:
            self.error(
                "WORKSPACE_MODE_SUGGESTIONS",
                f"suggestions.{field} must be true",
                catalog_relpath,
            )
    if suggestions.get("automatic_acceptance") is not False:
        self.error(
            "WORKSPACE_MODE_AUTO_ACCEPT",
            "mode suggestions must never be accepted automatically",
            catalog_relpath,
        )


def _validate_root_context(
    self: Any, root_context: dict[str, Any], root_relpath: str
) -> str | None:
    if (
        root_context.get("schema_version") != 1
        or root_context.get("descriptor_kind") != "target-workspace-root-context"
    ):
        self.error(
            "WORKSPACE_MODE_ROOT_SCHEMA",
            "root context schema or kind is invalid",
            root_relpath,
        )
    root_state = root_context.get("state")
    if root_state not in {"enabled", "disabled"}:
        self.error(
            "WORKSPACE_MODE_ROOT_STATE",
            "root context state must be enabled or disabled",
            root_relpath,
        )
    if not is_resolved_string(root_context.get("owner")):
        self.error(
            "WORKSPACE_MODE_ROOT_OWNER",
            "root context owner must be resolved",
            root_relpath,
        )
    root_required = _target_path_list(
        self,
        root_context.get("required_context"),
        "WORKSPACE_MODE_ROOT_CONTEXT",
        "required_context",
        root_relpath,
        require_exists=root_state == "enabled",
    )
    root_conditional = _validate_root_conditional_context(
        self, root_context, root_relpath, root_state
    )
    if root_state == "disabled" and (root_required or root_conditional):
        self.error(
            "WORKSPACE_MODE_ROOT_DISABLED_CONTENT",
            "disabled root context must not route support paths",
            root_relpath,
        )
    return root_state if isinstance(root_state, str) else None


def _validate_root_conditional_context(
    self: Any,
    root_context: dict[str, Any],
    root_relpath: str,
    root_state: Any,
) -> list[Any]:
    root_conditional = root_context.get("conditional_context")
    if not isinstance(root_conditional, list):
        self.error(
            "WORKSPACE_MODE_ROOT_CONTEXT",
            "conditional_context must be a list",
            root_relpath,
        )
        return []
    for index, entry in enumerate(root_conditional):
        if (
            not isinstance(entry, dict)
            or not is_resolved_string(entry.get("path"))
            or not is_target_relative_path(entry["path"])
            or not is_resolved_string(entry.get("when"))
        ):
            self.error(
                "WORKSPACE_MODE_ROOT_CONTEXT",
                f"conditional_context[{index}] requires target-relative path and condition",
                root_relpath,
            )
        elif root_state == "enabled" and not self.target_path(entry["path"]).exists():
            self.error(
                "WORKSPACE_MODE_ROOT_CONTEXT",
                f"conditional_context[{index}] points to missing target context",
                root_relpath,
            )
    return root_conditional


def _validate_modes(
    self: Any,
    catalog: dict[str, Any],
    catalog_relpath: str,
    root_state: str | None,
    workspace_id: str | None,
) -> set[str]:
    modes = catalog.get("modes")
    if not isinstance(modes, list) or not modes:
        self.error(
            "WORKSPACE_MODE_EMPTY",
            "enabled workspace-modes module requires at least one catalog mode",
            catalog_relpath,
        )
        modes = []
    state = _ModeValidationState()
    for index, entry in enumerate(modes):
        _validate_catalog_mode_entry(
            self, entry, index, catalog_relpath, root_state, workspace_id, state
        )
    return state.accepted_ids


class _ModeValidationState:
    def __init__(self) -> None:
        self.seen_ids: set[str] = set()
        self.seen_paths: set[str] = set()
        self.accepted_ids: set[str] = set()


def _validate_catalog_mode_entry(
    self: Any,
    entry: Any,
    index: int,
    catalog_relpath: str,
    root_state: str | None,
    workspace_id: str | None,
    validation_state: _ModeValidationState,
) -> None:
    location = f"{catalog_relpath}:modes[{index}]"
    if not isinstance(entry, dict):
        self.error("WORKSPACE_MODE_CATALOG_ENTRY", "mode entry must be an object", location)
        return
    mode_id = entry.get("id")
    state = entry.get("state")
    mode_kind = entry.get("mode_kind")
    path = entry.get("path")
    if not _valid_mode_id(mode_id):
        self.error("WORKSPACE_MODE_ID", "mode ID must be resolved kebab-case", location)
        return
    if mode_id in validation_state.seen_ids:
        self.error("WORKSPACE_MODE_DUPLICATE", f"duplicate mode ID {mode_id}", location)
    validation_state.seen_ids.add(mode_id)
    if state not in MODE_STATES or mode_kind not in MODE_KINDS:
        self.error(
            "WORKSPACE_MODE_CATALOG_ENTRY",
            "mode state or kind is invalid",
            location,
        )
    for field in ["title", "summary", "evidence_revision"]:
        if not is_resolved_string(entry.get(field)):
            self.error(
                "WORKSPACE_MODE_CATALOG_ENTRY",
                f"mode {field} must be resolved",
                location,
            )
    expected_path = f".ai/project/workspace-modes/modes/{mode_id}/mode.json"
    if path != expected_path or path in validation_state.seen_paths or "_template" in str(path):
        self.error(
            "WORKSPACE_MODE_PATH",
            f"mode path must be unique and equal {expected_path}",
            location,
        )
    if isinstance(path, str):
        validation_state.seen_paths.add(path)
    descriptor = self.load_json_object(self.target_path(expected_path), "WORKSPACE_MODE")
    readme_path = f".ai/project/workspace-modes/modes/{mode_id}/README.md"
    if not self.target_path(readme_path).is_file():
        self.error(
            "WORKSPACE_MODE_README_MISSING",
            "actual mode directory requires README.md",
            readme_path,
        )
    if descriptor is None:
        self.error(
            "WORKSPACE_MODE_DESCRIPTOR_MISSING",
            "catalog mode descriptor is missing",
            expected_path,
        )
        return
    if state == "accepted":
        validation_state.accepted_ids.add(mode_id)
    _validate_mode_descriptor(
        self, descriptor, expected_path, mode_id, state, mode_kind, root_state, workspace_id
    )


def _valid_mode_id(value: Any) -> bool:
    return (
        is_resolved_string(value)
        and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) is not None
    )


def _validate_mode_descriptor(
    self: Any,
    descriptor: dict[str, Any],
    expected_path: str,
    mode_id: str,
    state: Any,
    mode_kind: Any,
    root_state: str | None,
    workspace_id: str | None,
) -> None:
    if (
        descriptor.get("schema_version") != 1
        or descriptor.get("descriptor_kind") != "target-workspace-mode"
    ):
        self.error(
            "WORKSPACE_MODE_DESCRIPTOR_SCHEMA",
            "mode descriptor schema or kind is invalid",
            expected_path,
        )
    if (
        descriptor.get("id") != mode_id
        or descriptor.get("state") != state
        or descriptor.get("mode_kind") != mode_kind
    ):
        self.error(
            "WORKSPACE_MODE_DESCRIPTOR_DRIFT",
            "catalog and descriptor identity state or kind differ",
            expected_path,
        )
    for field in [
        "title",
        "purpose",
        "owner",
        "decision_authority",
        "last_reviewed",
        "evidence_revision",
    ]:
        if not is_resolved_string(descriptor.get(field)):
            self.error(
                "WORKSPACE_MODE_DESCRIPTOR_FIELD",
                f"mode {field} must be resolved",
                expected_path,
            )
    _validate_mode_scope(self, descriptor, expected_path, state)
    _validate_mode_signals(self, descriptor, expected_path)
    _validate_mode_relationships(self, descriptor, expected_path, state, workspace_id)
    _validate_mode_context(self, descriptor, expected_path, state, root_state)
    _validate_mode_lists_and_constraints(self, descriptor, expected_path)


def _validate_mode_scope(
    self: Any, descriptor: dict[str, Any], expected_path: str, state: Any
) -> None:
    scope = descriptor.get("workspace_scope")
    if (
        not isinstance(scope, dict)
        or not is_resolved_string(scope.get("root"))
        or not is_target_relative_path(scope["root"])
    ):
        self.error(
            "WORKSPACE_MODE_SCOPE",
            "workspace_scope requires a target-relative root",
            expected_path,
        )
        return
    if state == "accepted" and not self.target_path(scope["root"]).exists():
        self.error(
            "WORKSPACE_MODE_SCOPE",
            f"accepted workspace_scope.root points to missing target scope {scope['root']}",
            expected_path,
        )
    _target_path_list(
        self,
        scope.get("include"),
        "WORKSPACE_MODE_SCOPE",
        "workspace_scope.include",
        expected_path,
        non_empty=state == "accepted",
    )
    _target_path_list(
        self,
        scope.get("exclude"),
        "WORKSPACE_MODE_SCOPE",
        "workspace_scope.exclude",
        expected_path,
    )


def _validate_mode_signals(self: Any, descriptor: dict[str, Any], expected_path: str) -> None:
    for field in ["use_when", "do_not_use_when"]:
        value = descriptor.get(field)
        if not is_string_list(value, resolved=True):
            self.error(
                "WORKSPACE_MODE_SIGNALS",
                f"{field} must be a non-empty resolved string list",
                expected_path,
            )


def _validate_mode_relationships(
    self: Any,
    descriptor: dict[str, Any],
    expected_path: str,
    state: Any,
    workspace_id: str | None,
) -> None:
    relationships = descriptor.get("relationships")
    active_roots = 0
    if not isinstance(relationships, list) or not relationships:
        self.error(
            "WORKSPACE_MODE_RELATIONSHIPS",
            "relationships must be a non-empty list",
            expected_path,
        )
    else:
        active_roots = _validate_relationship_entries(
            self, relationships, expected_path, workspace_id
        )
    if state == "accepted" and active_roots != 1:
        self.error(
            "WORKSPACE_MODE_ACTIVE_ROOT",
            "accepted mode must define exactly one active workspace-root relationship",
            expected_path,
        )


def _validate_relationship_entries(
    self: Any,
    relationships: list[Any],
    expected_path: str,
    workspace_id: str | None,
) -> int:
    active_roots = 0
    for relationship_index, relationship in enumerate(relationships):
        rel_location = f"{expected_path}:relationships[{relationship_index}]"
        if not isinstance(relationship, dict):
            self.error("WORKSPACE_MODE_RELATIONSHIP", "relationship must be an object", rel_location)
            continue
        if not is_resolved_string(relationship.get("subject")):
            self.error(
                "WORKSPACE_MODE_RELATIONSHIP",
                "relationship subject must be resolved",
                rel_location,
            )
        rel_type = relationship.get("relationship")
        role = relationship.get("adapter_role")
        if (
            rel_type not in RELATIONSHIP_TYPES
            or role not in ADAPTER_ROLES
            or relationship.get("ownership") not in OWNERSHIP_VALUES
        ):
            self.error(
                "WORKSPACE_MODE_RELATIONSHIP",
                "relationship type adapter role or ownership is invalid",
                rel_location,
            )
        _target_path_list(
            self,
            relationship.get("evidence"),
            "WORKSPACE_MODE_RELATIONSHIP_EVIDENCE",
            "relationship.evidence",
            rel_location,
            non_empty=True,
            require_exists=True,
        )
        if role == "active":
            if rel_type != "workspace-root":
                self.error(
                    "WORKSPACE_MODE_NESTED_ADAPTER",
                    "only workspace-root may have an active adapter role",
                    rel_location,
                )
            else:
                active_roots += 1
                if workspace_id is not None and relationship.get("subject") != workspace_id:
                    self.error(
                        "WORKSPACE_MODE_ACTIVE_ROOT",
                        "active root subject must match catalog workspace ID",
                        rel_location,
                    )
        if rel_type in {"dependency", "scaffold-origin"} and role not in {
            "passive",
            "provenance-only",
        }:
            self.error(
                "WORKSPACE_MODE_NESTED_ADAPTER",
                "dependency and scaffold adapters must remain passive or provenance-only",
                rel_location,
            )
    return active_roots


def _validate_mode_context(
    self: Any,
    descriptor: dict[str, Any],
    expected_path: str,
    state: Any,
    root_state: str | None,
) -> None:
    context = descriptor.get("context")
    if not isinstance(context, dict) or context.get("root_context") not in {
        "inherit",
        "required",
        "skip",
    }:
        self.error(
            "WORKSPACE_MODE_CONTEXT",
            "context requires inherit required or skip root_context",
            expected_path,
        )
        return
    if (
        state == "accepted"
        and context.get("root_context") == "required"
        and root_state != "enabled"
    ):
        self.error(
            "WORKSPACE_MODE_CONTEXT",
            "accepted mode cannot require disabled shared root context",
            expected_path,
        )
    _target_path_list(
        self,
        context.get("required_context"),
        "WORKSPACE_MODE_CONTEXT",
        "context.required_context",
        expected_path,
        require_exists=state == "accepted",
    )
    _validate_mode_conditional_context(self, context, expected_path, state)


def _validate_mode_conditional_context(
    self: Any,
    context: dict[str, Any],
    expected_path: str,
    state: Any,
) -> None:
    conditional = context.get("conditional_context")
    if not isinstance(conditional, list):
        self.error(
            "WORKSPACE_MODE_CONTEXT",
            "context.conditional_context must be a list",
            expected_path,
        )
        return
    for conditional_index, conditional_entry in enumerate(conditional):
        if (
            not isinstance(conditional_entry, dict)
            or not is_resolved_string(conditional_entry.get("path"))
            or not is_target_relative_path(conditional_entry["path"])
            or not is_resolved_string(conditional_entry.get("when"))
        ):
            self.error(
                "WORKSPACE_MODE_CONTEXT",
                f"conditional context {conditional_index} is invalid",
                expected_path,
            )
        elif state == "accepted" and not self.target_path(
            conditional_entry["path"]
        ).exists():
            self.error(
                "WORKSPACE_MODE_CONTEXT",
                f"conditional context {conditional_index} points to missing target context",
                expected_path,
            )


def _validate_mode_lists_and_constraints(
    self: Any, descriptor: dict[str, Any], expected_path: str
) -> None:
    for field in ["source_of_truth_ids", "validation_entry_point_ids", "known_gaps"]:
        value = descriptor.get(field)
        if not is_string_list(value, non_empty=False, resolved=True):
            self.error(
                "WORKSPACE_MODE_DESCRIPTOR_FIELD",
                f"{field} must be a resolved string list",
                expected_path,
            )
    constraints = descriptor.get("constraints")
    if not isinstance(constraints, dict):
        self.error(
            "WORKSPACE_MODE_CONSTRAINTS",
            "constraints must be an object",
            expected_path,
        )
        return
    narrowing = constraints.get("narrows_allowed_actions")
    if not isinstance(narrowing, list) or any(item not in ALLOWED_ACTION_MODES for item in narrowing):
        self.error(
            "WORKSPACE_MODE_CONSTRAINTS",
            "narrows_allowed_actions contains an invalid mode",
            expected_path,
        )
    for field in [
        "grants_write_scope",
        "grants_approval",
        "grants_permissions",
        "grants_authority",
        "grants_tools",
        "activates_nested_adapters",
        "bypasses_gates",
    ]:
        if constraints.get(field) is not False:
            self.error(
                "WORKSPACE_MODE_GRANT",
                f"constraints.{field} must be false",
                expected_path,
            )


def _validate_default_mode(
    self: Any,
    catalog: dict[str, Any],
    accepted_ids: set[str],
    catalog_relpath: str,
) -> None:
    selection = catalog.get("selection")
    default_mode = (
        selection.get("default_mode_id") if isinstance(selection, dict) else None
    )
    if default_mode is not None and default_mode not in accepted_ids:
        self.error(
            "WORKSPACE_MODE_DEFAULT",
            "default_mode_id must reference an accepted mode",
            catalog_relpath,
        )


def _validate_operation_and_router(
    self: Any, catalog_relpath: str, root_relpath: str
) -> None:
    operations = self.load_json_object(
        self.target_path(".ai/assistant/operation-catalog.json"), "OPERATION_CATALOG"
    )
    operation = next(
        (
            item
            for item in (operations.get("operations", []) if isinstance(operations, dict) else [])
            if isinstance(item, dict) and item.get("id") == "workspace-mode"
        ),
        None,
    )
    if not isinstance(operation, dict) or operation.get("required_module") != "workspace-modes":
        self.error(
            "WORKSPACE_MODE_OPERATION_UNROUTED",
            "workspace-mode operation must require the enabled module",
            ".ai/assistant/operation-catalog.json",
        )
    router = self.load_json_object(self.target_path(".ai/assistant/context-router.json"), "ROUTER")
    overlays = router.get("intent_overlays") if isinstance(router, dict) else None
    route = overlays.get("workspace-mode-request") if isinstance(overlays, dict) else None
    mode_routing = router.get("workspace_mode_routing") if isinstance(router, dict) else None
    if not isinstance(route, dict) or route.get("operation_candidates") != ["workspace-mode"]:
        self.error(
            "WORKSPACE_MODE_INTENT_UNROUTED",
            "workspace mode intent must route the workspace-mode operation",
            ".ai/assistant/context-router.json",
        )
    if (
        not isinstance(mode_routing, dict)
        or mode_routing.get("catalog") != catalog_relpath
        or mode_routing.get("root_context") != root_relpath
        or mode_routing.get("ambiguity_behavior") != "ask-user-and-remain-read-only"
    ):
        self.error(
            "WORKSPACE_MODE_ROUTER",
            "workspace mode routing must bind catalog root context and safe ambiguity behavior",
            ".ai/assistant/context-router.json",
        )
