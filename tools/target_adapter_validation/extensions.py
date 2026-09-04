"""Validate target-owned extensions support."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from target_validation_support import ManifestData, dotted, is_placeholder, is_target_relative_path, is_unresolved_value

from target_adapter_validation.capability import (
    CapabilityValidationContext,
    FunctionCapabilityModule,
)


def validate_extensions(
    context: CapabilityValidationContext,
    manifest: ManifestData | None,
) -> None:
    if not context.module_validation_enabled(
        "extensions",
        "EXTENSION_MODULE_UNDECLARED",
        "EXTENSION_MODULE_STATE_MISSING",
        "extensions",
    ):
        return

    required_paths = [
        ".ai/assistant/extensions/README.md",
        ".ai/assistant/extensions/catalog.json",
        ".ai/assistant/extensions/lock.json",
        ".ai/assistant/context/intents/extension-request.json",
        ".ai/assistant/flows/extension-lifecycle.flow.md",
        ".ai/assistant/gates/extensions.md",
        ".ai/assistant/templates/extension-review.md",
        ".ai/assistant/templates/extension-lifecycle-record.md",
        ".ai/framework/extensions.md",
    ]
    missing = False
    for relpath in required_paths:
        if not context.target_path(relpath).is_file():
            missing = True
            context.error(
                "EXTENSION_REQUIRED_FILE_MISSING",
                "enabled extensions module is missing a contract",
                relpath,
            )
    if missing:
        return

    if manifest is not None:
        expected_manifest = {
            ("extensions", "index"): required_paths[0],
            ("extensions", "catalog"): required_paths[1],
            ("extensions", "lock"): required_paths[2],
            ("extensions", "intent"): required_paths[3],
            ("extensions", "flow"): required_paths[4],
            ("extensions", "gate"): required_paths[5],
            ("extensions", "review"): required_paths[6],
            ("extensions", "lifecycle_record"): required_paths[7],
            ("operations", "extension_management"): required_paths[4],
            ("operations", "extension_review"): required_paths[6],
            ("operations", "extension_lifecycle_record"): required_paths[7],
        }
        for key, expected in expected_manifest.items():
            scalar = manifest.scalars.get(key)
            if scalar is None or scalar.value != expected:
                context.error(
                    "EXTENSION_MANIFEST_PATH",
                    f"{dotted(key)} must be {expected} when extensions are enabled",
                    ".ai/alatyr.yaml",
                )

    catalog_relpath = required_paths[1]
    lock_relpath = required_paths[2]
    catalog = context.load_json_object(
        context.target_path(catalog_relpath), "EXTENSION_CATALOG"
    )
    lock = context.load_json_object(context.target_path(lock_relpath), "EXTENSION_LOCK")
    if catalog is None or lock is None:
        return

    if catalog.get("schema_version") != 1:
        context.error("EXTENSION_CATALOG_SCHEMA", "schema_version should be 1", catalog_relpath)
    if catalog.get("catalog_kind") != "target-alatyr-extension-catalog":
        context.error("EXTENSION_CATALOG_KIND", "catalog_kind is invalid", catalog_relpath)
    if catalog.get("extension_api") != 1:
        context.error("EXTENSION_CATALOG_API", "extension_api should be 1", catalog_relpath)
    if lock.get("schema_version") != 1:
        context.error("EXTENSION_LOCK_SCHEMA", "schema_version should be 1", lock_relpath)
    if lock.get("lock_kind") != "target-alatyr-extension-lock":
        context.error("EXTENSION_LOCK_KIND", "lock_kind is invalid", lock_relpath)
    if lock.get("extension_api") != 1:
        context.error("EXTENSION_LOCK_API", "extension_api should be 1", lock_relpath)

    for field in ["owner", "last_reviewed"]:
        value = catalog.get(field)
        if not isinstance(value, str) or is_placeholder(value) or is_unresolved_value(value):
            context.error("EXTENSION_CATALOG_METADATA", f"enabled extension catalog requires resolved {field}", catalog_relpath)

    target_baseline = lock.get("target_baseline")
    if not isinstance(target_baseline, dict):
        context.error("EXTENSION_TARGET_BASELINE", "target_baseline must be an object", lock_relpath)
        target_baseline = {}
    baseline_framework = target_baseline.get("framework_version")
    baseline_schema = target_baseline.get("adapter_schema_version")
    baseline_template = target_baseline.get("template_version")
    baseline_registry = target_baseline.get("rule_registry")
    if not isinstance(baseline_framework, str) or is_placeholder(baseline_framework) or is_unresolved_value(baseline_framework):
        context.error("EXTENSION_TARGET_BASELINE", "target baseline framework version is unresolved", lock_relpath)
    if not isinstance(baseline_schema, int) or isinstance(baseline_schema, bool) or baseline_schema < 1:
        context.error("EXTENSION_TARGET_BASELINE", "target baseline adapter schema must be a positive integer", lock_relpath)
    if not isinstance(baseline_template, int) or isinstance(baseline_template, bool) or baseline_template < 1:
        context.error("EXTENSION_TARGET_BASELINE", "target baseline template version must be a positive integer", lock_relpath)
    if not isinstance(baseline_registry, str) or not is_target_relative_path(baseline_registry):
        context.error("EXTENSION_TARGET_BASELINE", "target baseline rule registry must be target-relative", lock_relpath)
    elif not context.target_path(baseline_registry).is_file():
        context.error("EXTENSION_TARGET_BASELINE", "target baseline rule registry is missing", baseline_registry)
    if manifest is not None:
        expected_baseline = {
            "framework_version": manifest.scalars.get(("framework", "version")),
            "adapter_schema_version": manifest.scalars.get(("schema_version",)),
            "template_version": manifest.scalars.get(("framework", "template_version")),
            "rule_registry": manifest.scalars.get(("framework", "rule_registry")),
        }
        actual_baseline = {
            "framework_version": str(baseline_framework),
            "adapter_schema_version": str(baseline_schema),
            "template_version": str(baseline_template),
            "rule_registry": str(baseline_registry),
        }
        for field, scalar in expected_baseline.items():
            if scalar is None or scalar.value != actual_baseline[field]:
                context.error("EXTENSION_TARGET_BASELINE_DRIFT", f"target baseline {field} differs from the adapter manifest", lock_relpath)

    catalog_entries = catalog.get("extensions")
    lock_entries = lock.get("extensions")
    if not isinstance(catalog_entries, list):
        context.error("EXTENSION_CATALOG_ENTRIES", "extensions must be a list", catalog_relpath)
        catalog_entries = []
    if not isinstance(lock_entries, list):
        context.error("EXTENSION_LOCK_ENTRIES", "extensions must be a list", lock_relpath)
        lock_entries = []

    extension_id_re = re.compile(r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
    digest_re = re.compile(r"^[0-9a-f]{64}$")

    def resolved(value: Any) -> bool:
        return (
            isinstance(value, str)
            and bool(value.strip())
            and not is_placeholder(value)
            and not is_unresolved_value(value)
        )

    catalog_by_id: dict[str, dict[str, Any]] = {}
    valid_catalog_states = {
        "available", "reviewed", "planned", "active", "blocked",
        "disabled", "deprecated", "removed",
    }
    for index, entry in enumerate(catalog_entries):
        if not isinstance(entry, dict):
            context.error("EXTENSION_CATALOG_ENTRY", f"extensions[{index}] must be an object", catalog_relpath)
            continue
        extension_id = entry.get("id")
        if not isinstance(extension_id, str) or not extension_id_re.fullmatch(extension_id):
            context.error("EXTENSION_ID", f"extensions[{index}].id is invalid", catalog_relpath)
            continue
        if extension_id in catalog_by_id:
            context.error("EXTENSION_CATALOG_DUPLICATE", f"duplicate extension id {extension_id}", catalog_relpath)
        catalog_by_id[extension_id] = entry
        if entry.get("state") not in valid_catalog_states:
            context.error("EXTENSION_CATALOG_STATE", f"extension {extension_id} has invalid state", catalog_relpath)
        for field in ["version", "owner", "lock_id", "manifest", "bindings", "last_reviewed", "evidence_revision"]:
            if not resolved(entry.get(field)):
                context.error("EXTENSION_CATALOG_UNRESOLVED", f"extension {extension_id} requires resolved {field}", catalog_relpath)
        for field in ["item_ids", "supported_assistants", "known_gaps"]:
            values = entry.get(field)
            if not isinstance(values, list) or not all(resolved(value) for value in values):
                context.error("EXTENSION_CATALOG_LIST", f"extension {extension_id}.{field} must contain resolved strings", catalog_relpath)

    lock_by_id: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(lock_entries):
        if not isinstance(entry, dict):
            context.error("EXTENSION_LOCK_ENTRY", f"extensions[{index}] must be an object", lock_relpath)
            continue
        extension_id = entry.get("id")
        if not isinstance(extension_id, str) or not extension_id_re.fullmatch(extension_id):
            context.error("EXTENSION_ID", f"extensions[{index}].id is invalid", lock_relpath)
            continue
        if extension_id in lock_by_id:
            context.error("EXTENSION_LOCK_DUPLICATE", f"duplicate extension id {extension_id}", lock_relpath)
        lock_by_id[extension_id] = entry
        for field in [
            "lock_id", "version", "state", "source_type", "source",
            "source_revision", "license_status", "manifest", "bindings",
            "adaptation_record", "approval_record", "installed_at",
        ]:
            if not resolved(entry.get(field)):
                context.error("EXTENSION_LOCK_UNRESOLVED", f"extension {extension_id} requires resolved {field}", lock_relpath)
        if entry.get("state") not in {"active", "disabled", "deprecated"}:
            context.error("EXTENSION_LOCK_STATE", f"extension {extension_id} lock state is invalid", lock_relpath)
        if entry.get("source_type") not in {"local-path", "git-url", "https-url", "package", "plugin", "assistant-native", "pasted"}:
            context.error("EXTENSION_SOURCE_TYPE", f"extension {extension_id} source_type is invalid", lock_relpath)
        digest = entry.get("package_digest_sha256")
        if not isinstance(digest, str) or not digest_re.fullmatch(digest):
            context.error("EXTENSION_PACKAGE_DIGEST", f"extension {extension_id} package digest must be lowercase SHA-256", lock_relpath)
        compatibility = entry.get("compatibility")
        if not isinstance(compatibility, dict) or compatibility.get("result") != "compatible":
            context.error("EXTENSION_COMPATIBILITY", f"extension {extension_id} compatibility must be compatible", lock_relpath)
        validation = entry.get("validation")
        if not isinstance(validation, list) or not validation:
            context.error("EXTENSION_VALIDATION", f"extension {extension_id} requires validation evidence", lock_relpath)

        namespace = f".ai/assistant/extensions/{extension_id}/"
        for field in ["manifest", "bindings", "adaptation_record"]:
            value = entry.get(field)
            if not isinstance(value, str) or not value.startswith(namespace):
                context.error("EXTENSION_NAMESPACE", f"extension {extension_id}.{field} must remain under {namespace}", lock_relpath)
            elif not context.target_path(value).is_file():
                context.error("EXTENSION_LOCK_PATH_MISSING", f"extension {extension_id}.{field} is missing", value)

        approval_record = entry.get("approval_record")
        if isinstance(approval_record, str):
            if not is_target_relative_path(approval_record):
                context.error("EXTENSION_APPROVAL_PATH", f"extension {extension_id} approval record must be target-relative", lock_relpath)
            elif not context.target_path(approval_record).is_file():
                context.error("EXTENSION_APPROVAL_MISSING", f"extension {extension_id} approval record is missing", approval_record)

        installed_files = entry.get("installed_files")
        if not isinstance(installed_files, list) or not installed_files:
            context.error("EXTENSION_INSTALLED_FILES", f"extension {extension_id} requires installed_files", lock_relpath)
            installed_files = []
        seen_paths: set[str] = set()
        for file_index, record in enumerate(installed_files):
            if not isinstance(record, dict):
                context.error("EXTENSION_FILE_RECORD", f"extension {extension_id} installed_files[{file_index}] must be an object", lock_relpath)
                continue
            relpath = record.get("path")
            if not isinstance(relpath, str) or not is_target_relative_path(relpath) or not relpath.startswith(namespace):
                context.error("EXTENSION_FILE_PATH", f"extension {extension_id} has unsafe or out-of-namespace installed path", lock_relpath)
                continue
            if relpath in seen_paths:
                context.error("EXTENSION_FILE_DUPLICATE", f"extension {extension_id} repeats installed path {relpath}", lock_relpath)
            seen_paths.add(relpath)
            if record.get("owner") != extension_id:
                context.error("EXTENSION_FILE_OWNER", f"extension {extension_id} does not own {relpath} exactly", lock_relpath)
            expected_hash = record.get("sha256")
            if not isinstance(expected_hash, str) or not digest_re.fullmatch(expected_hash):
                context.error("EXTENSION_FILE_HASH", f"extension {extension_id} has invalid hash for {relpath}", lock_relpath)
                continue
            path = context.target_path(relpath)
            if path.is_symlink():
                context.error("EXTENSION_FILE_SYMLINK", "installed extension files must not be symlinks", relpath)
            elif not path.is_file():
                context.error("EXTENSION_FILE_MISSING", "locked installed extension file is missing", relpath)
            elif hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
                context.error("EXTENSION_FILE_DRIFT", "installed extension file differs from its lock hash", relpath)

        required_binding_ids: set[str] = set()
        normalized_manifest = context.load_json_object(
            context.target_path(str(entry.get("manifest", ""))),
            "EXTENSION_INSTALLED_MANIFEST",
        )
        if normalized_manifest is not None:
            if normalized_manifest.get("package_kind") != "alatyr-extension":
                context.error("EXTENSION_INSTALLED_MANIFEST_KIND", f"extension {extension_id} normalized manifest kind is invalid", str(entry.get("manifest")))
            if normalized_manifest.get("id") != extension_id or normalized_manifest.get("version") != entry.get("version"):
                context.error("EXTENSION_INSTALLED_MANIFEST_IDENTITY", f"extension {extension_id} normalized manifest identity differs from the lock", str(entry.get("manifest")))
            provides = normalized_manifest.get("provides")
            provided_ids: list[str] = []
            provided_paths: set[str] = set()
            if not isinstance(provides, list) or not provides:
                context.error("EXTENSION_INSTALLED_ITEMS", f"extension {extension_id} normalized manifest requires provided items", str(entry.get("manifest")))
                provides = []
            for item_index, item in enumerate(provides):
                if not isinstance(item, dict):
                    context.error("EXTENSION_INSTALLED_ITEM", f"extension {extension_id} provides[{item_index}] must be an object", str(entry.get("manifest")))
                    continue
                item_id = item.get("id")
                item_relpath = item.get("path")
                if not resolved(item_id) or item_id in provided_ids:
                    context.error("EXTENSION_INSTALLED_ITEM_ID", f"extension {extension_id} has unresolved or duplicate provided item ID", str(entry.get("manifest")))
                if isinstance(item_id, str):
                    provided_ids.append(item_id)
                if (
                    not isinstance(item_relpath, str)
                    or not item_relpath.startswith("items/")
                    or ".." in item_relpath.split("/")
                    or "\\" in item_relpath
                ):
                    context.error("EXTENSION_INSTALLED_ITEM_PATH", f"extension {extension_id} has unsafe provided item path", str(entry.get("manifest")))
                elif item_relpath in provided_paths:
                    context.error("EXTENSION_INSTALLED_ITEM_PATH", f"extension {extension_id} repeats provided item path {item_relpath}", str(entry.get("manifest")))
                else:
                    provided_paths.add(item_relpath)
                    installed_item_path = namespace + item_relpath
                    if installed_item_path not in seen_paths:
                        context.error("EXTENSION_ITEM_UNLOCKED", f"extension {extension_id} item {installed_item_path} is not covered by installed_files", str(entry.get("manifest")))
            catalog_item_ids = catalog_by_id.get(extension_id, {}).get("item_ids")
            if isinstance(catalog_item_ids, list) and sorted(catalog_item_ids) != sorted(provided_ids):
                context.error("EXTENSION_ITEM_INDEX_DRIFT", f"extension {extension_id} catalog item IDs differ from the normalized manifest", catalog_relpath)
            if normalized_manifest.get("extension_dependencies") not in (None, []):
                context.error("EXTENSION_INSTALLED_DEPENDENCIES", f"extension {extension_id} normalized manifest must not contain extension dependencies", str(entry.get("manifest")))
            lifecycle = normalized_manifest.get("lifecycle")
            if isinstance(lifecycle, dict) and lifecycle.get("arbitrary_hooks") is not False:
                context.error("EXTENSION_INSTALLED_HOOK", f"extension {extension_id} normalized manifest must prohibit arbitrary hooks", str(entry.get("manifest")))
            project_bindings = normalized_manifest.get("project_bindings")
            if isinstance(project_bindings, list):
                required_binding_ids = {
                    binding.get("id")
                    for binding in project_bindings
                    if isinstance(binding, dict)
                    and binding.get("required") is True
                    and isinstance(binding.get("id"), str)
                }

        bindings = context.load_json_object(
            context.target_path(str(entry.get("bindings", ""))),
            "EXTENSION_BINDINGS",
        )
        if bindings is not None:
            if bindings.get("schema_version") != 1 or bindings.get("binding_kind") != "target-alatyr-extension-bindings":
                context.error("EXTENSION_BINDING_CONTRACT", f"extension {extension_id} bindings contract is invalid", str(entry.get("bindings")))
            if bindings.get("extension_id") != extension_id:
                context.error("EXTENSION_BINDING_IDENTITY", f"extension {extension_id} bindings identity differs from the lock", str(entry.get("bindings")))
            binding_entries = bindings.get("bindings")
            if not isinstance(binding_entries, list):
                context.error("EXTENSION_BINDING_ENTRIES", f"extension {extension_id} bindings must be a list", str(entry.get("bindings")))
            else:
                seen_bindings: set[str] = set()
                for binding_index, binding in enumerate(binding_entries):
                    if not isinstance(binding, dict):
                        context.error("EXTENSION_BINDING_ENTRY", f"extension {extension_id} bindings[{binding_index}] must be an object", str(entry.get("bindings")))
                        continue
                    binding_id = binding.get("id")
                    if not resolved(binding_id) or binding_id in seen_bindings:
                        context.error("EXTENSION_BINDING_ID", f"extension {extension_id} has unresolved or duplicate binding ID", str(entry.get("bindings")))
                    if isinstance(binding_id, str):
                        seen_bindings.add(binding_id)
                    for field in ["value", "owner", "source"]:
                        if not resolved(binding.get(field)):
                            context.error("EXTENSION_BINDING_UNRESOLVED", f"extension {extension_id} binding {binding_id} requires resolved {field}", str(entry.get("bindings")))
                missing_bindings = sorted(required_binding_ids - seen_bindings)
                if missing_bindings:
                    context.error("EXTENSION_REQUIRED_BINDING_MISSING", f"extension {extension_id} is missing required bindings: {', '.join(missing_bindings)}", str(entry.get("bindings")))

        integration_surfaces = entry.get("integration_surfaces")
        if not isinstance(integration_surfaces, list) or not all(
            isinstance(value, str) and is_target_relative_path(value)
            for value in integration_surfaces
        ):
            context.error("EXTENSION_INTEGRATION_SURFACES", f"extension {extension_id} integration_surfaces must be target-relative paths", lock_relpath)

    for extension_id, entry in catalog_by_id.items():
        if entry.get("state") in {"active", "disabled", "deprecated"}:
            locked = lock_by_id.get(extension_id)
            if locked is None:
                context.error("EXTENSION_LOCK_MISSING", f"catalog extension {extension_id} has no lock entry", lock_relpath)
                continue
            for field in ["version", "state", "lock_id", "manifest", "bindings"]:
                if entry.get(field) != locked.get(field):
                    context.error("EXTENSION_CATALOG_LOCK_DRIFT", f"extension {extension_id}.{field} differs between catalog and lock", catalog_relpath)
    for extension_id in sorted(set(lock_by_id) - set(catalog_by_id)):
        context.error("EXTENSION_CATALOG_MISSING", f"lock extension {extension_id} has no catalog entry", catalog_relpath)

    catalog = context.load_json_object(
        context.target_path(".ai/assistant/operation-catalog.json"),
        "OPERATION_CATALOG",
    )
    operations = catalog.get("operations") if isinstance(catalog, dict) else None
    operation = next(
        (
            item for item in operations or []
            if isinstance(item, dict) and item.get("id") == "extension-management"
        ),
        None,
    )
    if not isinstance(operation, dict) or operation.get("required_module") != "core-profile":
        context.error("EXTENSION_OPERATION_UNROUTED", "extension-management must remain available through core-profile", ".ai/assistant/operation-catalog.json")

    context.info(
        "EXTENSION_EVIDENCE_LIMIT",
        "extension structural checks do not prove source trust, license interpretation, semantic quality, target suitability, or safe runtime behavior",
    )


EXTENSIONS_MODULE = FunctionCapabilityModule(
    check_id="check_extensions",
    validator=validate_extensions,
)
