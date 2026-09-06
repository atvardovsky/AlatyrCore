#!/usr/bin/env python3
"""Prepare migration-first evidence for an installed Alatyr adapter upgrade."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_target_adapter import git_branch_name, git_head_revision, parse_manifest


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


def source_commit_for_version(source: Path, version: str) -> str | None:
    """Resolve the nearest reachable source commit that owns an exact VERSION."""

    if version in {"", "unknown"}:
        return None
    history = run(["git", "log", "--format=%H", "--", "VERSION"], source)
    if history.returncode != 0:
        return None
    for commit in history.stdout.splitlines():
        value = run(["git", "show", f"{commit}:VERSION"], source)
        if value.returncode == 0 and value.stdout.strip() == version:
            return commit
    return None


def materialize_git_subtree(
    source: Path, commit: str, relpath: str, destination: Path
) -> bool:
    """Materialize one historical contract subtree without archive extraction."""

    listing = run(
        ["git", "ls-tree", "-r", "--name-only", commit, "--", relpath], source
    )
    if listing.returncode != 0:
        return False
    paths = [value for value in listing.stdout.splitlines() if value]
    if not paths:
        return False
    for value in paths:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or not value.startswith(relpath + "/"):
            return False
        content = subprocess.run(
            ["git", "show", f"{commit}:{value}"],
            cwd=source,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if content.returncode != 0:
            return False
        output = destination / path.relative_to(relpath)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content.stdout)
    return True


def replace_assessment_outputs(
    staged_paths: list[Path], destination_paths: list[Path]
) -> None:
    """Replace one assessment set and restore the previous set on failure."""

    if len(staged_paths) != len(destination_paths) or not destination_paths:
        raise ValueError("assessment output sets must be non-empty and equal")
    output_dir = destination_paths[0].parent
    if any(path.parent != output_dir for path in destination_paths):
        raise ValueError("assessment outputs must share one directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".alatyr-assessment-backup-", dir=output_dir.parent
    ) as directory:
        backup_dir = Path(directory)
        backups: list[tuple[Path, Path]] = []
        installed: list[Path] = []
        try:
            for destination in destination_paths:
                if destination.is_symlink() or (
                    destination.exists() and not destination.is_file()
                ):
                    raise OSError(
                        f"assessment output is not a regular file: {destination}"
                    )
                if destination.is_file():
                    backup = backup_dir / destination.name
                    os.replace(destination, backup)
                    backups.append((destination, backup))
            for staged, destination in zip(staged_paths, destination_paths):
                os.replace(staged, destination)
                installed.append(destination)
        except OSError as exc:
            rollback_errors: list[str] = []
            for destination in reversed(installed):
                try:
                    destination.unlink(missing_ok=True)
                except OSError as rollback_exc:
                    rollback_errors.append(str(rollback_exc))
            for destination, backup in reversed(backups):
                try:
                    os.replace(backup, destination)
                except OSError as rollback_exc:
                    rollback_errors.append(str(rollback_exc))
            if rollback_errors:
                raise OSError(
                    f"assessment replacement failed ({exc}); rollback also failed: "
                    + "; ".join(rollback_errors)
                ) from exc
            raise


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def installed_owner_path(path: str) -> str:
    if path.startswith("framework/"):
        return ".ai/framework/" + path[len("framework/") :]
    return path


def enrich_upgrade_impact(
    path: Path,
    *,
    target: Path,
    framework_pack: str,
    migration_report: Path,
) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    manifest = parse_manifest(target / ".ai" / "alatyr.yaml")
    payload["target"] = {
        "branch": git_branch_name(target) or "not available",
        "revision": git_head_revision(target) or "not available",
        "framework_pack": framework_pack,
        "support_profile": manifest_value(target, ("installation", "support_profile")),
        "enabled_modules": sorted(
            scalar.value
            for scalar in manifest.lists.get(("modules", "enabled"), [])
            if scalar.value and not scalar.value.startswith("{")
        ),
    }
    payload["evidence"] = {
        "migration_report": migration_report.name,
        "migration_report_sha256": sha256(migration_report),
        "target_manifest": ".ai/alatyr.yaml",
        "target_manifest_sha256": sha256(target / ".ai" / "alatyr.yaml"),
    }
    affected = payload.get("affected", {})
    framework_files = payload.get("framework_files", {})
    target_surfaces = payload.get("target_template_surfaces", {})
    canonical_sources = (
        affected.get("canonical_sources", []) if isinstance(affected, dict) else []
    )
    changed_framework = (
        framework_files.get("added", []) + framework_files.get("changed", [])
        if isinstance(framework_files, dict)
        else []
    )
    changed_target_surfaces = (
        target_surfaces.get("added", []) + target_surfaces.get("changed", [])
        if isinstance(target_surfaces, dict)
        else []
    )
    candidate_context = sorted(
        {
            *(installed_owner_path(value) for value in canonical_sources),
            *(f".ai/framework/{value}" for value in changed_framework),
            *changed_target_surfaces,
        }
    )
    payload["routing"] = {
        "first_context": [path.name, ".ai/alatyr.yaml"],
        "candidate_context": candidate_context,
        "removed_framework_files": (
            framework_files.get("removed", [])
            if isinstance(framework_files, dict)
            else []
        ),
        "removed_target_surfaces": (
            target_surfaces.get("removed", [])
            if isinstance(target_surfaces, dict)
            else []
        ),
        "full_corpus_required": False,
        "full_corpus_trigger": (
            "only when impact is ambiguous, validation disproves the boundary, "
            "or a full compatibility audit is explicitly requested"
        ),
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def add_validation_impact(path: Path, validation_report: Path) -> None:
    """Route installed-surface findings after the validator has inspected them."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    validation = json.loads(validation_report.read_text(encoding="utf-8"))
    findings = validation.get("findings", [])
    relevant = [
        finding
        for finding in findings
        if isinstance(finding, dict)
        and finding.get("level") in {"error", "warning"}
        and isinstance(finding.get("path"), str)
        and finding["path"]
    ]
    affected_paths = sorted({str(finding["path"]) for finding in relevant})
    routing = payload.setdefault("routing", {})
    candidate_context = routing.get("candidate_context", [])
    if not isinstance(candidate_context, list):
        candidate_context = []
    routing["candidate_context"] = sorted(set(candidate_context) | set(affected_paths))
    routing["validator_affected_paths"] = affected_paths
    payload["validator_impact"] = {
        "report": validation_report.name,
        "report_sha256": sha256(validation_report),
        "finding_codes": sorted(
            {
                str(finding.get("code"))
                for finding in relevant
                if finding.get("code")
            }
        ),
        "affected_paths": affected_paths,
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def render_plan(
    *,
    target: Path,
    migration_status: str,
    validation_status: str,
    validation_counts: dict[str, object],
    validation_contract: dict[str, object],
    from_versions: tuple[str, str, str],
    to_versions: tuple[str, str, str],
    framework_pack: str,
) -> str:
    target_revision = git_head_revision(target) or "not available"
    target_branch = git_branch_name(target) or "not available"
    validation_phase = validation_contract.get("validation_phase", "unknown")
    acceptance_eligible = validation_contract.get("acceptance_eligible", False)
    unresolved_active = validation_contract.get("unresolved_active", "unknown")
    return f"""# Alatyr Target Upgrade Assessment

Evidence basis: `current-state`
Observed target branch: `{target_branch}`
Observed target revision: `{target_revision}`
Target repository label: `{target.name}`

## Version Scope

- Framework: `{from_versions[0]}` -> `{to_versions[0]}`
- Adapter schema: `{from_versions[1]}` -> `{to_versions[1]}`
- Template: `{from_versions[2]}` -> `{to_versions[2]}`
- Framework pack: `{framework_pack}` -> `{framework_pack}`

## Assessment Outputs

- Migration report: `migration-report.md` ({migration_status})
- Upgrade impact router: `upgrade-impact.json` ({migration_status})
- Structural validator report: `adapter-validation.json` ({validation_status})
- Validation phase: `{validation_phase}`
- Acceptance eligible: `{str(acceptance_eligible).lower()}`
- Unresolved active placeholders: `{unresolved_active}`
- Validator counts: `{json.dumps(validation_counts, sort_keys=True)}`

## Apply Gate

This assessment does not apply an upgrade, approve protected changes, or
replace target validation. Review `upgrade-impact.json` first, load only its
affected canonical sources and target surfaces, preserve local deviations,
prepare a target migration note, and obtain approval before protected changes.
Evidence applies only to the named checked-out branch and observed revision.
It does not prove that another branch contains the same adapter state.

Migration-staging validation may inventory unresolved target facts, but it
cannot complete or accept an update. Resolve every active placeholder and run
the validator with `--validation-phase acceptance` before reporting the
adapter as updated.

## Next Actions

1. Review the impact router, then load its changed rules, canonical sources,
   framework files, target surfaces, and pack compatibility evidence.
2. Resolve structural validator errors or record accepted target deviations.
3. Map affected source changes to installed adapter surfaces and local owners.
4. Prepare the target migration note and explicit approval scope.
5. Apply approved changes separately, then rerun adapter and target validation
   in the acceptance phase on the branch and revision being accepted.
"""


def parse_args() -> argparse.Namespace:
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
    parser.add_argument(
        "--validation-phase",
        choices=["acceptance", "migration-staging"],
        default="acceptance",
    )
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="Deprecated alias for --validation-phase migration-staging.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing assessment outputs in --output-dir.",
    )
    return parser.parse_args()


def execute_assessment(args: argparse.Namespace, validation_phase: str) -> int:

    target = args.target.resolve()
    source = args.framework_source.resolve()
    output_dir = args.output_dir.resolve()
    final_outputs = [
        output_dir / "migration-report.md",
        output_dir / "upgrade-impact.json",
        output_dir / "adapter-validation.json",
        output_dir / "upgrade-assessment.md",
    ]

    if not target.is_dir():
        print(f"Target repository does not exist: {target}", file=sys.stderr)
        return 2
    if not (source / "framework" / "rule-registry.json").is_file():
        print(f"Framework source is incomplete: {source}", file=sys.stderr)
        return 2
    existing = [path for path in final_outputs if path.exists()]
    if existing and not args.overwrite:
        names = ", ".join(path.name for path in existing)
        print(f"Assessment output already exists: {names}; pass --overwrite", file=sys.stderr)
        return 2
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = tempfile.TemporaryDirectory(
        prefix=f".{output_dir.name}-assessment-", dir=output_dir.parent
    )
    staging_dir = Path(staging.name)
    migration_report = staging_dir / "migration-report.md"
    impact_report = staging_dir / "upgrade-impact.json"
    validation_report = staging_dir / "adapter-validation.json"
    assessment_plan = staging_dir / "upgrade-assessment.md"

    from_versions = (
        manifest_value(target, ("framework", "version")),
        manifest_value(target, ("schema_version",)),
        manifest_value(target, ("framework", "template_version")),
    )
    framework_pack = manifest_value(target, ("framework", "pack"))
    if framework_pack == "unknown":
        framework_pack = "complete"
    if framework_pack not in {"kernel", "core", "standard", "complete"}:
        print(
            f"Unsupported target framework.pack: {framework_pack}",
            file=sys.stderr,
        )
        staging.cleanup()
        return 2
    to_versions = (
        source_version(source, "VERSION"),
        source_version(source, "ADAPTER_SCHEMA_VERSION"),
        source_version(source, "TEMPLATE_VERSION"),
    )

    old_rules = target / ".ai" / "framework" / "rule-registry.json"
    old_framework = target / ".ai" / "framework"
    reporter = source / "tools" / "report_migration_diff.py"
    with tempfile.TemporaryDirectory(prefix="alatyr-upgrade-pack-") as directory:
        working = Path(directory)
        to_framework = source / "framework"
        if framework_pack != "complete":
            projection_target = working / "next-pack"
            projection_target.mkdir()
            support_profile = {
                "kernel": "kernel",
                "core": "core",
                "standard": "standard",
            }[framework_pack]
            projection = run(
                [
                    sys.executable,
                    str(source / "tools" / "scaffold_target_structure.py"),
                    "--target",
                    str(projection_target),
                    "--write",
                    "--profile",
                    support_profile,
                    "--framework-pack",
                    framework_pack,
                ],
                source,
            )
            if projection.returncode != 0:
                print(
                    projection.stderr.strip()
                    or projection.stdout.strip()
                    or "framework pack projection failed",
                    file=sys.stderr,
                )
                staging.cleanup()
                return 2
            to_framework = projection_target / ".ai" / "framework"

        migration_command = [
            sys.executable,
            str(reporter),
            "--from-rules",
            str(old_rules),
            "--to-rules",
            str(to_framework / "rule-registry.json"),
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
            str(to_framework),
            "--output",
            str(migration_report),
            "--json-output",
            str(impact_report),
        ]
        previous_commit = source_commit_for_version(source, from_versions[0])
        if previous_commit is not None:
            previous_schema_dir = working / "previous-schemas"
            previous_template_dir = working / "previous-templates"
            schemas_available = materialize_git_subtree(
                source, previous_commit, "schemas", previous_schema_dir
            )
            templates_available = materialize_git_subtree(
                source,
                previous_commit,
                "templates/target",
                previous_template_dir,
            )
            if schemas_available:
                migration_command.extend(
                    [
                        "--from-schema-dir",
                        str(previous_schema_dir),
                        "--to-schema-dir",
                        str(source / "schemas"),
                    ]
                )
            if templates_available:
                migration_command.extend(
                    [
                        "--from-template-dir",
                        str(previous_template_dir),
                        "--to-template-dir",
                        str(source / "templates" / "target"),
                    ]
                )
            migration_command.extend(
                ["--from-source-label", f"source-version:{from_versions[0]}@{previous_commit}"]
            )
        migration_command.extend(
            ["--to-source-label", f"source-version:{to_versions[0]}"]
        )
        migration = run(migration_command, source)
    migration_status = "generated" if migration.returncode == 0 else "failed"

    if migration.returncode == 0:
        try:
            enrich_upgrade_impact(
                impact_report,
                target=target,
                framework_pack=framework_pack,
                migration_report=migration_report,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"Cannot finalize upgrade impact: {exc}", file=sys.stderr)
            migration_status = "impact generation failed"
            migration = subprocess.CompletedProcess(
                migration.args, 1, migration.stdout, str(exc)
            )

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
        validator_command.extend(["--validation-phase", validation_phase])
        validation = run(validator_command, source)
        validation_code = validation.returncode
        validation_status = "findings require review"
        if validation_report.is_file():
            try:
                payload = json.loads(validation_report.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                validation_status = "invalid validator report"
            else:
                validation_counts = payload.get("counts", {})
                validation_status = str(payload.get("status", "unknown"))
                try:
                    add_validation_impact(impact_report, validation_report)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    validation_status = f"validator impact routing failed: {exc}"
                    validation_code = 1

    validation_contract: dict[str, object] = {
        "validation_phase": validation_phase,
        "acceptance_eligible": False,
        "unresolved_active": "unknown",
    }
    if validation_report.is_file():
        try:
            validation_payload = json.loads(validation_report.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
        else:
            placeholder_validation = validation_payload.get("placeholder_validation", {})
            validation_contract = {
                "validation_phase": validation_payload.get("validation_phase", validation_phase),
                "acceptance_eligible": (
                    placeholder_validation.get("acceptance_eligible", False)
                    if isinstance(placeholder_validation, dict)
                    else False
                ),
                "unresolved_active": (
                    placeholder_validation.get("unresolved_active", "unknown")
                    if isinstance(placeholder_validation, dict)
                    else "unknown"
                ),
            }

    assessment_plan.write_text(
        render_plan(
            target=target,
            migration_status=migration_status,
            validation_status=validation_status,
            validation_counts=validation_counts,
            validation_contract=validation_contract,
            from_versions=from_versions,
            to_versions=to_versions,
            framework_pack=framework_pack,
        ),
        encoding="utf-8",
    )

    if migration.returncode != 0:
        print(migration.stderr.strip() or migration.stdout.strip(), file=sys.stderr)
        print("Upgrade assessment failed; existing outputs were preserved", file=sys.stderr)
        staging.cleanup()
        return 1
    try:
        replace_assessment_outputs(
            [migration_report, impact_report, validation_report, assessment_plan],
            final_outputs,
        )
    except (OSError, ValueError) as exc:
        print(f"Upgrade assessment replacement failed: {exc}", file=sys.stderr)
        staging.cleanup()
        return 1
    staging.cleanup()
    print(f"Wrote migration report: {final_outputs[0]}")
    print(f"Wrote upgrade impact: {final_outputs[1]}")
    print(f"Wrote validator report: {final_outputs[2]}")
    print(f"Wrote upgrade assessment: {final_outputs[3]}")
    return validation_code


def main() -> int:
    args = parse_args()
    validation_phase = (
        "migration-staging" if args.allow_placeholders else args.validation_phase
    )
    return execute_assessment(args, validation_phase)


if __name__ == "__main__":
    raise SystemExit(main())
