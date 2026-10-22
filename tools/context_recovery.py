"""Bounded recovery proposals; never usable context packets or approvals."""

from __future__ import annotations

from typing import Iterable

from context_catalog import CatalogItem


def decomposition_proposal(items: Iterable[CatalogItem], *, max_files: int, max_words: int, max_characters: int | None) -> dict:
    selected = sorted(items, key=lambda item: item.item_id)
    result = {"kind": "owner-preserving-decomposition", "execution_ready": False,
              "requires_rerouting": True, "required_item_count": len(selected),
              "instruction": "Split the task by accepted fact/area boundaries, then reroute every phase with its required owner closure; do not execute these groups as packets."}
    if len(selected) > 128:
        return {**result, "state": "manual-decomposition-required", "reason": "more than 128 required items; retain the original route and decompose the task before replanning"}
    phases, group, words, characters = [], [], 0, 0
    for item in selected:
        if group and (len(group) >= max_files or words + item.estimated_words > max_words or max_characters is not None and characters + item.estimated_characters > max_characters):
            phases.append(group)
            group, words, characters = [], 0, 0
        group.append({"id": item.item_id, "path": item.path, "owner_refs": list(item.owner_refs)})
        words += item.estimated_words
        characters += item.estimated_characters
    if group:
        phases.append(group)
    return {**result, "state": "proposal-only", "groups": phases,
            "limitation": "Groups preserve every selected item, not independent readiness or a waiver of semantic and owner budgets."}
