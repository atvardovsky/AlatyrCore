"""Target-validator scenarios for current baseline claim synchronization."""

from __future__ import annotations

from pathlib import Path

from .common import parse_manifest, validator
from target_adapter_validation.baseline_claims import validate_baseline_claims


def run(target: Path, failures: list[str]) -> None:
    claim_target = target / "baseline-claims"
    lifecycle = claim_target / ".ai/assistant/lifecycle.md"
    lifecycle.parent.mkdir(parents=True)
    lifecycle.write_text(
        "# Lifecycle\n\nFramework version: `0.1.0-alpha.69`.\n"
        "Adapter schema version: `57`.\nTemplate version: `64`.\n",
        encoding="utf-8",
    )
    manifest_path = claim_target / ".ai/alatyr.yaml"
    manifest_path.write_text(
        "schema_version: '58'\n"
        "framework:\n"
        "  version: 0.1.0-alpha.70\n"
        "  baseline: 1b11ebec84e8e927dcc635354fb1922bf297e25d\n"
        "  template_version: '65'\n"
        "validation:\n"
        "  baseline_claim_surfaces:\n"
        "    - .ai/assistant/lifecycle.md\n",
        encoding="utf-8",
    )
    manifest = parse_manifest(manifest_path)
    stale = validator(claim_target)
    validate_baseline_claims(stale, manifest)
    drift = [
        finding for finding in stale.findings if finding.code == "BASELINE_CLAIM_DRIFT"
    ]
    if len(drift) != 3:
        failures.append("baseline claim drift must detect framework, schema, and template")

    lifecycle.write_text(
        "# Lifecycle\n\nFramework version: `0.1.0-alpha.70`.\n"
        "Adapter schema version: `58`.\nTemplate version: `65`.\n"
        "Previous framework version: `0.1.0-alpha.69`.\n",
        encoding="utf-8",
    )
    current = validator(claim_target)
    validate_baseline_claims(current, manifest)
    if any(finding.code == "BASELINE_CLAIM_DRIFT" for finding in current.findings):
        failures.append("current claims must pass while explicit history remains allowed")
