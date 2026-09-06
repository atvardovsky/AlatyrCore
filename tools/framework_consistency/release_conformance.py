"""Release, conformance, and evidence checks for framework consistency."""

from __future__ import annotations

import json

from .context import CheckContext


def check_release_tools(context: CheckContext) -> list[str]:
    failures: list[str] = []
    release_process = context.root / "docs" / "release-process.md"
    if not release_process.is_file():
        failures.append("missing docs/release-process.md")
    else:
        release_process_text = context.read_text("docs/release-process.md")
        for required_release_text in [
            "not an installed target adapter requirement",
            "`VERSION`",
            "`ADAPTER_SCHEMA_VERSION`",
            "`TEMPLATE_VERSION`",
            "`CHANGELOG.md`",
            "`framework/rule-registry.json`",
            "`framework/rule-ownership.md`",
            "`docs/release-migration-report-template.md`",
            "`tools/report_migration_diff.py`",
            "`tools/check_release_migration_template.py`",
            "`tools/check_migration_diff_report.py`",
            "`tools/check_versioning.py`",
            "`docs/framework-maintenance.md`",
            "`recheck-after-framework-update`",
        ]:
            if required_release_text not in release_process_text:
                failures.append(
                    f"docs/release-process.md missing {required_release_text}"
                )
    for relpath in [
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_versioning.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_versioning.py")

    release_migration_template_tool = (
        context.root / "tools" / "check_release_migration_template.py"
    )
    if not release_migration_template_tool.is_file():
        failures.append("missing tools/check_release_migration_template.py")
    else:
        release_template_tool_text = context.read_text(
            "tools/check_release_migration_template.py"
        )
        for required_release_template_tool_text in [
            "release migration report template",
            "portable",
            "REQUIRED_TEMPLATE_TEXT",
            "REQUIRED_REPORTER_TEXT",
            "OK: checked",
        ]:
            if required_release_template_tool_text not in release_template_tool_text:
                failures.append(
                    "tools/check_release_migration_template.py missing "
                    f"{required_release_template_tool_text}"
                )
    release_migration_template = (
        context.root / "docs" / "release-migration-report-template.md"
    )
    if not release_migration_template.is_file():
        failures.append("missing docs/release-migration-report-template.md")
    else:
        release_template_text = context.read_text("docs/release-migration-report-template.md")
        for required_release_template_text in [
            "# Alatyr Release Migration Report",
            "## Version Scope",
            "## Adapter Contract Impact",
            "## Affected Rule Categories",
            "## Affected Task Profiles",
            "## Affected Canonical Sources",
            "## Migration Action Hints",
            "## Rule Changes",
            "## Rule Owner Changes",
            "## Framework File Changes",
            "## Target Template Surface Changes",
            "## Required Target Actions",
            "## Optional Target Actions",
            "## Approval Needs",
            "## Validation Run",
            "## Residual Risks",
            "## Safety",
            "evidence only",
        ]:
            if required_release_template_text not in release_template_text:
                failures.append(
                    "docs/release-migration-report-template.md missing "
                    f"{required_release_template_text}"
                )
    for relpath in [
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_release_migration_template.py" not in context.read_text(relpath):
            failures.append(
                f"{relpath} missing check_release_migration_template.py"
            )

    migration_diff_tool = context.root / "tools" / "report_migration_diff.py"
    if not migration_diff_tool.is_file():
        failures.append("missing tools/report_migration_diff.py")
    else:
        migration_diff_text = context.read_text("tools/report_migration_diff.py")
        for required_migration_tool_text in [
            "--from-rules",
            "--to-rules",
            "--from-framework-dir",
            "--from-template-dir",
            "Alatyr Release Migration Report",
            "Rule Owner Changes",
            "Adapter Contract Impact",
            "Affected Rule Categories",
            "Affected Task Profiles",
            "Affected Canonical Sources",
            "Migration Action Hints",
            "Framework File Changes",
            "Target Template Surface Changes",
            "evidence only",
            "framework/rule-registry.json",
            "release-migration-report-template.md",
        ]:
            if required_migration_tool_text not in migration_diff_text:
                failures.append(
                    "tools/report_migration_diff.py missing "
                    f"{required_migration_tool_text}"
                )

    migration_diff_report_tool = context.root / "tools" / "check_migration_diff_report.py"
    if not migration_diff_report_tool.is_file():
        failures.append("missing tools/check_migration_diff_report.py")
    else:
        migration_diff_report_text = context.read_text("tools/check_migration_diff_report.py")
        for required_migration_diff_report_text in [
            "migration diff reporter output shape",
            "portable",
            "REQUIRED_OUTPUT_TEXT",
            "ZERO_CHANGE_TEXT",
            "OK: checked",
        ]:
            if required_migration_diff_report_text not in migration_diff_report_text:
                failures.append(
                    "tools/check_migration_diff_report.py missing "
                    f"{required_migration_diff_report_text}"
                )
    for relpath in [
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
        "docs/release-process.md",
    ]:
        if "check_migration_diff_report.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_migration_diff_report.py")

    conformance_tool = context.root / "tools" / "check_conformance_fixtures.py"
    if not conformance_tool.is_file():
        failures.append("missing tools/check_conformance_fixtures.py")
    else:
        conformance_tool_text = context.read_text("tools/check_conformance_fixtures.py")
        if "OK: checked conformance fixture metadata" not in conformance_tool_text:
            failures.append(
                "tools/check_conformance_fixtures.py missing success message"
            )

    fixture_materializer_tool = context.root / "tools" / "materialize_conformance_fixtures.py"
    if not fixture_materializer_tool.is_file():
        failures.append("missing tools/materialize_conformance_fixtures.py")
    else:
        fixture_materializer_text = context.read_text(
            "tools/materialize_conformance_fixtures.py"
        )
        for required_fixture_materializer_text in [
            "seed-only conformance fixture repositories",
            "does not scaffold Alatyr",
            "--output",
            "--fixture",
            "--overwrite",
        ]:
            if required_fixture_materializer_text not in fixture_materializer_text:
                failures.append(
                    "tools/materialize_conformance_fixtures.py missing "
                    f"{required_fixture_materializer_text}"
                )

    return failures


def check_conformance_tools(context: CheckContext) -> list[str]:
    failures: list[str] = []
    conformance_run_preparer_tool = context.root / "tools" / "prepare_conformance_run.py"
    if not conformance_run_preparer_tool.is_file():
        failures.append("missing tools/prepare_conformance_run.py")
    else:
        conformance_run_preparer_text = context.read_text("tools/prepare_conformance_run.py")
        for required_conformance_run_preparer_text in [
            "per-fixture prompt files",
            "does not run an assistant",
            "assistant-surfaces.json",
            "--allow-custom-surface",
            "--assistant-surface",
            "assistant-run-result",
            "check_conformance_reports.py --actual-dir",
        ]:
            if required_conformance_run_preparer_text not in conformance_run_preparer_text:
                failures.append(
                    "tools/prepare_conformance_run.py missing "
                    f"{required_conformance_run_preparer_text}"
                )

    conformance_reports_tool = context.root / "tools" / "check_conformance_reports.py"
    if not conformance_reports_tool.is_file():
        failures.append("missing tools/check_conformance_reports.py")
    else:
        conformance_reports_text = context.read_text("tools/check_conformance_reports.py")
        for required_conformance_reports_text in [
            "not an assistant installation test",
            "assistant-run-result",
            "--actual-dir",
            "--actual-root",
            "--require-actual-reports",
            "--require-all-fixtures",
            "source_commit",
            "bridge_behavior_evidence",
            "auto_load_observed",
            "assistant-result-conformance",
            "forbidden_claims_absent",
            "OK: checked golden and registered captured conformance reports",
        ]:
            if required_conformance_reports_text not in conformance_reports_text:
                failures.append(
                    "tools/check_conformance_reports.py missing "
                    f"{required_conformance_reports_text}"
                )

    conformance_summary_tool = context.root / "tools" / "summarize_conformance_reports.py"
    if not conformance_summary_tool.is_file():
        failures.append("missing tools/summarize_conformance_reports.py")
    else:
        conformance_summary_text = context.read_text("tools/summarize_conformance_reports.py")
        for required_conformance_summary_text in [
            "Summarize captured assistant-run conformance reports",
            "validate_actual_reports",
            "Surface Coverage",
            "Fixture Coverage",
            "Residual Risk Counts",
            "Unresolved Validation Counts",
            "Adapter Evidence Counts",
            "does not run an assistant",
        ]:
            if required_conformance_summary_text not in conformance_summary_text:
                failures.append(
                    "tools/summarize_conformance_reports.py missing "
                    f"{required_conformance_summary_text}"
                )

    for conformance_run_file in [
        "conformance/runs/README.md",
        "conformance/runs/assistant-results/README.md",
        "conformance/runs/assistant-results/index.json",
        "conformance/runs/assistant-run-report-template.json",
        "conformance/runs/assistant-surfaces.json",
    ]:
        if not (context.root / conformance_run_file).is_file():
            failures.append(f"missing {conformance_run_file}")

    surfaces_path = context.root / "conformance" / "runs" / "assistant-surfaces.json"
    if surfaces_path.is_file():
        try:
            surface_data = json.loads(surfaces_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(
                f"conformance/runs/assistant-surfaces.json invalid JSON: {exc}"
            )
            surface_data = {}
        surfaces = surface_data.get("surfaces")
        if not isinstance(surfaces, list) or not surfaces:
            failures.append("assistant-surfaces.json must contain surfaces")
        else:
            surface_ids = {
                surface.get("id")
                for surface in surfaces
                if isinstance(surface, dict)
            }
            if None in surface_ids or len(surface_ids) != len(surfaces):
                failures.append("assistant-surfaces.json IDs must be unique strings")
            for surface in surfaces:
                if not isinstance(surface, dict):
                    continue
                if not isinstance(surface.get("label"), str) or not isinstance(
                    surface.get("bridge_paths"), list
                ):
                    failures.append(
                        "assistant-surfaces.json entries require label and bridge_paths"
                    )

    scaffold_conformance_tool = context.root / "tools" / "run_conformance_scaffold.py"
    if not scaffold_conformance_tool.is_file():
        failures.append("missing tools/run_conformance_scaffold.py")
    else:
        scaffold_conformance_text = context.read_text("tools/run_conformance_scaffold.py")
        for required_scaffold_conformance_text in [
            "not an assistant installation test",
            "REQUIRED_SCAFFOLD_FILES",
            "PLACEHOLDER_FILES",
            "PLACEHOLDER_PATTERN",
            "scaffold snapshot drift",
            "--write-golden-snapshots",
            "scaffold conformance fixtures passed",
            "scaffold_plan",
        ]:
            if required_scaffold_conformance_text not in scaffold_conformance_text:
                failures.append(
                    "tools/run_conformance_scaffold.py missing "
                    f"{required_scaffold_conformance_text}"
                )

    scaffold_snapshots = context.root / "conformance" / "golden" / "scaffolded-adapters"
    if not (scaffold_snapshots / "README.md").is_file():
        failures.append("missing conformance/golden/scaffolded-adapters/README.md")
    for fixture_name in [
        "backend-api-minimal",
        "frontend-app-minimal",
        "monorepo-mixed",
        "python-cli-existing-ai",
    ]:
        snapshot_path = scaffold_snapshots / f"{fixture_name}.json"
        if not snapshot_path.is_file():
            failures.append(f"missing scaffolded-adapter snapshot: {snapshot_path}")
            continue
        try:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{snapshot_path} is invalid JSON: {exc}")
            continue
        if snapshot.get("snapshot_kind") != "scaffolded-adapter":
            failures.append(f"{snapshot_path} must be scaffolded-adapter snapshot")
        if snapshot.get("claims_installation_complete") is not False:
            failures.append(f"{snapshot_path} must not claim completed installation")
        for key in [
            "created_paths",
            "preserved_seed_paths",
            "skipped_existing_paths",
            "placeholder_paths",
        ]:
            if not isinstance(snapshot.get(key), list):
                failures.append(f"{snapshot_path} missing list {key}")

    bridge_tool = context.root / "tools" / "check_bridge_templates.py"
    if not bridge_tool.is_file():
        failures.append("missing tools/check_bridge_templates.py")
    else:
        bridge_tool_text = context.read_text("tools/check_bridge_templates.py")
        for required_bridge_tool_text in [
            "OK: checked",
            "bridge templates",
            "alatyr-ai-inventory",
            "alatyr-adaptation",
            "alatyr-add-ai",
        ]:
            if required_bridge_tool_text not in bridge_tool_text:
                failures.append(
                    "tools/check_bridge_templates.py missing "
                    f"{required_bridge_tool_text}"
                )

    bridge_manifest = context.root / "tools" / "bridge_template_manifest.json"
    if not bridge_manifest.is_file():
        failures.append("missing tools/bridge_template_manifest.json")
    else:
        try:
            bridge_manifest_data = json.loads(bridge_manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"tools/bridge_template_manifest.json is invalid JSON: {exc}")
            bridge_manifest_data = {}
        if bridge_manifest_data.get("schema_version") != 1:
            failures.append("tools/bridge_template_manifest.json schema_version must be 1")
        templates = bridge_manifest_data.get("templates")
        if not isinstance(templates, list) or not templates:
            failures.append(
                "tools/bridge_template_manifest.json must contain templates"
            )
        else:
            manifest_paths = sorted(
                template.get("path")
                for template in templates
                if isinstance(template, dict)
            )
            if manifest_paths != sorted(context.bridge_files):
                failures.append(
                    "tools/bridge_template_manifest.json paths must match bridge files"
                )

    bridge_renderer = context.root / "tools" / "render_bridge_templates.py"
    if not bridge_renderer.is_file():
        failures.append("missing tools/render_bridge_templates.py")
    else:
        bridge_renderer_text = context.read_text("tools/render_bridge_templates.py")
        for required_renderer_text in [
            "bridge_template_manifest.json",
            "--write",
            "not an installation",
            "OK: checked",
        ]:
            if required_renderer_text not in bridge_renderer_text:
                failures.append(
                    "tools/render_bridge_templates.py missing "
                    f"{required_renderer_text}"
                )

    for relpath in [
        "conformance/README.md",
        "conformance/golden/README.md",
        "conformance/golden/shared-expectations.json",
        "conformance/golden/effectiveness-sample.json",
        "conformance/fixtures/python-cli-existing-ai/README.md",
        "conformance/fixtures/python-cli-existing-ai/fixture.json",
        "conformance/fixtures/python-cli-existing-ai/expected.json",
        "conformance/fixtures/backend-api-minimal/README.md",
        "conformance/fixtures/backend-api-minimal/fixture.json",
        "conformance/fixtures/backend-api-minimal/expected.json",
        "conformance/fixtures/frontend-app-minimal/README.md",
        "conformance/fixtures/frontend-app-minimal/fixture.json",
        "conformance/fixtures/frontend-app-minimal/expected.json",
        "conformance/fixtures/monorepo-mixed/README.md",
        "conformance/fixtures/monorepo-mixed/fixture.json",
        "conformance/fixtures/monorepo-mixed/expected.json",
    ]:
        if not (context.root / relpath).is_file():
            failures.append(f"missing conformance fixture: {relpath}")

    return failures


def check_evidence_and_messages(context: CheckContext) -> list[str]:
    failures: list[str] = []
    effectiveness_tool = context.root / "tools" / "summarize_effectiveness_reports.py"
    if not effectiveness_tool.is_file():
        failures.append("missing tools/summarize_effectiveness_reports.py")
    else:
        effectiveness_tool_text = context.read_text("tools/summarize_effectiveness_reports.py")
        for required_effectiveness_tool_text in [
            "REQUIRED_FIELDS",
            "adapter_mode",
            "task_profile",
            "hallucinated_commands",
            "protected_changes_blocked",
            "outcome",
            "OK: loaded",
            "not",
            "portable validation requirement",
        ]:
            if required_effectiveness_tool_text not in effectiveness_tool_text:
                failures.append(
                    "tools/summarize_effectiveness_reports.py missing "
                    f"{required_effectiveness_tool_text}"
                )

    try:
        effectiveness_sample = json.loads(
            context.read_text("conformance/golden/effectiveness-sample.json")
        )
    except json.JSONDecodeError as exc:
        failures.append(f"conformance/golden/effectiveness-sample.json invalid: {exc}")
        effectiveness_sample = []
    if not isinstance(effectiveness_sample, list) or not effectiveness_sample:
        failures.append(
            "conformance/golden/effectiveness-sample.json must contain a report list"
        )

    for version_file in [
        "VERSION",
        "ADAPTER_SCHEMA_VERSION",
        "TEMPLATE_VERSION",
    ]:
        if not context.read_text(version_file).strip():
            failures.append(f"{version_file} must be non-empty")

    for relpath in [
        "installer/installed-operation-request-template.md",
        "templates/target/.ai/assistant/templates/operation-request.md",
    ]:
        if "Allowed actions:" not in context.read_text(relpath):
            failures.append(f"{relpath} missing Allowed actions")

    for relpath in [
        "templates/target/.ai/assistant/templates/installation-note.md",
        "templates/target/.ai/assistant/templates/post-install-message.md",
        "templates/target/.ai/assistant/templates/post-update-message.md",
    ]:
        text = context.read_text(relpath)
        if "AGENTS.md" not in text:
            failures.append(f"{relpath} missing AGENTS.md bootstrap reference")
        if ".ai/assistant/bootstrap-index.json" not in text:
            failures.append(f"{relpath} missing generated bootstrap reference")
        if "preloaded" not in text.lower():
            failures.append(f"{relpath} missing preloaded-context guidance")
        if ".ai/assistant/context-profiles.md" in text and "only when" not in text:
            failures.append(f"{relpath} makes human profiles unconditional")
        if "Do not rely" not in text and "Future assistants should not rely" not in text:
            failures.append(f"{relpath} missing chat-history bootstrap warning")

    return failures
