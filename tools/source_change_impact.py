"""Derived source-maintainer change view; never an authorization or edit list."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from path_spec import PathDialect, matches_any, logical_path
from source_context_selection import read_source_object
from source_check_manifest import matches, routes


def source_change_impact(root: Path, paths: list[str], checks: list[dict]) -> dict[str, Any]:
    """Join existing owners without introducing a parallel ownership registry."""
    if (not isinstance(paths, list) or any(not isinstance(p, str) or not p for p in paths)
            or len(set(paths)) > 128):
        raise ValueError("source impact requires at most 128 exact changed paths; decompose larger work")
    for path in paths:
        logical_path(path)
    capabilities = read_source_object(root, "framework/capabilities.json")["modules"]
    compatibility = read_source_object(root, "tools/target-adapter-contract-compatibility.json")["contracts"]
    rows = []
    groups = {}
    for path in sorted(set(paths)):
        modules = []
        contracts = []
        for name, module in sorted(capabilities.items()):
            framework = {"framework/" + p for p in module.get("framework_files", [])}
            templates = {"templates/target/" + p for p in module.get("target_files", [])}
            if path in framework | templates:
                modules.append(name)
                groups["capability:" + name] = {
                    "canonical_owner_candidates": sorted(framework),
                    "companion_review_candidates": sorted(framework | templates)}
        for name, contract in sorted(compatibility.items()):
            artifacts = {a[k] for a in contract["artifacts"].values()
                         for k in ("schema", "template") if k in a}
            if path in artifacts:
                contracts.append(name)
                groups["contract:" + name] = {"companion_review_candidates": sorted(artifacts)}
        bound_checks = [c for c in checks if matches(c, path) or routes(c, path)]
        tests = sorted({p for c in bound_checks for p in c["contract_inputs"]
                        if p.startswith("tests/")})
        validator_change = path.startswith("tools/target_adapter_validation/") and path.endswith(".py")
        rows.append({"path": path, "capabilities": modules, "contracts": contracts,
                     "review_groups": ["capability:" + name for name in modules]
                         + ["contract:" + name for name in contracts],
                     "check_ids": [c["id"] for c in bound_checks],
                     "test_selectors": tests,
                     "semantic_relationships": "mapped" if modules or contracts else "review-required",
                     "acceptance_impact_review": validator_change,
                     "contract_review_required": bool(contracts or validator_change)})
    from refresh_source_projections import STAGES
    generated = sorted(path for path in set(paths) if any(
        matches_any(path, stage.outputs, dialect=PathDialect.SOURCE_HOST_V1) for stage in STAGES))
    return {"schema_version": 1, "view_kind": "source-change-impact",
            "rows": rows, "review_groups": groups,
            "contract_review_dimensions": ["valid-public-path", "malformed-and-boundary",
                "disabled-and-minimal", "freshness-and-concurrency", "cross-contract-parity"],
            "generated_paths": generated,
            "authored_or_unclassified_paths": sorted(set(paths) - set(generated)),
            "projection_review": [{"id": s.name, "generator": "tools/" + s.command[0],
                "depends_on": list(s.dependencies)} for s in STAGES]
                if paths else [],
            "projection_scope": "conservative-complete-source-closure",
            "unmapped_semantic_paths": [r["path"] for r in rows if r["semantic_relationships"] != "mapped"],
            "claim_boundary": "Review candidates, not mandatory edits, complete semantic impact, authorization, or acceptance."}
