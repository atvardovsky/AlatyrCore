"""Capability registry and dispatch for optional target adapter surfaces."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from capability_catalog import load_modules
from target_adapter_validation.ai_infrastructure import (
    AI_INFRASTRUCTURE_ROUTER_MODULE,
)
from target_adapter_validation.architecture_knowledge import ARCHITECTURE_KNOWLEDGE_MODULE
from target_adapter_validation.capability import (
    CapabilityModule,
    CapabilityValidationContext,
)
from target_adapter_validation.consistency_map import CONSISTENCY_MAP_MODULE
from target_adapter_validation.code_documentation import CODE_DOCUMENTATION_MODULE
from target_adapter_validation.dependency_knowledge import DEPENDENCY_KNOWLEDGE_MODULE
from target_adapter_validation.development_evidence import DEVELOPMENT_EVIDENCE_MODULE
from target_adapter_validation.diagrams import DISCUSSION_DIAGRAMS_MODULE
from target_adapter_validation.extensions import EXTENSIONS_MODULE
from target_adapter_validation.project_vocabulary import PROJECT_VOCABULARY_MODULE
from target_adapter_validation.support_generation import SUPPORT_GENERATION_MODULE
from target_adapter_validation.subagent_delegation import SUBAGENT_DELEGATION_MODULE
from target_adapter_validation.team_collaboration import TEAM_COLLABORATION_MODULE
from target_adapter_validation.test_first_development import TEST_FIRST_DEVELOPMENT_MODULE
from target_adapter_validation.workspace_modes import WORKSPACE_MODES_MODULE


class CapabilityRouteKind(str, Enum):
    """How an enabled capability reaches target adapter validation."""

    MODULAR = "modular"
    UNIVERSAL = "universal"
    STRUCTURAL_ONLY = "structural-only"
    COMPATIBILITY = "compatibility"


@dataclass(frozen=True)
class CapabilityRoute:
    """Closed routing declaration for one capability catalog entry."""

    capability_id: str
    kind: CapabilityRouteKind
    checks: tuple[str, ...] = ()


def _route(
    capability_id: str,
    kind: CapabilityRouteKind,
    *checks: str,
) -> CapabilityRoute:
    return CapabilityRoute(capability_id, kind, tuple(checks))


class ModuleValidator(Protocol):
    def capability_validation_context(self) -> CapabilityValidationContext: ...

    def check_ai_infrastructure_router(self) -> None: ...
    def check_development_evidence(self, manifest: Any) -> None: ...
    def check_dependency_knowledge(self, manifest: Any) -> None: ...
    def check_debug_mode(self, manifest: Any) -> None: ...
    def check_workspace_modes(self, manifest: Any) -> None: ...


MODULE_IMPLEMENTATIONS: dict[str, CapabilityModule] = {
    AI_INFRASTRUCTURE_ROUTER_MODULE.check_id: AI_INFRASTRUCTURE_ROUTER_MODULE,
    ARCHITECTURE_KNOWLEDGE_MODULE.check_id: ARCHITECTURE_KNOWLEDGE_MODULE,
    CODE_DOCUMENTATION_MODULE.check_id: CODE_DOCUMENTATION_MODULE,
    CONSISTENCY_MAP_MODULE.check_id: CONSISTENCY_MAP_MODULE,
    DEPENDENCY_KNOWLEDGE_MODULE.check_id: DEPENDENCY_KNOWLEDGE_MODULE,
    DEVELOPMENT_EVIDENCE_MODULE.check_id: DEVELOPMENT_EVIDENCE_MODULE,
    DISCUSSION_DIAGRAMS_MODULE.check_id: DISCUSSION_DIAGRAMS_MODULE,
    EXTENSIONS_MODULE.check_id: EXTENSIONS_MODULE,
    PROJECT_VOCABULARY_MODULE.check_id: PROJECT_VOCABULARY_MODULE,
    SUPPORT_GENERATION_MODULE.check_id: SUPPORT_GENERATION_MODULE,
    SUBAGENT_DELEGATION_MODULE.check_id: SUBAGENT_DELEGATION_MODULE,
    TEAM_COLLABORATION_MODULE.check_id: TEAM_COLLABORATION_MODULE,
    TEST_FIRST_DEVELOPMENT_MODULE.check_id: TEST_FIRST_DEVELOPMENT_MODULE,
    WORKSPACE_MODES_MODULE.check_id: WORKSPACE_MODES_MODULE,
}

CAPABILITY_ROUTES: dict[str, CapabilityRoute] = {
    "ai-infrastructure": _route(
        "ai-infrastructure",
        CapabilityRouteKind.MODULAR,
        "check_ai_infrastructure_router",
        "check_development_evidence",
    ),
    "architecture-knowledge": _route(
        "architecture-knowledge",
        CapabilityRouteKind.MODULAR,
        "check_architecture_knowledge",
    ),
    "assistant-runtime-capabilities": _route(
        "assistant-runtime-capabilities", CapabilityRouteKind.UNIVERSAL
    ),
    "blueprint-change": _route(
        "blueprint-change", CapabilityRouteKind.UNIVERSAL
    ),
    "change-packages": _route(
        "change-packages", CapabilityRouteKind.UNIVERSAL
    ),
    "code-documentation": _route(
        "code-documentation",
        CapabilityRouteKind.MODULAR,
        "check_code_documentation",
    ),
    "consistency-map": _route(
        "consistency-map", CapabilityRouteKind.MODULAR, "check_consistency_map"
    ),
    "debug-mode": _route(
        "debug-mode", CapabilityRouteKind.COMPATIBILITY, "check_debug_mode"
    ),
    "dependency-knowledge": _route(
        "dependency-knowledge",
        CapabilityRouteKind.MODULAR,
        "check_dependency_knowledge",
    ),
    "diagrams": _route(
        "diagrams",
        CapabilityRouteKind.MODULAR,
        "check_discussion_diagrams",
    ),
    "durable-approvals": _route(
        "durable-approvals", CapabilityRouteKind.UNIVERSAL
    ),
    "effectiveness-metrics": _route(
        "effectiveness-metrics", CapabilityRouteKind.STRUCTURAL_ONLY
    ),
    "extensions": _route(
        "extensions", CapabilityRouteKind.MODULAR, "check_extensions"
    ),
    "installed-operations": _route(
        "installed-operations", CapabilityRouteKind.UNIVERSAL
    ),
    "large-task-orchestration": _route(
        "large-task-orchestration", CapabilityRouteKind.UNIVERSAL
    ),
    "migration-diff": _route(
        "migration-diff", CapabilityRouteKind.UNIVERSAL
    ),
    "multi-assistant-bridges": _route(
        "multi-assistant-bridges", CapabilityRouteKind.UNIVERSAL
    ),
    "project-vocabulary": _route(
        "project-vocabulary",
        CapabilityRouteKind.MODULAR,
        "check_project_vocabulary",
    ),
    "scaffolding": _route(
        "scaffolding", CapabilityRouteKind.STRUCTURAL_ONLY
    ),
    "subagent-delegation": _route(
        "subagent-delegation",
        CapabilityRouteKind.MODULAR,
        "check_subagent_delegation",
    ),
    "support-generation": _route(
        "support-generation",
        CapabilityRouteKind.MODULAR,
        "check_support_generation",
    ),
    "team-collaboration": _route(
        "team-collaboration",
        CapabilityRouteKind.MODULAR,
        "check_team_collaboration",
    ),
    "test-first-development": _route(
        "test-first-development",
        CapabilityRouteKind.MODULAR,
        "check_test_first_development",
    ),
    "workspace-modes": _route(
        "workspace-modes",
        CapabilityRouteKind.MODULAR,
        "check_workspace_modes",
    ),
}

# Compatibility views remain derived from the typed registry while callers migrate.
CAPABILITY_CHECKS: dict[str, tuple[str, ...]] = {
    capability_id: route.checks
    for capability_id, route in CAPABILITY_ROUTES.items()
    if route.checks
}
COMPATIBILITY_FALLBACKS = {
    check_id
    for route in CAPABILITY_ROUTES.values()
    if route.kind is CapabilityRouteKind.COMPATIBILITY
    for check_id in route.checks
}
COMPATIBILITY_DISPATCH = {
    "check_debug_mode": lambda validator, manifest: validator.check_debug_mode(manifest),
}


def registry_contract_errors() -> list[str]:
    """Return catalog and dispatch declarations that are not exactly closed."""

    catalog_ids = set(load_modules())
    route_ids = set(CAPABILITY_ROUTES)
    errors = [
        f"catalog capability has no validation route: {capability_id}"
        for capability_id in sorted(catalog_ids - route_ids)
    ]
    errors.extend(
        f"validation route has no catalog capability: {capability_id}"
        for capability_id in sorted(route_ids - catalog_ids)
    )
    modular_checks: set[str] = set()
    compatibility_checks: set[str] = set()
    for capability_id, route in CAPABILITY_ROUTES.items():
        if route.capability_id != capability_id:
            errors.append(
                f"capability route key {capability_id} declares id {route.capability_id}"
            )
        if route.kind is CapabilityRouteKind.MODULAR:
            if not route.checks:
                errors.append(f"modular capability has no checks: {capability_id}")
            modular_checks.update(route.checks)
        elif route.kind is CapabilityRouteKind.COMPATIBILITY:
            if not route.checks:
                errors.append(f"compatibility capability has no checks: {capability_id}")
            compatibility_checks.update(route.checks)
        elif route.checks:
            errors.append(
                f"{route.kind.value} capability must not declare dispatch checks: "
                f"{capability_id}"
            )

    errors.extend(
        f"modular capability check has no implementation: {check_id}"
        for check_id in sorted(modular_checks - set(MODULE_IMPLEMENTATIONS))
    )
    errors.extend(
        f"module implementation is not declared by a modular capability: {check_id}"
        for check_id in sorted(set(MODULE_IMPLEMENTATIONS) - modular_checks)
    )
    errors.extend(
        f"capability check cannot be both modular and compatibility: {check_id}"
        for check_id in sorted(modular_checks & compatibility_checks)
    )
    return errors


def dispatch_capability_checks(
    validator: ModuleValidator,
    enabled_modules: Iterable[str],
    manifest: Any,
) -> tuple[str, ...]:
    """Run each required optional check once and return dispatched method names."""

    contract_errors = registry_contract_errors()
    if contract_errors:
        raise RuntimeError("; ".join(contract_errors))
    dispatched: list[str] = []
    for module_id in sorted(set(enabled_modules)):
        route = CAPABILITY_ROUTES.get(module_id)
        if route is None:
            continue
        for method_name in route.checks:
            if method_name in dispatched:
                continue
            implementation = MODULE_IMPLEMENTATIONS.get(method_name)
            if implementation is not None:
                implementation.validate(
                    validator.capability_validation_context(), manifest
                )
            else:
                fallback = COMPATIBILITY_DISPATCH.get(method_name)
                if fallback is None:
                    raise RuntimeError(
                        f"capability check has no explicit implementation: {method_name}"
                    )
                fallback(validator, manifest)
            dispatched.append(method_name)
    return tuple(dispatched)
