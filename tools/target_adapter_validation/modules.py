"""Capability registry and dispatch for optional target adapter surfaces."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

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
from target_adapter_validation.extensions import EXTENSIONS_MODULE
from target_adapter_validation.project_vocabulary import PROJECT_VOCABULARY_MODULE
from target_adapter_validation.support_generation import SUPPORT_GENERATION_MODULE
from target_adapter_validation.team_collaboration import TEAM_COLLABORATION_MODULE
from target_adapter_validation.test_first_development import TEST_FIRST_DEVELOPMENT_MODULE


CAPABILITY_CHECKS: dict[str, tuple[str, ...]] = {
    "ai-infrastructure": (
        "check_ai_infrastructure_router",
        "check_development_evidence",
    ),
    "architecture-knowledge": ("check_architecture_knowledge",),
    "code-documentation": ("check_code_documentation",),
    "consistency-map": ("check_consistency_map",),
    "diagrams": ("check_discussion_diagrams",),
    "dependency-knowledge": ("check_dependency_knowledge",),
    "debug-mode": ("check_debug_mode",),
    "extensions": ("check_extensions",),
    "project-vocabulary": ("check_project_vocabulary",),
    "support-generation": ("check_support_generation",),
    "subagent-delegation": ("check_subagent_delegation",),
    "team-collaboration": ("check_team_collaboration",),
    "test-first-development": ("check_test_first_development",),
    "workspace-modes": ("check_workspace_modes",),
}


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
    EXTENSIONS_MODULE.check_id: EXTENSIONS_MODULE,
    PROJECT_VOCABULARY_MODULE.check_id: PROJECT_VOCABULARY_MODULE,
    SUPPORT_GENERATION_MODULE.check_id: SUPPORT_GENERATION_MODULE,
    TEAM_COLLABORATION_MODULE.check_id: TEAM_COLLABORATION_MODULE,
    TEST_FIRST_DEVELOPMENT_MODULE.check_id: TEST_FIRST_DEVELOPMENT_MODULE,
}

COMPATIBILITY_FALLBACKS = {
    "check_debug_mode",
    "check_discussion_diagrams",
    "check_subagent_delegation",
    "check_workspace_modes",
}


def registry_contract_errors() -> list[str]:
    """Return capability dispatch entries without an explicit implementation path."""

    declared = {
        check_id for check_ids in CAPABILITY_CHECKS.values() for check_id in check_ids
    }
    covered = set(MODULE_IMPLEMENTATIONS) | COMPATIBILITY_FALLBACKS
    errors = [
        f"capability check has no implementation or compatibility fallback: {check_id}"
        for check_id in sorted(declared - covered)
    ]
    errors.extend(
        f"module implementation is not declared by a capability: {check_id}"
        for check_id in sorted(set(MODULE_IMPLEMENTATIONS) - declared)
    )
    errors.extend(
        f"compatibility fallback is not declared by a capability: {check_id}"
        for check_id in sorted(COMPATIBILITY_FALLBACKS - declared)
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
        for method_name in CAPABILITY_CHECKS.get(module_id, ()):
            if method_name in dispatched:
                continue
            implementation = MODULE_IMPLEMENTATIONS.get(method_name)
            if implementation is not None:
                implementation.validate(
                    validator.capability_validation_context(), manifest
                )
            else:
                method = getattr(validator, method_name)
                method(manifest)
            dispatched.append(method_name)
    return tuple(dispatched)
