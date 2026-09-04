"""Debug Mode target validation."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema

from target_adapter_validation.contract_compatibility import (
    artifact_compatibility,
    contract_compatibility,
    minimum_index_version,
)
from target_adapter_validation.consistency_map import (
    RegistryFactEntry,
    parse_registry_fact_entries,
)
from target_adapter_validation.domain import DomainValidationHost
from target_validation_support import (
    ManifestData,
    dotted,
    git_head_revision,
    git_is_ancestor,
    git_range_changed_files,
    git_resolve_object,
    is_target_relative_path,
    scope_entries_cover,
)
from target_adapter_validation.values import is_resolved_string


ROOT = Path(__file__).resolve().parents[2]
DEBUG_SESSION_SCHEMA = ROOT / "schemas" / "alatyr-debug-session.schema.json"
DEBUG_CONTRACT = contract_compatibility("debug-mode")
DEBUG_INDEX = artifact_compatibility("debug-mode", "index")
DEBUG_RECORD = artifact_compatibility("debug-mode", "record")

DEBUG_LEGACY_METRIC_NAMES = [
    "human_interventions",
    "human_architectural_interventions",
    "alatyr_independent_findings",
    "derived_findings_after_human",
    "alatyr_independent_dependency_checks",
    "human_requested_dependency_checks",
    "derived_dependency_expansions_after_human",
    "hypotheses_tested",
    "hypotheses_rejected",
    "implementation_revisions",
    "implementation_corrections_after_human",
    "validation_expansions",
    "regression_scenarios_added",
    "maintainer_corrections",
    "post_review_rework",
]

DEBUG_V4_METRIC_NAMES = [
    "human_interventions",
    "human_architectural_interventions",
    "executor_independent_findings",
    "executor_derived_findings_after_human",
    "executor_independent_dependency_checks",
    "human_requested_dependency_checks",
    "executor_derived_dependency_expansions_after_human",
    "hypotheses_tested",
    "hypotheses_rejected",
    "implementation_revisions",
    "implementation_corrections_after_human",
    "validation_expansions",
    "regression_scenarios_added",
    "maintainer_corrections",
    "post_review_rework",
    "new_guidance_candidates",
    "known_guidance_routing_failures",
    "known_guidance_compliance_failures",
    "task_local_corrections",
    "scope_changes",
    "validation_requests",
]

DEBUG_EVENT_LINK_ROLES = {
    "finding",
    "decision",
    "implementation",
    "validation",
    "correction",
    "direction-change",
    "rejected-hypothesis",
}

DEBUG_MATERIALITY_KINDS = {
    "undocumented-invariant",
    "rejected-hypothesis",
    "non-obvious-dependency",
    "cross-area-impact",
    "broad-regression-matrix",
    "compatibility-or-public-contract",
    "reviewer-correction",
    "direction-change",
    "expensive-to-reconstruct",
    "unresolved-authority-or-contract",
}


def _surface_covers(changed_path: str, surfaces: list[str]) -> bool:
    for surface in surfaces:
        if not is_resolved_string(surface):
            continue
        normalized = surface.rstrip("/")
        if changed_path == normalized or changed_path.startswith(normalized + "/"):
            return True
        if scope_entries_cover(changed_path, [surface]):
            return True
    return False


def reconcile_debug_git_state(
    *,
    self: DomainValidationHost,
    record: dict[str, Any],
    record_ref: str,
    status: str,
    implementation_surfaces: list[str],
    binding: dict[str, Any],
    binding_kind: str | None,
    repository_lifecycle_state: str,
) -> None:
    """Compare selected Debug record claims with current Git evidence."""

    head = git_head_revision(self.target)
    if not head:
        self.warn(
            "DEBUG_MODE_GIT_STATE_UNAVAILABLE",
            "cannot resolve current Git HEAD for Debug reconciliation",
            record_ref,
        )
        return

    activation = record.get("activation")
    activation = activation if isinstance(activation, dict) else {}
    base_revision = (
        binding.get("base_revision")
        if is_resolved_string(binding.get("base_revision"))
        else activation.get("initial_revision")
    )
    result_revision = binding.get("result_revision")
    binding_state = binding.get("binding_state")
    committed_touching_surfaces: list[str] = []
    if is_resolved_string(base_revision) and git_resolve_object(
        self.target, str(base_revision), "commit"
    ):
        changed = git_range_changed_files(self.target, str(base_revision), head)
        if changed is None:
            self.warn(
                "DEBUG_MODE_GIT_STATE_UNAVAILABLE",
                f"cannot compute Debug Git range {base_revision}..{head}",
                record_ref,
            )
        else:
            committed_touching_surfaces = [
                path
                for path in changed
                if _surface_covers(path, implementation_surfaces)
            ]

    if status == "active" and committed_touching_surfaces:
        self.error(
            "DEBUG_MODE_ACTIVE_RESULT_DRIFT",
            "active Debug record has committed changes touching implementation surfaces: "
            + ", ".join(committed_touching_surfaces[:12]),
            record_ref,
        )
    if (
        committed_touching_surfaces
        and binding_state == "provisional"
        and status != "abandoned"
    ):
        self.error(
            "DEBUG_MODE_PROVISIONAL_BINDING_AFTER_COMMIT",
            "committed implementation work requires a final binding or an explicit finalization blocker",
            record_ref,
        )
    result_resolved = (
        git_resolve_object(self.target, str(result_revision), "commit")
        if is_resolved_string(result_revision) and binding_kind in {"commit", "pull-request"}
        else None
    )
    if (
        status == "active"
        and committed_touching_surfaces
        and result_resolved
        and result_resolved != head
    ):
        self.error(
            "DEBUG_MODE_RESULT_REVISION_STALE",
            f"active Debug result_revision {result_resolved} does not match current HEAD {head}",
            record_ref,
        )

    remote_ref = getattr(self, "debug_remote_ref", None)
    if not remote_ref:
        return
    remote = git_resolve_object(self.target, str(remote_ref), "commit")
    if remote is None:
        self.warn(
            "DEBUG_MODE_REMOTE_STATE_UNAVAILABLE",
            f"cannot resolve Debug publication evidence ref {remote_ref}",
            record_ref,
        )
        return
    published = remote == head or git_is_ancestor(self.target, head, remote) is True
    if published and (
        status == "active"
        or binding_state == "provisional"
        or repository_lifecycle_state not in {"published", "finalized"}
    ):
        self.error(
            "DEBUG_MODE_PUBLISHED_BUT_UNFINALIZED",
            f"Debug record is not finalized against published ref {remote_ref}",
            record_ref,
        )


def validate_debug_mode(self: DomainValidationHost, manifest: ManifestData | None) -> None:
    index_relpath = ".ai/project/debug/index.json"
    expected_manifest = {
        ("operations", "debug_mode"): ".ai/assistant/flows/debug-mode.flow.md",
        ("debug_mode", "index"): index_relpath,
        ("debug_mode", "records"): ".ai/project/debug/records",
        ("debug_mode", "overlay"): ".ai/assistant/context/task-scales/debug-mode.json",
        ("debug_mode", "flow"): ".ai/assistant/flows/debug-mode.flow.md",
        ("debug_mode", "gate"): ".ai/assistant/gates/debug-mode.md",
        ("debug_mode", "record_template"): ".ai/assistant/templates/debug-session-record.json",
        ("debug_mode", "summary_template"): ".ai/assistant/templates/debug-summary.md",
    }
    if manifest is not None:
        for key, expected in expected_manifest.items():
            scalar = manifest.scalars.get(key)
            if scalar is None or scalar.value != expected:
                self.error(
                    "DEBUG_MODE_MANIFEST_PATH",
                    f"{dotted(key)} must be {expected}",
                    ".ai/alatyr.yaml",
                )
        contract = manifest.scalars.get(("debug_mode", "contract_version"))
        expected_contract_version = str(DEBUG_CONTRACT["manifest_contract_version"])
        if contract is None or contract.value != expected_contract_version:
            self.error(
                "DEBUG_MODE_CONTRACT_VERSION",
                f"debug_mode.contract_version must be {expected_contract_version}",
                ".ai/alatyr.yaml",
            )

    template_relpath = ".ai/assistant/templates/debug-session-record.json"
    template = self.load_json_object(self.target_path(template_relpath), "DEBUG_MODE_TEMPLATE")
    if template is not None:
        template_final = template.get("final_result")
        template_binding = template_final.get("repository_binding") if isinstance(template_final, dict) else None
        if template.get("schema_version") != DEBUG_RECORD["current"]:
            self.error("DEBUG_MODE_TEMPLATE_VERSION", f"authoring template schema_version must be {DEBUG_RECORD['current']}", template_relpath)
        if not isinstance(template_binding, dict) or not {"binding_state", "prior_bindings"}.issubset(template_binding):
            self.error("DEBUG_MODE_TEMPLATE_BINDING", "version-6 authoring template must expose binding_state and prior_bindings", template_relpath)
        if not isinstance(template_final, dict) or not {
            "claim_validation", "engineering_evidence_decision",
            "lifecycle_coverage", "project_knowledge_candidates"
        }.issubset(template_final):
            self.error("DEBUG_MODE_TEMPLATE_EVIDENCE_DECISION", "version-6 authoring template must expose lifecycle, claim, engineering-evidence, and project-knowledge closure", template_relpath)
        if not isinstance(template.get("continuation"), dict):
            self.error("DEBUG_MODE_TEMPLATE_CONTINUATION", "version-3 authoring template must expose continuation lineage", template_relpath)

    index = self.load_json_object(
        self.target_path(index_relpath), "DEBUG_MODE_INDEX"
    )
    if index is None:
        return
    index_schema_version = index.get("schema_version")
    supported_index_versions = set(DEBUG_INDEX["supported"])
    if index_schema_version not in supported_index_versions:
        supported = ", ".join(str(value) for value in sorted(supported_index_versions))
        self.error("DEBUG_MODE_INDEX_SCHEMA", f"schema_version must be one of: {supported}", index_relpath)
    elif index_schema_version in set(DEBUG_INDEX["migration_limited"]):
        self.warn("DEBUG_MODE_INDEX_LEGACY", "legacy Debug index omits schema-version-6 lifecycle, validation, or knowledge-candidate projections", index_relpath)
    if index.get("index_kind") != "target-alatyr-debug-index":
        self.error(
            "DEBUG_MODE_INDEX_KIND",
            "index_kind must be target-alatyr-debug-index",
            index_relpath,
        )
    unresolved_report = self.warn if self.allow_placeholders else self.error
    for field in [
        "project",
        "owner",
        "storage_mode",
        "visibility",
        "retention_policy",
        "redaction_policy",
        "external_patch_policy",
    ]:
        value = index.get(field)
        if not isinstance(value, str) or not value.strip():
            self.error(
                "DEBUG_MODE_INDEX_METADATA",
                f"{field} must be a non-empty string",
                index_relpath,
            )
        elif not is_resolved_string(value):
            unresolved_report(
                "DEBUG_MODE_INDEX_METADATA_UNRESOLVED",
                f"{field} is unresolved",
                index_relpath,
            )

    self.check_policy_readme_projection(
        index=index,
        readme_relpath=".ai/project/debug/README.md",
        fields={
            "Owner": "owner",
            "Storage mode": "storage_mode",
            "Visibility": "visibility",
            "Retention policy": "retention_policy",
            "Redaction policy": "redaction_policy",
            "External patch policy": "external_patch_policy",
        },
        code_prefix="DEBUG_MODE_POLICY",
    )

    records = index.get("records")
    if not isinstance(records, list):
        self.error("DEBUG_MODE_INDEX_RECORDS", "records must be a list", index_relpath)
        return

    try:
        schema = json.loads(DEBUG_SESSION_SCHEMA.read_text(encoding="utf-8"))
        schema_validator = jsonschema.Draft7Validator(schema)
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        self.error("DEBUG_MODE_SOURCE_SCHEMA", f"cannot load Debug Mode schema: {exc}")
        return

    engineering_evidence_counts: dict[str, int] = {}
    engineering_evidence_entries: dict[str, list[dict[str, Any]]] = {}
    engineering_index_relpath = ".ai/project/engineering-evidence/index.json"
    engineering_index_path = self.target_path(engineering_index_relpath)
    if engineering_index_path.is_file():
        engineering_index, engineering_index_error = self.context.read_json(
            engineering_index_path
        )
        if engineering_index_error is not None:
            engineering_index = None
        if isinstance(engineering_index, dict):
            for evidence_entry in engineering_index.get("records", []):
                if not isinstance(evidence_entry, dict):
                    continue
                evidence_id = evidence_entry.get("evidence_id")
                if isinstance(evidence_id, str) and evidence_id:
                    engineering_evidence_counts[evidence_id] = (
                        engineering_evidence_counts.get(evidence_id, 0) + 1
                    )
                    engineering_evidence_entries.setdefault(evidence_id, []).append(
                        evidence_entry
                    )

    promotion_candidate_ids: set[str] = set()
    project_knowledge_index_path = self.target_path(
        ".ai/project/knowledge/index.json"
    )
    if project_knowledge_index_path.is_file():
        project_knowledge_index, knowledge_index_error = self.context.read_json(
            project_knowledge_index_path
        )
        if knowledge_index_error is not None:
            project_knowledge_index = None
        if isinstance(project_knowledge_index, dict):
            for promotion_entry in project_knowledge_index.get(
                "promotion_records", []
            ):
                if not isinstance(promotion_entry, dict):
                    continue
                promotion_ref = promotion_entry.get("path")
                if not isinstance(promotion_ref, str) or not is_target_relative_path(
                    promotion_ref
                ):
                    continue
                promotion_record = self.load_json_object(
                    self.target_path(promotion_ref),
                    "DEBUG_MODE_PROJECT_KNOWLEDGE_PROMOTION",
                )
                if not isinstance(promotion_record, dict):
                    continue
                candidate = promotion_record.get("candidate")
                candidate = candidate if isinstance(candidate, dict) else {}
                candidate_id = candidate.get("candidate_id")
                if isinstance(candidate_id, str) and candidate_id:
                    promotion_candidate_ids.add(candidate_id)

    registry_relpath = ".ai/project/source-of-truth-registry.md"
    registry_path = self.target_path(registry_relpath)
    registry_entries_by_fact_type: dict[str, list[RegistryFactEntry]] = {}
    if registry_path.is_file():
        for registry_entry in parse_registry_fact_entries(
            self.read_text(registry_path)
        ):
            registry_entries_by_fact_type.setdefault(
                registry_entry.heading_fact_type, []
            ).append(registry_entry)

    required_index_fields = {
        "debug_id",
        "status",
        "record",
        "task_references",
        "scope_kind",
        "scope_id",
        "task_class",
        "repository_binding_kind",
        "result_revision",
        "event_coverage",
        "observer_effect",
        "elapsed_seconds",
        "elapsed_evidence_kind",
        "metrics",
        "residual_uncertainty",
    }
    if index_schema_version == 3:
        required_index_fields.update(
            {"record_schema_version", "repository_binding_state", "engineering_evidence_status"}
        )
    elif index_schema_version in {4, 5, 6}:
        required_index_fields.update(
            {
                "record_schema_version",
                "repository_binding_state",
                "engineering_evidence_status",
                "continuation_kind",
                "continued_from_debug_id",
                "claim_validation_fidelity",
            }
        )
    if index_schema_version in {5, 6}:
        required_index_fields.update(
            {
                "lifecycle_completion_scope",
                "covered_phases",
                "continuation_expected",
                "knowledge_candidate_ids",
            }
        )
    if index_schema_version == 6:
        required_index_fields.update(
            {
                "repository_lifecycle_state",
                "validation_evidence_classes",
            }
        )
    indexed_entries = [entry for entry in records if isinstance(entry, dict)]
    indexed_id_counts: dict[str, int] = {}
    indexed_entries_by_id: dict[str, dict[str, Any]] = {}
    for indexed_entry in indexed_entries:
        indexed_debug_id = indexed_entry.get("debug_id")
        if isinstance(indexed_debug_id, str) and indexed_debug_id:
            indexed_id_counts[indexed_debug_id] = indexed_id_counts.get(indexed_debug_id, 0) + 1
            indexed_entries_by_id.setdefault(indexed_debug_id, indexed_entry)
    if index_schema_version in {4, 5, 6}:
        for indexed_debug_id in indexed_entries_by_id:
            visited: set[str] = set()
            current_id = indexed_debug_id
            while current_id in indexed_entries_by_id:
                if current_id in visited:
                    self.error(
                        "DEBUG_MODE_CONTINUATION_CYCLE",
                        f"continuation lineage for {indexed_debug_id} contains a cycle",
                        index_relpath,
                    )
                    break
                visited.add(current_id)
                current_entry = indexed_entries_by_id[current_id]
                if current_entry.get("continuation_kind") != "continued":
                    break
                previous_id = current_entry.get("continued_from_debug_id")
                if not isinstance(previous_id, str):
                    break
                current_id = previous_id
    seen_ids: set[str] = set()
    seen_records: set[str] = set()
    checked_debug_records: dict[str, dict[str, Any]] = {}
    for entry_index, entry in enumerate(records):
        label = f"records[{entry_index}]"
        if not isinstance(entry, dict):
            self.error("DEBUG_MODE_INDEX_ENTRY", f"{label} must be an object", index_relpath)
            continue
        missing = sorted(required_index_fields - set(entry))
        if missing:
            self.error("DEBUG_MODE_INDEX_FIELD", f"{label} missing {missing}", index_relpath)
            continue
        debug_id = entry.get("debug_id")
        if not is_resolved_string(debug_id):
            self.error("DEBUG_MODE_INDEX_ID", f"{label}.debug_id must be resolved", index_relpath)
            continue
        if debug_id in seen_ids:
            self.error("DEBUG_MODE_INDEX_DUPLICATE", f"duplicate debug_id {debug_id}", index_relpath)
        seen_ids.add(debug_id)
        if entry.get("status") not in {"active", "completed", "abandoned"}:
            self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.status is invalid", index_relpath)
        if entry.get("scope_kind") not in {"task", "session"}:
            self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.scope_kind is invalid", index_relpath)
        if entry.get("repository_binding_kind") not in {
            "commit", "pull-request", "tree", "selected-file-snapshot", "unverified"
        }:
            self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.repository_binding_kind is invalid", index_relpath)
        if entry.get("event_coverage") not in {"complete", "partial", "unknown"}:
            self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.event_coverage is invalid", index_relpath)
        if entry.get("observer_effect") not in {"negligible", "possible", "material", "unknown"}:
            self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.observer_effect is invalid", index_relpath)
        if entry.get("elapsed_evidence_kind") not in {"observed", "estimated", "unknown"}:
            self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.elapsed_evidence_kind is invalid", index_relpath)
        elapsed_index = entry.get("elapsed_seconds")
        if elapsed_index is not None and (not isinstance(elapsed_index, int) or elapsed_index < 0):
            self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.elapsed_seconds must be a non-negative integer or null", index_relpath)
        if index_schema_version in {4, 5, 6}:
            if entry.get("continuation_kind") not in {"initial", "continued", "legacy"}:
                self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.continuation_kind is invalid", index_relpath)
            if not isinstance(entry.get("continued_from_debug_id"), str) or not entry["continued_from_debug_id"].strip():
                self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.continued_from_debug_id must be a non-empty string", index_relpath)
            if entry.get("claim_validation_fidelity") not in {
                "exact-reproducer", "representative", "partial", "unavailable",
                "not-applicable", "legacy",
            }:
                self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.claim_validation_fidelity is invalid", index_relpath)
        indexed_record_version = entry.get("record_schema_version", 1)
        if index_schema_version in {5, 6}:
            lifecycle_scopes = (
                {"legacy"}
                if isinstance(indexed_record_version, int)
                and indexed_record_version < 5
                else {"active", "phase-complete", "full-task-complete"}
            )
            if entry.get("lifecycle_completion_scope") not in lifecycle_scopes:
                self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.lifecycle_completion_scope is invalid", index_relpath)
            covered_phases = entry.get("covered_phases")
            if (
                not isinstance(covered_phases, list)
                or len(covered_phases) != len(set(covered_phases))
                or not set(covered_phases).issubset(
                    {"analysis", "implementation", "validation", "finalization"}
                )
            ):
                self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.covered_phases is invalid", index_relpath)
            if not isinstance(entry.get("continuation_expected"), bool):
                self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.continuation_expected must be boolean", index_relpath)
            candidate_ids = entry.get("knowledge_candidate_ids")
            if (
                not isinstance(candidate_ids, list)
                or len(candidate_ids) != len(set(candidate_ids))
                or not all(is_resolved_string(value) for value in candidate_ids)
            ):
                self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.knowledge_candidate_ids must be a unique resolved string list", index_relpath)
        if index_schema_version == 6:
            if entry.get("repository_lifecycle_state") not in {
                "active",
                "validated",
                "committed",
                "published",
                "finalized",
                "abandoned",
                "legacy",
            }:
                self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.repository_lifecycle_state is invalid", index_relpath)
            validation_classes = entry.get("validation_evidence_classes")
            if (
                not isinstance(validation_classes, list)
                or len(validation_classes) != len(set(validation_classes))
                or not set(validation_classes).issubset(
                    {
                        "declared",
                        "locally-observed",
                        "tool-verified",
                        "ci-verified",
                        "reviewer-verified",
                        "production-verified",
                        "legacy",
                    }
                )
            ):
                self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.validation_evidence_classes is invalid", index_relpath)
        for field in ["task_references", "residual_uncertainty"]:
            values = entry.get(field)
            if not isinstance(values, list) or not all(is_resolved_string(value) for value in values):
                self.error("DEBUG_MODE_INDEX_LIST", f"{label}.{field} must be a resolved string list", index_relpath)
        for field in ["scope_id", "task_class", "result_revision"]:
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                self.error("DEBUG_MODE_INDEX_FIELD", f"{label}.{field} must be a non-empty string", index_relpath)
        index_metrics = entry.get("metrics")
        indexed_metric_names = (
            DEBUG_V4_METRIC_NAMES
            if isinstance(indexed_record_version, int) and indexed_record_version >= 4
            else DEBUG_LEGACY_METRIC_NAMES
        )
        if not isinstance(index_metrics, dict) or set(index_metrics) != set(indexed_metric_names):
            self.error("DEBUG_MODE_INDEX_METRICS", f"{label}.metrics must contain the canonical metric set", index_relpath)
        elif not all(value is None or (isinstance(value, int) and value >= 0) for value in index_metrics.values()):
            self.error("DEBUG_MODE_INDEX_METRICS", f"{label}.metrics values must be non-negative integers or null", index_relpath)

        record_ref = entry.get("record")
        if not is_resolved_string(record_ref):
            self.error("DEBUG_MODE_INDEX_RECORD", f"{label}.record must be resolved", index_relpath)
            continue
        if record_ref.startswith(("https://", "http://", "external:")):
            self.warn(
                "DEBUG_MODE_EXTERNAL_RECORD_UNCHECKED",
                f"{debug_id} uses an external record that this repository validator cannot inspect",
                index_relpath,
            )
            continue
        if not is_target_relative_path(record_ref):
            self.error("DEBUG_MODE_RECORD_PATH", f"record path must be target-relative: {record_ref}", index_relpath)
            continue
        if record_ref in seen_records:
            self.error("DEBUG_MODE_RECORD_DUPLICATE", f"record path is reused: {record_ref}", index_relpath)
        seen_records.add(record_ref)
        if not record_ref.startswith(".ai/project/debug/records/"):
            self.error("DEBUG_MODE_RECORD_LOCATION", "local records must stay under the target debug records directory", record_ref)
        record = self.load_json_object(self.target_path(record_ref), "DEBUG_MODE_RECORD")
        if record is None:
            continue
        checked_debug_records[str(debug_id)] = record

        for schema_error in sorted(
            schema_validator.iter_errors(record),
            key=lambda item: list(item.absolute_path),
        ):
            location = ".".join(str(item) for item in schema_error.absolute_path) or "root"
            self.error("DEBUG_MODE_RECORD_SCHEMA", f"{location}: {schema_error.message}", record_ref)
        record_schema_version = record.get("schema_version")
        required_index_version = minimum_index_version(
            "debug-mode", record_schema_version
        )
        if required_index_version is None:
            self.error(
                "DEBUG_MODE_INDEX_RECORD_VERSION",
                "record schema_version must be one of: "
                + ", ".join(str(value) for value in DEBUG_RECORD["supported"]),
                record_ref,
            )
        elif (
            not isinstance(index_schema_version, int)
            or index_schema_version < required_index_version
        ):
            self.error(
                "DEBUG_MODE_INDEX_RECORD_VERSION",
                f"schema-version-{record_schema_version} record requires index schema version {required_index_version} or later",
                index_relpath,
            )
        record_schema_version = record.get("schema_version") if isinstance(record.get("schema_version"), int) else 1
        if record_schema_version == 2:
            self.warn(
                "DEBUG_MODE_V2_CONTRACT",
                "schema-version-2 record remains readable but lacks structured materiality, claim fidelity, and continuation lineage",
                record_ref,
            )

        forbidden_keys = {
            "raw_chat",
            "raw_conversation",
            "raw_ai_conversation",
            "raw_human_conversation",
            "chat_transcript",
            "conversation_transcript",
            "chain_of_thought",
            "reasoning_trace",
            "prompt_text",
            "session_history",
            "complete_diff",
            "full_diff",
            "credentials",
            "secrets",
            "personal_data",
            "verbose_logs",
            "speculative_reasoning",
        }

        def find_forbidden(value: Any, prefix: str = "") -> list[str]:
            found: list[str] = []
            if isinstance(value, dict):
                for key, child in value.items():
                    path = f"{prefix}.{key}" if prefix else str(key)
                    if key.casefold() in forbidden_keys:
                        found.append(path)
                    found.extend(find_forbidden(child, path))
            elif isinstance(value, list):
                for item_index, child in enumerate(value):
                    found.extend(find_forbidden(child, f"{prefix}[{item_index}]"))
            return found

        forbidden = find_forbidden(record)
        if forbidden:
            self.error(
                "DEBUG_MODE_PROHIBITED_CONTENT_FIELD",
                f"record contains prohibited raw-content fields: {forbidden}",
                record_ref,
            )

        privacy = record.get("privacy")
        if isinstance(privacy, dict):
            for field in [
                "raw_ai_conversation_stored",
                "raw_human_conversation_stored",
                "chain_of_thought_stored",
                "prompts_stored",
                "secrets_stored",
                "credentials_stored",
                "unrelated_personal_data_stored",
                "unrelated_session_history_stored",
                "unused_speculation_stored",
                "complete_diffs_stored",
                "verbose_logs_stored",
            ]:
                if privacy.get(field) is not False:
                    self.error("DEBUG_MODE_PRIVACY", f"privacy.{field} must be false", record_ref)

        task = record.get("task") if isinstance(record.get("task"), dict) else {}
        task_references = task.get("references") if isinstance(task.get("references"), list) else []
        activation = record.get("activation") if isinstance(record.get("activation"), dict) else {}
        if activation.get("enabled_by") != "explicit-user-request":
            self.error("DEBUG_MODE_ACTIVATION", "activation must be bound to an explicit current user request", record_ref)
        status = record.get("status")
        ended_by = activation.get("ended_by")
        if status == "active" and ended_by != "active":
            self.error("DEBUG_MODE_EXPIRY", "active record must have ended_by active", record_ref)
        if status in {"completed", "abandoned"} and ended_by == "active":
            self.error("DEBUG_MODE_EXPIRY", "closed record must identify its expiry event", record_ref)

        continuation = record.get("continuation") if isinstance(record.get("continuation"), dict) else {}
        continuation_kind = "legacy"
        continued_from_debug_id = "not-applicable"
        if record_schema_version >= 3:
            continuation_kind = str(continuation.get("kind", ""))
            continued_from_debug_id = str(continuation.get("previous_debug_id", ""))
            if continuation_kind == "initial":
                if continued_from_debug_id != "not-applicable":
                    self.error(
                        "DEBUG_MODE_CONTINUATION",
                        "initial Debug record must use previous_debug_id not-applicable",
                        record_ref,
                    )
            elif continuation_kind == "continued":
                if continued_from_debug_id in {"", "not-applicable", str(debug_id)}:
                    self.error(
                        "DEBUG_MODE_CONTINUATION",
                        "continued Debug record must name a different previous Debug ID",
                        record_ref,
                    )
                elif indexed_id_counts.get(continued_from_debug_id, 0) != 1:
                    self.error(
                        "DEBUG_MODE_CONTINUATION_REFERENCE",
                        f"previous Debug ID {continued_from_debug_id!r} must resolve exactly once in the index",
                        record_ref,
                    )
                else:
                    previous_entry = indexed_entries_by_id[continued_from_debug_id]
                    if previous_entry.get("status") not in {"completed", "abandoned"}:
                        self.error(
                            "DEBUG_MODE_CONTINUATION_STATE",
                            f"previous Debug ID {continued_from_debug_id!r} must be closed before continuation",
                            record_ref,
                        )
                    if record_schema_version >= 5:
                        previous_references = previous_entry.get("task_references")
                        previous_references = (
                            previous_references
                            if isinstance(previous_references, list)
                            else []
                        )
                        if not set(task_references) & set(previous_references):
                            self.error(
                                "DEBUG_MODE_CONTINUATION_LINEAGE",
                                "continued Debug record must share a task or issue reference with its predecessor",
                                record_ref,
                            )
                        if previous_entry.get("scope_id") == task.get("scope_id"):
                            self.error(
                                "DEBUG_MODE_CONTINUATION_SCOPE",
                                "continued Debug record must open a distinct logical scope ID",
                                record_ref,
                            )

        def parse_time_value(container: Any, field: str) -> datetime | None:
            item = container.get(field) if isinstance(container, dict) else None
            if not isinstance(item, dict):
                return None
            value = item.get("value")
            evidence_kind = item.get("evidence_kind")
            if evidence_kind == "unknown":
                if value is not None:
                    self.error("DEBUG_MODE_TIMING", f"{field} marked unknown must use null", record_ref)
                return None
            if not isinstance(value, str) or not value:
                self.error("DEBUG_MODE_TIMING", f"{field} with {evidence_kind} evidence requires a timestamp", record_ref)
                return None
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                self.error("DEBUG_MODE_TIMING", f"{field} is not a valid ISO-8601 timestamp", record_ref)
                return None
            if parsed.utcoffset() is None:
                self.error("DEBUG_MODE_TIMING", f"{field} must include a timezone offset", record_ref)
                return None
            return parsed

        def duration_value(container: Any, field: str) -> int | None:
            item = container.get(field) if isinstance(container, dict) else None
            if not isinstance(item, dict):
                return None
            value = item.get("value")
            evidence_kind = item.get("evidence_kind")
            if evidence_kind == "unknown":
                if value is not None:
                    self.error("DEBUG_MODE_TIMING", f"{field} marked unknown must use null", record_ref)
                return None
            if not isinstance(value, int) or value < 0:
                self.error("DEBUG_MODE_TIMING", f"{field} with {evidence_kind} evidence requires non-negative seconds", record_ref)
                return None
            return value

        timing = record.get("timing") if isinstance(record.get("timing"), dict) else {}
        started_at = parse_time_value(timing, "started_at")
        completed_at = parse_time_value(timing, "completed_at")
        elapsed_seconds = duration_value(timing, "elapsed_seconds")
        duration_value(timing, "active_work_seconds")
        capture_quality = record.get("capture_quality") if isinstance(record.get("capture_quality"), dict) else {}
        duration_value(capture_quality, "estimated_overhead_seconds")
        if started_at is not None and completed_at is not None:
            if completed_at < started_at:
                self.error("DEBUG_MODE_TIMING_ORDER", "completed_at precedes started_at", record_ref)
            elapsed_kind = timing.get("elapsed_seconds", {}).get("evidence_kind") if isinstance(timing.get("elapsed_seconds"), dict) else None
            start_kind = timing.get("started_at", {}).get("evidence_kind") if isinstance(timing.get("started_at"), dict) else None
            end_kind = timing.get("completed_at", {}).get("evidence_kind") if isinstance(timing.get("completed_at"), dict) else None
            if start_kind == end_kind == "observed" and elapsed_kind == "observed" and elapsed_seconds is not None:
                actual = round((completed_at - started_at).total_seconds())
                if abs(actual - elapsed_seconds) > 1:
                    self.error("DEBUG_MODE_TIMING_DRIFT", "observed elapsed seconds do not match observed timestamps", record_ref)

        coverage = capture_quality.get("event_coverage")
        missing_intervals = capture_quality.get("missing_intervals")
        if coverage == "complete" and missing_intervals:
            self.error("DEBUG_MODE_CAPTURE_QUALITY", "complete coverage cannot declare missing intervals", record_ref)
        if coverage == "partial" and not missing_intervals:
            self.error("DEBUG_MODE_CAPTURE_QUALITY", "partial coverage must name missing intervals", record_ref)
        if capture_quality.get("observer_effect") == "material":
            self.warn("DEBUG_MODE_OBSERVER_EFFECT", "record declares material observer effect; comparison claims must account for it", record_ref)

        events = record.get("events") if isinstance(record.get("events"), list) else []
        if record_schema_version == 1:
            self.warn(
                "DEBUG_MODE_LEGACY_ATTRIBUTION",
                "schema-version-1 attribution is accepted as historical evidence but is not comparable to version-2 intervention metrics without qualification",
                record_ref,
            )
        event_by_id: dict[str, dict[str, Any]] = {}
        event_order: dict[str, int] = {}
        event_times: dict[str, datetime] = {}
        for event_index, event in enumerate(events):
            event_label = f"events[{event_index}]"
            if not isinstance(event, dict):
                continue
            event_id = event.get("event_id")
            if not is_resolved_string(event_id):
                self.error("DEBUG_MODE_EVENT_ID", f"{event_label}.event_id must be resolved", record_ref)
                continue
            if event_id in event_by_id:
                self.error("DEBUG_MODE_EVENT_DUPLICATE", f"duplicate event_id {event_id}", record_ref)
            event_by_id[event_id] = event
            event_order[event_id] = event_index
            if event.get("sequence") != event_index + 1:
                self.error("DEBUG_MODE_EVENT_SEQUENCE", f"{event_label}.sequence must be {event_index + 1}", record_ref)
            event_time = parse_time_value(
                {"occurred_at": event.get("occurred_at")}, "occurred_at"
            )
            if event_time is not None:
                event_times[event_id] = event_time
            evidence = event.get("evidence")
            if not isinstance(evidence, list) or not evidence or not all(is_resolved_string(item) for item in evidence):
                self.error("DEBUG_MODE_EVENT_EVIDENCE", f"{event_label}.evidence must be a non-empty resolved string list", record_ref)

        for event_id, event in event_by_id.items():
            causes = event.get("caused_by_event_ids")
            if not isinstance(causes, list):
                continue
            for cause in causes:
                if cause not in event_by_id:
                    self.error("DEBUG_MODE_EVENT_CAUSE", f"{event_id} references unknown cause {cause}", record_ref)
                elif event_order[cause] >= event_order[event_id]:
                    self.error("DEBUG_MODE_EVENT_CAUSE_ORDER", f"{event_id} cause {cause} must be earlier", record_ref)

        def lifecycle_finding(code: str, message: str) -> None:
            finding = self.error if record_schema_version >= 3 else self.warn
            finding(code, message, record_ref)

        if record_schema_version >= 3 and status == "completed" and (
            started_at is None or completed_at is None
        ):
            self.error(
                "DEBUG_MODE_COMPLETION_TIME_REQUIRED",
                "completed schema-version-3 record requires concrete start and completion timestamps",
                record_ref,
            )
        if record_schema_version >= 3 and status == "active" and completed_at is not None:
            self.error(
                "DEBUG_MODE_ACTIVE_COMPLETION_TIME",
                "active schema-version-3 record cannot declare a completion timestamp",
                record_ref,
            )

        previous_event_id: str | None = None
        for event_id in event_order:
            event_time = event_times.get(event_id)
            if event_time is None:
                previous_event_id = event_id
                continue
            if started_at is not None and event_time < started_at:
                lifecycle_finding(
                    "DEBUG_MODE_EVENT_TIME_WINDOW",
                    f"{event_id} occurs before timing.started_at",
                )
            if status == "completed" and completed_at is not None and event_time > completed_at:
                lifecycle_finding(
                    "DEBUG_MODE_EVENT_TIME_WINDOW",
                    f"{event_id} occurs after timing.completed_at",
                )
            if previous_event_id is not None:
                previous_time = event_times.get(previous_event_id)
                if previous_time is not None and event_time < previous_time:
                    lifecycle_finding(
                        "DEBUG_MODE_EVENT_TIME_ORDER",
                        f"{event_id} timestamp precedes earlier sequence event {previous_event_id}",
                    )
            previous_event_id = event_id

        for event_id, event in event_by_id.items():
            event_time = event_times.get(event_id)
            if event_time is None:
                continue
            for cause_id in event.get("caused_by_event_ids", []):
                cause_time = event_times.get(cause_id)
                if cause_time is not None and cause_time > event_time:
                    lifecycle_finding(
                        "DEBUG_MODE_EVENT_CAUSAL_TIME",
                        f"{event_id} occurs before its cause {cause_id}",
                    )

        def has_matching_ancestor(event: dict[str, Any], predicate: Any) -> bool:
            pending = list(event.get("caused_by_event_ids", []))
            visited: set[str] = set()
            while pending:
                cause_id = pending.pop()
                if cause_id in visited:
                    continue
                visited.add(cause_id)
                cause = event_by_id.get(cause_id)
                if cause is None:
                    continue
                if predicate(cause):
                    return True
                pending.extend(cause.get("caused_by_event_ids", []))
            return False

        def event_actor_role(event: dict[str, Any]) -> Any:
            if record_schema_version >= 4:
                return event.get("actor_role")
            return event.get("actor")

        def is_human_intervention(event: dict[str, Any]) -> bool:
            if record_schema_version == 1:
                return event.get("origin") == "human-initiated"
            return event_actor_role(event) == "human" and event.get("causal_class") == "intervention"

        def is_external_intervention(event: dict[str, Any]) -> bool:
            if record_schema_version == 1:
                return event.get("origin") == "external-maintainer"
            return event_actor_role(event) == "external-maintainer" and event.get("causal_class") == "intervention"

        def has_human_ancestor(event: dict[str, Any]) -> bool:
            return has_matching_ancestor(event, is_human_intervention)

        def has_external_ancestor(event: dict[str, Any]) -> bool:
            return has_matching_ancestor(event, is_external_intervention)

        def has_correction_ancestor(event: dict[str, Any]) -> bool:
            return has_matching_ancestor(
                event,
                lambda cause: (
                    is_human_intervention(cause) or is_external_intervention(cause)
                )
                and (
                    cause.get("intervention_kind") == "correction"
                    if record_schema_version >= 2
                    else cause.get("category") == "review-correction"
                ),
            )

        def has_ancestor(event: dict[str, Any], ancestor_id: str) -> bool:
            pending = list(event.get("caused_by_event_ids", []))
            visited: set[str] = set()
            while pending:
                cause_id = pending.pop()
                if cause_id == ancestor_id:
                    return True
                if cause_id in visited:
                    continue
                visited.add(cause_id)
                cause = event_by_id.get(cause_id)
                if cause is not None:
                    pending.extend(cause.get("caused_by_event_ids", []))
            return False

        for event_id, event in event_by_id.items():
            origin = event.get("origin")
            actor = event_actor_role(event) if record_schema_version >= 2 else None
            causal_class = event.get("causal_class") if record_schema_version >= 2 else None
            intervention_kind = event.get("intervention_kind") if record_schema_version >= 2 else None
            human_ancestor = has_human_ancestor(event)
            external_ancestor = has_external_ancestor(event)
            if record_schema_version == 1:
                if origin == "derived-after-human-intervention" and not human_ancestor:
                    self.error("DEBUG_MODE_DERIVATION_CAUSE", f"{event_id} has no human-initiated ancestor", record_ref)
                if origin == "alatyr-initiated" and human_ancestor:
                    self.error("DEBUG_MODE_INDEPENDENCE", f"{event_id} cannot be independent because its causal chain contains a human intervention", record_ref)
            else:
                if actor in {"human", "external-maintainer"}:
                    if causal_class != "intervention" or intervention_kind == "not-applicable":
                        self.error("DEBUG_MODE_INTERVENTION_CLASSIFICATION", f"{event_id} human or external input must be a typed intervention", record_ref)
                elif actor not in {"human", "external-maintainer"}:
                    if causal_class == "intervention" or intervention_kind != "not-applicable":
                        self.error("DEBUG_MODE_AGENT_CLASSIFICATION", f"{event_id} non-human contribution cannot be classified as an intervention", record_ref)
                if causal_class == "derived-from-human" and not human_ancestor:
                    self.error("DEBUG_MODE_DERIVATION_CAUSE", f"{event_id} has no human intervention ancestor", record_ref)
                if causal_class == "derived-from-external" and not external_ancestor:
                    self.error("DEBUG_MODE_DERIVATION_CAUSE", f"{event_id} has no external-maintainer intervention ancestor", record_ref)
                if record_schema_version >= 4:
                    derived_role = {
                        "derived-from-executor": "executor",
                        "derived-from-alatyr-system": "alatyr-system",
                        "derived-from-automation": "automation",
                    }.get(causal_class)
                    if derived_role and not has_matching_ancestor(
                        event, lambda cause: event_actor_role(cause) == derived_role
                    ):
                        self.error(
                            "DEBUG_MODE_DERIVATION_CAUSE",
                            f"{event_id} has no {derived_role} ancestor",
                            record_ref,
                        )
                if causal_class == "independent-within-scope" and (human_ancestor or external_ancestor):
                    self.error("DEBUG_MODE_INDEPENDENCE", f"{event_id} cannot be independent because its causal chain contains an intervention", record_ref)
                if event.get("post_review_rework") is True and not has_correction_ancestor(event):
                    self.error(
                        "DEBUG_MODE_POST_REVIEW_CAUSE",
                        f"{event_id} claims post-review rework without a human or external correction ancestor",
                        record_ref,
                    )

            impacts = event.get("architectural_impacts")
            decision_effect = event.get("decision_effect")
            if impacts is None or decision_effect is None:
                self.warn(
                    "DEBUG_MODE_STRUCTURED_CLASSIFICATION_MISSING",
                    f"{event_id} predates or omits structured architectural impact and decision-effect evidence",
                    record_ref,
                )
            impact_values = impacts if isinstance(impacts, list) else []
            is_human_input = (
                origin in {"human-initiated", "external-maintainer"}
                if record_schema_version == 1
                else actor in {"human", "external-maintainer"}
            )
            claims_supervision = event.get("architectural_supervision") is True
            if claims_supervision and not is_human_input:
                self.error(
                    "DEBUG_MODE_ARCHITECTURAL_SUPERVISION_ORIGIN",
                    f"{event_id} cannot claim human architectural supervision with origin {origin}",
                    record_ref,
                )
            if is_human_input and impact_values and not claims_supervision:
                self.error(
                    "DEBUG_MODE_ARCHITECTURAL_SUPERVISION_DRIFT",
                    f"{event_id} has human architectural impacts but architectural_supervision is false",
                    record_ref,
                )
            if claims_supervision and not impact_values:
                finding = (
                    self.warn
                    if impacts is None and decision_effect is None
                    else self.error
                )
                finding(
                    "DEBUG_MODE_ARCHITECTURAL_IMPACT_MISSING",
                    f"{event_id} claims architectural supervision without structured architectural impacts",
                    record_ref,
                )
            if decision_effect == "changes-direction" and not impact_values:
                self.error(
                    "DEBUG_MODE_DIRECTION_IMPACT_MISSING",
                    f"{event_id} changes direction but names no architectural impact",
                    record_ref,
                )
            if (
                event.get("category") == "review-correction"
                and is_human_input
                and decision_effect in {None, "not-assessed"}
                and not claims_supervision
            ):
                self.warn(
                    "DEBUG_MODE_REVIEW_CORRECTION_UNASSESSED",
                    f"{event_id} is a review correction without an assessed architectural effect",
                    record_ref,
                )

        for direction_id, direction_event in event_by_id.items():
            if direction_event.get("decision_effect") != "changes-direction":
                continue
            rejected_hypotheses = [
                (event_id, event)
                for event_id, event in event_by_id.items()
                if event.get("category") == "hypothesis"
                and event.get("hypothesis_outcome") == "rejected"
                and has_ancestor(event, direction_id)
            ]
            if not rejected_hypotheses:
                self.error(
                    "DEBUG_MODE_DIRECTION_HYPOTHESIS_MISSING",
                    f"{direction_id} changes direction without a causally linked rejected hypothesis",
                    record_ref,
                )
                continue
            rejected_ids = {event_id for event_id, _event in rejected_hypotheses}
            replacements = [
                event_id
                for event_id, event in event_by_id.items()
                if event.get("category") in {"invariant", "architecture-area"}
                and any(has_ancestor(event, rejected_id) for rejected_id in rejected_ids)
            ]
            if not replacements:
                self.error(
                    "DEBUG_MODE_DIRECTION_REPLACEMENT_MISSING",
                    f"{direction_id} has a rejected hypothesis but no causally linked replacement invariant or architecture direction",
                    record_ref,
                )

        project_candidate_records_v5: list[dict[str, Any]] = []
        candidate_event_ids_v5: list[str] = []
        if record_schema_version >= 5:
            candidate_container = record.get("final_result")
            project_candidate_records_v5 = (
                candidate_container.get("project_knowledge_candidates", [])
                if isinstance(candidate_container, dict)
                else []
            )
            project_candidate_records_v5 = [
                candidate
                for candidate in project_candidate_records_v5
                if isinstance(candidate, dict)
            ]
            for candidate in project_candidate_records_v5:
                if isinstance(candidate, dict) and isinstance(candidate.get("event_ids"), list):
                    candidate_event_ids_v5.extend(
                        event_id
                        for event_id in candidate["event_ids"]
                        if isinstance(event_id, str)
                    )

        def matching_event_ids(metric_name: str) -> list[str]:
            def matches(event: dict[str, Any]) -> bool:
                origin = event.get("origin")
                actor = event_actor_role(event)
                causal_class = event.get("causal_class")
                intervention_kind = event.get("intervention_kind")
                contribution_kind = event.get("contribution_kind")
                category = event.get("category")
                if record_schema_version == 1:
                    if metric_name == "human_interventions":
                        return origin == "human-initiated"
                    if metric_name == "human_architectural_interventions":
                        return origin == "human-initiated" and event.get("architectural_supervision") is True
                    if metric_name == "alatyr_independent_findings":
                        return origin == "alatyr-initiated"
                    if metric_name == "derived_findings_after_human":
                        return origin == "derived-after-human-intervention"
                    if metric_name == "alatyr_independent_dependency_checks":
                        return origin == "alatyr-initiated" and category == "dependency"
                    if metric_name == "human_requested_dependency_checks":
                        return origin == "human-initiated" and category == "dependency"
                    if metric_name == "derived_dependency_expansions_after_human":
                        return origin == "derived-after-human-intervention" and event.get("dependency_expansion") is True
                    if metric_name == "hypotheses_tested":
                        return category == "hypothesis" and event.get("hypothesis_outcome") in {"confirmed", "rejected"}
                    if metric_name == "hypotheses_rejected":
                        return category == "hypothesis" and event.get("hypothesis_outcome") == "rejected"
                    if metric_name == "implementation_revisions":
                        return category == "implementation-revision"
                    if metric_name == "implementation_corrections_after_human":
                        return category == "implementation-revision" and origin == "derived-after-human-intervention"
                    if metric_name == "validation_expansions":
                        return event.get("validation_expansion") is True
                    if metric_name == "regression_scenarios_added":
                        return category == "regression-scenario"
                    if metric_name == "maintainer_corrections":
                        return origin == "external-maintainer"
                    if metric_name == "post_review_rework":
                        return event.get("post_review_rework") is True
                    return False

                if record_schema_version >= 4:
                    if metric_name == "human_interventions":
                        return actor == "human" and causal_class == "intervention"
                    if metric_name == "human_architectural_interventions":
                        return actor == "human" and causal_class == "intervention" and event.get("architectural_supervision") is True
                    if metric_name == "executor_independent_findings":
                        return actor == "executor" and causal_class == "independent-within-scope" and contribution_kind == "finding"
                    if metric_name == "executor_derived_findings_after_human":
                        return actor == "executor" and causal_class == "derived-from-human" and contribution_kind == "finding"
                    if metric_name == "executor_independent_dependency_checks":
                        return actor == "executor" and causal_class == "independent-within-scope" and contribution_kind == "finding" and category == "dependency"
                    if metric_name == "human_requested_dependency_checks":
                        return actor == "human" and causal_class == "intervention" and category == "dependency"
                    if metric_name == "executor_derived_dependency_expansions_after_human":
                        return actor == "executor" and causal_class == "derived-from-human" and contribution_kind == "finding" and event.get("dependency_expansion") is True
                    if metric_name == "hypotheses_tested":
                        return contribution_kind == "finding" and category == "hypothesis" and event.get("hypothesis_outcome") in {"confirmed", "rejected"}
                    if metric_name == "hypotheses_rejected":
                        return contribution_kind == "finding" and category == "hypothesis" and event.get("hypothesis_outcome") == "rejected"
                    if metric_name == "implementation_revisions":
                        return contribution_kind == "implementation"
                    if metric_name == "implementation_corrections_after_human":
                        return contribution_kind == "implementation" and has_matching_ancestor(
                            event,
                            lambda cause: event_actor_role(cause) == "human"
                            and cause.get("causal_class") == "intervention"
                            and cause.get("correction_disposition")
                            in {
                                "new-guidance-candidate",
                                "known-guidance-routing-failure",
                                "known-guidance-compliance-failure",
                                "task-local",
                            },
                        )
                    if metric_name == "validation_expansions":
                        return contribution_kind == "validation" and event.get("validation_expansion") is True
                    if metric_name == "regression_scenarios_added":
                        return contribution_kind == "validation" and category == "regression-scenario"
                    if metric_name == "maintainer_corrections":
                        return actor == "external-maintainer" and causal_class == "intervention" and event.get("correction_disposition") in {
                            "new-guidance-candidate",
                            "known-guidance-routing-failure",
                            "known-guidance-compliance-failure",
                            "task-local",
                        }
                    if metric_name == "post_review_rework":
                        return event.get("post_review_rework") is True and has_matching_ancestor(
                            event,
                            lambda cause: event_actor_role(cause) == "external-maintainer"
                            and cause.get("causal_class") == "intervention"
                            and cause.get("correction_disposition")
                            in {
                                "new-guidance-candidate",
                                "known-guidance-routing-failure",
                                "known-guidance-compliance-failure",
                                "task-local",
                            },
                        )
                    if metric_name == "new_guidance_candidates":
                        if record_schema_version >= 5:
                            return event.get("event_id") in candidate_event_ids_v5
                        return event.get("correction_disposition") == "new-guidance-candidate"
                    disposition_metrics = {
                        "known_guidance_routing_failures": "known-guidance-routing-failure",
                        "known_guidance_compliance_failures": "known-guidance-compliance-failure",
                        "task_local_corrections": "task-local",
                        "scope_changes": "scope-change",
                        "validation_requests": "validation-request",
                    }
                    expected_disposition = disposition_metrics.get(metric_name)
                    if expected_disposition is not None:
                        return event.get("correction_disposition") == expected_disposition
                    return False

                if metric_name == "human_interventions":
                    return actor == "human" and causal_class == "intervention"
                if metric_name == "human_architectural_interventions":
                    return actor == "human" and causal_class == "intervention" and event.get("architectural_supervision") is True
                if metric_name == "alatyr_independent_findings":
                    return actor == "alatyr" and causal_class == "independent-within-scope" and contribution_kind == "finding"
                if metric_name == "derived_findings_after_human":
                    return actor == "alatyr" and causal_class == "derived-from-human" and contribution_kind == "finding"
                if metric_name == "alatyr_independent_dependency_checks":
                    return actor == "alatyr" and causal_class == "independent-within-scope" and contribution_kind == "finding" and category == "dependency"
                if metric_name == "human_requested_dependency_checks":
                    return actor == "human" and causal_class == "intervention" and category == "dependency"
                if metric_name == "derived_dependency_expansions_after_human":
                    return actor == "alatyr" and causal_class == "derived-from-human" and contribution_kind == "finding" and event.get("dependency_expansion") is True
                if metric_name == "hypotheses_tested":
                    return contribution_kind == "finding" and category == "hypothesis" and event.get("hypothesis_outcome") in {"confirmed", "rejected"}
                if metric_name == "hypotheses_rejected":
                    return contribution_kind == "finding" and category == "hypothesis" and event.get("hypothesis_outcome") == "rejected"
                if metric_name == "implementation_revisions":
                    return contribution_kind == "implementation" and category == "implementation-revision"
                if metric_name == "implementation_corrections_after_human":
                    return contribution_kind == "implementation" and category == "implementation-revision" and causal_class == "derived-from-human" and has_correction_ancestor(event)
                if metric_name == "validation_expansions":
                    return contribution_kind == "validation" and event.get("validation_expansion") is True
                if metric_name == "regression_scenarios_added":
                    return contribution_kind == "validation" and category == "regression-scenario"
                if metric_name == "maintainer_corrections":
                    return actor == "external-maintainer" and causal_class == "intervention" and intervention_kind == "correction"
                if metric_name == "post_review_rework":
                    return contribution_kind == "implementation" and event.get("post_review_rework") is True and has_correction_ancestor(event)
                return False

            return [event_id for event_id, event in event_by_id.items() if matches(event)]

        metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
        metric_names = (
            DEBUG_V4_METRIC_NAMES
            if record_schema_version >= 4
            else DEBUG_LEGACY_METRIC_NAMES
        )
        for metric_name in metric_names:
            metric = metrics.get(metric_name)
            if not isinstance(metric, dict):
                continue
            metric_event_ids = metric.get("event_ids")
            unknown_event_ids = sorted(
                set(metric_event_ids if isinstance(metric_event_ids, list) else []) - set(event_by_id)
            )
            if unknown_event_ids:
                self.error("DEBUG_MODE_METRIC_EVENT", f"metrics.{metric_name} references unknown events {unknown_event_ids}", record_ref)
            if metric.get("evidence_kind") == "event-derived":
                expected_ids = matching_event_ids(metric_name)
                expected_value = (
                    len(project_candidate_records_v5)
                    if record_schema_version >= 5
                    and metric_name == "new_guidance_candidates"
                    else len(expected_ids)
                )
                if metric.get("value") != expected_value or metric_event_ids != expected_ids:
                    self.error("DEBUG_MODE_METRIC_DRIFT", f"metrics.{metric_name} does not match its event predicate", record_ref)
            elif metric.get("evidence_kind") == "unavailable" and (metric.get("value") is not None or metric_event_ids):
                self.error("DEBUG_MODE_METRIC_UNAVAILABLE", f"metrics.{metric_name} marked unavailable must have null value and no event IDs", record_ref)
        if status == "completed":
            if not events:
                self.error("DEBUG_MODE_COMPLETED_EMPTY", "completed record must contain at least one material event", record_ref)
            for metric_name in metric_names:
                metric = metrics.get(metric_name)
                if not isinstance(metric, dict) or metric.get("evidence_kind") != "event-derived":
                    self.error("DEBUG_MODE_COMPLETED_METRICS", f"completed record requires event-derived metrics.{metric_name}", record_ref)

        final_result = record.get("final_result") if isinstance(record.get("final_result"), dict) else {}
        linked_evidence = final_result.get("engineering_evidence_ids")
        if isinstance(linked_evidence, list):
            for evidence_id in linked_evidence:
                if evidence_id in event_by_id:
                    self.error(
                        "DEBUG_MODE_ENGINEERING_EVIDENCE_EVENT_ID",
                        f"Debug event ID {evidence_id} cannot be used as durable engineering evidence",
                        record_ref,
                    )
                    continue
                resolution_count = engineering_evidence_counts.get(evidence_id, 0)
                if resolution_count != 1:
                    self.error(
                        "DEBUG_MODE_ENGINEERING_EVIDENCE_REFERENCE",
                        f"engineering evidence {evidence_id} resolves {resolution_count} times in {engineering_index_relpath}; expected exactly once",
                        record_ref,
                    )

        implementation_surfaces = [
            value
            for value in final_result.get("implementation_surfaces", [])
            if isinstance(value, str)
        ]
        lifecycle_completion_scope = "legacy"
        covered_phases: list[str] = []
        continuation_expected = False
        project_candidate_ids: list[str] = []
        repository_lifecycle_state = "legacy"
        validation_evidence_classes: list[str] = []
        if record_schema_version >= 5:
            all_phases = {
                "analysis", "implementation", "validation", "finalization"
            }
            lifecycle = final_result.get("lifecycle_coverage")
            lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
            lifecycle_completion_scope = str(
                lifecycle.get("completion_scope", "")
            )
            covered_value = lifecycle.get("covered_phases")
            omitted_value = lifecycle.get("omitted_phases")
            covered_phases = (
                covered_value if isinstance(covered_value, list) else []
            )
            omitted_phases = (
                omitted_value if isinstance(omitted_value, list) else []
            )
            continuation_expected = lifecycle.get("continuation_expected") is True
            next_phase = lifecycle.get("next_phase")
            if set(covered_phases) & set(omitted_phases) or (
                set(covered_phases) | set(omitted_phases)
            ) != all_phases:
                self.error(
                    "DEBUG_MODE_LIFECYCLE_PARTITION",
                    "covered and omitted phases must form an exact lifecycle partition",
                    record_ref,
                )
            if status == "active":
                if lifecycle_completion_scope != "active":
                    self.error(
                        "DEBUG_MODE_LIFECYCLE_STATE",
                        "active Debug record requires active lifecycle coverage",
                        record_ref,
                    )
            elif lifecycle_completion_scope == "active":
                self.error(
                    "DEBUG_MODE_LIFECYCLE_STATE",
                    "closed Debug record cannot retain active lifecycle coverage",
                    record_ref,
                )
            if lifecycle_completion_scope == "full-task-complete":
                if set(covered_phases) != all_phases or continuation_expected or next_phase != "not-applicable":
                    self.error(
                        "DEBUG_MODE_LIFECYCLE_COMPLETE",
                        "full-task completion requires all phases and no expected continuation",
                        record_ref,
                    )
            if lifecycle_completion_scope == "phase-complete":
                if not omitted_phases:
                    self.error(
                        "DEBUG_MODE_LIFECYCLE_PHASE",
                        "phase-complete evidence must identify omitted lifecycle phases",
                        record_ref,
                    )
                if continuation_expected and next_phase not in omitted_phases:
                    self.error(
                        "DEBUG_MODE_LIFECYCLE_CONTINUATION",
                        "expected continuation must name one omitted next phase",
                        record_ref,
                    )
                if not continuation_expected and next_phase != "not-applicable":
                    self.error(
                        "DEBUG_MODE_LIFECYCLE_CONTINUATION",
                        "non-continuing phase completion must use next_phase not-applicable",
                        record_ref,
                    )
            contribution_kinds = {
                event.get("contribution_kind")
                for event in events
                if isinstance(event, dict)
            }
            validation_results = final_result.get("validation")
            validation_results = (
                validation_results.get("results", [])
                if isinstance(validation_results, dict)
                else []
            )
            if (
                implementation_surfaces
                or "implementation" in contribution_kinds
            ) and "implementation" not in covered_phases:
                self.error(
                    "DEBUG_MODE_LIFECYCLE_IMPLEMENTATION",
                    "implementation evidence requires implementation phase coverage",
                    record_ref,
                )
            if (
                validation_results or "validation" in contribution_kinds
            ) and "validation" not in covered_phases:
                self.error(
                    "DEBUG_MODE_LIFECYCLE_VALIDATION",
                    "validation evidence requires validation phase coverage",
                    record_ref,
                )
            if status == "completed" and "finalization" not in covered_phases:
                self.error(
                    "DEBUG_MODE_LIFECYCLE_FINALIZATION",
                    "completed Debug evidence must cover finalization",
                    record_ref,
                )

            candidate_ids_seen: set[str] = set()
            candidate_event_coverage: set[str] = set()
            for candidate_index, candidate in enumerate(
                project_candidate_records_v5
            ):
                candidate_id = candidate.get("candidate_id")
                if not is_resolved_string(candidate_id):
                    continue
                project_candidate_ids.append(candidate_id)
                if candidate_id in candidate_ids_seen:
                    self.error(
                        "DEBUG_MODE_KNOWLEDGE_CANDIDATE_DUPLICATE",
                        f"duplicate project knowledge candidate {candidate_id}",
                        record_ref,
                    )
                candidate_ids_seen.add(candidate_id)
                event_ids = candidate.get("event_ids")
                event_ids = event_ids if isinstance(event_ids, list) else []
                unknown_ids = sorted(set(event_ids) - set(event_by_id))
                if unknown_ids:
                    self.error(
                        "DEBUG_MODE_KNOWLEDGE_CANDIDATE_EVENT",
                        f"project_knowledge_candidates[{candidate_index}] references unknown events {unknown_ids}",
                        record_ref,
                    )
                candidate_event_coverage.update(
                    event_id for event_id in event_ids if event_id in event_by_id
                )
                disposition = candidate.get("disposition")
                references = candidate.get("references")
                references = references if isinstance(references, list) else []
                if disposition == "preserved-as-engineering-evidence" and not (
                    set(references) & set(linked_evidence or [])
                ):
                    self.error(
                        "DEBUG_MODE_KNOWLEDGE_CANDIDATE_EVIDENCE",
                        f"candidate {candidate_id} does not reference linked engineering evidence",
                        record_ref,
                    )
                if (
                    disposition == "promotion-proposed"
                    and candidate_id not in promotion_candidate_ids
                ):
                    self.error(
                        "DEBUG_MODE_KNOWLEDGE_CANDIDATE_PROMOTION",
                        f"candidate {candidate_id} has no indexed promotion proposal",
                        record_ref,
                    )
                if disposition == "existing-canonical-owner" and not any(
                    is_target_relative_path(reference)
                    and self.target_path(reference).is_file()
                    for reference in references
                ):
                    self.error(
                        "DEBUG_MODE_KNOWLEDGE_CANDIDATE_OWNER",
                        f"candidate {candidate_id} does not resolve an existing canonical owner",
                        record_ref,
                    )
            if set(candidate_event_ids_v5) != candidate_event_coverage:
                self.error(
                    "DEBUG_MODE_KNOWLEDGE_CANDIDATE_COVERAGE",
                    "knowledge candidate metric events and dispositions differ",
                    record_ref,
                )
        evidence_status = "legacy"
        claim_fidelity = "legacy"
        if record_schema_version >= 2:
            evidence_decision = final_result.get("engineering_evidence_decision")
            if not isinstance(evidence_decision, dict):
                self.error("DEBUG_MODE_EVIDENCE_DECISION", "versioned record requires engineering_evidence_decision", record_ref)
                evidence_decision = {}
            evidence_status = str(evidence_decision.get("status", ""))
            evidence_ids = linked_evidence if isinstance(linked_evidence, list) else []
            if status == "completed" and evidence_status == "pending":
                self.error("DEBUG_MODE_EVIDENCE_PENDING", "completed Debug session cannot leave durable engineering evidence pending", record_ref)
            if evidence_status == "captured" and not evidence_ids:
                self.error("DEBUG_MODE_EVIDENCE_CAPTURE", "captured decision requires at least one engineering evidence ID", record_ref)
            if evidence_status in {"skipped", "blocked"} and evidence_ids:
                self.error("DEBUG_MODE_EVIDENCE_DECISION", f"{evidence_status} decision cannot list captured engineering evidence IDs", record_ref)
            if evidence_status == "blocked" and not is_resolved_string(evidence_decision.get("next_safe_action")):
                self.error("DEBUG_MODE_EVIDENCE_BLOCKED", "blocked evidence decision requires a next safe action", record_ref)

            if record_schema_version == 2:
                trigger_ids = evidence_decision.get("trigger_event_ids")
                trigger_ids = trigger_ids if isinstance(trigger_ids, list) else []
                unknown_triggers = sorted(set(trigger_ids) - set(event_by_id))
                if unknown_triggers:
                    self.error("DEBUG_MODE_EVIDENCE_TRIGGER", f"engineering-evidence decision references unknown events {unknown_triggers}", record_ref)
                material_trigger_ids = {
                    event_id
                    for event_id, event in event_by_id.items()
                    if (
                        event.get("hypothesis_outcome") == "rejected"
                        or event.get("decision_effect") == "changes-direction"
                        or event.get("intervention_kind") == "correction"
                    )
                }
                missing_material_triggers = sorted(material_trigger_ids - set(trigger_ids))
                if missing_material_triggers:
                    self.error("DEBUG_MODE_EVIDENCE_TRIGGER", f"material evidence triggers are not represented in the decision: {missing_material_triggers}", record_ref)
                trigger_kinds = evidence_decision.get("trigger_kinds")
                if trigger_ids and (not isinstance(trigger_kinds, list) or not trigger_kinds):
                    self.error("DEBUG_MODE_EVIDENCE_TRIGGER", "triggered evidence decision must name at least one trigger kind", record_ref)
                preserved_by = evidence_decision.get("knowledge_preserved_by")
                if material_trigger_ids and evidence_status == "skipped" and (not isinstance(preserved_by, list) or not preserved_by):
                    self.error("DEBUG_MODE_EVIDENCE_SKIP", "material Debug findings may be skipped only when canonical durable knowledge already preserves them", record_ref)
                if status == "completed" and material_trigger_ids and evidence_status not in {"captured", "blocked", "skipped"}:
                    self.error("DEBUG_MODE_EVIDENCE_DECISION", "material completed Debug work requires captured, blocked, or justified skipped durable evidence", record_ref)
            else:
                def event_matches_role(event: dict[str, Any], role: str) -> bool:
                    if role == "finding":
                        return event.get("contribution_kind") == "finding"
                    if role == "decision":
                        return event.get("contribution_kind") == "decision"
                    if role == "implementation":
                        return event.get("contribution_kind") == "implementation"
                    if role == "validation":
                        return event.get("contribution_kind") == "validation"
                    if role == "correction":
                        return (
                            event_actor_role(event) in {"human", "external-maintainer"}
                            and event.get("causal_class") == "intervention"
                            and (
                                event.get("correction_disposition")
                                in {
                                    "new-guidance-candidate",
                                    "known-guidance-routing-failure",
                                    "known-guidance-compliance-failure",
                                    "task-local",
                                }
                                if record_schema_version >= 4
                                else event.get("intervention_kind") == "correction"
                            )
                        )
                    if role == "direction-change":
                        return event.get("decision_effect") == "changes-direction"
                    if role == "rejected-hypothesis":
                        return (
                            event.get("contribution_kind") == "finding"
                            and event.get("category") == "hypothesis"
                            and event.get("hypothesis_outcome") == "rejected"
                        )
                    return False

                event_links = evidence_decision.get("event_links")
                event_links = event_links if isinstance(event_links, list) else []
                linked_event_ids: set[str] = set()
                for link_index, link in enumerate(event_links):
                    if not isinstance(link, dict):
                        continue
                    event_id = link.get("event_id")
                    role = link.get("role")
                    if event_id not in event_by_id:
                        self.error(
                            "DEBUG_MODE_EVIDENCE_EVENT_LINK",
                            f"event_links[{link_index}] references unknown event {event_id}",
                            record_ref,
                        )
                        continue
                    linked_event_ids.add(str(event_id))
                    if role not in DEBUG_EVENT_LINK_ROLES or not event_matches_role(event_by_id[event_id], str(role)):
                        self.error(
                            "DEBUG_MODE_EVIDENCE_EVENT_ROLE",
                            f"event_links[{link_index}] role {role!r} is incompatible with event {event_id}",
                            record_ref,
                        )

                evaluations = evidence_decision.get("materiality_evaluations")
                evaluations = evaluations if isinstance(evaluations, list) else []
                evaluations_by_kind: dict[str, dict[str, Any]] = {}
                evaluation_counts: dict[str, int] = {}
                all_evaluation_event_ids: set[str] = set()
                for evaluation_index, evaluation in enumerate(evaluations):
                    if not isinstance(evaluation, dict):
                        continue
                    kind = str(evaluation.get("kind", ""))
                    evaluation_counts[kind] = evaluation_counts.get(kind, 0) + 1
                    evaluations_by_kind.setdefault(kind, evaluation)
                    event_ids = evaluation.get("event_ids")
                    event_ids = event_ids if isinstance(event_ids, list) else []
                    unknown_ids = sorted(set(event_ids) - set(event_by_id))
                    if unknown_ids:
                        self.error(
                            "DEBUG_MODE_MATERIALITY_EVENT",
                            f"materiality_evaluations[{evaluation_index}] references unknown events {unknown_ids}",
                            record_ref,
                        )
                    all_evaluation_event_ids.update(
                        event_id for event_id in event_ids if event_id in event_by_id
                    )
                    evidence_refs = evaluation.get("evidence")
                    evidence_refs = evidence_refs if isinstance(evidence_refs, list) else []
                    outcome = evaluation.get("outcome")
                    if outcome == "applicable" and not event_ids and not evidence_refs:
                        self.error(
                            "DEBUG_MODE_MATERIALITY_EVIDENCE",
                            f"applicable materiality kind {kind!r} requires event or external evidence",
                            record_ref,
                        )
                    if outcome == "not-applicable" and event_ids:
                        self.error(
                            "DEBUG_MODE_MATERIALITY_EVIDENCE",
                            f"not-applicable materiality kind {kind!r} cannot cite trigger events",
                            record_ref,
                        )

                missing_kinds = sorted(DEBUG_MATERIALITY_KINDS - set(evaluations_by_kind))
                duplicate_kinds = sorted(
                    kind for kind, count in evaluation_counts.items() if count > 1
                )
                extra_kinds = sorted(set(evaluations_by_kind) - DEBUG_MATERIALITY_KINDS)
                if missing_kinds or duplicate_kinds or extra_kinds:
                    self.error(
                        "DEBUG_MODE_MATERIALITY_SET",
                        f"materiality evaluation set drift: missing={missing_kinds}, duplicate={duplicate_kinds}, extra={extra_kinds}",
                        record_ref,
                    )
                missing_event_links = sorted(all_evaluation_event_ids - linked_event_ids)
                if missing_event_links:
                    self.error(
                        "DEBUG_MODE_MATERIALITY_EVENT_LINK",
                        f"materiality events lack typed event links: {missing_event_links}",
                        record_ref,
                    )

                deterministic_materiality = {
                    "rejected-hypothesis": {
                        event_id
                        for event_id, event in event_by_id.items()
                        if event_matches_role(event, "rejected-hypothesis")
                    },
                    "reviewer-correction": {
                        event_id
                        for event_id, event in event_by_id.items()
                        if event_matches_role(event, "correction")
                    },
                    "direction-change": {
                        event_id
                        for event_id, event in event_by_id.items()
                        if event_matches_role(event, "direction-change")
                    },
                }
                for kind, expected_event_ids in deterministic_materiality.items():
                    evaluation = evaluations_by_kind.get(kind, {})
                    recorded_ids = set(evaluation.get("event_ids", [])) if isinstance(evaluation, dict) else set()
                    if expected_event_ids and (
                        evaluation.get("outcome") != "applicable"
                        or not expected_event_ids.issubset(recorded_ids)
                    ):
                        self.error(
                            "DEBUG_MODE_MATERIALITY_TRIGGER",
                            f"materiality kind {kind!r} must be applicable and include events {sorted(expected_event_ids)}",
                            record_ref,
                        )

                applicable_kinds = {
                    kind
                    for kind, evaluation in evaluations_by_kind.items()
                    if evaluation.get("outcome") == "applicable"
                }
                unknown_kinds = {
                    kind
                    for kind, evaluation in evaluations_by_kind.items()
                    if evaluation.get("outcome") == "unknown"
                }
                preservation = evidence_decision.get("knowledge_preserved_by")
                preservation = preservation if isinstance(preservation, list) else []
                preserved_kinds: set[str] = set()
                for preservation_index, item in enumerate(preservation):
                    if not isinstance(item, dict):
                        continue
                    kind = str(item.get("materiality_kind", ""))
                    fact_type = str(item.get("fact_type", ""))
                    canonical_source = str(item.get("canonical_source", ""))
                    if kind not in applicable_kinds:
                        self.error(
                            "DEBUG_MODE_PRESERVATION_SCOPE",
                            f"knowledge_preserved_by[{preservation_index}] names non-applicable kind {kind!r}",
                            record_ref,
                        )
                    registry_matches = registry_entries_by_fact_type.get(fact_type, [])
                    if len(registry_matches) != 1:
                        self.error(
                            "DEBUG_MODE_PRESERVATION_REGISTRY",
                            f"fact type {fact_type!r} must resolve exactly once in {registry_relpath}",
                            record_ref,
                        )
                    elif not any(
                        canonical_source in owner_value
                        for owner_value in registry_matches[0].canonical_owner_values
                    ):
                        self.error(
                            "DEBUG_MODE_PRESERVATION_OWNER",
                            f"{canonical_source!r} is not registered as an owner for fact type {fact_type!r}",
                            record_ref,
                        )
                    if not is_target_relative_path(canonical_source) or not self.target_path(canonical_source).is_file():
                        self.error(
                            "DEBUG_MODE_PRESERVATION_SOURCE",
                            f"canonical preservation source must be an existing target file: {canonical_source}",
                            record_ref,
                        )
                    preserved_kinds.add(kind)

                if evidence_status == "skipped":
                    if unknown_kinds:
                        self.error(
                            "DEBUG_MODE_EVIDENCE_SKIP_UNKNOWN",
                            f"skipped evidence decision cannot leave unknown materiality: {sorted(unknown_kinds)}",
                            record_ref,
                        )
                    missing_preservation = sorted(applicable_kinds - preserved_kinds)
                    if missing_preservation:
                        self.error(
                            "DEBUG_MODE_EVIDENCE_SKIP",
                            f"skipped evidence lacks canonical preservation for applicable materiality: {missing_preservation}",
                            record_ref,
                        )
                if status == "completed" and (applicable_kinds or unknown_kinds) and evidence_status not in {"captured", "blocked", "skipped"}:
                    self.error(
                        "DEBUG_MODE_EVIDENCE_DECISION",
                        "material completed Debug work requires captured, blocked, or fully justified skipped evidence",
                        record_ref,
                    )

                claim_validation = final_result.get("claim_validation")
                claim_validation = claim_validation if isinstance(claim_validation, dict) else {}
                claim_fidelity = str(claim_validation.get("fidelity", ""))
                claim_evidence = claim_validation.get("evidence")
                claim_evidence = claim_evidence if isinstance(claim_evidence, list) else []
                claims = claim_validation.get("claims")
                claims = claims if isinstance(claims, list) else []
                if claim_fidelity in {"exact-reproducer", "representative", "partial"} and (
                    not claims or not claim_evidence
                ):
                    self.error(
                        "DEBUG_MODE_CLAIM_EVIDENCE",
                        f"claim fidelity {claim_fidelity!r} requires claims and validation evidence",
                        record_ref,
                    )
                if claim_fidelity == "not-applicable" and implementation_surfaces:
                    self.error(
                        "DEBUG_MODE_CLAIM_FIDELITY",
                        "implemented Debug result cannot mark claim validation not-applicable",
                        record_ref,
                    )
                if status == "completed" and claim_fidelity in {"partial", "unavailable"}:
                    residual = record.get("residual_uncertainty")
                    if not isinstance(residual, list) or not residual:
                        self.error(
                            "DEBUG_MODE_CLAIM_UNCERTAINTY",
                            f"completed result with {claim_fidelity} validation must retain residual uncertainty",
                            record_ref,
                        )

        if record_schema_version >= 6:
            repository_lifecycle = final_result.get("repository_lifecycle")
            repository_lifecycle = (
                repository_lifecycle
                if isinstance(repository_lifecycle, dict)
                else {}
            )
            repository_lifecycle_state = str(
                repository_lifecycle.get("state", "")
            )
            completed_transitions = repository_lifecycle.get(
                "completed_transitions"
            )
            completed_transitions = (
                completed_transitions
                if isinstance(completed_transitions, list)
                else []
            )
            validation_value = final_result.get("validation")
            validation_value = (
                validation_value if isinstance(validation_value, dict) else {}
            )
            validation_items = validation_value.get("results")
            validation_items = (
                validation_items if isinstance(validation_items, list) else []
            )
            class_counts: dict[str, int] = {}
            for validation_index, validation_item in enumerate(validation_items):
                if not isinstance(validation_item, dict):
                    continue
                evidence_class = validation_item.get("evidence_class")
                if isinstance(evidence_class, str) and evidence_class:
                    class_counts[evidence_class] = class_counts.get(evidence_class, 0) + 1
                source = validation_item.get("source")
                revision = validation_item.get("revision")
                if not is_resolved_string(source) or not is_resolved_string(revision):
                    self.error(
                        "DEBUG_MODE_VALIDATION_EVIDENCE",
                        f"validation.results[{validation_index}] must name resolved source and revision",
                        record_ref,
                    )
                if evidence_class in {
                    "ci-verified",
                    "reviewer-verified",
                    "production-verified",
                } and not any(
                    marker in str(source).casefold()
                    for marker in {
                        "ci",
                        "workflow",
                        "actions",
                        "review",
                        "reviewer",
                        "production",
                        "deployment",
                    }
                ):
                    self.error(
                        "DEBUG_MODE_VALIDATION_EVIDENCE_CLASS",
                        f"{evidence_class} validation requires matching source evidence",
                        record_ref,
                    )
            validation_evidence_classes = sorted(class_counts)
            if (
                status == "active"
                and repository_lifecycle_state != "active"
            ):
                self.error(
                    "DEBUG_MODE_REPOSITORY_LIFECYCLE_STATE",
                    "active Debug record requires active repository lifecycle state",
                    record_ref,
                )
            if (
                status in {"completed", "abandoned"}
                and repository_lifecycle_state == "active"
            ):
                self.error(
                    "DEBUG_MODE_REPOSITORY_LIFECYCLE_STATE",
                    "closed Debug record cannot retain active repository lifecycle state",
                    record_ref,
                )
            if (
                status == "completed"
                and lifecycle_completion_scope == "full-task-complete"
                and repository_lifecycle_state != "finalized"
            ):
                self.error(
                    "DEBUG_MODE_REPOSITORY_LIFECYCLE_FINAL",
                    "full-task completed Debug record requires finalized repository lifecycle state",
                    record_ref,
                )
            if (
                repository_lifecycle_state in {"committed", "published"}
                or "commit" in completed_transitions
                or "publish" in completed_transitions
            ) and "commit" not in completed_transitions:
                self.error(
                    "DEBUG_MODE_REPOSITORY_LIFECYCLE_COMMIT",
                    "committed or published lifecycle state requires commit transition evidence",
                    record_ref,
                )
            if (
                (
                    repository_lifecycle_state == "published"
                    or "publish" in completed_transitions
                )
                and not repository_lifecycle.get("publish_evidence")
            ):
                self.error(
                    "DEBUG_MODE_REPOSITORY_LIFECYCLE_PUBLISH",
                    "published lifecycle state requires publish evidence",
                    record_ref,
                )
            if repository_lifecycle_state == "finalized" and (
                "finalization" not in completed_transitions
                or not repository_lifecycle.get("finalization_evidence")
            ):
                self.error(
                    "DEBUG_MODE_REPOSITORY_LIFECYCLE_FINALIZATION",
                    "finalized lifecycle state requires finalization transition evidence",
                    record_ref,
                )

        binding = final_result.get("repository_binding")
        binding_kind, result_revision = self.check_repository_binding(
            binding=binding,
            record_relpath=record_ref,
            code_prefix="DEBUG_MODE",
            record_status=str(status or ""),
            schema_version=record_schema_version,
            implementation_surfaces=implementation_surfaces,
        )
        binding_value = binding if isinstance(binding, dict) else {}
        if record_schema_version >= 6:
            binding_state = binding_value.get("binding_state")
            if (
                repository_lifecycle_state in {"committed", "published"}
                and (
                    binding_kind == "unverified"
                    or binding_state == "provisional"
                )
            ):
                self.error(
                    "DEBUG_MODE_PROVISIONAL_BINDING_AFTER_COMMIT",
                    "committed, published, or finalized Debug lifecycle requires a final reproducible repository binding",
                    record_ref,
                )
            if repository_lifecycle_state == "published" and not final_result.get(
                "upstream_projection"
            ):
                self.error(
                    "DEBUG_MODE_PUBLISHED_BUT_UNFINALIZED",
                    "published Debug lifecycle requires external projection evidence",
                    record_ref,
                )
        if getattr(self, "debug_git_state", False):
            reconcile_debug_git_state(
                self=self,
                record=record,
                record_ref=record_ref,
                status=str(status or ""),
                implementation_surfaces=implementation_surfaces,
                binding=binding_value,
                binding_kind=binding_kind,
                repository_lifecycle_state=repository_lifecycle_state,
            )

        projection = final_result.get("upstream_projection") if isinstance(final_result.get("upstream_projection"), dict) else {}
        projected_paths = projection.get("projected_paths") if isinstance(projection.get("projected_paths"), list) else []
        if projection.get("kind") == "clean-external":
            if projection.get("included_debug_files") is not False:
                self.error("DEBUG_MODE_UPSTREAM_BOUNDARY", "clean external projection must exclude debug files", record_ref)
            if any(isinstance(path, str) and path.startswith(".ai/") for path in projected_paths):
                self.error("DEBUG_MODE_UPSTREAM_PATH", "clean external projection contains an Alatyr support path", record_ref)

        publication = record.get("publication") if isinstance(record.get("publication"), dict) else {}
        if publication.get("included_in_external_patch") is True and "exclude" in str(index.get("external_patch_policy", "")).casefold():
            self.error("DEBUG_MODE_PUBLICATION_SCOPE", "record inclusion contradicts the debug index external-patch policy", record_ref)
        if projection.get("kind") == "clean-external" and publication.get("included_in_external_patch") is not False:
            self.error("DEBUG_MODE_PUBLICATION_SCOPE", "clean external projection must keep the debug record outside the patch", record_ref)

        metric_values = {
            metric_name: metrics.get(metric_name, {}).get("value")
            if isinstance(metrics.get(metric_name), dict)
            else None
            for metric_name in metric_names
        }
        comparisons = {
            "debug_id": record.get("debug_id"),
            "status": status,
            "task_references": task_references,
            "scope_kind": task.get("scope_kind"),
            "scope_id": task.get("scope_id"),
            "task_class": task.get("task_class"),
            "repository_binding_kind": binding_kind,
            "result_revision": result_revision,
            "event_coverage": capture_quality.get("event_coverage"),
            "observer_effect": capture_quality.get("observer_effect"),
            "elapsed_seconds": timing.get("elapsed_seconds", {}).get("value") if isinstance(timing.get("elapsed_seconds"), dict) else None,
            "elapsed_evidence_kind": timing.get("elapsed_seconds", {}).get("evidence_kind") if isinstance(timing.get("elapsed_seconds"), dict) else None,
            "metrics": metric_values,
            "residual_uncertainty": record.get("residual_uncertainty"),
        }
        if index_schema_version in {3, 4}:
            binding_value = binding if isinstance(binding, dict) else {}
            comparisons.update(
                {
                    "record_schema_version": record_schema_version,
                    "repository_binding_state": binding_value.get("binding_state", "legacy"),
                    "engineering_evidence_status": evidence_status,
                }
            )
        if index_schema_version in {4, 5, 6}:
            comparisons.update(
                {
                    "continuation_kind": continuation_kind,
                    "continued_from_debug_id": continued_from_debug_id,
                    "claim_validation_fidelity": claim_fidelity,
                }
            )
        if index_schema_version in {5, 6}:
            comparisons.update(
                {
                    "lifecycle_completion_scope": lifecycle_completion_scope,
                    "covered_phases": covered_phases,
                    "continuation_expected": continuation_expected,
                    "knowledge_candidate_ids": project_candidate_ids,
                }
            )
        if index_schema_version == 6:
            if record_schema_version < 6:
                validation_evidence_classes = ["legacy"]
            comparisons.update(
                {
                    "repository_lifecycle_state": repository_lifecycle_state,
                    "validation_evidence_classes": validation_evidence_classes,
                }
            )
        for field, record_value in comparisons.items():
            index_value = entry.get(field)
            if isinstance(record_value, list) and isinstance(index_value, list):
                matches = sorted(record_value) == sorted(index_value)
            else:
                matches = record_value == index_value
            if not matches:
                self.error("DEBUG_MODE_INDEX_DRIFT", f"{label}.{field} differs from record {debug_id}", index_relpath)

        self.info(
            "DEBUG_MODE_CHECKED",
            f"checked Debug Mode record {debug_id}; structural validation cannot prove event completeness, attribution, engineering quality, or reduced supervision",
            record_ref,
        )

    implementation_debug_ids: set[str] = set()
    for candidate_id, candidate_record in checked_debug_records.items():
        candidate_final = candidate_record.get("final_result")
        candidate_final = candidate_final if isinstance(candidate_final, dict) else {}
        candidate_lifecycle = candidate_final.get("lifecycle_coverage")
        candidate_lifecycle = (
            candidate_lifecycle
            if isinstance(candidate_lifecycle, dict)
            else {}
        )
        candidate_phases = candidate_lifecycle.get("covered_phases")
        if isinstance(candidate_phases, list) and "implementation" in candidate_phases:
            implementation_debug_ids.add(candidate_id)
    for debug_id, record in checked_debug_records.items():
        task_value = record.get("task") if isinstance(record.get("task"), dict) else {}
        debug_refs = set(
            value
            for value in task_value.get("references", [])
            if isinstance(value, str)
        )
        final_value = (
            record.get("final_result")
            if isinstance(record.get("final_result"), dict)
            else {}
        )
        linked_ids = final_value.get("engineering_evidence_ids")
        linked_ids = linked_ids if isinstance(linked_ids, list) else []
        for evidence_id in linked_ids:
            entries = engineering_evidence_entries.get(str(evidence_id), [])
            if len(entries) != 1:
                continue
            evidence_entry = entries[0]
            evidence_ref = evidence_entry.get("record")
            if not isinstance(evidence_ref, str) or not is_target_relative_path(
                evidence_ref
            ):
                continue
            evidence_record = self.load_json_object(
                self.target_path(evidence_ref), "DEBUG_MODE_ENGINEERING_EVIDENCE"
            )
            if not isinstance(evidence_record, dict):
                continue
            evidence_schema_version = evidence_record.get("schema_version")
            related_records = evidence_record.get("related_records")
            related_records = (
                related_records if isinstance(related_records, dict) else {}
            )
            evidence_debug_ids = related_records.get("debug_session_ids")
            if isinstance(evidence_schema_version, int) and evidence_schema_version >= 3:
                if not isinstance(evidence_debug_ids, list) or debug_id not in evidence_debug_ids:
                    self.error(
                        "DEBUG_MODE_ENGINEERING_EVIDENCE_RECIPROCITY",
                        f"engineering evidence {evidence_id} does not link back to Debug record {debug_id}",
                        evidence_ref,
                    )
                evidence_task = evidence_record.get("task")
                evidence_task = evidence_task if isinstance(evidence_task, dict) else {}
                evidence_refs = set(
                    value
                    for value in evidence_task.get("references", [])
                    if isinstance(value, str)
                )
                if debug_refs and evidence_refs and not debug_refs & evidence_refs:
                    self.error(
                        "DEBUG_MODE_ENGINEERING_EVIDENCE_LINEAGE",
                        f"engineering evidence {evidence_id} does not share task lineage with Debug record {debug_id}",
                        evidence_ref,
                    )

        lifecycle = final_value.get("lifecycle_coverage")
        lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
        if (
            isinstance(record.get("schema_version"), int)
            and record.get("schema_version") >= 5
            and record.get("status") == "completed"
            and lifecycle.get("completion_scope") == "phase-complete"
            and lifecycle.get("continuation_expected") is True
            and "implementation" not in lifecycle.get("covered_phases", [])
        ):
            def continues_from(candidate_id: str, ancestor_id: str) -> bool:
                visited: set[str] = set()
                current_id = candidate_id
                while current_id in indexed_entries_by_id and current_id not in visited:
                    visited.add(current_id)
                    current_entry = indexed_entries_by_id[current_id]
                    if current_entry.get("continuation_kind") != "continued":
                        return False
                    previous_id = current_entry.get("continued_from_debug_id")
                    if previous_id == ancestor_id:
                        return True
                    if not isinstance(previous_id, str):
                        return False
                    current_id = previous_id
                return False

            has_implementation_continuation = any(
                candidate_id in implementation_debug_ids
                and continues_from(candidate_id, debug_id)
                for candidate_id in indexed_entries_by_id
            )
            if not has_implementation_continuation:
                for evidence_entries in engineering_evidence_entries.values():
                    for evidence_entry in evidence_entries:
                        evidence_refs = set(
                            value
                            for value in evidence_entry.get("task_references", [])
                            if isinstance(value, str)
                        )
                        if debug_refs & evidence_refs:
                            self.warn(
                                "DEBUG_MODE_IMPLEMENTATION_CONTINUATION_MISSING",
                                f"later engineering evidence shares task lineage with phase-complete Debug record {debug_id}, but no implementation continuation is indexed",
                                index_relpath,
                            )
                            has_implementation_continuation = True
                            break
                    if has_implementation_continuation:
                        break
