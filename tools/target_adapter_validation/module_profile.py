"""Shared module-profile parsing for target adapter validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ENABLED_MODULE_STATES = {"enabled", "required"}
MODULE_PROFILE_PATH = ".ai/assistant/module-profile.md"
STATE_START = "<!-- alatyr:module-state:start -->"
STATE_END = "<!-- alatyr:module-state:end -->"
MODULE_STATES = ENABLED_MODULE_STATES | {"staged", "deferred", "disabled", "not-applicable", "blocked"}
MODULE_BLOCK_RE = re.compile(r"^Module: `([^`\r\n]+)`[ \t]*\r?$([\s\S]*?)(?=^Module: `|\Z)", re.MULTILINE)
STATE_LINE_RE = re.compile(r"^State:[ \t]*`?([^`\r\n]+?)`?[ \t]*\r?$", re.MULTILINE)


@dataclass(frozen=True)
class ModuleStateProjection:
    path: Path
    before: bytes
    desired: bytes
    inputs: dict[Path, bytes]


def project_manifest_state(text: str, modules: dict[str, list[str]], *, allow_unresolved: bool = False) -> str:
    """Refresh opted-in machine state without rewriting target-owned rationale."""
    if STATE_START not in text and STATE_END not in text:
        return text
    if not isinstance(modules, dict):
        raise ValueError("manifest modules must be a mapping")
    if text.count(STATE_START) != 1 or text.count(STATE_END) != 1:
        raise ValueError("module-state projection requires one complete marker pair")
    start, end = text.index(STATE_START) + len(STATE_START), text.index(STATE_END)
    if start >= end:
        raise ValueError("module-state projection markers are out of order")
    summary_labels = []
    for line in text[start:end].splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"(Selected|Staged|Enabled) modules from manifest: `[^`\r\n]*`", line.strip())
        if match is None:
            raise ValueError("module-state summary contains authored or unknown content; preserve it outside the markers")
        summary_labels.append(match.group(1))
    if sorted(summary_labels) != ["Enabled", "Selected", "Staged"]:
        raise ValueError("module-state summary requires exactly one selected, staged and enabled field")
    unresolved = False
    for field in ("selected", "staged", "enabled"):
        values = modules.get(field)
        if (not isinstance(values, list)
                or any(not isinstance(value, str) or not value.strip()
                       or any(c in value for c in "`\r\n") for value in values)
                or len(values) != len(set(values))):
            raise ValueError(f"modules.{field} must contain unique resolved module IDs")
        from target_validation_support import is_unresolved_value
        if any(is_unresolved_value(value) for value in values):
            unresolved = True
    if unresolved:
        if allow_unresolved:
            return text
        raise ValueError("module lists must be resolved before projecting state")
    staged, enabled = set(modules["staged"]), set(modules["enabled"])
    if staged & enabled:
        raise ValueError("modules cannot be staged and enabled simultaneously")
    declarations = parse_module_profile(text)
    for module_id in staged | enabled:
        if len(declarations.get(module_id, [])) != 1 or declarations[module_id][0].state not in MODULE_STATES:
            raise ValueError(f"module {module_id} requires one explicit profile state")
    for module_id, rows in declarations.items():
        if len(rows) != 1:
            raise ValueError(f"duplicate module profile declaration: {module_id}")
        if rows[0].state is None:
            raise ValueError(f"module {module_id} requires exactly one same-line state field")
        if rows[0].state in ENABLED_MODULE_STATES | {"staged"} and module_id not in staged | enabled:
            raise ValueError(f"module {module_id} needs an explicit inactive disposition; cannot infer disablement")
    newline = "\r\n" if "\r\n" in text else "\n"
    summary = newline.join(
        f"{field.title()} modules from manifest: `" + (", ".join(sorted(modules[field])) or "none") + "`"
        for field in ("selected", "staged", "enabled")
    )
    rendered = text[:start] + newline + summary + newline + text[end:]
    for module_id in sorted(staged | enabled):
        old = declarations[module_id][0].state
        state = "staged" if module_id in staged else "required" if old == "required" else "enabled"
        pattern = re.compile(
            rf"(^Module: `{re.escape(module_id)}`[ \t]*\r?$[\s\S]*?^State:[ \t]*)`?([^`\r\n]+)`?[ \t]*\r?$",
            re.MULTILINE,
        )
        rendered, count = pattern.subn(lambda match: match.group(1) + f"`{state}`" + ("\r" if newline == "\r\n" else ""), rendered, count=1)
        if count != 1:
            raise ValueError(f"cannot project module state: {module_id}")
    return rendered


def state_projection(target: Path, *, migration_staging: bool = False) -> ModuleStateProjection | None:
    """Return a byte-bound single-file projection; unmarked legacy files are inert."""
    from target_adapter_validation.context import TargetRepositoryView
    from target_validation_support import parse_manifest
    context = TargetRepositoryView(target)
    path = target / MODULE_PROFILE_PATH
    if not context.is_target_file(path):
        return None
    before = context.read_bytes(path)
    inputs = {path: before}
    text = before.decode("utf-8")
    desired = text
    if STATE_START in text or STATE_END in text:
        manifest_path = target / ".ai/alatyr.yaml"
        inputs[manifest_path] = context.read_bytes(manifest_path)
        manifest = parse_manifest(context.text_source(manifest_path))
        if manifest.parse_failures or any(("modules", key) not in manifest.lists for key in ("selected", "staged", "enabled")):
            raise ValueError("module-state projection requires valid manifest module lists")
        modules = {key: [item.value for item in manifest.lists[("modules", key)]] for key in ("selected", "staged", "enabled")}
        desired = project_manifest_state(text, modules, allow_unresolved=migration_staging)
    if context.finalize():
        raise ValueError("module-state projection inputs changed during planning")
    return ModuleStateProjection(path, before, desired.encode("utf-8"), inputs)


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
    declarations = parse_module_profile(text).get(module_id, [])
    return declarations[0] if declarations else ModuleProfileState(module_id, False, None)


def parse_module_profile(text: str) -> dict[str, list[ModuleProfileState]]:
    """Parse every module block once while preserving duplicate declarations."""

    states: dict[str, list[ModuleProfileState]] = {}
    for match in MODULE_BLOCK_RE.finditer(text):
        module_id = match.group(1)
        block = match.group(2)
        state_match = STATE_LINE_RE.search(block) if len(re.findall(r"^State:", block, re.MULTILINE)) == 1 else None
        state = state_match.group(1).strip().casefold() if state_match else None
        states.setdefault(module_id, []).append(
            ModuleProfileState(
                module_id=module_id,
                declared=True,
                state=state or None,
            )
        )
    return states
