"""Validate target-owned dependency knowledge support."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from target_validation_support import ManifestData, dotted, is_placeholder, is_target_relative_path, is_unresolved_value

from target_adapter_validation.capability import (
    CapabilityValidationContext,
    FunctionCapabilityModule,
)


def validate_dependency_knowledge(
    context: CapabilityValidationContext,
    manifest: ManifestData | None,
) -> None:
    required_paths = [
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
    ]
    missing = False
    for relpath in required_paths:
        if not context.target_path(relpath).is_file():
            missing = True
            context.error(
                "DEPENDENCY_KNOWLEDGE_REQUIRED_FILE_MISSING",
                "enabled dependency-knowledge module is missing a contract",
                relpath,
            )
    if missing:
        return

    expected_manifest = {
        ("dependency_knowledge", "index"): required_paths[1],
        ("dependency_knowledge", "policy"): required_paths[2],
        ("dependency_knowledge", "catalog"): required_paths[3],
        ("dependency_knowledge", "lock"): required_paths[4],
        ("dependency_knowledge", "deviations"): required_paths[5],
        ("dependency_knowledge", "snapshots"): ".ai/project/dependencies/snapshots",
        ("dependency_knowledge", "intent"): required_paths[7],
        ("dependency_knowledge", "flow"): required_paths[8],
        ("dependency_knowledge", "gate"): required_paths[9],
        ("dependency_knowledge", "report"): required_paths[10],
        ("operations", "dependency_knowledge"): required_paths[8],
        ("operations", "dependency_knowledge_report"): required_paths[10],
    }
    if manifest is not None:
        for key, expected in expected_manifest.items():
            scalar = manifest.scalars.get(key)
            if scalar is None or scalar.value != expected:
                context.error(
                    "DEPENDENCY_KNOWLEDGE_MANIFEST_PATH",
                    f"{dotted(key)} must be {expected} when dependency knowledge is enabled",
                    ".ai/alatyr.yaml",
                )
    policy_relpath = required_paths[2]
    catalog_relpath = required_paths[3]
    lock_relpath = required_paths[4]
    deviation_relpath = required_paths[5]
    policy = context.load_json_object(context.target_path(policy_relpath), "DEPENDENCY_KNOWLEDGE_POLICY")
    catalog = context.load_json_object(context.target_path(catalog_relpath), "DEPENDENCY_KNOWLEDGE_CATALOG")
    lock = context.load_json_object(context.target_path(lock_relpath), "DEPENDENCY_KNOWLEDGE_LOCK")
    deviations = context.load_json_object(context.target_path(deviation_relpath), "DEPENDENCY_KNOWLEDGE_DEVIATIONS")
    if any(value is None for value in [policy, catalog, lock, deviations]):
        return

    def resolved(value: Any) -> bool:
        return (
            isinstance(value, str)
            and bool(value.strip())
            and not is_placeholder(value)
            and not is_unresolved_value(value)
        )

    if policy.get("schema_version") != 1 or policy.get("policy_kind") != "target-dependency-knowledge-policy":
        context.error("DEPENDENCY_KNOWLEDGE_POLICY_SCHEMA", "policy schema or kind is invalid", policy_relpath)
    if policy.get("state") not in {"enabled", "required"}:
        context.error("DEPENDENCY_KNOWLEDGE_POLICY_STATE", "enabled module requires enabled or required policy state", policy_relpath)
    if not resolved(policy.get("owner")):
        context.error("DEPENDENCY_KNOWLEDGE_POLICY_OWNER", "enabled policy requires a resolved owner", policy_relpath)
    sources = policy.get("package_sources")
    if not isinstance(sources, list) or not sources:
        context.error("DEPENDENCY_KNOWLEDGE_SOURCES", "enabled policy requires package_sources", policy_relpath)
    else:
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                context.error("DEPENDENCY_KNOWLEDGE_SOURCE", f"package_sources[{index}] must be an object", policy_relpath)
                continue
            for field in ["ecosystem", "manifest", "lockfile", "metadata_locator"]:
                if not resolved(source.get(field)):
                    context.error("DEPENDENCY_KNOWLEDGE_SOURCE", f"package_sources[{index}].{field} must be resolved", policy_relpath)
            if source.get("metadata_locator_kind") != "native-package-metadata-key":
                context.error(
                    "DEPENDENCY_KNOWLEDGE_SOURCE_LOCATOR",
                    f"package_sources[{index}].metadata_locator_kind must be native-package-metadata-key",
                    policy_relpath,
                )
            for field in ["manifest", "lockfile"]:
                value = source.get(field)
                if resolved(value) and not is_target_relative_path(value):
                    context.error("DEPENDENCY_KNOWLEDGE_SOURCE_PATH", f"package_sources[{index}].{field} must be target-relative", policy_relpath)
                elif resolved(value) and not context.target_path(value).is_file():
                    context.error("DEPENDENCY_KNOWLEDGE_SOURCE_MISSING", f"package_sources[{index}].{field} does not exist", policy_relpath)
    discovery = policy.get("discovery")
    expected_discovery = {
        "native_metadata_only": True,
        "recursive_scan": False,
        "execute_package_manager": False,
        "execute_package_hooks": False,
    }
    if not isinstance(discovery, dict) or any(discovery.get(key) is not value for key, value in expected_discovery.items()):
        context.error("DEPENDENCY_KNOWLEDGE_DISCOVERY", "discovery must be native-metadata-only and non-executing", policy_relpath)
    trust = policy.get("trust")
    if not isinstance(trust, dict) or trust.get("raw_content_is_instruction") is not False or trust.get("require_artifact_binding") is not True or trust.get("require_digest") is not True:
        context.error("DEPENDENCY_KNOWLEDGE_TRUST", "trust policy must keep raw content as data and require artifact binding and digest", policy_relpath)
    limits = policy.get("limits")
    if not isinstance(limits, dict):
        context.error("DEPENDENCY_KNOWLEDGE_LIMITS", "limits must be an object", policy_relpath)
    else:
        for field in ["max_manifest_bytes", "max_export_bytes", "max_exports_per_package", "max_graph_depth", "max_graph_instances"]:
            value = limits.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                context.error("DEPENDENCY_KNOWLEDGE_LIMIT", f"limits.{field} must be a positive integer", policy_relpath)
    routing = policy.get("routing")
    if not isinstance(routing, dict) or routing.get("routine_bootstrap") is not False or routing.get("load_selected_facts_only") is not True:
        context.error("DEPENDENCY_KNOWLEDGE_ROUTING", "routing must stay outside bootstrap and load selected facts only", policy_relpath)

    if catalog.get("schema_version") != 1 or catalog.get("catalog_kind") != "target-dependency-knowledge-catalog":
        context.error("DEPENDENCY_KNOWLEDGE_CATALOG_SCHEMA", "catalog schema or kind is invalid", catalog_relpath)
    if lock.get("schema_version") != 1 or lock.get("lock_kind") != "target-dependency-knowledge-lock" or lock.get("knowledge_api") != 1:
        context.error("DEPENDENCY_KNOWLEDGE_LOCK_SCHEMA", "knowledge lock schema kind or API is invalid", lock_relpath)
    if deviations.get("schema_version") != 1 or deviations.get("deviation_kind") != "target-dependency-knowledge-deviations":
        context.error("DEPENDENCY_KNOWLEDGE_DEVIATION_SCHEMA", "deviation schema or kind is invalid", deviation_relpath)
    for value, source, field in [
        (catalog.get("owner"), catalog_relpath, "owner"),
        (deviations.get("owner"), deviation_relpath, "owner"),
        (catalog.get("package_lock_fingerprint"), catalog_relpath, "package_lock_fingerprint"),
        (lock.get("package_lock_fingerprint"), lock_relpath, "package_lock_fingerprint"),
    ]:
        if not resolved(value):
            context.error("DEPENDENCY_KNOWLEDGE_METADATA", f"{field} must be resolved", source)
    if catalog.get("package_lock_fingerprint") != lock.get("package_lock_fingerprint"):
        context.error("DEPENDENCY_KNOWLEDGE_FINGERPRINT_DRIFT", "catalog and knowledge lock fingerprints differ", catalog_relpath)
    packages = catalog.get("packages")
    instances = lock.get("instances")
    deviation_entries = deviations.get("deviations")
    catalog_instance_ids: set[str] = set()
    lock_instance_ids: set[str] = set()
    catalog_exports: dict[str, set[str]] = {}
    lock_exports: dict[str, set[str]] = {}
    digest_pattern = re.compile(r"^[0-9a-f]{64}$")

    def dependency_digest(value: Any) -> bool:
        return isinstance(value, str) and digest_pattern.fullmatch(value) is not None

    def dependency_list(value: Any) -> bool:
        return (
            isinstance(value, list)
            and bool(value)
            and all(resolved(item) for item in value)
        )

    def package_relative(value: Any) -> bool:
        if not resolved(value):
            return False
        if "\\" in value:
            return False
        path = Path(value)
        return not path.is_absolute() and ".." not in path.parts

    if not isinstance(packages, list):
        context.error("DEPENDENCY_KNOWLEDGE_PACKAGES", "catalog packages must be a list", catalog_relpath)
    else:
        for index, package in enumerate(packages):
            location = f"{catalog_relpath}:packages[{index}]"
            if not isinstance(package, dict):
                context.error("DEPENDENCY_KNOWLEDGE_PACKAGE_RECORD", "catalog package must be an object", location)
                continue
            for field in ["instance_id", "ecosystem", "name", "version"]:
                if not resolved(package.get(field)):
                    context.error("DEPENDENCY_KNOWLEDGE_PACKAGE_RECORD", f"catalog package {field} must be resolved", location)
            instance_id = package.get("instance_id")
            if resolved(instance_id):
                if instance_id in catalog_instance_ids:
                    context.error("DEPENDENCY_KNOWLEDGE_INSTANCE_DUPLICATE", f"duplicate catalog instance_id {instance_id}", location)
                catalog_instance_ids.add(instance_id)
            if package.get("export_status") not in {"available", "unsupported", "blocked", "missing"}:
                context.error("DEPENDENCY_KNOWLEDGE_EXPORT_STATUS", "export_status must be available, unsupported, blocked, or missing", location)
            if package.get("trust") not in {"unreviewed", "reviewed", "blocked"}:
                context.error("DEPENDENCY_KNOWLEDGE_TRUST_STATE", "trust must be unreviewed, reviewed, or blocked", location)
            if package.get("freshness") not in {"current", "stale", "missing", "modified"}:
                context.error("DEPENDENCY_KNOWLEDGE_FRESHNESS", "freshness must be current, stale, missing, or modified", location)
            export_records = package.get("exports")
            package_export_ids: set[str] = set()
            if not isinstance(export_records, list):
                context.error("DEPENDENCY_KNOWLEDGE_EXPORT_RECORD", "catalog package exports must be a list", location)
            else:
                for export_index, export in enumerate(export_records):
                    export_location = f"{location}.exports[{export_index}]"
                    if not isinstance(export, dict):
                        context.error("DEPENDENCY_KNOWLEDGE_EXPORT_RECORD", "catalog export must be an object", export_location)
                        continue
                    for field in ["id", "type", "summary"]:
                        if not resolved(export.get(field)):
                            context.error("DEPENDENCY_KNOWLEDGE_EXPORT_RECORD", f"catalog export {field} must be resolved", export_location)
                    export_id = export.get("id")
                    if resolved(export_id):
                        if export_id in package_export_ids:
                            context.error("DEPENDENCY_KNOWLEDGE_EXPORT_DUPLICATE", f"duplicate export ID {export_id} for {instance_id}", export_location)
                        package_export_ids.add(export_id)
                    if not dependency_digest(export.get("content_digest")):
                        context.error("DEPENDENCY_KNOWLEDGE_EXPORT_DIGEST", "catalog export content_digest must be lowercase SHA-256", export_location)
                    if export.get("authority") not in {"upstream-canonical", "upstream-derived", "observed", "third-party", "target-deviation"}:
                        context.error("DEPENDENCY_KNOWLEDGE_AUTHORITY", "catalog export authority is invalid", export_location)
                    if export.get("stability") not in {"stable", "experimental", "deprecated", "internal", "unknown"}:
                        context.error("DEPENDENCY_KNOWLEDGE_STABILITY", "catalog export stability is invalid", export_location)
                    applicability = export.get("applicability")
                    if not isinstance(applicability, dict) or applicability.get("state") not in {"active", "inactive", "conditional", "contradicted"} or not isinstance(applicability.get("conditions"), list) or not all(isinstance(item, str) for item in applicability.get("conditions", [])):
                        context.error("DEPENDENCY_KNOWLEDGE_APPLICABILITY", "catalog export applicability requires a valid independent state and string conditions", export_location)
                    if not dependency_list(export.get("evidence")):
                        context.error("DEPENDENCY_KNOWLEDGE_EXPORT_EVIDENCE", "catalog export evidence must be a non-empty resolved string list", export_location)
            if resolved(instance_id):
                catalog_exports[instance_id] = package_export_ids
    if not isinstance(instances, list):
        context.error("DEPENDENCY_KNOWLEDGE_INSTANCES", "knowledge lock instances must be a list", lock_relpath)
    else:
        for index, instance in enumerate(instances):
            location = f"{lock_relpath}:instances[{index}]"
            if not isinstance(instance, dict):
                context.error("DEPENDENCY_KNOWLEDGE_INSTANCE_RECORD", "knowledge-lock instance must be an object", location)
                continue
            for field in ["instance_id", "ecosystem", "name", "version", "source", "integrity", "revision"]:
                if not resolved(instance.get(field)):
                    context.error("DEPENDENCY_KNOWLEDGE_INSTANCE_RECORD", f"knowledge-lock instance {field} must be resolved", location)
            instance_id = instance.get("instance_id")
            if resolved(instance_id):
                if instance_id in lock_instance_ids:
                    context.error("DEPENDENCY_KNOWLEDGE_INSTANCE_DUPLICATE", f"duplicate knowledge-lock instance_id {instance_id}", location)
                lock_instance_ids.add(instance_id)
            modifications = instance.get("modifications")
            valid_modifications = {"replacement", "fork", "alias", "patch", "path", "workspace", "modified-tree"}
            if not isinstance(modifications, list) or any(item not in valid_modifications for item in modifications):
                context.error("DEPENDENCY_KNOWLEDGE_MODIFICATIONS", "modifications must contain only supported artifact modification classes", location)
            manifest_record = instance.get("manifest")
            if manifest_record is not None and (
                not isinstance(manifest_record, dict)
                or not package_relative(manifest_record.get("path"))
                or not dependency_digest(manifest_record.get("content_digest"))
            ):
                context.error("DEPENDENCY_KNOWLEDGE_MANIFEST_RECORD", "manifest requires a contained package-relative path and lowercase SHA-256 digest", location)
            export_records = instance.get("exports")
            instance_export_ids: set[str] = set()
            if not isinstance(export_records, list):
                context.error("DEPENDENCY_KNOWLEDGE_LOCK_EXPORT", "knowledge-lock exports must be a list", location)
            else:
                for export_index, export in enumerate(export_records):
                    export_location = f"{location}.exports[{export_index}]"
                    if not isinstance(export, dict) or not resolved(export.get("id")) or not package_relative(export.get("path")) or not dependency_digest(export.get("content_digest")):
                        context.error("DEPENDENCY_KNOWLEDGE_LOCK_EXPORT", "knowledge-lock export requires ID, contained path, and lowercase SHA-256 digest", export_location)
                        continue
                    export_id = export["id"]
                    if export_id in instance_export_ids:
                        context.error("DEPENDENCY_KNOWLEDGE_EXPORT_DUPLICATE", f"duplicate knowledge-lock export ID {export_id} for {instance_id}", export_location)
                    instance_export_ids.add(export_id)
            if manifest_record is None and instance_export_ids:
                context.error("DEPENDENCY_KNOWLEDGE_MANIFEST_RECORD", "an instance with exports must record its export manifest path and digest", location)
            if resolved(instance_id):
                lock_exports[instance_id] = instance_export_ids
            graph = instance.get("graph")
            if not isinstance(graph, dict) or not resolved(graph.get("dependency_set")) or not isinstance(graph.get("direct"), bool) or not isinstance(graph.get("public_instance_ids"), list) or not all(resolved(item) for item in graph.get("public_instance_ids", [])):
                context.error("DEPENDENCY_KNOWLEDGE_GRAPH_RECORD", "graph requires dependency_set, boolean direct, and resolved public_instance_ids", location)
    if not isinstance(deviation_entries, list):
        context.error("DEPENDENCY_KNOWLEDGE_DEVIATIONS", "deviations must be a list", deviation_relpath)
    else:
        deviation_ids: set[str] = set()
        for index, deviation in enumerate(deviation_entries):
            location = f"{deviation_relpath}:deviations[{index}]"
            if not isinstance(deviation, dict):
                context.error("DEPENDENCY_KNOWLEDGE_DEVIATION_RECORD", "deviation must be an object", location)
                continue
            for field in ["id", "instance_id", "owner", "source", "effect", "reviewed_at"]:
                if not resolved(deviation.get(field)):
                    context.error("DEPENDENCY_KNOWLEDGE_DEVIATION_RECORD", f"deviation {field} must be resolved", location)
            if resolved(deviation.get("source")) and not is_target_relative_path(deviation["source"]):
                context.error("DEPENDENCY_KNOWLEDGE_DEVIATION_SOURCE", "deviation source must be target-relative", location)
            deviation_id = deviation.get("id")
            if resolved(deviation_id):
                if deviation_id in deviation_ids:
                    context.error("DEPENDENCY_KNOWLEDGE_DEVIATION_DUPLICATE", f"duplicate deviation ID {deviation_id}", location)
                deviation_ids.add(deviation_id)
            if deviation.get("type") not in {"restriction", "wrapper", "patch", "configuration", "applicability", "conflict"}:
                context.error("DEPENDENCY_KNOWLEDGE_DEVIATION_TYPE", "deviation type is invalid", location)
            if deviation.get("state") not in {"active", "inactive", "superseded"}:
                context.error("DEPENDENCY_KNOWLEDGE_DEVIATION_STATE", "deviation state is invalid", location)
            if not isinstance(deviation.get("export_ids"), list) or not all(resolved(item) for item in deviation.get("export_ids", [])):
                context.error("DEPENDENCY_KNOWLEDGE_DEVIATION_EXPORTS", "deviation export_ids must be a resolved string list", location)

    for instance_id in sorted(catalog_instance_ids - lock_instance_ids):
        context.error("DEPENDENCY_KNOWLEDGE_LOCK_MISSING", f"catalog instance {instance_id} has no knowledge-lock instance", lock_relpath)
    for instance_id in sorted(lock_instance_ids - catalog_instance_ids):
        context.error("DEPENDENCY_KNOWLEDGE_CATALOG_MISSING", f"knowledge-lock instance {instance_id} has no catalog package", catalog_relpath)
    for instance_id in sorted(catalog_instance_ids & lock_instance_ids):
        if catalog_exports.get(instance_id, set()) != lock_exports.get(instance_id, set()):
            context.error("DEPENDENCY_KNOWLEDGE_EXPORT_SET_DRIFT", f"catalog and knowledge-lock export IDs differ for {instance_id}", catalog_relpath)
    if isinstance(instances, list):
        for index, instance in enumerate(instances):
            if not isinstance(instance, dict) or not isinstance(instance.get("graph"), dict):
                continue
            references = instance["graph"].get("public_instance_ids")
            if not isinstance(references, list):
                continue
            for reference in references:
                if resolved(reference) and reference not in lock_instance_ids:
                    context.error("DEPENDENCY_KNOWLEDGE_GRAPH_REFERENCE", f"knowledge-lock graph references unknown instance {reference}", f"{lock_relpath}:instances[{index}]")
    if isinstance(deviation_entries, list):
        for index, deviation in enumerate(deviation_entries):
            if not isinstance(deviation, dict):
                continue
            instance_id = deviation.get("instance_id")
            if resolved(instance_id) and instance_id not in lock_instance_ids:
                context.error("DEPENDENCY_KNOWLEDGE_DEVIATION_INSTANCE", f"deviation references unknown instance {instance_id}", f"{deviation_relpath}:deviations[{index}]")
                continue
            export_ids = deviation.get("export_ids")
            if not isinstance(export_ids, list):
                continue
            for export_id in export_ids:
                if resolved(export_id) and export_id not in catalog_exports.get(instance_id, set()):
                    context.error("DEPENDENCY_KNOWLEDGE_DEVIATION_EXPORT", f"deviation references unknown export {export_id} for {instance_id}", f"{deviation_relpath}:deviations[{index}]")

    operations = context.load_json_object(context.target_path(".ai/assistant/operation-catalog.json"), "OPERATION_CATALOG")
    operation = next((item for item in operations.get("operations", []) if isinstance(item, dict) and item.get("id") == "dependency-knowledge"), None) if isinstance(operations, dict) else None
    if not isinstance(operation, dict) or operation.get("required_module") != "dependency-knowledge":
        context.error("DEPENDENCY_KNOWLEDGE_OPERATION_UNROUTED", "dependency-knowledge operation must require the enabled module", ".ai/assistant/operation-catalog.json")
    router = context.load_json_object(context.target_path(".ai/assistant/context-router.json"), "ROUTER")
    overlays = router.get("intent_overlays") if isinstance(router, dict) else None
    route = overlays.get("dependency-knowledge-request") if isinstance(overlays, dict) else None
    if not isinstance(route, dict) or route.get("operation_candidates") != ["dependency-knowledge"]:
        context.error("DEPENDENCY_KNOWLEDGE_INTENT_UNROUTED", "dependency knowledge intent must route the dependency-knowledge operation", ".ai/assistant/context-router.json")

    context.info(
        "DEPENDENCY_KNOWLEDGE_EVIDENCE_LIMIT",
        "dependency knowledge structural checks do not prove publisher identity, semantic correctness, completeness, current applicability, client instruction precedence, or safe runtime behavior",
    )


DEPENDENCY_KNOWLEDGE_MODULE = FunctionCapabilityModule(
    check_id="check_dependency_knowledge",
    validator=validate_dependency_knowledge,
)
