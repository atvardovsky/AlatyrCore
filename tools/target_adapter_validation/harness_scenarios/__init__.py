"""Ordered scenario orchestration for the target-adapter validator harness."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Tuple

from . import (
    approval_scope,
    assistant_surfaces,
    authorization,
    capabilities_delegation,
    context_catalogs,
    context_routing,
    evidence_contracts,
    extensions,
    framework_packaging,
    module_surfaces,
    operation_catalog,
    support_information,
    team_collaboration,
    testing_dependencies,
    workspace_modes,
)

Scenario = Callable[[Path, list], None]

SCENARIOS: Tuple[Tuple[str, Scenario], ...] = (
    ("context-catalogs", context_catalogs.run),
    ("assistant-surfaces", assistant_surfaces.run),
    ("authorization", authorization.run),
    ("context-routing", context_routing.run),
    ("framework-packaging", framework_packaging.run),
    ("capabilities-delegation", capabilities_delegation.run),
    ("operation-catalog", operation_catalog.run),
    ("module-surfaces", module_surfaces.run),
    ("testing-dependencies", testing_dependencies.run),
    ("workspace-modes", workspace_modes.run),
    ("extensions", extensions.run),
    ("support-information", support_information.run),
    ("team-collaboration", team_collaboration.run),
    ("approval-scope", approval_scope.run),
    ("evidence-contracts", evidence_contracts.run),
)


def run_scenarios(target: Path, failures: list[str]) -> None:
    """Run every scenario group in its established aggregate order."""

    for _, scenario in SCENARIOS:
        scenario(target, failures)
