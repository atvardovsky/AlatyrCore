"""Validate target-owned project vocabulary support."""

from __future__ import annotations

from typing import Any
from target_validation_support import ManifestData, dotted
from target_adapter_validation.values import is_resolved_string

from target_adapter_validation.capability import (
    CapabilityValidationContext,
    FunctionCapabilityModule,
)


def validate_project_vocabulary(
    context: CapabilityValidationContext,
    manifest: ManifestData | None,
) -> None:
    if not context.module_validation_enabled(
        "project-vocabulary",
        "VOCABULARY_MODULE_UNDECLARED",
        "VOCABULARY_MODULE_STATE_MISSING",
        "project-vocabulary",
    ):
        return

    required_paths = [
        ".ai/project/vocabulary/README.md",
        ".ai/project/vocabulary/catalog.json",
        ".ai/project/vocabulary/terms.json",
        ".ai/project/vocabulary/data-dictionary-links.json",
        ".ai/assistant/context/intents/vocabulary-request.json",
        ".ai/assistant/flows/project-vocabulary.flow.md",
        ".ai/assistant/templates/vocabulary-term-review.md",
        ".ai/assistant/skills/project-vocabulary/SKILL.md",
        ".ai/framework/project-vocabulary.md",
    ]
    missing = False
    for relpath in required_paths:
        if not context.target_path(relpath).is_file():
            missing = True
            context.error(
                "VOCABULARY_REQUIRED_FILE_MISSING",
                "enabled project-vocabulary module is missing a contract",
                relpath,
            )
    if missing:
        return

    if manifest is not None:
        expected_manifest = {
            ("source_of_truth", "vocabulary_index"): required_paths[0],
            ("source_of_truth", "vocabulary_catalog"): required_paths[1],
            ("source_of_truth", "vocabulary_terms"): required_paths[2],
            ("source_of_truth", "vocabulary_data_dictionary_links"): required_paths[3],
            ("operations", "project_vocabulary"): required_paths[5],
            ("operations", "vocabulary_term_review"): required_paths[6],
            ("project_vocabulary", "catalog"): required_paths[1],
            ("project_vocabulary", "terms"): required_paths[2],
            ("project_vocabulary", "data_dictionary_links"): required_paths[3],
            ("project_vocabulary", "intent"): required_paths[4],
            ("project_vocabulary", "flow"): required_paths[5],
            ("project_vocabulary", "term_review"): required_paths[6],
            ("project_vocabulary", "skill"): required_paths[7],
        }
        for key, expected in expected_manifest.items():
            scalar = manifest.scalars.get(key)
            if scalar is None or scalar.value != expected:
                context.error(
                    "VOCABULARY_MANIFEST_PATH",
                    f"{dotted(key)} must be {expected} when project vocabulary is enabled",
                    ".ai/alatyr.yaml",
                )

    concrete = is_resolved_string

    def string_list(
        value: Any, label: str, relpath: str, *, non_empty: bool = True
    ) -> list[str]:
        if not isinstance(value, list) or (non_empty and not value) or not all(
            isinstance(item, str) and item for item in value
        ):
            context.error(
                "VOCABULARY_STRING_LIST",
                f"{label} must contain strings" + (" and be non-empty" if non_empty else ""),
                relpath,
            )
            return []
        return value

    catalog_relpath = required_paths[1]
    terms_relpath = required_paths[2]
    links_relpath = required_paths[3]
    catalog = context.load_json_object(
        context.target_path(catalog_relpath), "VOCABULARY_CATALOG"
    )
    term_data = context.load_json_object(
        context.target_path(terms_relpath), "VOCABULARY_TERMS"
    )
    link_data = context.load_json_object(
        context.target_path(links_relpath), "VOCABULARY_LINKS"
    )
    if catalog is None or term_data is None or link_data is None:
        return

    if catalog.get("schema_version") != 1:
        context.error("VOCABULARY_CATALOG_SCHEMA", "schema_version should be 1", catalog_relpath)
    if catalog.get("catalog_kind") != "target-project-vocabulary-catalog":
        context.error("VOCABULARY_CATALOG_KIND", "catalog_kind is invalid", catalog_relpath)
    expected_catalog = {
        "human_index": required_paths[0],
        "terms": required_paths[2],
        "data_dictionary_links": required_paths[3],
    }
    for field, expected in expected_catalog.items():
        if catalog.get(field) != expected:
            context.error("VOCABULARY_CATALOG_PATH", f"{field} must be {expected}", catalog_relpath)
    for field in [
        "project", "module_state", "vocabulary_owner",
        "term_decision_authority", "normalization_policy",
        "last_reviewed", "evidence_revision",
    ]:
        if not concrete(catalog.get(field)):
            context.error(
                "VOCABULARY_ENABLED_METADATA_UNRESOLVED",
                f"enabled project vocabulary requires resolved {field}",
                catalog_relpath,
            )

    if term_data.get("schema_version") != 1:
        context.error("VOCABULARY_TERM_SCHEMA", "schema_version should be 1", terms_relpath)
    if term_data.get("record_kind") != "target-project-vocabulary-terms":
        context.error("VOCABULARY_TERM_KIND", "record_kind is invalid", terms_relpath)
    valid_states = {
        "observed", "proposed", "accepted", "deprecated", "contradicted", "unknown"
    }
    required_term_fields = {
        "id", "canonical_term", "normalized_term", "kind", "state",
        "domains", "usage_scopes", "audiences", "definition",
        "non_meanings", "aliases", "acronyms", "acronym_expansions",
        "discouraged_synonyms", "replacement_term_id", "owner",
        "decision_authority", "canonical_sources", "evidence",
        "related_term_ids", "data_dictionary_refs", "examples",
        "sensitivity", "validation", "last_verified_revision",
        "contradictions", "known_gaps",
    }
    terms = term_data.get("terms")
    if not isinstance(terms, list) or not terms:
        context.error("VOCABULARY_TERMS_EMPTY", "enabled module requires term records", terms_relpath)
        terms = []
    term_ids: set[str] = set()
    term_by_id: dict[str, dict[str, Any]] = {}
    accepted_count = 0
    accepted_lookup: dict[tuple[str, tuple[str, ...]], str] = {}
    pending_term_refs: list[tuple[str, str, str]] = []
    pending_data_refs: list[tuple[str, str]] = []
    for index, term in enumerate(terms):
        label = f"terms[{index}]"
        if not isinstance(term, dict):
            context.error("VOCABULARY_TERM_SHAPE", f"{label} must be an object", terms_relpath)
            continue
        missing_fields = sorted(required_term_fields - set(term))
        if missing_fields:
            context.error("VOCABULARY_TERM_FIELDS", f"{label} missing {missing_fields}", terms_relpath)
        term_id = term.get("id")
        if concrete(term_id):
            if term_id in term_ids:
                context.error("VOCABULARY_TERM_ID_DUPLICATE", f"duplicate term ID {term_id}", terms_relpath)
            term_ids.add(term_id)
            term_by_id[term_id] = term
        state = term.get("state")
        if not concrete(state) or state not in valid_states:
            context.error("VOCABULARY_TERM_STATE", f"{label}.state is invalid or unresolved", terms_relpath)
        domains = string_list(term.get("domains"), f"{label}.domains", terms_relpath)
        aliases = string_list(term.get("aliases"), f"{label}.aliases", terms_relpath, non_empty=False)
        acronyms = string_list(term.get("acronyms"), f"{label}.acronyms", terms_relpath, non_empty=False)
        string_list(term.get("acronym_expansions"), f"{label}.acronym_expansions", terms_relpath, non_empty=False)
        related = string_list(term.get("related_term_ids"), f"{label}.related_term_ids", terms_relpath, non_empty=False)
        data_refs = string_list(term.get("data_dictionary_refs"), f"{label}.data_dictionary_refs", terms_relpath, non_empty=False)
        for ref in related:
            if concrete(ref) and concrete(term_id):
                pending_term_refs.append((term_id, ref, "related_term_ids"))
        for ref in data_refs:
            if concrete(ref) and concrete(term_id):
                pending_data_refs.append((term_id, ref))
        if state == "accepted":
            accepted_count += 1
            for field in [
                "id", "canonical_term", "normalized_term", "kind",
                "definition", "owner", "decision_authority", "sensitivity",
                "last_verified_revision",
            ]:
                if not concrete(term.get(field)):
                    context.error("VOCABULARY_ACCEPTED_UNRESOLVED", f"{label}.{field} must be resolved", terms_relpath)
            canonical_sources = string_list(term.get("canonical_sources"), f"{label}.canonical_sources", terms_relpath)
            validation = string_list(term.get("validation"), f"{label}.validation", terms_relpath)
            for values, field in [
                (domains, "domains"),
                (canonical_sources, "canonical_sources"),
                (validation, "validation"),
            ]:
                if not any(concrete(value) for value in values):
                    context.error("VOCABULARY_ACCEPTED_UNRESOLVED", f"{label}.{field} needs concrete values", terms_relpath)
            lookup_values = [term.get("normalized_term"), *aliases, *acronyms]
            domain_key = tuple(sorted(value.casefold() for value in domains if concrete(value)))
            for lookup in lookup_values:
                if not concrete(lookup) or not concrete(term_id):
                    continue
                key = (lookup.casefold(), domain_key)
                prior = accepted_lookup.get(key)
                if prior is not None and prior != term_id:
                    context.error(
                        "VOCABULARY_ACCEPTED_AMBIGUITY",
                        f"accepted terms {prior} and {term_id} share lookup {lookup} in the same domains",
                        terms_relpath,
                    )
                else:
                    accepted_lookup[key] = term_id
    if accepted_count == 0:
        context.error(
            "VOCABULARY_NO_ACCEPTED_TERM",
            "enabled project-vocabulary module requires at least one accepted term",
            terms_relpath,
        )
    for source_id, ref, field in pending_term_refs:
        if ref not in term_ids:
            context.error("VOCABULARY_TERM_REFERENCE", f"{source_id}.{field} references unknown term {ref}", terms_relpath)

    catalog_entries = catalog.get("entries")
    if not isinstance(catalog_entries, list) or not catalog_entries:
        context.error("VOCABULARY_CATALOG_EMPTY", "enabled catalog requires entries", catalog_relpath)
    else:
        catalog_ids: set[str] = set()
        for index, entry in enumerate(catalog_entries):
            label = f"entries[{index}]"
            if not isinstance(entry, dict):
                context.error("VOCABULARY_CATALOG_ENTRY_SHAPE", f"{label} must be an object", catalog_relpath)
                continue
            required_catalog_fields = {
                "term_id", "canonical_term", "normalized_term", "aliases",
                "acronyms", "domains", "state", "record",
                "replacement_term_id", "last_verified_revision",
            }
            missing_fields = sorted(required_catalog_fields - set(entry))
            if missing_fields:
                context.error("VOCABULARY_CATALOG_ENTRY_FIELDS", f"{label} missing {missing_fields}", catalog_relpath)
            term_id = entry.get("term_id")
            if concrete(term_id):
                if term_id in catalog_ids:
                    context.error("VOCABULARY_CATALOG_ID_DUPLICATE", f"duplicate catalog term ID {term_id}", catalog_relpath)
                catalog_ids.add(term_id)
                if term_id not in term_ids:
                    context.error("VOCABULARY_CATALOG_REFERENCE", f"{label} references unknown term {term_id}", catalog_relpath)
                else:
                    term = term_by_id[term_id]
                    for field in [
                        "canonical_term", "normalized_term", "state",
                        "replacement_term_id", "last_verified_revision",
                    ]:
                        if entry.get(field) != term.get(field):
                            context.error(
                                "VOCABULARY_CATALOG_DRIFT",
                                f"{label}.{field} does not match term record {term_id}",
                                catalog_relpath,
                            )
                    list_pairs = {
                        "aliases": "aliases",
                        "acronyms": "acronyms",
                        "domains": "domains",
                    }
                    for catalog_field, term_field in list_pairs.items():
                        catalog_values = entry.get(catalog_field)
                        term_values = term.get(term_field)
                        if (
                            not isinstance(catalog_values, list)
                            or not isinstance(term_values, list)
                            or sorted(catalog_values) != sorted(term_values)
                        ):
                            context.error(
                                "VOCABULARY_CATALOG_DRIFT",
                                f"{label}.{catalog_field} does not match term record {term_id}",
                                catalog_relpath,
                            )
                    expected_record = f".ai/project/vocabulary/terms.json#{term_id}"
                    if entry.get("record") != expected_record:
                        context.error(
                            "VOCABULARY_CATALOG_RECORD",
                            f"{label}.record must be {expected_record}",
                            catalog_relpath,
                        )
        for term_id in term_ids - catalog_ids:
            context.error("VOCABULARY_TERM_UNINDEXED", f"term {term_id} is missing from compact catalog", catalog_relpath)

    if link_data.get("schema_version") != 1:
        context.error("VOCABULARY_LINK_SCHEMA", "schema_version should be 1", links_relpath)
    if link_data.get("record_kind") != "target-vocabulary-data-dictionary-links":
        context.error("VOCABULARY_LINK_KIND", "record_kind is invalid", links_relpath)
    links = link_data.get("links")
    if not isinstance(links, list):
        context.error("VOCABULARY_LINKS_SHAPE", "links must be a list", links_relpath)
        links = []
    link_ids: set[str] = set()
    required_link_fields = {
        "id", "term_id", "fact_type", "canonical_owner",
        "target_identifier", "relationship", "direction", "evidence",
        "validation", "last_verified_revision", "known_gaps",
    }
    for index, link in enumerate(links):
        label = f"links[{index}]"
        if not isinstance(link, dict):
            context.error("VOCABULARY_LINK_SHAPE", f"{label} must be an object", links_relpath)
            continue
        missing_fields = sorted(required_link_fields - set(link))
        if missing_fields:
            context.error("VOCABULARY_LINK_FIELDS", f"{label} missing {missing_fields}", links_relpath)
        link_id = link.get("id")
        if concrete(link_id):
            if link_id in link_ids:
                context.error("VOCABULARY_LINK_ID_DUPLICATE", f"duplicate data link ID {link_id}", links_relpath)
            link_ids.add(link_id)
        term_id = link.get("term_id")
        if concrete(term_id) and term_id not in term_ids:
            context.error("VOCABULARY_LINK_TERM_REFERENCE", f"{label} references unknown term {term_id}", links_relpath)
        for field in ["fact_type", "canonical_owner", "target_identifier", "relationship", "direction", "last_verified_revision"]:
            if not concrete(link.get(field)):
                context.error("VOCABULARY_LINK_UNRESOLVED", f"{label}.{field} must be resolved", links_relpath)
    for term_id, ref in pending_data_refs:
        if ref not in link_ids:
            context.error("VOCABULARY_DATA_REFERENCE", f"term {term_id} references unknown data link {ref}", terms_relpath)

    operation_catalog = context.load_json_object(
        context.target_path(".ai/assistant/operation-catalog.json"),
        "OPERATION_CATALOG",
    )
    operations = operation_catalog.get("operations") if isinstance(operation_catalog, dict) else None
    operation = next(
        (item for item in operations
         if isinstance(item, dict) and item.get("id") == "project-vocabulary"),
        None,
    ) if isinstance(operations, list) else None
    if not isinstance(operation, dict):
        context.error("VOCABULARY_OPERATION_MISSING", "enabled vocabulary requires project-vocabulary operation", ".ai/assistant/operation-catalog.json")
    else:
        if operation.get("required_module") != "project-vocabulary":
            context.error("VOCABULARY_OPERATION_MODULE", "project-vocabulary operation module is invalid", ".ai/assistant/operation-catalog.json")
        if operation.get("flow") != required_paths[5]:
            context.error("VOCABULARY_OPERATION_FLOW", f"project-vocabulary must route to {required_paths[5]}", ".ai/assistant/operation-catalog.json")
        if operation.get("allowed_actions") != ["read-only", "docs-only", "full-with-approval"]:
            context.error("VOCABULARY_OPERATION_ACTIONS", "project-vocabulary allowed actions are invalid", ".ai/assistant/operation-catalog.json")

    router = context.load_json_object(
        context.target_path(".ai/assistant/context-router.json"), "ROUTER"
    )
    overlays = router.get("intent_overlays") if isinstance(router, dict) else None
    route = overlays.get("vocabulary-request") if isinstance(overlays, dict) else None
    if not isinstance(route, dict) or route.get("operation_candidates") != ["project-vocabulary"]:
        context.error("VOCABULARY_OPERATION_UNROUTED", "enabled vocabulary has no vocabulary-request intent route", ".ai/assistant/context-router.json")

    required_text = {
        required_paths[0]: ["## Term States", "## Vocabulary Boundaries", "## Lookup Behavior"],
        required_paths[5]: ["## Routing Modes", "`lookup`", "`terminology-check`", "Do not mark observed or proposed records accepted"],
        required_paths[6]: ["Selected term IDs:", "Data dictionary links:", "Acceptance state:"],
        required_paths[7]: ["Preserve `observed`, `proposed`, `accepted`", "Do not activate this placeholder"],
        required_paths[8]: ["ALATYR-VOCABULARY-001", "## Compact Catalog And Lookup", "## Data Dictionary Links"],
    }
    for relpath, snippets in required_text.items():
        text = context.read_text(context.target_path(relpath))
        for snippet in snippets:
            if snippet not in text:
                context.error("VOCABULARY_CONTRACT_INCOMPLETE", f"project-vocabulary contract is missing {snippet}", relpath)

    context.info(
        "VOCABULARY_EVIDENCE_LIMIT",
        "project-vocabulary structural checks do not prove term meaning, ownership, relationship, acceptance, or semantic consistency",
    )


PROJECT_VOCABULARY_MODULE = FunctionCapabilityModule(
    check_id="check_project_vocabulary",
    validator=validate_project_vocabulary,
)
