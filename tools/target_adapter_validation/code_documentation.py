"""Validate target-owned code documentation support."""

from __future__ import annotations

from typing import Any
from target_validation_support import ManifestData, dotted
from target_adapter_validation.values import is_resolved_string

from target_adapter_validation.capability import (
    CapabilityValidationContext,
    FunctionCapabilityModule,
)


def validate_code_documentation(
    context: CapabilityValidationContext,
    manifest: ManifestData | None,
) -> None:
    if not context.module_validation_enabled(
        "code-documentation",
        "CODEDOC_MODULE_UNDECLARED",
        "CODEDOC_MODULE_STATE_MISSING",
        "code-documentation",
    ):
        return

    required_paths = [
        ".ai/project/documentation/README.md",
        ".ai/project/documentation/catalog.json",
        ".ai/project/documentation/profiles.json",
        ".ai/assistant/context/intents/code-documentation.json",
        ".ai/assistant/flows/documentation-sync.flow.md",
        ".ai/assistant/templates/code-documentation-profile-review.md",
        ".ai/assistant/skills/code-documentation/SKILL.md",
        ".ai/framework/code-documentation.md",
    ]
    missing = False
    for relpath in required_paths:
        if not context.target_path(relpath).is_file():
            missing = True
            context.error(
                "CODEDOC_REQUIRED_FILE_MISSING",
                "enabled code-documentation module is missing a contract",
                relpath,
            )
    if missing:
        return

    if manifest is not None:
        expected_manifest = {
            ("source_of_truth", "code_documentation_index"): required_paths[0],
            ("source_of_truth", "code_documentation_catalog"): required_paths[1],
            ("source_of_truth", "code_documentation_profiles"): required_paths[2],
            ("operations", "documentation_sync"): required_paths[4],
            ("operations", "code_documentation_profile_review"): required_paths[5],
            ("code_documentation", "catalog"): required_paths[1],
            ("code_documentation", "profiles"): required_paths[2],
            ("code_documentation", "intent"): required_paths[3],
            ("code_documentation", "flow"): required_paths[4],
            ("code_documentation", "profile_review"): required_paths[5],
            ("code_documentation", "skill"): required_paths[6],
        }
        for key, expected in expected_manifest.items():
            scalar = manifest.scalars.get(key)
            if scalar is None or scalar.value != expected:
                context.error(
                    "CODEDOC_MANIFEST_PATH",
                    f"{dotted(key)} must be {expected} when code documentation is enabled",
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
                "CODEDOC_LIST_SHAPE",
                f"{label} must be a {'non-empty ' if non_empty else ''}string list",
                relpath,
            )
            return []
        return value

    catalog_relpath = required_paths[1]
    catalog = context.load_json_object(
        context.target_path(catalog_relpath), "CODEDOC_CATALOG"
    )
    profiles_relpath = required_paths[2]
    profile_data = context.load_json_object(
        context.target_path(profiles_relpath), "CODEDOC_PROFILES"
    )
    if catalog is None or profile_data is None:
        return
    if catalog.get("schema_version") != 1:
        context.error("CODEDOC_CATALOG_SCHEMA", "schema_version should be 1", catalog_relpath)
    if catalog.get("catalog_kind") != "target-code-documentation-catalog":
        context.error("CODEDOC_CATALOG_KIND", "catalog_kind is invalid", catalog_relpath)
    if catalog.get("human_index") != required_paths[0]:
        context.error("CODEDOC_CATALOG_INDEX", "human_index is invalid", catalog_relpath)
    if catalog.get("profiles") != required_paths[2]:
        context.error("CODEDOC_CATALOG_PROFILES", "profiles path is invalid", catalog_relpath)
    for field in [
        "project", "module_state", "documentation_owner",
        "profile_decision_authority", "generation_owner",
        "last_reviewed", "evidence_revision",
    ]:
        if not concrete(catalog.get(field)):
            context.error(
                "CODEDOC_ENABLED_METADATA_UNRESOLVED",
                f"enabled code documentation requires resolved {field}",
                catalog_relpath,
            )

    if profile_data.get("schema_version") != 1:
        context.error("CODEDOC_PROFILE_SCHEMA", "schema_version should be 1", profiles_relpath)
    if profile_data.get("profile_kind") != "target-code-documentation-profiles":
        context.error("CODEDOC_PROFILE_KIND", "profile_kind is invalid", profiles_relpath)
    selection = profile_data.get("selection_policy")
    if not isinstance(selection, dict):
        context.error("CODEDOC_SELECTION_POLICY", "selection_policy must be an object", profiles_relpath)
    else:
        for field in ["order", "on_equal_conflict", "on_no_accepted_match"]:
            if field not in selection:
                context.error("CODEDOC_SELECTION_POLICY", f"selection_policy missing {field}", profiles_relpath)

    entries = profile_data.get("profiles")
    if not isinstance(entries, list) or not entries:
        context.error("CODEDOC_PROFILES_EMPTY", "enabled module requires profiles", profiles_relpath)
        entries = []
    valid_states = {"proposed", "accepted", "deprecated", "contradicted", "unknown"}
    valid_outputs = {"ci-artifact", "committed-generated", "local-only", "external-publish", "unresolved"}
    profile_ids: set[str] = set()
    accepted_count = 0
    accepted_selectors: dict[tuple[Any, ...], str] = {}
    required_fields = {
        "id", "state", "owner", "priority", "match", "audiences",
        "visibility", "purpose", "evidence", "comment_contract",
        "generation", "validation", "assistant_skill", "migration_scope",
        "approval_needs", "known_gaps",
    }
    for index, profile in enumerate(entries):
        label = f"profiles[{index}]"
        if not isinstance(profile, dict):
            context.error("CODEDOC_PROFILE_SHAPE", f"{label} must be an object", profiles_relpath)
            continue
        missing_fields = sorted(required_fields - set(profile))
        if missing_fields:
            context.error("CODEDOC_PROFILE_FIELDS", f"{label} missing {missing_fields}", profiles_relpath)
        profile_id = profile.get("id")
        if concrete(profile_id):
            if profile_id in profile_ids:
                context.error("CODEDOC_PROFILE_ID_DUPLICATE", f"duplicate profile ID {profile_id}", profiles_relpath)
            profile_ids.add(profile_id)
        state = profile.get("state")
        if not concrete(state) or state not in valid_states:
            context.error("CODEDOC_PROFILE_STATE", f"{label}.state is invalid or unresolved", profiles_relpath)
        match = profile.get("match")
        if not isinstance(match, dict):
            context.error("CODEDOC_PROFILE_MATCH", f"{label}.match must be an object", profiles_relpath)
            match = {}
        include = string_list(match.get("include"), f"{label}.match.include", profiles_relpath)
        exclude = string_list(match.get("exclude"), f"{label}.match.exclude", profiles_relpath, non_empty=False)
        languages = string_list(match.get("languages"), f"{label}.match.languages", profiles_relpath)
        frameworks = string_list(match.get("frameworks"), f"{label}.match.frameworks", profiles_relpath, non_empty=False)
        audiences = string_list(profile.get("audiences"), f"{label}.audiences", profiles_relpath)
        validation = string_list(profile.get("validation"), f"{label}.validation", profiles_relpath)
        comment = profile.get("comment_contract")
        generation = profile.get("generation")
        if not isinstance(comment, dict):
            context.error("CODEDOC_COMMENT_CONTRACT", f"{label}.comment_contract must be an object", profiles_relpath)
            comment = {}
        if not isinstance(generation, dict):
            context.error("CODEDOC_GENERATION_CONTRACT", f"{label}.generation must be an object", profiles_relpath)
            generation = {}
        if generation.get("direct_edit") != "forbidden":
            context.error("CODEDOC_DIRECT_EDIT", f"{label} must forbid direct generated-output edits", profiles_relpath)
        output_policy = generation.get("output_policy")
        if concrete(output_policy) and output_policy not in valid_outputs:
            context.error("CODEDOC_OUTPUT_POLICY", f"{label}.generation.output_policy is invalid", profiles_relpath)
        if state == "accepted":
            accepted_count += 1
            for field in ["id", "owner", "visibility", "purpose"]:
                if not concrete(profile.get(field)):
                    context.error("CODEDOC_ACCEPTED_UNRESOLVED", f"{label}.{field} must be resolved", profiles_relpath)
            for field in ["syntax", "uncertainty_policy"]:
                if not concrete(comment.get(field)):
                    context.error("CODEDOC_ACCEPTED_UNRESOLVED", f"{label}.comment_contract.{field} must be resolved", profiles_relpath)
            for field in ["generator", "entry_point", "output", "output_policy", "publication_boundary"]:
                if not concrete(generation.get(field)):
                    context.error("CODEDOC_ACCEPTED_UNRESOLVED", f"{label}.generation.{field} must be resolved", profiles_relpath)
            for values, field in [(include, "include"), (languages, "languages"), (audiences, "audiences"), (validation, "validation")]:
                if not any(concrete(item) for item in values):
                    context.error("CODEDOC_ACCEPTED_UNRESOLVED", f"{label}.{field} needs concrete values", profiles_relpath)
            selector = (
                tuple(sorted(include)), tuple(sorted(exclude)),
                tuple(sorted(languages)), tuple(sorted(frameworks)),
                profile.get("priority"),
            )
            prior = accepted_selectors.get(selector)
            if prior is not None:
                context.error(
                    "CODEDOC_ACCEPTED_AMBIGUITY",
                    f"accepted profiles {prior} and {profile_id} have equal selectors and priority",
                    profiles_relpath,
                )
            elif concrete(profile_id):
                accepted_selectors[selector] = profile_id
    if accepted_count == 0:
        context.error(
            "CODEDOC_NO_ACCEPTED_PROFILE",
            "enabled code-documentation module requires at least one accepted profile",
            profiles_relpath,
        )

    areas = catalog.get("areas")
    if not isinstance(areas, list) or not areas:
        context.error("CODEDOC_AREAS_EMPTY", "enabled catalog requires areas", catalog_relpath)
    else:
        for index, area in enumerate(areas):
            label = f"areas[{index}]"
            if not isinstance(area, dict):
                context.error("CODEDOC_AREA_SHAPE", f"{label} must be an object", catalog_relpath)
                continue
            for ref in string_list(area.get("profile_ids"), f"{label}.profile_ids", catalog_relpath):
                if concrete(ref) and ref not in profile_ids:
                    context.error("CODEDOC_PROFILE_REFERENCE", f"{label} references unknown profile {ref}", catalog_relpath)

    router = context.load_json_object(
        context.target_path(".ai/assistant/context-router.json"), "ROUTER"
    )
    overlays = router.get("intent_overlays") if isinstance(router, dict) else None
    route = overlays.get("code-documentation") if isinstance(overlays, dict) else None
    if not isinstance(route, dict) or route.get("operation_candidates") != ["documentation-sync"]:
        context.error(
            "CODEDOC_OPERATION_UNROUTED",
            "enabled code documentation has no documentation intent route",
            ".ai/assistant/context-router.json",
        )

    required_text = {
        required_paths[0]: ["## Profile States", "## Source-Of-Truth Boundary", "## Documentation Areas"],
        required_paths[4]: ["## Routing Modes", "`propose`", "`document`", "`generate`", "Never edit a configured generated output directly"],
        required_paths[5]: ["Profile state:", "Generator and configuration:", "Approval needs:"],
        required_paths[6]: ["most specific accepted profile", "Never edit generated output directly", "Do not activate this placeholder"],
        required_paths[7]: ["ALATYR-CODEDOC-001", "## Multiple Documentation Profiles", "## Generation And Output Policy"],
    }
    for relpath, snippets in required_text.items():
        text = context.read_text(context.target_path(relpath))
        for snippet in snippets:
            if snippet not in text:
                context.error("CODEDOC_CONTRACT_INCOMPLETE", f"code-documentation contract is missing {snippet}", relpath)

    context.info(
        "CODEDOC_EVIDENCE_LIMIT",
        "code-documentation structural checks do not prove comment truth, semantic completeness, or generated-reference quality",
    )


CODE_DOCUMENTATION_MODULE = FunctionCapabilityModule(
    check_id="check_code_documentation",
    validator=validate_code_documentation,
)
