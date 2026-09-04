"""Target-validator scenarios for extensions."""

from __future__ import annotations

from .common import (
    Path,
    hashlib,
    validator,
    write_json,
)


def run(target: Path, failures: list[str]) -> None:
    catalog_path = target / ".ai" / "assistant" / "operation-catalog.json"
    module_profile_path = target / ".ai" / "assistant" / "module-profile.md"
    extension_id = "example.review"
    extension_root = target / ".ai/assistant/extensions" / extension_id
    extension_root.mkdir(parents=True, exist_ok=True)
    manifest_path = extension_root / "manifest.json"
    bindings_path = extension_root / "bindings.json"
    item_path = extension_root / "items" / "review.md"
    adaptation_path = extension_root / "adaptation-record.md"
    approval_path = target / ".ai/assistant/approvals/extension.json"
    rule_registry_path = target / ".ai/framework/rule-registry.json"
    write_json(
        manifest_path,
        {
            "schema_version": 1,
            "package_kind": "alatyr-extension",
            "id": extension_id,
            "version": "1.0.0",
            "provides": [{"id": "review", "type": "skill", "path": "items/review.md"}],
        },
    )
    write_json(
        bindings_path,
        {
            "schema_version": 1,
            "binding_kind": "target-alatyr-extension-bindings",
            "extension_id": extension_id,
            "bindings": [
                {
                    "id": "project-owner",
                    "value": "fixture-owner",
                    "owner": "fixture-owner",
                    "source": ".ai/project/contour.md",
                }
            ],
        },
    )
    item_path.parent.mkdir(parents=True, exist_ok=True)
    item_path.write_text("normalized review item\n", encoding="utf-8")
    adaptation_path.write_text("review and approval evidence\n", encoding="utf-8")
    write_json(approval_path, {"approval_id": "extension-fixture"})
    write_json(rule_registry_path, {"schema_version": 1, "rules": []})

    def extension_hash(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    installed_files = [
        {
            "path": path.relative_to(target).as_posix(),
            "sha256": extension_hash(path),
            "owner": extension_id,
        }
        for path in [manifest_path, bindings_path, item_path, adaptation_path]
    ]
    catalog_entry = {
        "id": extension_id,
        "version": "1.0.0",
        "state": "active",
        "owner": "fixture-owner",
        "lock_id": "extension-fixture-lock",
        "manifest": manifest_path.relative_to(target).as_posix(),
        "bindings": bindings_path.relative_to(target).as_posix(),
        "item_ids": ["review"],
        "supported_assistants": ["generic"],
        "last_reviewed": "2026-08-12",
        "evidence_revision": "fixture-revision",
        "known_gaps": [],
    }
    lock_entry = {
        "id": extension_id,
        "lock_id": "extension-fixture-lock",
        "version": "1.0.0",
        "state": "active",
        "source_type": "git-url",
        "source": "https://example.invalid/review.git",
        "source_revision": "0123456789abcdef0123456789abcdef01234567",
        "package_digest_sha256": "a" * 64,
        "license_status": "accepted",
        "compatibility": {"result": "compatible"},
        "manifest": manifest_path.relative_to(target).as_posix(),
        "bindings": bindings_path.relative_to(target).as_posix(),
        "adaptation_record": adaptation_path.relative_to(target).as_posix(),
        "installed_files": installed_files,
        "integration_surfaces": [".ai/assistant/operation-catalog.json"],
        "approval_record": approval_path.relative_to(target).as_posix(),
        "validation": ["fixture structural validation passed"],
        "installed_at": "2026-08-12T00:00:00Z",
    }
    write_json(
        target / ".ai/assistant/extensions/catalog.json",
        {
            "schema_version": 1,
            "catalog_kind": "target-alatyr-extension-catalog",
            "extension_api": 1,
            "owner": "fixture-owner",
            "last_reviewed": "2026-08-12",
            "extensions": [catalog_entry],
        },
    )
    write_json(
        target / ".ai/assistant/extensions/lock.json",
        {
            "schema_version": 1,
            "lock_kind": "target-alatyr-extension-lock",
            "extension_api": 1,
            "target_baseline": {
                "framework_version": "0.1.0-alpha.8",
                "adapter_schema_version": 7,
                "template_version": 8,
                "rule_registry": ".ai/framework/rule-registry.json",
            },
            "extensions": [lock_entry],
        },
    )
    write_json(
        catalog_path,
        {
            "operations": [
                {"id": "extension-management", "required_module": "core-profile"}
            ]
        },
    )
    installed_extension = validator(target)
    installed_extension.check_extensions(None)
    extension_errors = [
        finding.code
        for finding in installed_extension.findings
        if finding.level == "error" and finding.code.startswith("EXTENSION_")
    ]
    if extension_errors:
        failures.append(
            "resolved installed extension produced errors: "
            + ", ".join(extension_errors)
        )
    item_path.write_text("locally modified review item\n", encoding="utf-8")
    drifted_extension = validator(target)
    drifted_extension.check_extensions(None)
    if "EXTENSION_FILE_DRIFT" not in {
        finding.code for finding in drifted_extension.findings
    }:
        failures.append("extension lock must detect installed-file drift")

    module_profile_path.write_text(
        "# Module Profile\n\n"
        "Module: `architecture-knowledge`\nState: `enabled`\n",
        encoding="utf-8",
    )

    architecture_text_files = {
        ".ai/project/architecture/README.md": (
            "## Status Meanings\n## Architecture Patterns And Items\n"
            "Evidence revision:\n"
        ),
        ".ai/assistant/context/intents/architecture-request.json": "{}\n",
        ".ai/assistant/flows/architecture-assistance.flow.md": (
            "## Routing Modes\nno-change baseline\n"
            "reuse of an accepted project pattern\n"
            "adaptation of an existing pattern\nnew pattern\n"
            "`docs-only`\n`full-with-approval`\n"
        ),
        ".ai/assistant/templates/architecture-pattern.md": (
            "Pattern ID:\nProblem addressed:\nRules and invariants:\n"
            "Do not use when:\nLast verified revision:\n"
        ),
        ".ai/assistant/templates/architecture-area.md": (
            "Area ID:\nResponsibilities:\nPattern IDs:\n"
            "Validation or fitness checks:\n"
        ),
        ".ai/assistant/templates/architecture-discussion-result.md": (
            "No-change baseline:\nReuse accepted project pattern:\n"
            "Adapt existing project pattern:\nIntroduce new pattern:\n"
            "Pattern-proliferation result:\n"
        ),
        ".ai/framework/architecture-knowledge.md": (
            "# Architecture Knowledge\n"
        ),
    }
    for relpath, content in architecture_text_files.items():
        path = target / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    write_json(
        target / ".ai" / "project" / "architecture" / "catalog.json",
        {
            "schema_version": 1,
            "catalog_kind": "target-architecture-knowledge-catalog",
            "project": "fixture",
            "module_state": "enabled",
            "human_index": ".ai/project/architecture/README.md",
            "architecture_owner": "architecture-team",
            "decision_authority": "architecture-board",
            "canonical_sources": ["docs/architecture.md"],
            "decision_sources": ["docs/decisions"],
            "last_reviewed": "2026-08-03",
            "evidence_revision": "fixture-revision",
            "areas": [
                {
                    "id": "area-core",
                    "name": "Core",
                    "status": "accepted",
                    "owner": "core-team",
                    "detail": "docs/core.md",
                    "evidence": ["src/core"],
                    "pattern_ids": ["missing-pattern"],
                },
                {
                    "id": "area-core",
                    "name": "Duplicate",
                    "status": "observed",
                    "owner": "core-team",
                    "detail": "docs/core.md",
                    "evidence": ["src/core"],
                    "pattern_ids": [],
                },
            ],
            "patterns": [
                {
                    "id": "pattern-layered",
                    "name": "Layered",
                    "kind": "invalid-kind",
                    "status": "accepted",
                    "scope": ["area-core"],
                    "problem": "dependency direction",
                    "decision_owner": "architecture-board",
                    "decision_record": "{UNRESOLVED_DECISION_RECORD}",
                    "detail": "docs/patterns/layered.md",
                    "evidence": ["src/core"],
                    "validation": ["architecture check"],
                    "related_pattern_ids": ["missing-pattern"],
                    "last_verified_revision": "fixture-revision",
                }
            ],
            "known_gaps": [],
        },
    )
    invalid_architecture = validator(target)
    invalid_architecture.check_architecture_knowledge(None)
    invalid_architecture_codes = {
        finding.code for finding in invalid_architecture.findings
    }
    for required in [
        "ARCHITECTURE_AREA_ID_DUPLICATE",
        "ARCHITECTURE_PATTERN_KIND",
        "ARCHITECTURE_PATTERN_REFERENCE",
        "ARCHITECTURE_ACCEPTED_EVIDENCE",
        "ARCHITECTURE_OPERATION_MISSING",
        "ARCHITECTURE_OPERATION_UNROUTED",
    ]:
        if required not in invalid_architecture_codes:
            failures.append(
                f"invalid architecture catalog missing finding {required}"
            )

    routing_path = (
        target / ".ai" / "assistant" / "flows" / "operation-routing.flow.md"
    )
    routing_path.parent.mkdir(parents=True, exist_ok=True)
    routing_path.write_text(
        "Load bootstrap context only. Do not load all `.ai/framework` files.\n",
        encoding="utf-8",
    )
    bounded_routing = validator(target)
    bounded_routing.check_bootstrap_references()
    if "ROUTING_LOADS_BROAD_CONTEXT" in {
        finding.code for finding in bounded_routing.findings
    }:
        failures.append("negative broad-load guidance must not fail routing checks")
    routing_path.write_text(
        "Load bootstrap context only. Load all `.ai/framework` files.\n",
        encoding="utf-8",
    )
    broad_routing = validator(target)
    broad_routing.check_bootstrap_references()
    if "ROUTING_LOADS_BROAD_CONTEXT" not in {
        finding.code for finding in broad_routing.findings
    }:
        failures.append("positive broad-load guidance must fail routing checks")
