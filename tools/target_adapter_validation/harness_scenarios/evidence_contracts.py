"""Target-validator scenarios for evidence contracts."""

from __future__ import annotations

from .common import (
    Finding,
    ROOT,
    findings_payload,
    json,
    parse_manifest,
    shutil,
    validator,
    write_json,
)


def run(target: Path, failures: list[str]) -> None:
    active_target = target / "active-surface"
    active_readme = active_target / ".ai/project/debug/README.md"
    active_readme.parent.mkdir(parents=True, exist_ok=True)
    active_readme.write_text("Owner: `{DEBUG_EVIDENCE_OWNER}`\n", encoding="utf-8")
    strict_placeholders = validator(active_target, validation_phase="acceptance")
    strict_placeholders.capability_modules = {
        "debug-mode": {"target_files": [".ai/project/debug/README.md"]}
    }
    strict_placeholders.check_placeholders(
        None, "core", {"debug-mode"}
    )
    if "PLACEHOLDER_UNRESOLVED" not in {
        finding.code for finding in strict_placeholders.findings
    }:
        failures.append("acceptance must reject placeholders on enabled live surfaces")

    staged_placeholders = validator(
        active_target, validation_phase="migration-staging"
    )
    staged_placeholders.capability_modules = strict_placeholders.capability_modules
    staged_placeholders.check_placeholders(None, "core", {"debug-mode"})
    if "PLACEHOLDER_STAGING_UNRESOLVED" not in {
        finding.code for finding in staged_placeholders.findings
    }:
        failures.append("migration staging must inventory live placeholders")
    if any(
        finding.code == "PLACEHOLDER_UNRESOLVED"
        for finding in staged_placeholders.findings
    ):
        failures.append("migration staging must classify rather than accept/reject placeholders")

    profile_target = target / "module-profile-sync"
    profile_path = profile_target / ".ai/assistant/module-profile.md"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text("# Module Profile\n", encoding="utf-8")
    profile_manifest_path = profile_target / ".ai/alatyr.yaml"
    profile_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    profile_manifest_path.write_text(
        "modules:\n  enabled:\n    - debug-mode\n", encoding="utf-8"
    )
    profile_manifest = parse_manifest(profile_manifest_path)
    profile_validator = validator(profile_target)
    profile_validator.capability_modules = {"debug-mode": {}}
    profile_validator.check_module_profile_sync(profile_manifest)
    if "MODULE_PROFILE_ENABLED_MISSING" not in {
        finding.code for finding in profile_validator.findings
    }:
        failures.append("manifest-enabled modules must require a matching profile block")

    projection_target = target / "policy-projection"
    projection_readme = projection_target / ".ai/project/debug/README.md"
    projection_readme.parent.mkdir(parents=True, exist_ok=True)
    projection_readme.write_text("Owner: human-owner\n", encoding="utf-8")
    projection_validator = validator(projection_target)
    projection_validator.check_policy_readme_projection(
        index={"owner": "machine-owner"},
        readme_relpath=".ai/project/debug/README.md",
        fields={"Owner": "owner"},
        code_prefix="DEBUG_MODE_POLICY",
    )
    if "DEBUG_MODE_POLICY_DRIFT" not in {
        finding.code for finding in projection_validator.findings
    }:
        failures.append("machine and human policy metadata drift must be rejected")

    health_payload = findings_payload(
        [
            Finding(
                "warning",
                "OPERATION_CATALOG_MISSING",
                "catalog missing",
                ".ai/assistant/operation-catalog.json",
            )
        ],
        target=target,
        strict_warnings=False,
        installation_state="accepted",
    )
    if health_payload.get("adapter_health", {}).get("state") != "attention":
        failures.append("validator warning must produce attention health state")
    if health_payload.get("adapter_health", {}).get("repair_operations") != [
        "recheck-after-installation"
    ]:
        failures.append("validator health must return prioritized repair routes")
    health_finding = health_payload.get("findings", [{}])[0]
    if health_finding.get("automatic_repair") is not False:
        failures.append("validator findings must not imply automatic repair")
    extension_health = findings_payload(
        [
            Finding(
                "warning",
                "EXTENSION_FILE_DRIFT",
                "extension item changed",
                ".ai/assistant/extensions/example/items/review.md",
            )
        ],
        target=target,
        strict_warnings=False,
        installation_state="accepted",
    )
    if extension_health.get("adapter_health", {}).get("repair_operations") != [
        "extension-management"
    ]:
        failures.append("extension findings must route to extension-management")
    if extension_health.get("exit_code") != 0:
        failures.append("ordinary advisory warnings must remain non-blocking by default")

    contract_target = target / "versioned-record-contracts"
    shutil.copytree(ROOT / "templates" / "target", contract_target)
    engineering_template_path = contract_target / ".ai/assistant/templates/engineering-evidence-record.json"
    engineering_template = json.loads(engineering_template_path.read_text(encoding="utf-8"))
    engineering_template["schema_version"] = 1
    engineering_template["repository_binding"].pop("binding_state")
    engineering_template["repository_binding"].pop("prior_bindings")
    write_json(engineering_template_path, engineering_template)
    debug_template_path = contract_target / ".ai/assistant/templates/debug-session-record.json"
    debug_template = json.loads(debug_template_path.read_text(encoding="utf-8"))
    debug_template["schema_version"] = 1
    debug_template["final_result"]["repository_binding"].pop("binding_state")
    debug_template["final_result"]["repository_binding"].pop("prior_bindings")
    debug_template.pop("continuation")
    debug_template["final_result"].pop("claim_validation")
    debug_template["final_result"].pop("engineering_evidence_decision")
    write_json(debug_template_path, debug_template)
    stale_templates = validator(contract_target)
    manifest = parse_manifest(contract_target / ".ai/alatyr.yaml")
    stale_templates.check_engineering_evidence(manifest)
    stale_templates.check_debug_mode(manifest)
    stale_template_codes = {finding.code for finding in stale_templates.findings}
    for required in {
        "ENGINEERING_EVIDENCE_TEMPLATE_VERSION",
        "ENGINEERING_EVIDENCE_TEMPLATE_BINDING",
        "DEBUG_MODE_TEMPLATE_VERSION",
        "DEBUG_MODE_TEMPLATE_BINDING",
        "DEBUG_MODE_TEMPLATE_EVIDENCE_DECISION",
        "DEBUG_MODE_TEMPLATE_CONTINUATION",
    }:
        if required not in stale_template_codes:
            failures.append(f"installed validator did not detect stale authoring contract {required}")

    manifest_path = contract_target / ".ai/alatyr.yaml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_text = manifest_text.replace(
        "engineering_evidence:\n  contract_version: 3",
        "engineering_evidence:\n  contract_version: 1",
    ).replace(
        "debug_mode:\n  contract_version: 6",
        "debug_mode:\n  contract_version: 1",
    )
    manifest_path.write_text(manifest_text, encoding="utf-8")
    stale_contracts = validator(contract_target)
    stale_manifest = parse_manifest(manifest_path)
    stale_contracts.check_engineering_evidence(stale_manifest)
    stale_contracts.check_debug_mode(stale_manifest)
    stale_contract_codes = {finding.code for finding in stale_contracts.findings}
    for required in {
        "ENGINEERING_EVIDENCE_CONTRACT_VERSION",
        "DEBUG_MODE_CONTRACT_VERSION",
    }:
        if required not in stale_contract_codes:
            failures.append(f"installed validator did not detect stale manifest contract {required}")
