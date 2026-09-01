"""Durable engineering-evidence target validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from target_adapter_validation.contract_compatibility import (
    artifact_compatibility,
    contract_compatibility,
    minimum_index_version,
)
from target_adapter_validation.domain import DomainValidationHost
from target_adapter_validation.values import is_resolved_string
from target_validation_support import (
    ManifestData,
    dotted,
    is_target_relative_path,
)


ROOT = Path(__file__).resolve().parents[2]
ENGINEERING_EVIDENCE_SCHEMA = (
    ROOT / "schemas" / "alatyr-engineering-evidence.schema.json"
)
ENGINEERING_CONTRACT = contract_compatibility("engineering-evidence")
ENGINEERING_INDEX = artifact_compatibility("engineering-evidence", "index")
ENGINEERING_RECORD = artifact_compatibility("engineering-evidence", "record")


def validate_engineering_evidence(self: DomainValidationHost, manifest: ManifestData | None) -> None:
    index_relpath = ".ai/project/engineering-evidence/index.json"
    expected_manifest = {
        ("source_of_truth", "engineering_evidence_index"): index_relpath,
        ("engineering_evidence", "index"): index_relpath,
        ("engineering_evidence", "records"): ".ai/project/engineering-evidence/records",
        ("engineering_evidence", "flow"): ".ai/assistant/flows/engineering-evidence-capture.flow.md",
        ("engineering_evidence", "gate"): ".ai/assistant/gates/engineering-evidence.md",
        ("engineering_evidence", "machine_template"): ".ai/assistant/templates/engineering-evidence-record.json",
        ("operations", "engineering_evidence_capture"): ".ai/assistant/flows/engineering-evidence-capture.flow.md",
        ("operations", "engineering_evidence_record"): ".ai/assistant/templates/engineering-evidence-record.json",
    }
    if manifest is not None:
        for key, expected in expected_manifest.items():
            scalar = manifest.scalars.get(key)
            if scalar is None or scalar.value != expected:
                self.error(
                    "ENGINEERING_EVIDENCE_MANIFEST_PATH",
                    f"{dotted(key)} must be {expected}",
                    ".ai/alatyr.yaml",
                )
        contract = manifest.scalars.get(("engineering_evidence", "contract_version"))
        expected_contract_version = str(
            ENGINEERING_CONTRACT["manifest_contract_version"]
        )
        if contract is None or contract.value != expected_contract_version:
            self.error(
                "ENGINEERING_EVIDENCE_CONTRACT_VERSION",
                "engineering_evidence.contract_version must be "
                f"{expected_contract_version}",
                ".ai/alatyr.yaml",
            )

    template_relpath = ".ai/assistant/templates/engineering-evidence-record.json"
    template = self.load_json_object(self.target_path(template_relpath), "ENGINEERING_EVIDENCE_TEMPLATE")
    if template is not None:
        template_binding = template.get("repository_binding")
        if template.get("schema_version") != ENGINEERING_RECORD["current"]:
            self.error("ENGINEERING_EVIDENCE_TEMPLATE_VERSION", f"authoring template schema_version must be {ENGINEERING_RECORD['current']}", template_relpath)
        if not isinstance(template_binding, dict) or not {"binding_state", "prior_bindings"}.issubset(template_binding):
            self.error("ENGINEERING_EVIDENCE_TEMPLATE_BINDING", "version-3 authoring template must expose binding_state and prior_bindings", template_relpath)
        related_records = template.get("related_records")
        if not isinstance(related_records, dict) or "debug_session_ids" not in related_records:
            self.error("ENGINEERING_EVIDENCE_TEMPLATE_DEBUG_LINK", "version-3 authoring template must expose Debug session lineage", template_relpath)

    index = self.load_json_object(
        self.target_path(index_relpath), "ENGINEERING_EVIDENCE_INDEX"
    )
    if index is None:
        return
    index_schema_version = index.get("schema_version")
    supported_index_versions = set(ENGINEERING_INDEX["supported"])
    if index_schema_version not in supported_index_versions:
        supported = ", ".join(str(value) for value in sorted(supported_index_versions))
        self.error("ENGINEERING_EVIDENCE_INDEX_SCHEMA", f"schema_version must be one of: {supported}", index_relpath)
    elif index_schema_version in set(ENGINEERING_INDEX["migration_limited"]):
        self.warn("ENGINEERING_EVIDENCE_INDEX_LEGACY", "schema-version-2 index omits record contract and binding-state projections", index_relpath)
    if index.get("index_kind") != "target-engineering-evidence-index":
        self.error(
            "ENGINEERING_EVIDENCE_INDEX_KIND",
            "index_kind must be target-engineering-evidence-index",
            index_relpath,
        )
    unresolved_report = self.warn if self.allow_placeholders else self.error
    for field in [
        "project",
        "owner",
        "storage_mode",
        "external_patch_policy",
        "retention_policy",
        "redaction_policy",
    ]:
        value = index.get(field)
        if not isinstance(value, str) or not value.strip():
            self.error(
                "ENGINEERING_EVIDENCE_INDEX_METADATA",
                f"{field} must be a non-empty string",
                index_relpath,
            )
        elif not is_resolved_string(value):
            unresolved_report(
                "ENGINEERING_EVIDENCE_INDEX_METADATA_UNRESOLVED",
                f"{field} is unresolved",
                index_relpath,
            )

    self.check_policy_readme_projection(
        index=index,
        readme_relpath=".ai/project/engineering-evidence/README.md",
        fields={
            "Owner": "owner",
            "Storage mode": "storage_mode",
            "External patch policy": "external_patch_policy",
            "Retention policy": "retention_policy",
            "Redaction policy": "redaction_policy",
        },
        code_prefix="ENGINEERING_EVIDENCE_POLICY",
    )
    if manifest is not None:
        for manifest_field, index_field in {
            "storage_mode": "storage_mode",
            "external_patch_policy": "external_patch_policy",
            "retention_policy": "retention_policy",
            "redaction_policy": "redaction_policy",
        }.items():
            scalar = manifest.scalars.get(("engineering_evidence", manifest_field))
            index_value = index.get(index_field)
            if scalar is None or scalar.value != index_value:
                self.error(
                    "ENGINEERING_EVIDENCE_MANIFEST_POLICY_DRIFT",
                    f"engineering_evidence.{manifest_field} differs from index.{index_field}",
                    ".ai/alatyr.yaml",
                )

    records = index.get("records")
    if not isinstance(records, list):
        self.error(
            "ENGINEERING_EVIDENCE_INDEX_RECORDS",
            "records must be a list",
            index_relpath,
        )
        return

    try:
        schema = json.loads(ENGINEERING_EVIDENCE_SCHEMA.read_text(encoding="utf-8"))
        schema_validator = jsonschema.Draft7Validator(schema)
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        self.error(
            "ENGINEERING_EVIDENCE_SOURCE_SCHEMA",
            f"cannot load engineering-evidence schema: {exc}",
        )
        return

    debug_entries_by_id: dict[str, list[dict[str, Any]]] = {}
    debug_index_path = self.target_path(".ai/project/debug/index.json")
    if debug_index_path.is_file():
        try:
            debug_index = json.loads(debug_index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            debug_index = None
        if isinstance(debug_index, dict):
            for debug_entry in debug_index.get("records", []):
                if not isinstance(debug_entry, dict):
                    continue
                indexed_debug_id = debug_entry.get("debug_id")
                if isinstance(indexed_debug_id, str) and indexed_debug_id:
                    debug_entries_by_id.setdefault(indexed_debug_id, []).append(
                        debug_entry
                    )

    required_index_fields = {
        "evidence_id",
        "status",
        "record",
        "task_references",
        "changed_fact_ids",
        "architecture_areas",
        "repository_binding_kind",
        "result_revision",
        "residual_uncertainty",
    }
    if index_schema_version in {3, 4}:
        required_index_fields.update({"record_schema_version", "repository_binding_state"})
    if index_schema_version == 4:
        required_index_fields.add("debug_session_ids")
    seen_ids: set[str] = set()
    seen_records: set[str] = set()
    for entry_index, entry in enumerate(records):
        label = f"records[{entry_index}]"
        if not isinstance(entry, dict):
            self.error("ENGINEERING_EVIDENCE_INDEX_ENTRY", f"{label} must be an object", index_relpath)
            continue
        missing = sorted(required_index_fields - set(entry))
        if missing:
            self.error("ENGINEERING_EVIDENCE_INDEX_FIELD", f"{label} missing {missing}", index_relpath)
            continue
        evidence_id = entry.get("evidence_id")
        if not is_resolved_string(evidence_id):
            self.error("ENGINEERING_EVIDENCE_INDEX_ID", f"{label}.evidence_id must be resolved", index_relpath)
            continue
        if evidence_id in seen_ids:
            self.error("ENGINEERING_EVIDENCE_INDEX_DUPLICATE", f"duplicate evidence_id {evidence_id}", index_relpath)
        seen_ids.add(evidence_id)
        if entry.get("status") not in {"draft", "validated", "superseded", "blocked"}:
            self.error("ENGINEERING_EVIDENCE_INDEX_FIELD", f"{label}.status is invalid", index_relpath)
        if entry.get("repository_binding_kind") not in {
            "commit",
            "pull-request",
            "tree",
            "selected-file-snapshot",
            "unverified",
        }:
            self.error(
                "ENGINEERING_EVIDENCE_INDEX_FIELD",
                f"{label}.repository_binding_kind is invalid",
                index_relpath,
            )
        if not is_resolved_string(entry.get("result_revision")):
            self.error(
                "ENGINEERING_EVIDENCE_INDEX_FIELD",
                f"{label}.result_revision must be resolved",
                index_relpath,
            )
        for field in ["task_references", "changed_fact_ids", "architecture_areas", "residual_uncertainty"]:
            values = entry.get(field)
            if not isinstance(values, list) or not all(is_resolved_string(value) for value in values):
                self.error("ENGINEERING_EVIDENCE_INDEX_LIST", f"{label}.{field} must be a resolved string list", index_relpath)
        if not entry.get("task_references"):
            self.error(
                "ENGINEERING_EVIDENCE_TASK_REFERENCE",
                f"{label} requires a task or issue reference",
                index_relpath,
            )
        for field in ["changed_fact_ids", "architecture_areas"]:
            if not entry.get(field):
                self.error(
                    "ENGINEERING_EVIDENCE_INDEX_LIST",
                    f"{label}.{field} must not be empty",
                    index_relpath,
                )

        record_ref = entry.get("record")
        if not is_resolved_string(record_ref):
            self.error("ENGINEERING_EVIDENCE_INDEX_RECORD", f"{label}.record must be resolved", index_relpath)
            continue
        if record_ref.startswith(("https://", "http://", "external:")):
            self.warn(
                "ENGINEERING_EVIDENCE_EXTERNAL_RECORD_UNCHECKED",
                f"{evidence_id} uses an external record that this repository validator cannot inspect",
                index_relpath,
            )
            continue
        if not is_target_relative_path(record_ref):
            self.error("ENGINEERING_EVIDENCE_RECORD_PATH", f"record path must be target-relative: {record_ref}", index_relpath)
            continue
        if record_ref in seen_records:
            self.error("ENGINEERING_EVIDENCE_RECORD_DUPLICATE", f"record path is reused: {record_ref}", index_relpath)
        seen_records.add(record_ref)
        if not record_ref.startswith(".ai/project/engineering-evidence/records/"):
            self.error("ENGINEERING_EVIDENCE_RECORD_LOCATION", "local records must stay under the target engineering-evidence records directory", record_ref)
        record_path = self.target_path(record_ref)
        record = self.load_json_object(record_path, "ENGINEERING_EVIDENCE_RECORD")
        if record is None:
            continue

        for schema_error in sorted(
            schema_validator.iter_errors(record),
            key=lambda item: list(item.absolute_path),
        ):
            location = ".".join(str(item) for item in schema_error.absolute_path) or "root"
            self.error(
                "ENGINEERING_EVIDENCE_RECORD_SCHEMA",
                f"{location}: {schema_error.message}",
                record_ref,
            )
        record_schema_version = record.get("schema_version")
        required_index_version = minimum_index_version(
            "engineering-evidence", record_schema_version
        )
        if required_index_version is None:
            self.error(
                "ENGINEERING_EVIDENCE_INDEX_RECORD_VERSION",
                "record schema_version must be one of: "
                + ", ".join(
                    str(value) for value in ENGINEERING_RECORD["supported"]
                ),
                record_ref,
            )
        elif (
            not isinstance(index_schema_version, int)
            or index_schema_version < required_index_version
        ):
            self.error(
                "ENGINEERING_EVIDENCE_INDEX_RECORD_VERSION",
                f"schema-version-{record_schema_version} record requires index schema version {required_index_version} or later",
                index_relpath,
            )

        forbidden_keys = {
            "raw_chat",
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
                "ENGINEERING_EVIDENCE_PROHIBITED_CONTENT_FIELD",
                f"record contains prohibited raw-content fields: {forbidden}",
                record_ref,
            )

        privacy = record.get("privacy")
        if isinstance(privacy, dict):
            for field in [
                "raw_chat_stored",
                "chain_of_thought_stored",
                "secrets_stored",
                "unrelated_session_history_stored",
            ]:
                if privacy.get(field) is not False:
                    self.error(
                        "ENGINEERING_EVIDENCE_PRIVACY",
                        f"privacy.{field} must be false",
                        record_ref,
                    )

        def resolved_list(container: Any, field: str, *, required: bool = True) -> list[str]:
            values = container.get(field) if isinstance(container, dict) else None
            if not isinstance(values, list) or (required and not values) or not all(is_resolved_string(value) for value in values):
                self.error("ENGINEERING_EVIDENCE_RECORD_LIST", f"{field} must be a {'non-empty ' if required else ''}resolved string list", record_ref)
                return []
            return values

        task = record.get("task")
        task_refs = resolved_list(task, "references")
        related_records_value = record.get("related_records")
        related_records_value = (
            related_records_value
            if isinstance(related_records_value, dict)
            else {}
        )
        debug_session_ids = related_records_value.get("debug_session_ids")
        if record.get("schema_version") == 3:
            debug_session_ids = resolved_list(
                related_records_value, "debug_session_ids", required=False
            )
            for debug_session_id in debug_session_ids:
                debug_entries = debug_entries_by_id.get(debug_session_id, [])
                if len(debug_entries) != 1:
                    self.error(
                        "ENGINEERING_EVIDENCE_DEBUG_REFERENCE",
                        f"Debug session {debug_session_id} resolves {len(debug_entries)} times; expected exactly once",
                        record_ref,
                    )
                    continue
                debug_entry = debug_entries[0]
                debug_record_ref = debug_entry.get("record")
                if not isinstance(debug_record_ref, str) or not is_target_relative_path(
                    debug_record_ref
                ):
                    self.error(
                        "ENGINEERING_EVIDENCE_DEBUG_REFERENCE",
                        f"Debug session {debug_session_id} has no inspectable target record",
                        record_ref,
                    )
                    continue
                debug_record = self.load_json_object(
                    self.target_path(debug_record_ref),
                    "ENGINEERING_EVIDENCE_DEBUG_RECORD",
                )
                if not isinstance(debug_record, dict):
                    continue
                debug_final = debug_record.get("final_result")
                debug_final = debug_final if isinstance(debug_final, dict) else {}
                debug_evidence_ids = debug_final.get("engineering_evidence_ids")
                if not isinstance(debug_evidence_ids, list) or evidence_id not in debug_evidence_ids:
                    self.error(
                        "ENGINEERING_EVIDENCE_DEBUG_RECIPROCITY",
                        f"Debug session {debug_session_id} does not link back to engineering evidence {evidence_id}",
                        record_ref,
                    )
                debug_task = debug_record.get("task")
                debug_task = debug_task if isinstance(debug_task, dict) else {}
                debug_task_refs = set(
                    value
                    for value in debug_task.get("references", [])
                    if isinstance(value, str)
                )
                if debug_task_refs and not debug_task_refs & set(task_refs):
                    self.error(
                        "ENGINEERING_EVIDENCE_DEBUG_LINEAGE",
                        f"Debug session {debug_session_id} does not share task lineage with engineering evidence {evidence_id}",
                        record_ref,
                    )
        invariants = record.get("invariants")
        if isinstance(invariants, list):
            for invariant_index, invariant in enumerate(invariants):
                invariant_label = f"invariants[{invariant_index}]"
                if not isinstance(invariant, dict):
                    self.error("ENGINEERING_EVIDENCE_INVARIANT", f"{invariant_label} must be an object", record_ref)
                    continue
                for field in ["statement", "status", "canonical_owner"]:
                    if not is_resolved_string(invariant.get(field)):
                        self.error("ENGINEERING_EVIDENCE_INVARIANT", f"{invariant_label}.{field} must be resolved", record_ref)
                if invariant.get("status") not in {"observed", "proposed", "accepted", "unknown"}:
                    self.error("ENGINEERING_EVIDENCE_INVARIANT_STATUS", f"{invariant_label}.status is invalid", record_ref)
                resolved_list(invariant, "evidence")

        hypotheses = record.get("hypotheses")
        if isinstance(hypotheses, list):
            for hypothesis_index, hypothesis in enumerate(hypotheses):
                hypothesis_label = f"hypotheses[{hypothesis_index}]"
                if not isinstance(hypothesis, dict):
                    self.error("ENGINEERING_EVIDENCE_HYPOTHESIS", f"{hypothesis_label} must be an object", record_ref)
                    continue
                for field in ["statement", "outcome", "decision_impact"]:
                    if not is_resolved_string(hypothesis.get(field)):
                        self.error("ENGINEERING_EVIDENCE_HYPOTHESIS", f"{hypothesis_label}.{field} must be resolved", record_ref)
                if hypothesis.get("outcome") not in {"confirmed", "rejected", "unresolved"}:
                    self.error("ENGINEERING_EVIDENCE_HYPOTHESIS_OUTCOME", f"{hypothesis_label}.outcome is invalid", record_ref)
                resolved_list(hypothesis, "evidence")

        root_cause = record.get("root_cause")
        solution = record.get("chosen_solution")
        for container, fields, code in [
            (root_cause, ["statement"], "ENGINEERING_EVIDENCE_ROOT_CAUSE"),
            (solution, ["summary", "rationale"], "ENGINEERING_EVIDENCE_SOLUTION"),
        ]:
            for field in fields:
                if not isinstance(container, dict) or not is_resolved_string(container.get(field)):
                    self.error(code, f"{field} must be resolved", record_ref)
        resolved_list(root_cause, "evidence")

        alternatives = solution.get("material_rejected_alternatives") if isinstance(solution, dict) else None
        if not isinstance(alternatives, list):
            self.error("ENGINEERING_EVIDENCE_ALTERNATIVES", "material_rejected_alternatives must be a list", record_ref)
        else:
            for alternative_index, alternative in enumerate(alternatives):
                if not isinstance(alternative, dict) or not all(
                    is_resolved_string(alternative.get(field)) for field in ["alternative", "reason"]
                ):
                    self.error("ENGINEERING_EVIDENCE_ALTERNATIVES", f"material_rejected_alternatives[{alternative_index}] must contain resolved alternative and reason", record_ref)

        matrix = record.get("regression_matrix")
        if isinstance(matrix, list):
            for case_index, case in enumerate(matrix):
                if not isinstance(case, dict) or not all(
                    is_resolved_string(case.get(field))
                    for field in ["case", "protects", "expected_result", "validation_evidence"]
                ):
                    self.error("ENGINEERING_EVIDENCE_REGRESSION", f"regression_matrix[{case_index}] must explain case, protected invariant/risk, expected result, and evidence", record_ref)

        impact_value = record.get("impact") if isinstance(record.get("impact"), dict) else {}
        implementation_surfaces = [
            value
            for value in impact_value.get("code_and_test_surfaces", [])
            if isinstance(value, str)
        ]
        binding_kind, result_revision = self.check_repository_binding(
            binding=record.get("repository_binding"),
            record_relpath=record_ref,
            code_prefix="ENGINEERING_EVIDENCE",
            record_status=str(record.get("status", "")),
            schema_version=record.get("schema_version") if isinstance(record.get("schema_version"), int) else 1,
            implementation_surfaces=implementation_surfaces,
        )

        publication = record.get("publication")
        if (
            isinstance(publication, dict)
            and publication.get("included_in_external_patch") is True
            and isinstance(index.get("external_patch_policy"), str)
            and "exclude" in index["external_patch_policy"].casefold()
        ):
            self.error("ENGINEERING_EVIDENCE_PUBLICATION_SCOPE", "record inclusion contradicts the index external-patch policy", record_ref)

        impact = record.get("impact")
        changed_facts = resolved_list(impact, "changed_fact_ids")
        areas = [
            area.get("area")
            for area in record.get("affected_architecture", [])
            if isinstance(area, dict) and is_resolved_string(area.get("area"))
        ]
        residual = record.get("residual_uncertainty")
        residual = residual if isinstance(residual, list) else []
        comparisons = {
            "evidence_id": record.get("evidence_id"),
            "status": record.get("status"),
            "task_references": task_refs,
            "changed_fact_ids": changed_facts,
            "architecture_areas": areas,
            "repository_binding_kind": binding_kind,
            "result_revision": result_revision,
            "residual_uncertainty": residual,
        }
        if isinstance(index_schema_version, int) and index_schema_version >= 3:
            binding_value = record.get("repository_binding") if isinstance(record.get("repository_binding"), dict) else {}
            comparisons.update(
                {
                    "record_schema_version": record.get("schema_version"),
                    "repository_binding_state": binding_value.get("binding_state", "legacy"),
                }
            )
        if index_schema_version == 4:
            related_records = record.get("related_records") if isinstance(record.get("related_records"), dict) else {}
            comparisons["debug_session_ids"] = related_records.get("debug_session_ids", [])
        for field, record_value in comparisons.items():
            index_value = entry.get(field)
            if isinstance(record_value, list) and isinstance(index_value, list):
                matches = sorted(record_value) == sorted(index_value)
            else:
                matches = record_value == index_value
            if not matches:
                self.error("ENGINEERING_EVIDENCE_INDEX_DRIFT", f"{label}.{field} differs from record {evidence_id}", index_relpath)

        self.info(
            "ENGINEERING_EVIDENCE_CHECKED",
            f"checked durable engineering evidence {evidence_id}; structural validation does not prove invariant, root-cause, solution, or regression correctness",
            record_ref,
        )
