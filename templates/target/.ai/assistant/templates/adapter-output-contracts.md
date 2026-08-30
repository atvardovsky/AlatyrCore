# Alatyr Adapter Output Contracts

Use this file in `{PROJECT_NAME}` to define the minimum evidence an assistant
must report after installation, framework update, or adapter recheck work.

Replace placeholders with target facts before accepting installation.

## Contract: `operation-completion-evidence`

Use after any material operation where the assistant intends to report a final
status, especially after modifying files, committing, publishing, or completing
a large task package.

- Template path: `.ai/assistant/templates/operation-completion-evidence.json`
- Operation id: `{OPERATION_ID}`
- Operation type: `{OPERATION_TYPE}`
- Operation status: `{COMPLETED_PARTIAL_BLOCKED_OR_NOT_STARTED}`
- Completion claim: `{COMPLETE_PARTIAL_BLOCKED_OR_UNVERIFIED}`
- Current user authorization: `{CURRENT_SCOPE_SOURCE_AUTHORIZED_PHASES_INVALIDATION_AND_ACTIONS_PERFORMED}`
- Changed facts: `{FACT_IDS_STATEMENTS_OWNERS_AND_STATUS_OR_NOT_APPLICABLE}`
- Validation completion basis: `{VALIDATED_WITH_REQUIRED_CHECKS_BLOCKED_PARTIAL_OR_UNVERIFIED}`
- Tests run: `{COMMAND_LEVEL_RESULT_EVIDENCE_AND_SEMANTIC_SCOPE_OR_NOT_APPLICABLE}`
- Required checks: `{CHECKS_RESULTS_AND_REASONS}`
- Skipped or unavailable checks: `{CHECKS_REASONS_AND_RESIDUAL_RISK_OR_NONE}`
- Logical integrity result: `{PASSED_FAILED_BLOCKED_OR_UNVERIFIED}`
- Companion surfaces: `{SURFACES_DECISIONS_AND_EVIDENCE}`
- Approval scope result: `{PASSED_FAILED_NOT_REQUIRED_OR_UNVERIFIED}`
- Residual risks: `{RESIDUAL_RISKS_OR_NONE}`
- May claim complete: `{TRUE_ONLY_WHEN_REQUIRED_EVIDENCE_PASSED_OR_IS_NOT_APPLICABLE}`
- Blocking reasons: `{BLOCKING_REASONS_OR_NONE}`
- Next owner or action: `{OWNER_ACTION_OR_NONE}`

Do not report `complete` when current authorization is missing, required
validation failed or was unavailable without an accepted target reason, logical
integrity is unresolved, approval scope is required but unverified, or residual
risk needs a target owner decision.

## Contract: `adapter-health-output`

Use after `Alatyr status`, `Alatyr doctor`, or another read-only adapter
health request.

- Operation id: `{OPERATION_ID}`
- Operation type: `adapter-health`
- Current user authorization: `{CURRENT_SCOPE_SOURCE_AUTHORIZED_READ_ONLY_PHASE}`
- Evidence basis: `{CURRENT_STATE_STRUCTURAL_OR_UNAVAILABLE}`
- Observed at: `{OBSERVATION_DATE_TIME_OR_UNKNOWN}`
- Observed repository branch: `{REPOSITORY_BRANCH_OR_DETACHED_HEAD_OR_NOT_AVAILABLE}`
- Observed repository revision: `{REPOSITORY_REVISION_OR_NOT_AVAILABLE}`
- Manifest path: `.ai/alatyr.yaml`
- Health state: `{READY_ATTENTION_BLOCKED_OR_UNVERIFIED}`
- Installation state: `{SCAFFOLDED_STAGED_ACCEPTED_DEGRADED_OR_INVALID}`
- Installation transition record: `{PATH_FINAL_SEQUENCE_REVISION_VALIDATION_AND_CONTINUITY_RESULT}`
- Validation phase: `{ACCEPTANCE_OR_MIGRATION_STAGING}`
- Acceptance eligible: `{YES_OR_NO_WITH_REASON}`
- Required final strict rerun: `{COMMAND_OR_NOT_REQUIRED}`
- Checks run: `{COMMANDS_AND_MANUAL_CHECKS_OR_NONE}`
- Checks unavailable: `{CHECKS_AND_REASONS_OR_NONE}`
- Finding counts: `{ERRORS_WARNINGS_BLOCKING_WARNINGS_INFO}`
- Blocking findings: `{SEVERITY_CODE_OWNER_EVIDENCE_REPAIR_APPROVAL_OR_NONE}`
- Attention findings: `{SEVERITY_CODE_OWNER_EVIDENCE_REPAIR_APPROVAL_OR_NONE}`
- Repair operations: `{UP_TO_THREE_OPERATION_IDS_OR_NONE}`
- Automatic repair performed: `false`
- Files changed: `none`
- Residual risk: `{RESIDUAL_RISK}`

## Contract: `installation-output`

Use after the initial Alatyr Core installation or a scoped adapter expansion.

- Operation id: `{OPERATION_ID}`
- Operation type: `{INSTALLATION_OR_ADAPTER_EXPANSION}`
- Current user authorization: `{CURRENT_SCOPE_SOURCE_AUTHORIZED_PHASES_INVALIDATION_AND_ACTIONS_PERFORMED}`
- Evidence basis: `{CURRENT_STATE_HISTORICAL_RECORD_OR_MIXED}`
- Observed at: `{OBSERVATION_DATE_TIME}`
- Observed repository branch: `{REPOSITORY_BRANCH_OR_DETACHED_HEAD_OR_NOT_AVAILABLE}`
- Observed repository revision: `{REPOSITORY_REVISION_OR_NOT_AVAILABLE}`
- Historical records used: `{DATED_OPERATION_APPROVAL_OR_MIGRATION_RECORDS_OR_NONE}`
- Unverifiable historical claims: `{UNVERIFIABLE_HISTORICAL_CLAIMS_OR_NONE}`
- Installation id: `{INSTALLATION_ID}`
- Requested by: `{REQUESTER_OR_ROLE}`
- Framework source or baseline: `{ALATYR_CORE_SOURCE_OR_BASELINE}`
- Framework version: `{ALATYR_CORE_VERSION}`
- Adapter schema version: `{ALATYR_ADAPTER_SCHEMA_VERSION}`
- Template version: `{ALATYR_TEMPLATE_VERSION}`
- Manifest path: `.ai/alatyr.yaml`
- Installation state: `{SCAFFOLDED_STAGED_ACCEPTED_DEGRADED_OR_INVALID}`
- Installation transition record: `{PATH_FINAL_SEQUENCE_REVISION_VALIDATION_AND_CONTINUITY_RESULT}`
- Installation plan path or summary: `{INSTALLATION_PLAN_PATH_OR_SUMMARY}`
- Approval records used: `{APPROVAL_RECORDS_USED_OR_NOT_REQUIRED}`
- Approval scope enforcement: `{DIFF_BASE_RECORDS_CHANGED_PATHS_AND_RESULT_OR_NOT_REQUIRED}`
- Surfaces created: `{SURFACES_CREATED}`
- Surfaces updated: `{SURFACES_UPDATED}`
- Surfaces skipped: `{SURFACES_SKIPPED_AND_REASON}`
- Existing files preserved: `{EXISTING_FILES_PRESERVED}`
- Existing files overwritten with approval:
  `{EXISTING_FILES_OVERWRITTEN_WITH_APPROVAL_OR_NONE}`
- Required core profile result: `{REQUIRED_CORE_PROFILE_RESULT}`
- Optional module profile result: `{OPTIONAL_MODULE_PROFILE_RESULT}`
- Workspace-mode result: `{MODULE_STATE_WORKSPACE_IDENTITY_PROPOSED_ACCEPTED_OR_REJECTED_MODES_USER_DECISIONS_ROOT_AND_PER_MODE_CONTEXT_VALIDATION_AND_GAPS}`
- Context profiles result: `{CONTEXT_PROFILES_RESULT}`
- Operation catalog and automatic routing result: `{OPERATION_CATALOG_ROUTING_RESULT}`
- Adapter health and evidence freshness: `{HEALTH_STATE_TIME_REVISION_OR_UNVERIFIED}`
- Pre-change preview result: `{SHOWN_SKIPPED_OR_NOT_APPLICABLE_WITH_REASON}`
- Context receipt and cost evidence: `{LOADED_FILES_VOLUME_EXPANSIONS_OR_NOT_REQUIRED}`
- Large-task orchestration result: `{LARGE_TASK_ORCHESTRATION_RESULT_OR_SKIPPED}`
- Operation packet template result: `{OPERATION_PACKET_TEMPLATE_RESULT_OR_SKIPPED}`
- Change-package module result: `{INDEX_FLOW_SCHEMA_RETENTION_VALIDATOR_AND_GAPS_OR_SKIPPED}`
- Durable engineering-evidence result: `{CAPTURED_SKIPPED_OR_BLOCKED_RECORD_ID_TASK_REVISION_BINDING_PRIVACY_PUBLICATION_VALIDATION_AND_REASON}`
- Debug Mode result: `{MODULE_STATE_DEPENDENCIES_OWNER_POLICY_INDEX_OPERATION_VALIDATOR_AND_INACTIVE_OR_EXPLICIT_CURRENT_SCOPE_RECORD_RESULT}`
- Team-collaboration result: `{MODULE_OWNER_BACKEND_REGISTRY_OVERLAP_HANDOFF_REVIEW_AND_GAPS_OR_SKIPPED}`
- Source-of-truth registry result: `{SOURCE_OF_TRUTH_REGISTRY_RESULT}`
- Consistency-map result: `{CONSISTENCY_MAP_RESULT_OR_SKIPPED}`
- Logical integrity evidence: `{CHANGED_FACTS_RELATIONSHIPS_COMPANION_SURFACES_AND_GAPS}`
- Task-specific maturity result: `{TASK_SPECIFIC_MATURITY_RESULT}`
- Bridge capability matrix result: `{BRIDGE_CAPABILITY_MATRIX_RESULT}`
- Root entry points checked: `{ROOT_ENTRY_POINTS_CHECKED}`
- Supported bridge files checked: `{SUPPORTED_BRIDGE_FILES_CHECKED}`
- Adapter drift checks result: `{ADAPTER_DRIFT_CHECKS_RESULT}`
- Local path leakage result: `{LOCAL_PATH_LEAKAGE_RESULT}`
- Target-local checker status: `{TARGET_LOCAL_CHECKER_STATUS_OR_UNRESOLVED}`
- AI infrastructure inventory result:
  `{AI_INFRASTRUCTURE_INVENTORY_RESULT_OR_SKIPPED}`
- AI infrastructure recommendation result: `{PROJECT_EVIDENCE_EXISTING_ITEM_COMPARISON_COST_QUALITY_ACCEPTANCE_AND_NEXT_ROUTE_OR_SKIPPED}`
- Development-pattern evidence result: `{INDEX_OWNER_RETENTION_CAPTURE_AND_FRAMEWORK_BOUNDARY_OR_SKIPPED}`
- AI infrastructure router result: `{AI_INFRASTRUCTURE_ROUTER_RESULT_OR_SKIPPED}`
- AI infrastructure adaptation-record result: `{AI_INFRASTRUCTURE_ADAPTATION_RECORD_RESULT_OR_SKIPPED}`
- Support/product change cost: `{SUPPORT_PRODUCT_FILE_AND_LINE_RATIO_OR_SKIPPED}`
- Contract artifact result: `{CONTRACT_ARTIFACT_UPDATED_PROPOSED_SKIPPED_OR_NOT_APPLICABLE}`
- Visual validation result: `{VISUAL_VALIDATION_EVIDENCE_OR_SKIPPED}`
- Validation run: `{TARGET_VALIDATION_RUN_OR_MANUAL_REVIEW}`
- Validation phase: `{ACCEPTANCE_OR_MIGRATION_STAGING}`
- Active unresolved placeholders: `{COUNT_AND_PATHS_OR_NONE}`
- Manifest/module-profile agreement: `{MATCH_OR_DRIFT_DETAILS}`
- Acceptance eligible: `{YES_OR_NO_WITH_REASON}`
- Required final strict rerun: `{COMMAND_OR_NOT_REQUIRED}`
- Validation skipped or unresolved: `{VALIDATION_SKIPPED_OR_UNRESOLVED}`
- Post-install message result: `{POST_INSTALL_MESSAGE_SENT_SKIPPED_OR_BLOCKED}`
- Post-install delivery status: `{SENT_SKIPPED_OR_BLOCKED}`
- Post-install delivery mechanism: `{CHAT_SURFACE_OR_UNAVAILABLE}`
- Post-install delivery reason: `{WHY_SENT_SKIPPED_OR_BLOCKED}`
- Post-install delivery observed at: `{DELIVERY_TIMESTAMP_OR_NOT_OBSERVED}`
- Final evidence: `{FINAL_EVIDENCE}`
- Residual risk: `{RESIDUAL_RISK}`

## Contract: `framework-update-output`

Use after updating or comparing an installed adapter against a newer Alatyr
Core baseline.

- Operation id: `{OPERATION_ID}`
- Operation type: `{FRAMEWORK_UPDATE_OR_IMPACT_REVIEW}`
- Current user authorization: `{CURRENT_SCOPE_SOURCE_AUTHORIZED_PHASES_INVALIDATION_AND_ACTIONS_PERFORMED}`
- Evidence basis: `{CURRENT_STATE_HISTORICAL_RECORD_OR_MIXED}`
- Observed at: `{OBSERVATION_DATE_TIME}`
- Observed repository branch: `{REPOSITORY_BRANCH_OR_DETACHED_HEAD_OR_NOT_AVAILABLE}`
- Observed repository revision: `{REPOSITORY_REVISION_OR_NOT_AVAILABLE}`
- Historical records used: `{DATED_OPERATION_APPROVAL_OR_MIGRATION_RECORDS_OR_NONE}`
- Unverifiable historical claims: `{UNVERIFIABLE_HISTORICAL_CLAIMS_OR_NONE}`
- Update source or baseline: `{ALATYR_UPDATE_SOURCE_OR_BASELINE}`
- Previous framework version: `{PREVIOUS_ALATYR_CORE_VERSION}`
- New framework version: `{NEW_ALATYR_CORE_VERSION}`
- Framework version: `{NEW_ALATYR_CORE_VERSION}`
- Previous adapter schema version: `{PREVIOUS_ADAPTER_SCHEMA_VERSION}`
- New adapter schema version: `{NEW_ADAPTER_SCHEMA_VERSION}`
- Adapter schema version: `{NEW_ADAPTER_SCHEMA_VERSION}`
- Previous template version: `{PREVIOUS_TEMPLATE_VERSION}`
- New template version: `{NEW_TEMPLATE_VERSION}`
- Template version: `{NEW_TEMPLATE_VERSION}`
- Manifest path: `.ai/alatyr.yaml`
- Installation state: `{SCAFFOLDED_STAGED_ACCEPTED_DEGRADED_OR_INVALID}`
- Installation transition record: `{PATH_FINAL_SEQUENCE_REVISION_VALIDATION_AND_CONTINUITY_RESULT}`
- Migration note path: `.ai/assistant/templates/migration-note.md`
- Migration assessment result/path: `{MIGRATION_ASSESSMENT_RESULT_OR_PATH}`
- Migration diff result: `{MIGRATION_DIFF_RESULT}`
- Changed rule ids: `{CHANGED_RULE_IDS_OR_NONE}`
- Added or removed framework files: `{ADDED_OR_REMOVED_FRAMEWORK_FILES}`
- Target adapter actions required: `{TARGET_ADAPTER_ACTIONS_REQUIRED}`
- Target adapter actions optional: `{TARGET_ADAPTER_ACTIONS_OPTIONAL}`
- Surfaces created: `{SURFACES_CREATED}`
- Surfaces updated: `{SURFACES_UPDATED}`
- Surfaces skipped: `{SURFACES_SKIPPED_AND_REASON}`
- Existing files preserved: `{EXISTING_FILES_PRESERVED}`
- Approval records used: `{APPROVAL_RECORDS_USED_OR_NOT_REQUIRED}`
- Approval scope enforcement: `{DIFF_BASE_RECORDS_CHANGED_PATHS_AND_RESULT_OR_NOT_REQUIRED}`
- Required core profile result: `{REQUIRED_CORE_PROFILE_RESULT}`
- Optional module profile result: `{OPTIONAL_MODULE_PROFILE_RESULT}`
- Workspace-mode migration result: `{PRESERVED_ACCEPTED_MODES_PROPOSED_MIGRATIONS_USER_DECISIONS_ROUTING_VALIDATION_AND_GAPS}`
- Context profiles result: `{CONTEXT_PROFILES_RESULT}`
- Context receipt and cost evidence: `{LOADED_FILES_VOLUME_EXPANSIONS_OR_NOT_REQUIRED}`
- Large-task orchestration result: `{LARGE_TASK_ORCHESTRATION_RESULT_OR_SKIPPED}`
- Operation packet template result: `{OPERATION_PACKET_TEMPLATE_RESULT_OR_SKIPPED}`
- Change-package migration result: `{RULE_SCHEMA_RECORD_PRESERVATION_PROVENANCE_VALIDATOR_AND_GAPS_OR_SKIPPED}`
- Durable engineering-evidence migration result: `{POLICY_INDEX_RECORD_SCHEMA_AND_EXISTING_RECORD_PRESERVATION_RESULT}`
- Debug Mode migration result: `{RULE_MODULE_SCHEMA_RECORD_PRESERVATION_ACTIVE_SCOPE_EXPIRY_ROUTING_VALIDATION_AND_GAPS_OR_SKIPPED}`
- Team-collaboration migration result: `{SCHEMA_ACTIVE_RECORD_PRESERVATION_STALE_CLAIMS_ROUTES_AND_GAPS_OR_SKIPPED}`
- Source-of-truth registry result: `{SOURCE_OF_TRUTH_REGISTRY_RESULT}`
- Consistency-map result: `{CONSISTENCY_MAP_RESULT_OR_SKIPPED}`
- Logical integrity evidence: `{CHANGED_FACTS_RELATIONSHIPS_COMPANION_SURFACES_AND_GAPS}`
- Task-specific maturity result: `{TASK_SPECIFIC_MATURITY_RESULT}`
- Operation catalog, health, preview, help, and routing result:
  `{OPERATION_CONTROL_SURFACE_RESULT}`
- Bridge capability matrix result: `{BRIDGE_CAPABILITY_MATRIX_RESULT}`
- Adapter drift checks result: `{ADAPTER_DRIFT_CHECKS_RESULT}`
- Local path leakage result: `{LOCAL_PATH_LEAKAGE_RESULT}`
- Target-local checker status: `{TARGET_LOCAL_CHECKER_STATUS_OR_UNRESOLVED}`
- AI infrastructure router result: `{AI_INFRASTRUCTURE_ROUTER_RESULT_OR_SKIPPED}`
- AI infrastructure recommendation result: `{PROJECT_EVIDENCE_EXISTING_ITEM_COMPARISON_COST_QUALITY_ACCEPTANCE_AND_NEXT_ROUTE_OR_SKIPPED}`
- Development-pattern evidence result: `{INDEX_OWNER_RETENTION_CAPTURE_AND_FRAMEWORK_BOUNDARY_OR_SKIPPED}`
- AI infrastructure adaptation-record result: `{AI_INFRASTRUCTURE_ADAPTATION_RECORD_RESULT_OR_SKIPPED}`
- Support/product change cost: `{SUPPORT_PRODUCT_FILE_AND_LINE_RATIO_OR_SKIPPED}`
- Contract artifact result: `{CONTRACT_ARTIFACT_UPDATED_PROPOSED_SKIPPED_OR_NOT_APPLICABLE}`
- Visual validation result: `{VISUAL_VALIDATION_EVIDENCE_OR_SKIPPED}`
- Validation run: `{TARGET_VALIDATION_RUN_OR_MANUAL_REVIEW}`
- Validation phase: `{ACCEPTANCE_OR_MIGRATION_STAGING}`
- Active unresolved placeholders: `{COUNT_AND_PATHS_OR_NONE}`
- Manifest/module-profile agreement: `{MATCH_OR_DRIFT_DETAILS}`
- Acceptance eligible: `{YES_OR_NO_WITH_REASON}`
- Required final strict rerun: `{COMMAND_OR_NOT_REQUIRED}`
- Validation skipped or unresolved: `{VALIDATION_SKIPPED_OR_UNRESOLVED}`
- Post-update message result: `{POST_UPDATE_MESSAGE_SENT_SKIPPED_OR_BLOCKED}`
- Post-update delivery status: `{SENT_SKIPPED_OR_BLOCKED}`
- Post-update delivery mechanism: `{CHAT_SURFACE_OR_UNAVAILABLE}`
- Post-update delivery reason: `{WHY_SENT_SKIPPED_OR_BLOCKED}`
- Post-update delivery observed at: `{DELIVERY_TIMESTAMP_OR_NOT_OBSERVED}`
- Final evidence: `{FINAL_EVIDENCE}`
- Residual risk: `{RESIDUAL_RISK}`

## Contract: `adapter-recheck-output`

Use after read-only, adapter-only, or maturity-focused rechecks of an installed
adapter.

- Operation id: `{OPERATION_ID}`
- Operation type: `{ADAPTER_RECHECK_OR_MATURITY_REVIEW}`
- Current user authorization: `{CURRENT_SCOPE_SOURCE_AUTHORIZED_PHASES_INVALIDATION_AND_ACTIONS_PERFORMED}`
- Evidence basis: `{CURRENT_STATE_HISTORICAL_RECORD_OR_MIXED}`
- Observed at: `{OBSERVATION_DATE_TIME}`
- Observed repository branch: `{REPOSITORY_BRANCH_OR_DETACHED_HEAD_OR_NOT_AVAILABLE}`
- Observed repository revision: `{REPOSITORY_REVISION_OR_NOT_AVAILABLE}`
- Historical records used: `{DATED_OPERATION_APPROVAL_OR_MIGRATION_RECORDS_OR_NONE}`
- Unverifiable historical claims: `{UNVERIFIABLE_HISTORICAL_CLAIMS_OR_NONE}`
- Recheck trigger: `{RECHECK_TRIGGER}`
- Allowed actions: `{READ_ONLY_DOCS_ONLY_ADAPTER_ONLY_CODE_AND_TESTS_OR_FULL_WITH_APPROVAL}`
- Manifest path: `.ai/alatyr.yaml`
- Installation state: `{SCAFFOLDED_STAGED_ACCEPTED_DEGRADED_OR_INVALID}`
- Installation transition record: `{PATH_FINAL_SEQUENCE_REVISION_VALIDATION_AND_CONTINUITY_RESULT}`
- Installation note status: `{INSTALLATION_NOTE_STATUS}`
- Migration assessment result/path: `{MIGRATION_ASSESSMENT_RESULT_PATH_OR_NOT_APPLICABLE}`
- Framework version: `{ALATYR_CORE_VERSION}`
- Adapter schema version: `{ALATYR_ADAPTER_SCHEMA_VERSION}`
- Template version: `{ALATYR_TEMPLATE_VERSION}`
- Approval records used: `{APPROVAL_RECORDS_USED_OR_NOT_REQUIRED}`
- Approval scope enforcement: `{DIFF_BASE_RECORDS_CHANGED_PATHS_AND_RESULT_OR_NOT_REQUIRED}`
- Surfaces created: `{SURFACES_CREATED_OR_NONE}`
- Surfaces updated: `{SURFACES_UPDATED_OR_NONE}`
- Surfaces skipped: `{SURFACES_SKIPPED_AND_REASON}`
- Existing files preserved: `{EXISTING_FILES_PRESERVED}`
- Required core profile result: `{REQUIRED_CORE_PROFILE_RESULT}`
- Optional module profile result: `{OPTIONAL_MODULE_PROFILE_RESULT}`
- Workspace-mode recheck result: `{WORKSPACE_IDENTITY_ACCEPTED_PROPOSED_STALE_OR_AMBIGUOUS_MODES_ROUTING_VALIDATION_AND_GAPS}`
- Context profiles result: `{CONTEXT_PROFILES_RESULT}`
- Context receipt and cost evidence: `{LOADED_FILES_VOLUME_EXPANSIONS_OR_NOT_REQUIRED}`
- Large-task orchestration result: `{LARGE_TASK_ORCHESTRATION_RESULT_OR_SKIPPED}`
- Operation packet template result: `{OPERATION_PACKET_TEMPLATE_RESULT_OR_SKIPPED}`
- Change-package recheck result: `{MODULE_INDEX_RECORD_SCHEMA_PROVENANCE_VALIDATOR_AND_GAPS_OR_SKIPPED}`
- Durable engineering-evidence recheck result: `{POLICY_INDEX_RECORD_SCHEMA_ROUTING_VALIDATION_AND_GAPS}`
- Debug Mode recheck result: `{MODULE_DEPENDENCY_ACTIVATION_INDEX_RECORD_ROUTING_PRIVACY_METRIC_VALIDATION_AND_GAPS_OR_SKIPPED}`
- Team-collaboration recheck result: `{MODULE_BACKEND_REGISTRY_ACTIVE_OVERLAPS_STALE_CLAIMS_HANDOFFS_REVIEWS_AND_GAPS_OR_SKIPPED}`
- Source-of-truth registry result: `{SOURCE_OF_TRUTH_REGISTRY_RESULT}`
- Consistency-map result: `{CONSISTENCY_MAP_RESULT_OR_SKIPPED}`
- Logical integrity evidence: `{CHANGED_FACTS_RELATIONSHIPS_COMPANION_SURFACES_AND_GAPS}`
- Task-specific maturity result: `{TASK_SPECIFIC_MATURITY_RESULT}`
- Bridge capability matrix result: `{BRIDGE_CAPABILITY_MATRIX_RESULT}`
- Operation catalog, health, preview, help, and routing result:
  `{OPERATION_CONTROL_SURFACE_RESULT}`
- Approval-record policy result: `{APPROVAL_RECORD_POLICY_RESULT}`
- Adapter drift checks result: `{ADAPTER_DRIFT_CHECKS_RESULT}`
- Local path leakage result: `{LOCAL_PATH_LEAKAGE_RESULT}`
- Target-local checker status: `{TARGET_LOCAL_CHECKER_STATUS_OR_UNRESOLVED}`
- AI infrastructure inventory result:
  `{AI_INFRASTRUCTURE_INVENTORY_RESULT_OR_SKIPPED}`
- AI infrastructure recommendation result: `{PROJECT_EVIDENCE_EXISTING_ITEM_COMPARISON_COST_QUALITY_ACCEPTANCE_AND_NEXT_ROUTE_OR_SKIPPED}`
- Development-pattern evidence result: `{INDEX_OWNER_RETENTION_CAPTURE_AND_FRAMEWORK_BOUNDARY_OR_SKIPPED}`
- AI infrastructure router result: `{AI_INFRASTRUCTURE_ROUTER_RESULT_OR_SKIPPED}`
- AI infrastructure adaptation-record result: `{AI_INFRASTRUCTURE_ADAPTATION_RECORD_RESULT_OR_SKIPPED}`
- Prompt-injection policy result: `{PROMPT_INJECTION_POLICY_RESULT}`
- Support/product change cost: `{SUPPORT_PRODUCT_FILE_AND_LINE_RATIO_OR_SKIPPED}`
- Contract artifact result: `{CONTRACT_ARTIFACT_UPDATED_PROPOSED_SKIPPED_OR_NOT_APPLICABLE}`
- Visual validation result: `{VISUAL_VALIDATION_EVIDENCE_OR_SKIPPED}`
- Validation run: `{TARGET_VALIDATION_RUN_OR_MANUAL_REVIEW}`
- Validation phase: `{ACCEPTANCE_OR_MIGRATION_STAGING}`
- Active unresolved placeholders: `{COUNT_AND_PATHS_OR_NONE}`
- Manifest/module-profile agreement: `{MATCH_OR_DRIFT_DETAILS}`
- Acceptance eligible: `{YES_OR_NO_WITH_REASON}`
- Required final strict rerun: `{COMMAND_OR_NOT_REQUIRED}`
- Validation skipped or unresolved: `{VALIDATION_SKIPPED_OR_UNRESOLVED}`
- Recommended next operation: `{RECOMMENDED_NEXT_OPERATION}`
- Final evidence: `{FINAL_EVIDENCE}`
- Residual risk: `{RESIDUAL_RISK}`
