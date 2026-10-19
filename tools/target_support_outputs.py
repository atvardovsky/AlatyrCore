"""Canonical renderer composition for owned target support transactions."""

from __future__ import annotations

from pathlib import Path


def step_outputs(step_id: str, target: Path) -> dict[Path, bytes | None]:
    if step_id == "approval-archive":
        from approval_archive import INDEX_PATH, build_archive_index
        from render_approval_archive_index import render
        return {target / INDEX_PATH: render(build_archive_index(target)).encode("utf-8")}
    if step_id == "package-index":
        from render_change_package_index import expected_outputs
        return {path: text.encode("utf-8") for path, text in expected_outputs(target).items()}
    if step_id == "entry-packet":
        from agent_entry_packet import PACKET_PATH, build_from_target, render
        return {target / PACKET_PATH: render(build_from_target(target)).encode("utf-8")}
    if step_id in ("bootstrap-pass-1", "bootstrap-pass-2"):
        from bootstrap_index import BOOTSTRAP_PATH, BOOTSTRAP_INTEGRITY_PATH, build_bundle_from_target, render
        bundle, integrity = build_bundle_from_target(target)
        return {target / BOOTSTRAP_PATH: render(bundle).encode("utf-8"), target / BOOTSTRAP_INTEGRITY_PATH: render(integrity).encode("utf-8")}
    if step_id in ("context-pass-1", "context-pass-2"):
        from render_installed_context_catalogs import expected_outputs, generated_paths
        expected = expected_outputs(target)
        return {**{path: text.encode("utf-8") for path, text in expected.items()},
                **{path: None for path in generated_paths(target) - expected.keys()}}
    if step_id == "support-state":
        from support_state import STATE_PATH, build_support_state, render_state
        return {target / STATE_PATH: render_state(build_support_state(target)).encode("utf-8")}
    raise ValueError(f"no canonical output owner for {step_id}")
