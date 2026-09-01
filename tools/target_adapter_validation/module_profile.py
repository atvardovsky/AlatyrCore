"""Shared module-profile parsing for target adapter validation."""

from __future__ import annotations

import re
from dataclasses import dataclass


ENABLED_MODULE_STATES = {"enabled", "required"}


@dataclass(frozen=True)
class ModuleProfileState:
    module_id: str
    declared: bool
    state: str | None

    @property
    def has_parseable_state(self) -> bool:
        return self.state is not None

    @property
    def validation_enabled(self) -> bool:
        return self.state in ENABLED_MODULE_STATES


def parse_module_profile_state(text: str, module_id: str) -> ModuleProfileState:
    module_match = re.search(
        rf"^Module: `{re.escape(module_id)}`\s*$([\s\S]*?)(?=^Module: `|\Z)",
        text,
        flags=re.MULTILINE,
    )
    if module_match is None:
        return ModuleProfileState(module_id=module_id, declared=False, state=None)

    state_match = re.search(
        r"^State:\s*`?([^`\n]+)`?\s*$",
        module_match.group(1),
        flags=re.MULTILINE,
    )
    if state_match is None:
        return ModuleProfileState(module_id=module_id, declared=True, state=None)
    return ModuleProfileState(
        module_id=module_id,
        declared=True,
        state=state_match.group(1).strip().casefold(),
    )
