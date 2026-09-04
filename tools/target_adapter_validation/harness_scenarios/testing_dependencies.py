"""Target-validator scenarios for testing dependencies."""

from __future__ import annotations

from .common import (
    ROOT,
    json,
    validator,
    write_json,
)


def run(target: Path, failures: list[str]) -> None:
    catalog_path = target / ".ai" / "assistant" / "operation-catalog.json"
    router_path = target / ".ai" / "assistant" / "context-router.json"
    module_profile_path = target / ".ai" / "assistant" / "module-profile.md"
    valid_policy_path = target / ".ai/project/testing/test-first-policy.json"
    valid_policy = json.loads(valid_policy_path.read_text(encoding="utf-8"))
    valid_policy["activation_triggers"][0]["test_level_ids"] = ["unit"]
    valid_policy["activation_triggers"][0]["exceptions"] = []
    valid_policy["test_levels"][0]["command_ids"] = ["unit-test"]
    write_json(valid_policy_path, valid_policy)
    write_json(
        catalog_path,
        {
            "operations": [
                {
                    "id": "test-first-configuration",
                    "required_module": "core-profile",
                },
                {
                    "id": "test-first-change",
                    "required_module": "test-first-development",
                },
            ]
        },
    )
    write_json(
        router_path,
        {
            "intent_overlays": {
                "test-first-request": {
                    "operation_candidates": [
                        "test-first-configuration",
                        "test-first-change",
                    ]
                }
            }
        },
    )
    enabled_policy = validator(target)
    enabled_policy.check_test_first_development(None)
    enabled_errors = [
        finding.code
        for finding in enabled_policy.findings
        if finding.level == "error" and finding.code.startswith("TDD_")
    ]
    if enabled_errors:
        failures.append(
            "resolved enabled test-first policy produced errors: "
            + ", ".join(enabled_errors)
        )

    module_profile_path.write_text(
        "# Module Profile\n\n"
        "Module: `dependency-knowledge`\nState: `enabled`\n",
        encoding="utf-8",
    )
    dependency_knowledge = validator(target)
    dependency_knowledge.check_dependency_knowledge(None)
    if "DEPENDENCY_KNOWLEDGE_REQUIRED_FILE_MISSING" not in {
        finding.code for finding in dependency_knowledge.findings
    }:
        failures.append(
            "enabled dependency knowledge must report missing contracts"
        )

    dependency_paths = [
        ".ai/framework/dependency-knowledge.md",
        ".ai/project/dependencies/README.md",
        ".ai/project/dependencies/policy.json",
        ".ai/project/dependencies/catalog.json",
        ".ai/project/dependencies/knowledge-lock.json",
        ".ai/project/dependencies/deviations.json",
        ".ai/project/dependencies/snapshots/README.md",
        ".ai/assistant/context/intents/dependency-knowledge-request.json",
        ".ai/assistant/flows/dependency-knowledge-sync.flow.md",
        ".ai/assistant/gates/dependency-knowledge.md",
        ".ai/assistant/templates/dependency-knowledge-sync-report.md",
        ".ai/assistant/operation-catalog.json",
        ".ai/assistant/context-router.json",
    ]
    for relpath in dependency_paths:
        source = (
            ROOT / "framework/dependency-knowledge.md"
            if relpath.startswith(".ai/framework/")
            else ROOT / "templates/target" / relpath
        )
        destination = target / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    (target / "package.json").write_text("{}\n", encoding="utf-8")
    (target / "package-lock.json").write_text("{}\n", encoding="utf-8")
    dependency_policy_path = target / ".ai/project/dependencies/policy.json"
    dependency_policy = json.loads(
        dependency_policy_path.read_text(encoding="utf-8")
    )
    dependency_policy.update({"state": "enabled", "owner": "fixture-owner"})
    dependency_policy["package_sources"] = [
        {
            "ecosystem": "fixture",
            "manifest": "package.json",
            "lockfile": "package-lock.json",
            "metadata_locator_kind": "native-package-metadata-key",
            "metadata_locator": "fixture.alatyr",
        }
    ]
    dependency_policy["limits"] = {
        key: 10
        for key in [
            "max_manifest_bytes",
            "max_export_bytes",
            "max_exports_per_package",
            "max_graph_depth",
            "max_graph_instances",
        ]
    }
    write_json(dependency_policy_path, dependency_policy)
    instance_id = "fixture:example/library@1.0.0#root"
    export_id = "fixture:example/library.public-contract"
    fingerprint = "a" * 64
    export_digest = "b" * 64
    manifest_digest = "c" * 64
    catalog_data = {
        "schema_version": 1,
        "catalog_kind": "target-dependency-knowledge-catalog",
        "owner": "fixture-owner",
        "package_lock_fingerprint": fingerprint,
        "packages": [
            {
                "instance_id": instance_id,
                "ecosystem": "fixture",
                "name": "example/library",
                "version": "1.0.0",
                "export_status": "available",
                "trust": "reviewed",
                "freshness": "current",
                "exports": [
                    {
                        "id": export_id,
                        "type": "public-contract",
                        "summary": "fixture public contract",
                        "content_digest": export_digest,
                        "authority": "upstream-canonical",
                        "stability": "stable",
                        "applicability": {
                            "state": "active",
                            "conditions": [],
                        },
                        "evidence": ["exports/contracts.json"],
                    }
                ],
            }
        ],
    }
    lock_data = {
        "schema_version": 1,
        "lock_kind": "target-dependency-knowledge-lock",
        "knowledge_api": 1,
        "package_lock_fingerprint": fingerprint,
        "instances": [
            {
                "instance_id": instance_id,
                "ecosystem": "fixture",
                "name": "example/library",
                "version": "1.0.0",
                "source": "fixture-source",
                "integrity": "fixture-integrity",
                "revision": "fixture-revision",
                "modifications": [],
                "manifest": {
                    "path": "alatyr-dependency.json",
                    "content_digest": manifest_digest,
                },
                "exports": [
                    {
                        "id": export_id,
                        "path": "exports/contracts.json",
                        "content_digest": export_digest,
                    }
                ],
                "graph": {
                    "dependency_set": "runtime",
                    "direct": True,
                    "public_instance_ids": [],
                },
            }
        ],
    }
    write_json(target / ".ai/project/dependencies/catalog.json", catalog_data)
    write_json(target / ".ai/project/dependencies/knowledge-lock.json", lock_data)
    write_json(
        target / ".ai/project/dependencies/deviations.json",
        {
            "schema_version": 1,
            "deviation_kind": "target-dependency-knowledge-deviations",
            "owner": "fixture-owner",
            "deviations": [],
        },
    )
    valid_dependency = validator(target)
    valid_dependency.check_dependency_knowledge(None)
    valid_dependency_errors = [
        finding.code
        for finding in valid_dependency.findings
        if finding.level == "error"
        and finding.code.startswith("DEPENDENCY_KNOWLEDGE_")
    ]
    if valid_dependency_errors:
        failures.append(
            "resolved dependency knowledge projection produced errors: "
            + ", ".join(valid_dependency_errors)
        )
    dependency_policy["package_sources"][0]["metadata_locator_kind"] = "adapter"
    write_json(dependency_policy_path, dependency_policy)
    invalid_locator = validator(target)
    invalid_locator.check_dependency_knowledge(None)
    if "DEPENDENCY_KNOWLEDGE_SOURCE_LOCATOR" not in {
        finding.code for finding in invalid_locator.findings
    }:
        failures.append(
            "dependency knowledge must reject non-native metadata locators"
        )
    dependency_policy["package_sources"][0]["metadata_locator_kind"] = (
        "native-package-metadata-key"
    )
    write_json(dependency_policy_path, dependency_policy)
    lock_data["instances"][0]["graph"]["public_instance_ids"] = [
        "fixture:missing@1.0.0#transitive"
    ]
    write_json(target / ".ai/project/dependencies/knowledge-lock.json", lock_data)
    dangling_dependency = validator(target)
    dangling_dependency.check_dependency_knowledge(None)
    if "DEPENDENCY_KNOWLEDGE_GRAPH_REFERENCE" not in {
        finding.code for finding in dangling_dependency.findings
    }:
        failures.append(
            "dependency knowledge must reject dangling graph references"
        )
