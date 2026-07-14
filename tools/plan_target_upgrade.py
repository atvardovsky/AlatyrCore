#!/usr/bin/env python3
"""Prepare migration-first evidence for an installed Alatyr adapter upgrade."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from validate_target_adapter import git_head_revision, parse_manifest


ROOT = Path(__file__).resolve().parents[1]


def source_version(source: Path, filename: str) -> str:
    path = source / filename
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def manifest_value(target: Path, key: tuple[str, ...]) -> str:
    manifest_path = target / ".ai" / "alatyr.yaml"
    if not manifest_path.is_file():
        return "unknown"
    manifest = parse_manifest(manifest_path)
    scalar = manifest.scalars.get(key)
    return scalar.value if scalar and scalar.value else "unknown"


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def render_plan(
    *,
    target: Path,
    migration_status: str,
    validation_status: str,
    validation_counts: dict[str, object],
    from_versions: tuple[str, str, str],
    to_versions: tuple[str, str, str],
) -> str:
    target_revision = git_head_revision(target) or "not available"
    return f"""# Alatyr Target Upgrade Assessment

Evidence basis: `current-state`
Observed target revision: `{target_revision}`
Target repository label: `{target.name}`

## Version Scope

- Framework: `{from_versions[0]}` -> `{to_versions[0]}`
- Adapter schema: `{from_versions[1]}` -> `{to_versions[1]}`
- Template: `{from_versions[2]}` -> `{to_versions[2]}`

## Assessment Outputs

- Migration report: `migration-report.md` ({migration_status})
- Structural validator report: `adapter-validation.json` ({validation_status})
- Validator counts: `{json.dumps(validation_counts, sort_keys=True)}`

## Apply Gate

This assessment does not apply an upgrade, approve protected changes, or
replace target validation. Review the migration report first, load only its
affected canonical sources and target surfaces, preserve local deviations,
prepare a target migration note, and obtain approval before protected changes.

## Next Actions

1. Review changed rules, categories, canonical sources, and framework files.
2. Resolve structural validator errors or record accepted target deviations.
3. Map affected source changes to installed adapter surfaces and local owners.
4. Prepare the target migration note and explicit approval scope.
5. Apply approved changes separately, then rerun adapter and target validation.
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare migration and structural evidence before an installed "
            "Alatyr adapter upgrade. No adapter files are changed."
        )
    )
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--framework-source", default=ROOT, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--diff-ref")
    parser.add_argument("--approval-record", action="append", default=[], type=Path)
    parser.add_argument("--allow-placeholders", action="store_true")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing assessment outputs in --output-dir.",
    )
    args = parser.parse_args()

    target = args.target.resolve()
    source = args.framework_source.resolve()
    output_dir = args.output_dir.resolve()
    migration_report = output_dir / "migration-report.md"
    validation_report = output_dir / "adapter-validation.json"
    assessment_plan = output_dir / "upgrade-assessment.md"
    outputs = [migration_report, validation_report, assessment_plan]

    if not target.is_dir():
        print(f"Target repository does not exist: {target}", file=sys.stderr)
        return 2
    if not (source / "framework" / "rule-registry.json").is_file():
        print(f"Framework source is incomplete: {source}", file=sys.stderr)
        return 2
    existing = [path for path in outputs if path.exists()]
    if existing and not args.overwrite:
        names = ", ".join(path.name for path in existing)
        print(f"Assessment output already exists: {names}; pass --overwrite", file=sys.stderr)
        return 2
    if args.overwrite:
        for path in existing:
            if path.is_file():
                path.unlink()
    output_dir.mkdir(parents=True, exist_ok=True)

    from_versions = (
        manifest_value(target, ("framework", "version")),
        manifest_value(target, ("schema_version",)),
        manifest_value(target, ("framework", "template_version")),
    )
    to_versions = (
        source_version(source, "VERSION"),
        source_version(source, "ADAPTER_SCHEMA_VERSION"),
        source_version(source, "TEMPLATE_VERSION"),
    )

    old_rules = target / ".ai" / "framework" / "rule-registry.json"
    old_framework = target / ".ai" / "framework"
    reporter = source / "tools" / "report_migration_diff.py"
    migration_command = [
        sys.executable,
        str(reporter),
        "--from-rules",
        str(old_rules),
        "--to-rules",
        str(source / "framework" / "rule-registry.json"),
        "--from-version",
        from_versions[0],
        "--to-version",
        to_versions[0],
        "--from-adapter-schema-version",
        from_versions[1],
        "--to-adapter-schema-version",
        to_versions[1],
        "--from-template-version",
        from_versions[2],
        "--to-template-version",
        to_versions[2],
        "--from-framework-dir",
        str(old_framework),
        "--to-framework-dir",
        str(source / "framework"),
        "--output",
        str(migration_report),
    ]
    migration = run(migration_command, source)
    migration_status = "generated" if migration.returncode == 0 else "failed"

    validation_status = "not run"
    validation_counts: dict[str, object] = {}
    validation_code = 1
    if migration.returncode == 0:
        validator_command = [
            sys.executable,
            str(source / "tools" / "validate_target_adapter.py"),
            "--target",
            str(target),
            "--framework-source",
            str(source),
            "--migration-diff",
            str(migration_report),
            "--output",
            str(validation_report),
        ]
        if args.diff_ref:
            validator_command.extend(["--diff-ref", args.diff_ref])
        for record in args.approval_record:
            validator_command.extend(["--approval-record", str(record)])
        if args.allow_placeholders:
            validator_command.append("--allow-placeholders")
        validation = run(validator_command, source)
        validation_code = validation.returncode
        validation_status = "passed" if validation.returncode == 0 else "findings require review"
        if validation_report.is_file():
            try:
                payload = json.loads(validation_report.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                validation_status = "invalid validator report"
            else:
                validation_counts = payload.get("counts", {})

    assessment_plan.write_text(
        render_plan(
            target=target,
            migration_status=migration_status,
            validation_status=validation_status,
            validation_counts=validation_counts,
            from_versions=from_versions,
            to_versions=to_versions,
        ),
        encoding="utf-8",
    )

    if migration.returncode != 0:
        print(migration.stderr.strip() or migration.stdout.strip(), file=sys.stderr)
        print(f"Wrote partial assessment: {assessment_plan}")
        return 1
    print(f"Wrote migration report: {migration_report}")
    print(f"Wrote validator report: {validation_report}")
    print(f"Wrote upgrade assessment: {assessment_plan}")
    return validation_code


if __name__ == "__main__":
    raise SystemExit(main())
