"""Target-validator scenarios for context catalogs."""

from __future__ import annotations

from .common import (
    ROOT,
    parse_manifest,
    subprocess,
    sys,
    validate_context_catalog_contract,
    validator,
)


def run(target: Path, failures: list[str]) -> None:
    catalog_target = target / "context-catalog"
    catalog_target.mkdir()
    scaffold_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/scaffold_target_structure.py"),
            "--target",
            str(catalog_target),
            "--write",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if scaffold_result.returncode != 0:
        failures.append("context-catalog target scaffold failed")
    else:
        catalog_manifest = parse_manifest(catalog_target / ".ai/alatyr.yaml")
        current_catalogs = validator(catalog_target)
        validate_context_catalog_contract(current_catalogs, catalog_manifest)
        if any(
            finding.level == "error" for finding in current_catalogs.findings
        ):
            failures.append("fresh scaffold context catalogs produced errors")
        contour_path = catalog_target / ".ai/assistant/contour.md"
        contour_path.write_text(
            contour_path.read_text(encoding="utf-8") + "\nCatalog drift fixture.\n",
            encoding="utf-8",
        )
        stale_catalogs = validator(catalog_target)
        validate_context_catalog_contract(stale_catalogs, catalog_manifest)
        if "CONTEXT_CATALOG_INVALID" not in {
            finding.code for finding in stale_catalogs.findings
        }:
            failures.append("context catalog content drift was not detected")
        repair_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/render_installed_context_catalogs.py"),
                "--target",
                str(catalog_target),
                "--write",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        repaired_catalogs = validator(catalog_target)
        validate_context_catalog_contract(repaired_catalogs, catalog_manifest)
        if repair_result.returncode != 0 or any(
            finding.level == "error" for finding in repaired_catalogs.findings
        ):
            failures.append("explicit installed context-catalog repair failed")
