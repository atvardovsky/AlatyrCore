"""Capability registry and dispatch for optional target adapter surfaces."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from target_adapter_validation.ai_infrastructure import (
    AI_INFRASTRUCTURE_ROUTER_MODULE,
)
from target_adapter_validation.capability import (
    CapabilityModule,
    CapabilityValidationContext,
)
from target_adapter_validation.consistency_map import CONSISTENCY_MAP_MODULE
from target_adapter_validation.support_generation import SUPPORT_GENERATION_MODULE


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
    CONSISTENCY_MAP_MODULE.check_id: CONSISTENCY_MAP_MODULE,
    SUPPORT_GENERATION_MODULE.check_id: SUPPORT_GENERATION_MODULE,
}


def dispatch_capability_checks(
    validator: ModuleValidator,
    enabled_modules: Iterable[str],
    manifest: Any,
) -> tuple[str, ...]:
    """Run each required optional check once and return dispatched method names."""

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
