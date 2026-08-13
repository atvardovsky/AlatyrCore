# Extension Lifecycle Record

Record ID: `{EXTENSION_LIFECYCLE_RECORD_ID}`
Operation ID: `{OPERATION_ID}`
Mode: `{INSTALL_UPDATE_DISABLE_REMOVE_OR_REVIEW}`
Extension ID: `{EXTENSION_ID}`
Prior state: `{AVAILABLE_REVIEWED_PLANNED_ACTIVE_BLOCKED_DISABLED_DEPRECATED_REMOVED_OR_NONE}`
Final state: `{REVIEWED_PLANNED_ACTIVE_BLOCKED_DISABLED_DEPRECATED_OR_REMOVED}`

## Source And Compatibility

Source type and location: `{SOURCE_TYPE_AND_LOCATION}`
Immutable revision: `{SOURCE_COMMIT_OR_VERSION}`
Package digest: `{SHA256_DIGEST}`
Package version: `{SEMVER_VERSION}`
License result: `{LICENSE_RESULT}`
Compatibility result: `{EXTENSION_API_FRAMEWORK_SCHEMA_TEMPLATE_AND_RULE_RESULT}`
Review record: `{EXTENSION_REVIEW_RECORD}`

## Target Adaptation

Resolved bindings: `{BINDING_IDS_TARGET_VALUES_AND_OWNERS}`
Unresolved bindings: `{UNRESOLVED_BINDINGS_OR_NONE}`
Requested permissions: `{REQUESTED_PERMISSIONS}`
Granted permissions: `{GRANTED_PERMISSIONS}`
Protected effects: `{PROTECTED_EFFECTS_OR_NONE}`
Rejected or rewritten source instructions: `{NORMALIZATION_RESULT}`
Extension-owned files: `{PATHS_AND_HASHES}`
Shared integration surfaces: `{PATHS_AND_SYNC_RESULT}`
Local modifications or ownership conflicts: `{CONFLICTS_OR_NONE}`
Dependents: `{ACTIVE_DEPENDENTS_OR_NONE}`

## Control Surfaces

Catalog result: `{CATALOG_RESULT}`
Lock result: `{LOCK_RESULT}`
AI infrastructure router result: `{ROUTER_RESULT}`
Operation and context route result: `{OPERATION_CONTEXT_RESULT}`
Gate result: `{GATE_RESULT}`
Bridge and wrapper result: `{BRIDGE_WRAPPER_RESULT}`
Module result: `{MODULE_RESULT}`

## Evidence

Approval records: `{APPROVAL_RECORDS_OR_NONE}`
Package validation: `{PACKAGE_VALIDATION}`
Adapter validation: `{ADAPTER_VALIDATION}`
Target validation: `{TARGET_VALIDATION}`
Removed files: `{REMOVED_FILES_OR_NONE}`
Preserved files and history: `{PRESERVED_FILES_AND_HISTORY}`
Skipped checks: `{SKIPPED_CHECKS}`
Context and maintenance cost: `{MEASURED_OR_LABELED_ESTIMATE}`
Residual risk: `{RESIDUAL_RISK}`
