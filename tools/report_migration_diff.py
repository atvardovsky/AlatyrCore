#!/usr/bin/env python3
"""Report differences between two Alatyr release baselines.

This source-repository helper produces migration evidence only. It does not
modify target adapters or approve protected changes. By default, it compares
against `framework/rule-registry.json` and emits the source release migration
report shape from `docs/release-migration-report-template.md`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = ROOT / "framework" / "rule-registry.json"
DEFAULT_FRAMEWORK_DIR = ROOT / "framework"
DEFAULT_TEMPLATE_DIR = ROOT / "templates" / "target"


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"missing manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit(f"manifest must be an object: {path}")
    if data.get("schema_version") != 1:
        raise SystemExit(f"unsupported schema_version in {path}: {data.get('schema_version')}")
    if not isinstance(data.get("rules"), list):
        raise SystemExit(f"manifest must contain a rules list: {path}")
    return data


def rule_index(data: dict[str, Any], path: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for rule in data["rules"]:
        if not isinstance(rule, dict) or not isinstance(rule.get("id"), str):
            raise SystemExit(f"each rule in {path} must be an object with an id")
        rule_id = rule["id"]
        if rule_id in index:
            raise SystemExit(f"duplicate rule id in {path}: {rule_id}")
        index[rule_id] = rule
    return index


def category_owner_index(data: dict[str, Any], path: Path) -> dict[str, dict[str, Any]]:
    owners = data.get("category_owners", [])
    if not isinstance(owners, list):
        raise SystemExit(f"manifest category_owners must be a list: {path}")

    index: dict[str, dict[str, Any]] = {}
    for owner in owners:
        if not isinstance(owner, dict) or not isinstance(owner.get("category"), str):
            raise SystemExit(
                f"each category owner in {path} must be an object with a category"
            )
        category = owner["category"]
        if category in index:
            raise SystemExit(f"duplicate category owner in {path}: {category}")
        index[category] = owner
    return index


def file_index(path: Path) -> dict[str, str]:
    if not path.exists():
        raise SystemExit(f"missing framework directory: {path}")
    if not path.is_dir():
        raise SystemExit(f"framework path must be a directory: {path}")

    index: dict[str, str] = {}
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        relpath = file_path.relative_to(path).as_posix()
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        index[relpath] = digest
    return index


def normalized_rule(rule: dict[str, Any]) -> str:
    return json.dumps(rule, sort_keys=True, separators=(",", ":"))


def normalized_mapping(item: dict[str, Any]) -> str:
    return json.dumps(item, sort_keys=True, separators=(",", ":"))


def bullet_list(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- `{item}`" for item in items]


def known_version_changed(previous: str, next_value: str) -> bool:
    if previous in {"", "unknown"}:
        return False
    if next_value in {"", "current"}:
        return False
    return previous != next_value


def affected_rule(rule_id: str, from_rules: dict[str, dict[str, Any]], to_rules: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return to_rules.get(rule_id) or from_rules.get(rule_id, {})


def affected_rule_values(
    rule_ids: list[str],
    from_rules: dict[str, dict[str, Any]],
    to_rules: dict[str, dict[str, Any]],
    key: str,
) -> list[str]:
    values: set[str] = set()
    for rule_id in rule_ids:
        value = affected_rule(rule_id, from_rules, to_rules).get(key)
        if isinstance(value, str) and value:
            values.add(value)
        elif isinstance(value, list):
            values.update(item for item in value if isinstance(item, str) and item)
    return sorted(values)


def contract_status(label: str, changed: bool, unknown: bool = False) -> str:
    if unknown:
        return f"- {label}: `not compared`"
    return f"- {label}: `{'changed' if changed else 'unchanged'}`"


def migration_action_hints(
    affected_categories: list[str],
    adapter_schema_changed: bool,
    template_version_changed: bool,
    framework_files_compared: bool,
    framework_files_changed: bool,
    template_files_compared: bool,
    template_files_changed: bool,
) -> list[str]:
    hints: set[str] = set()
    category_hints = {
        "ADAPTER": "Recheck target manifest, contours, adapter ownership, and local deviations.",
        "APPROVAL": "Recheck approval-record policy and protected-change approval scope.",
        "BRIDGE": "Recheck bridge capability matrix and supported assistant bridge files.",
        "CHANGE": "Recheck blueprint-driven change and product-change flow references.",
        "CONTEXT": "Recheck context profiles and bootstrap routing.",
        "EVIDENCE": "Recheck final-evidence and adapter output-contract expectations.",
        "INTEGRITY": "Recheck logical integrity review flow and companion-update rules.",
        "LIFECYCLE": "Prepare or update migration notes and post-update evidence.",
        "MODULE": "Recheck required core and optional module profile states.",
        "RISK": "Recheck risk classification and approval trigger routing.",
        "SAFETY": "Recheck security, prompt-injection, imported-source, and source-access policies.",
        "SOURCE": "Recheck source-of-truth registry entries and conflict resolution.",
    }
    for category in affected_categories:
        hint = category_hints.get(category)
        if hint:
            hints.add(hint)
    if adapter_schema_changed:
        hints.add("Update installed adapter manifest schema version and review schema migration needs.")
    if template_version_changed:
        hints.add("Compare target templates and decide which installed adapter placeholders need migration.")
    if framework_files_compared and framework_files_changed:
        hints.add("Compare installed `.ai/framework` files against changed framework sources before applying updates.")
    if template_files_compared and template_files_changed:
        hints.add("Compare installed adapter templates against changed target template surfaces before applying updates.")
    if not hints:
        return ["- none"]
    return [f"- {hint}" for hint in sorted(hints)]


def render_report(
    from_path: Path,
    to_path: Path,
    from_rules: dict[str, dict[str, Any]],
    to_rules: dict[str, dict[str, Any]],
    from_owner_categories: dict[str, dict[str, Any]],
    to_owner_categories: dict[str, dict[str, Any]],
    from_version: str,
    to_version: str,
    from_adapter_schema_version: str,
    to_adapter_schema_version: str,
    from_template_version: str,
    to_template_version: str,
    from_framework_dir: Path | None,
    to_framework_dir: Path | None,
    from_framework_files: dict[str, str] | None,
    to_framework_files: dict[str, str] | None,
    from_template_dir: Path | None,
    to_template_dir: Path | None,
    from_template_files: dict[str, str] | None,
    to_template_files: dict[str, str] | None,
) -> str:
    from_ids = set(from_rules)
    to_ids = set(to_rules)

    added = sorted(to_ids - from_ids)
    removed = sorted(from_ids - to_ids)
    changed = sorted(
        rule_id
        for rule_id in from_ids & to_ids
        if normalized_rule(from_rules[rule_id]) != normalized_rule(to_rules[rule_id])
    )
    unchanged = sorted((from_ids & to_ids) - set(changed))
    affected_rule_ids = sorted(set(added) | set(changed) | set(removed))
    affected_categories = affected_rule_values(
        affected_rule_ids, from_rules, to_rules, "category"
    )
    affected_profiles = affected_rule_values(
        affected_rule_ids, from_rules, to_rules, "applies_to"
    )
    affected_sources = affected_rule_values(
        affected_rule_ids, from_rules, to_rules, "canonical_source"
    )

    from_owner_ids = set(from_owner_categories)
    to_owner_ids = set(to_owner_categories)
    added_owners = sorted(to_owner_ids - from_owner_ids)
    removed_owners = sorted(from_owner_ids - to_owner_ids)
    changed_owners = sorted(
        category
        for category in from_owner_ids & to_owner_ids
        if normalized_mapping(from_owner_categories[category])
        != normalized_mapping(to_owner_categories[category])
    )

    if from_framework_files is not None and to_framework_files is not None:
        from_file_ids = set(from_framework_files)
        to_file_ids = set(to_framework_files)
        added_files = sorted(to_file_ids - from_file_ids)
        removed_files = sorted(from_file_ids - to_file_ids)
        changed_files = sorted(
            file_id
            for file_id in from_file_ids & to_file_ids
            if from_framework_files[file_id] != to_framework_files[file_id]
        )
    else:
        added_files = []
        removed_files = []
        changed_files = []

    if from_template_files is not None and to_template_files is not None:
        from_template_ids = set(from_template_files)
        to_template_ids = set(to_template_files)
        added_template_files = sorted(to_template_ids - from_template_ids)
        removed_template_files = sorted(from_template_ids - to_template_ids)
        changed_template_files = sorted(
            file_id
            for file_id in from_template_ids & to_template_ids
            if from_template_files[file_id] != to_template_files[file_id]
        )
    else:
        added_template_files = []
        removed_template_files = []
        changed_template_files = []

    has_changes = any(
        [
            added,
            changed,
            removed,
            added_owners,
            changed_owners,
            removed_owners,
            added_files,
            changed_files,
            removed_files,
            added_template_files,
            changed_template_files,
            removed_template_files,
        ]
    )
    framework_version_changed = known_version_changed(from_version, to_version)
    adapter_schema_changed = known_version_changed(
        from_adapter_schema_version, to_adapter_schema_version
    )
    template_version_changed = known_version_changed(
        from_template_version, to_template_version
    )
    framework_files_compared = (
        from_framework_files is not None and to_framework_files is not None
    )
    framework_files_changed = bool(added_files or changed_files or removed_files)
    template_files_compared = from_template_files is not None and to_template_files is not None
    template_files_changed = bool(
        added_template_files or changed_template_files or removed_template_files
    )
    action_hints = migration_action_hints(
        affected_categories,
        adapter_schema_changed,
        template_version_changed,
        framework_files_compared,
        framework_files_changed,
        template_files_compared,
        template_files_changed,
    )

    lines = [
        "# Alatyr Release Migration Report",
        "",
        "Generated from `tools/report_migration_diff.py` using the shape in "
        "`docs/release-migration-report-template.md`.",
        "",
        "Report ID: `generated-migration-diff`",
        "Prepared by: `tools/report_migration_diff.py`",
        "Prepared at: `not recorded by this source helper`",
        "",
        "## Version Scope",
        "",
        f"From manifest: `{from_path}`",
        f"To manifest: `{to_path}`",
        f"From framework version: `{from_version}`",
        f"To framework version: `{to_version}`",
        f"From adapter schema version: `{from_adapter_schema_version}`",
        f"To adapter schema version: `{to_adapter_schema_version}`",
        f"From template version: `{from_template_version}`",
        f"To template version: `{to_template_version}`",
        "",
        "## Summary",
        "",
        f"- Added rules: {len(added)}",
        f"- Changed rules: {len(changed)}",
        f"- Removed rules: {len(removed)}",
        f"- Unchanged rules: {len(unchanged)}",
        f"- Added rule owner categories: {len(added_owners)}",
        f"- Changed rule owner categories: {len(changed_owners)}",
        f"- Removed rule owner categories: {len(removed_owners)}",
        f"- Added framework files: {len(added_files)}",
        f"- Changed framework files: {len(changed_files)}",
        f"- Removed framework files: {len(removed_files)}",
        f"- Added target template surfaces: {len(added_template_files)}",
        f"- Changed target template surfaces: {len(changed_template_files)}",
        f"- Removed target template surfaces: {len(removed_template_files)}",
        "",
        "## Adapter Contract Impact",
        "",
        contract_status("Framework version", framework_version_changed),
        contract_status("Adapter schema version", adapter_schema_changed),
        contract_status("Template version", template_version_changed),
        contract_status("Rule registry", bool(added or changed or removed)),
        contract_status(
            "Rule ownership", bool(added_owners or changed_owners or removed_owners)
        ),
        contract_status(
            "Framework files",
            framework_files_changed,
            unknown=not framework_files_compared,
        ),
        contract_status(
            "Target template surfaces",
            template_files_changed,
            unknown=not template_files_compared,
        ),
        "",
        "## Affected Rule Categories",
        "",
        *bullet_list(affected_categories),
        "",
        "## Affected Task Profiles",
        "",
        *bullet_list(affected_profiles),
        "",
        "## Affected Canonical Sources",
        "",
        *bullet_list(affected_sources),
        "",
        "## Migration Action Hints",
        "",
        *action_hints,
        "",
        "## Rule Changes",
        "",
        "## Added Rules",
        "",
        *bullet_list(added),
        "",
        "## Changed Rules",
        "",
        *bullet_list(changed),
        "",
        "## Removed Rules",
        "",
        *bullet_list(removed),
        "",
        "## Unchanged Rules",
        "",
        *bullet_list(unchanged),
        "",
        "## Rule Owner Changes",
        "",
        "Added rule owner categories:",
        *bullet_list(added_owners),
        "",
        "Changed rule owner categories:",
        *bullet_list(changed_owners),
        "",
        "Removed rule owner categories:",
        *bullet_list(removed_owners),
        "",
        "## Framework File Changes",
        "",
    ]

    if from_framework_files is None or to_framework_files is None:
        lines.extend(
            [
                "- not requested; pass `--from-framework-dir` to compare framework file lists",
            ]
        )
    else:
        lines.extend(
            [
                f"From framework directory: `{from_framework_dir}`",
                f"To framework directory: `{to_framework_dir}`",
                "",
                "Added framework files:",
                *bullet_list(added_files),
                "",
                "Changed framework files:",
                *bullet_list(changed_files),
                "",
                "Removed framework files:",
                *bullet_list(removed_files),
            ]
        )

    lines.extend(["", "## Target Template Surface Changes", ""])
    if from_template_files is None or to_template_files is None:
        lines.extend(
            [
                "- not requested; pass `--from-template-dir` to compare target template surfaces",
            ]
        )
    else:
        lines.extend(
            [
                f"From template directory: `{from_template_dir}`",
                f"To template directory: `{to_template_dir}`",
                "",
                "Added target template surfaces:",
                *bullet_list(added_template_files),
                "",
                "Changed target template surfaces:",
                *bullet_list(changed_template_files),
                "",
                "Removed target template surfaces:",
                *bullet_list(removed_template_files),
            ]
        )

    lines.extend(
        [
            "",
        "## Required Target Actions",
        "",
        ]
    )

    if has_changes:
        lines.extend(
            [
                "- Review affected target adapters before applying changes.",
                "- Create or update a target migration note when the installed adapter is affected.",
                "- Require approval before overwriting existing AI instructions or changing protected adapter behavior.",
                "- Run target validation or record unresolved checks.",
            ]
        )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Optional Target Actions",
            "",
        ]
    )
    if has_changes:
        lines.extend(
            [
                "- Run `recheck-after-framework-update` in installed target adapters.",
                "- Compare local deviations against changed rule owners and framework files.",
            ]
        )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Approval Needs",
            "",
            "Approval needed: `target-dependent`",
            "Approval scope: `required before overwriting existing AI instructions or protected adapter behavior`",
            "",
            "## Validation Run",
            "",
            "Source validation: `run source-repository checks before release`",
            "Target validation: `target adapter decides local validation or unresolved checks`",
            "",
            "## Residual Risks",
            "",
        ]
    )
    if has_changes:
        lines.extend(
            [
                "- Target adapters may have local deviations not visible from source manifest comparison.",
                "- Source migration evidence does not prove target validation.",
            ]
        )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Safety",
            "",
            "This report is evidence only. It does not modify target files, approve changes, or complete an upgrade.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two Alatyr rule manifests and write a migration diff report."
    )
    parser.add_argument("--from-rules", required=True, type=Path)
    parser.add_argument("--to-rules", default=DEFAULT_RULES, type=Path)
    parser.add_argument("--from-version", default="unknown")
    parser.add_argument("--to-version", default="current")
    parser.add_argument("--from-adapter-schema-version", default="unknown")
    parser.add_argument("--to-adapter-schema-version", default="current")
    parser.add_argument("--from-template-version", default="unknown")
    parser.add_argument("--to-template-version", default="current")
    parser.add_argument(
        "--from-framework-dir",
        type=Path,
        help="Optional previous framework directory, such as a target .ai/framework.",
    )
    parser.add_argument(
        "--to-framework-dir",
        default=DEFAULT_FRAMEWORK_DIR,
        type=Path,
        help="Next framework directory. Defaults to this repository's framework/.",
    )
    parser.add_argument(
        "--from-template-dir",
        type=Path,
        help="Optional previous target template directory, such as templates/target from an older release.",
    )
    parser.add_argument(
        "--to-template-dir",
        default=DEFAULT_TEMPLATE_DIR,
        type=Path,
        help="Next target template directory. Defaults to this repository's templates/target/.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for a Markdown report. Defaults to stdout.",
    )
    args = parser.parse_args()

    from_path = args.from_rules.resolve()
    to_path = args.to_rules.resolve()
    from_data = load_manifest(from_path)
    to_data = load_manifest(to_path)
    from_rules = rule_index(from_data, from_path)
    to_rules = rule_index(to_data, to_path)
    from_owner_categories = category_owner_index(from_data, from_path)
    to_owner_categories = category_owner_index(to_data, to_path)
    from_framework_dir = args.from_framework_dir.resolve() if args.from_framework_dir else None
    to_framework_dir = args.to_framework_dir.resolve() if args.from_framework_dir else None
    from_framework_files = file_index(from_framework_dir) if from_framework_dir else None
    to_framework_files = file_index(to_framework_dir) if to_framework_dir else None
    from_template_dir = args.from_template_dir.resolve() if args.from_template_dir else None
    to_template_dir = args.to_template_dir.resolve() if args.from_template_dir else None
    from_template_files = file_index(from_template_dir) if from_template_dir else None
    to_template_files = file_index(to_template_dir) if to_template_dir else None

    report = render_report(
        from_path,
        to_path,
        from_rules,
        to_rules,
        from_owner_categories,
        to_owner_categories,
        args.from_version,
        args.to_version,
        args.from_adapter_schema_version,
        args.to_adapter_schema_version,
        args.from_template_version,
        args.to_template_version,
        from_framework_dir,
        to_framework_dir,
        from_framework_files,
        to_framework_files,
        from_template_dir,
        to_template_dir,
        from_template_files,
        to_template_files,
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
