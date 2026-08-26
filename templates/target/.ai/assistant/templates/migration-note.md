# Alatyr Migration Note

Use this note in `{PROJECT_NAME}` when installing, upgrading, or rechecking
Alatyr Core.

Replace placeholders with target facts before accepting the migration result.

Migration ID: `{MIGRATION_ID}`
Operation ID: `{OPERATION_ID}`
From framework version: `{FROM_ALATYR_CORE_VERSION}`
To framework version: `{TO_ALATYR_CORE_VERSION}`
From adapter schema version: `{FROM_ADAPTER_SCHEMA_VERSION}`
To adapter schema version: `{TO_ADAPTER_SCHEMA_VERSION}`
From template version: `{FROM_TEMPLATE_VERSION}`
To template version: `{TO_TEMPLATE_VERSION}`
Prepared by: `{PREPARED_BY}`
Prepared at: `{PREPARED_AT}`
Evidence basis: `{CURRENT_STATE_HISTORICAL_RECORD_OR_MIXED}`
Observed target branch: `{TARGET_BRANCH_OR_DETACHED_HEAD_OR_NOT_AVAILABLE}`
Observed target revision: `{TARGET_REVISION_OR_NOT_AVAILABLE}`
Migration assessment: `{MIGRATION_ASSESSMENT_PATH_OR_MANUAL_REVIEW}`

## Routed Context

Affected canonical framework sources:

- `{AFFECTED_CANONICAL_SOURCE_OR_NONE}`

Affected task profiles or rule categories:

- `{AFFECTED_PROFILE_OR_RULE_CATEGORY_OR_NONE}`

Candidate context intentionally omitted:

- `{OMITTED_CANDIDATE_CONTEXT_AND_REASON_OR_NONE}`

## Changed Framework Rules

Added rules:

- `{ADDED_RULE_ID_OR_NONE}`

Changed rules:

- `{CHANGED_RULE_ID_OR_NONE}`

Removed or deprecated rules:

- `{REMOVED_OR_DEPRECATED_RULE_ID_OR_NONE}`

## Required Target Actions

- `{REQUIRED_TARGET_ACTION}`

## Optional Target Actions

- `{OPTIONAL_TARGET_ACTION}`

## Local Deviations

- `{LOCAL_DEVIATION_TO_KEEP_OR_REPAIR}`

## Affected Target Surfaces

- `.ai/alatyr.yaml`: `{AFFECTED_OR_NOT}`
- `.ai/framework`: `{AFFECTED_OR_NOT}`
- `.ai/project`: `{AFFECTED_OR_NOT}`
- `.ai/assistant`: `{AFFECTED_OR_NOT}`
- `.ai/assistant/module-profile.md`: `{AFFECTED_OR_NOT}`
- bridge files: `{AFFECTED_OR_NOT}`
- validation or manual review: `{AFFECTED_OR_NOT}`

## Stateful Evidence Migration

Debug record/index versions and preservation result:

- `{DEBUG_VERSIONS_PRESERVED_NEW_AUTHORING_VERSION_AND_LINEAGE_ACTIONS_OR_NOT_ENABLED}`

Engineering-evidence record/index versions and reciprocal Debug-link result:

- `{ENGINEERING_EVIDENCE_VERSIONS_PRESERVED_NEW_AUTHORING_VERSION_AND_LINK_ACTIONS}`

Project-knowledge index version, adoption state, and reuse-evidence result:

- `{PROJECT_KNOWLEDGE_VERSION_ADOPTION_STATE_AND_EVIDENCE_ACTIONS}`

Historical records remain immutable: `{YES_OR_BLOCKER}`

## Approval And Validation

Approval needed: `{YES_NO_REASON}`
Approval record: `{APPROVAL_RECORD_OR_NOT_REQUIRED}`
Assessment completed before target changes: `{YES_NO_AND_REASON}`
Validation run: `{VALIDATION_RUN_OR_SKIPPED_WITH_REASON}`
Validation phase: `{ACCEPTANCE_OR_MIGRATION_STAGING}`
Active unresolved placeholders: `{COUNT_AND_PATHS_OR_NONE}`
Manifest/module-profile agreement: `{MATCH_OR_DRIFT_DETAILS}`
Acceptance eligible: `{YES_OR_NO_WITH_REASON}`
Required final strict rerun: `{COMMAND_OR_NOT_REQUIRED}`

## Final Evidence

Migration result: `{COMPLETE_STAGED_PARTIAL_OR_BLOCKED}`
Remaining gaps: `{REMAINING_GAPS_OR_NONE}`
Residual risk: `{RESIDUAL_RISK}`
