"""Target-validator scenarios for approval scope."""

from __future__ import annotations

from .common import (
    AdapterValidatorConfig,
    Finding,
    Validator,
    findings_payload,
    git_changed_files,
    subprocess,
    validator,
    write_json,
)


def run(target: Path, failures: list[str]) -> None:
    git_target = target / "approval-diff"
    git_target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=git_target, check=True)
    subprocess.run(
        ["git", "config", "user.email", "alatyr@example.invalid"],
        cwd=git_target,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Alatyr Check"],
        cwd=git_target,
        check=True,
    )
    source = git_target / "src"
    source.mkdir()
    (source / "allowed.txt").write_text("before\n", encoding="utf-8")
    (source / "outside.txt").write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=git_target, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "fixture"],
        cwd=git_target,
        check=True,
    )
    (source / "allowed.txt").write_text("after\n", encoding="utf-8")
    (source / "outside.txt").write_text("after\n", encoding="utf-8")
    (source / "untracked.txt").write_text("new\n", encoding="utf-8")
    approval_path = (
        git_target
        / ".ai"
        / "assistant"
        / "approvals"
        / "approval.json"
    )
    approval_data = {
        "schema_version": 1,
        "record_kind": "alatyr-approval-record",
        "evidence_classification": "historical-record",
        "approval_id": "approval-test",
        "operation": {"id": "operation-test", "type": "code-change"},
        "plan": {"version": "1", "sha256": "none", "file": "none"},
        "diff": {
            "base": "HEAD",
            "patch_sha256": "none",
            "repository_revision_at_approval": "HEAD",
        },
        "scope": {
            "allowed_protected_changes": ["test change"],
            "allowed_files_or_surfaces": [
                "src/allowed.txt",
                ".ai/assistant/approvals/approval.json",
            ],
            "excluded_files_or_surfaces": [],
            "excluded_actions": ["live actions"],
            "allowed_actions_mode": "code-and-tests",
            "invalidation_rule": "any scope change invalidates approval",
        },
        "approval": {
            "approved_by": "tester",
            "approved_at": "2026-07-14",
        },
        "use_result": {},
    }
    write_json(approval_path, approval_data)
    changed = git_changed_files(git_target, "HEAD")
    expected_changed = {
        ".ai/assistant/approvals/approval.json",
        "src/allowed.txt",
        "src/outside.txt",
        "src/untracked.txt",
    }
    if changed is None or set(changed) != expected_changed:
        failures.append(
            "approval diff collection must include tracked and untracked paths"
        )

    strict = Validator(
        git_target,
        framework_source=None,
        diff_ref="HEAD",
        approval_records=[approval_path],
        enforce_approval_scope=True,
        change_packages=[],
        enforce_change_package=False,
        migration_diff=None,
        allow_placeholders=True,
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
    )
    strict.check_approval_scope()
    mismatch_messages = [
        finding.message
        for finding in strict.findings
        if finding.code == "APPROVAL_SCOPE_MISMATCH" and finding.level == "error"
    ]
    if not any("src/outside.txt" in message for message in mismatch_messages):
        failures.append("strict approval scope must reject tracked out-of-scope files")
    if not any("src/untracked.txt" in message for message in mismatch_messages):
        failures.append("strict approval scope must reject untracked out-of-scope files")

    approval_data["scope"]["allowed_files_or_surfaces"] = [
        "src/*",
        ".ai/assistant/approvals/approval.json",
    ]
    write_json(approval_path, approval_data)
    covered = Validator(
        git_target,
        framework_source=None,
        diff_ref="HEAD",
        approval_records=[approval_path],
        enforce_approval_scope=True,
        change_packages=[],
        enforce_change_package=False,
        migration_diff=None,
        allow_placeholders=True,
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
    )
    covered.check_approval_scope()
    if any(
        finding.level == "error" and finding.code.startswith("APPROVAL_")
        for finding in covered.findings
    ):
        failures.append("covered strict approval scope should pass")

    historical_target = target / "historical-approval-selection"
    historical_path = (
        historical_target
        / ".ai"
        / "assistant"
        / "approvals"
        / "historical.json"
    )
    historical_data = dict(approval_data)
    historical_data["scope"] = dict(approval_data["scope"])
    historical_data["scope"]["allowed_files_or_surfaces"] = [
        "../external-project/**"
    ]
    historical_data["use_result"] = {
        "patch_changed_after_approval": "yes: historical correction",
        "implementation_within_scope": "yes",
    }
    write_json(historical_path, historical_data)

    ordinary_health = validator(
        historical_target, validation_phase="acceptance"
    )
    ordinary_health.check_approval_scope()
    ordinary_findings = {
        finding.code: finding.level for finding in ordinary_health.findings
    }
    for expected_archive_warning in {
        "APPROVAL_RECORD_SCOPE_INVALID",
        "APPROVAL_PATCH_CHANGED",
    }:
        if ordinary_findings.get(expected_archive_warning) != "warning":
            failures.append(
                "ordinary health must audit historical approval archives without "
                f"promoting {expected_archive_warning} to current-scope enforcement"
            )
    if "APPROVAL_SCOPE_MISMATCH" in ordinary_findings:
        failures.append(
            "ordinary current-health validation must not apply historical approval "
            "scope to the current diff"
        )
    if ordinary_findings.get("APPROVAL_ARCHIVE_CHECKED") != "info":
        failures.append("ordinary health must report historical approval archive audit")

    malformed_history = historical_path.with_name("malformed.json")
    malformed_history.write_text("{invalid\n", encoding="utf-8")
    malformed_health = validator(
        historical_target, validation_phase="acceptance"
    )
    malformed_health.check_approval_scope()
    if not any(
        finding.code == "APPROVAL_RECORD_INVALID_JSON"
        and finding.level == "warning"
        and finding.path.endswith("malformed.json")
        for finding in malformed_health.findings
    ):
        failures.append("ordinary health must detect malformed archived approvals")

    explicit_history = Validator(
        historical_target,
        framework_source=None,
        diff_ref=None,
        approval_records=[historical_path],
        enforce_approval_scope=False,
        change_packages=[],
        enforce_change_package=False,
        migration_diff=None,
        allow_placeholders=False,
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
        validation_phase="acceptance",
    )
    explicit_history.check_approval_scope()
    explicit_codes = {finding.code for finding in explicit_history.findings}
    for required in {
        "APPROVAL_RECORD_SCOPE_INVALID",
        "APPROVAL_PATCH_CHANGED",
    }:
        if required not in explicit_codes:
            failures.append(
                f"explicitly selected historical approval must retain {required}"
            )

    payload = findings_payload(
        [],
        target=target,
        strict_warnings=False,
        installation_state="accepted",
    )
    evidence = payload.get("evidence", {})
    if payload.get("schema_version") != 3:
        failures.append("validator JSON schema must expose evidence schema 3")
    if evidence.get("basis") != "current-state-structural":
        failures.append("validator JSON must classify current-state evidence")
    if evidence.get("historical_actions_verified") is not False:
        failures.append("validator JSON must not imply historical actions were verified")

    staging_payload = findings_payload(
        [
            Finding(
                "warning",
                "PLACEHOLDER_STAGING_UNRESOLVED",
                "staged placeholder",
                ".ai/project/debug/README.md:1",
            )
        ],
        target=target,
        strict_warnings=False,
        validation_phase="migration-staging",
        installation_state="staged",
    )
    if staging_payload.get("status") != "staged":
        failures.append("migration staging must not report passed status")
    if staging_payload.get("adapter_health", {}).get("state") != "unverified":
        failures.append("migration staging must report unverified adapter health")
    if staging_payload.get("placeholder_validation", {}).get("acceptance_eligible") is not False:
        failures.append("migration staging must never be acceptance eligible")
    if staging_payload.get("placeholder_validation", {}).get("unresolved_active") != 1:
        failures.append("migration staging must count unresolved active placeholders")
