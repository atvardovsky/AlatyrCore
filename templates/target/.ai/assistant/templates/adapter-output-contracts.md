# Alatyr Adapter Output Contracts

Use this file in `{PROJECT_NAME}` to define the minimum evidence an assistant
must report after installation, framework update, or adapter recheck work.

Replace placeholders with target facts before accepting installation.

## Contract: `installation-output`

Use after the initial Alatyr Core installation or a scoped adapter expansion.

- Operation id: `{OPERATION_ID}`
- Operation type: `{INSTALLATION_OR_ADAPTER_EXPANSION}`
- Installation id: `{INSTALLATION_ID}`
- Requested by: `{REQUESTER_OR_ROLE}`
- Framework source or baseline: `{ALATYR_CORE_SOURCE_OR_BASELINE}`
- Framework version: `{ALATYR_CORE_VERSION}`
- Adapter schema version: `{ALATYR_ADAPTER_SCHEMA_VERSION}`
- Template version: `{ALATYR_TEMPLATE_VERSION}`
- Manifest path: `.ai/alatyr.yaml`
- Installation plan path or summary: `{INSTALLATION_PLAN_PATH_OR_SUMMARY}`
- Approval records used: `{APPROVAL_RECORDS_USED_OR_NOT_REQUIRED}`
- Surfaces created: `{SURFACES_CREATED}`
- Surfaces updated: `{SURFACES_UPDATED}`
- Surfaces skipped: `{SURFACES_SKIPPED_AND_REASON}`
- Existing files preserved: `{EXISTING_FILES_PRESERVED}`
- Existing files overwritten with approval:
  `{EXISTING_FILES_OVERWRITTEN_WITH_APPROVAL_OR_NONE}`
- Required core profile result: `{REQUIRED_CORE_PROFILE_RESULT}`
- Optional module profile result: `{OPTIONAL_MODULE_PROFILE_RESULT}`
- Context profiles result: `{CONTEXT_PROFILES_RESULT}`
- Large-task orchestration result: `{LARGE_TASK_ORCHESTRATION_RESULT_OR_SKIPPED}`
- Operation packet template result: `{OPERATION_PACKET_TEMPLATE_RESULT_OR_SKIPPED}`
- Source-of-truth registry result: `{SOURCE_OF_TRUTH_REGISTRY_RESULT}`
- Consistency-map result: `{CONSISTENCY_MAP_RESULT_OR_SKIPPED}`
- Task-specific maturity result: `{TASK_SPECIFIC_MATURITY_RESULT}`
- Bridge capability matrix result: `{BRIDGE_CAPABILITY_MATRIX_RESULT}`
- Root entry points checked: `{ROOT_ENTRY_POINTS_CHECKED}`
- Supported bridge files checked: `{SUPPORTED_BRIDGE_FILES_CHECKED}`
- Adapter drift checks result: `{ADAPTER_DRIFT_CHECKS_RESULT}`
- Local path leakage result: `{LOCAL_PATH_LEAKAGE_RESULT}`
- Target-local checker status: `{TARGET_LOCAL_CHECKER_STATUS_OR_UNRESOLVED}`
- AI infrastructure inventory result:
  `{AI_INFRASTRUCTURE_INVENTORY_RESULT_OR_SKIPPED}`
- Validation run: `{TARGET_VALIDATION_RUN_OR_MANUAL_REVIEW}`
- Validation skipped or unresolved: `{VALIDATION_SKIPPED_OR_UNRESOLVED}`
- Post-install message result: `{POST_INSTALL_MESSAGE_SENT_OR_SKIPPED}`
- Final evidence: `{FINAL_EVIDENCE}`
- Residual risk: `{RESIDUAL_RISK}`

## Contract: `framework-update-output`

Use after updating or comparing an installed adapter against a newer Alatyr
Core baseline.

- Operation id: `{OPERATION_ID}`
- Operation type: `{FRAMEWORK_UPDATE_OR_IMPACT_REVIEW}`
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
- Migration note path: `.ai/assistant/templates/migration-note.md`
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
- Required core profile result: `{REQUIRED_CORE_PROFILE_RESULT}`
- Optional module profile result: `{OPTIONAL_MODULE_PROFILE_RESULT}`
- Context profiles result: `{CONTEXT_PROFILES_RESULT}`
- Large-task orchestration result: `{LARGE_TASK_ORCHESTRATION_RESULT_OR_SKIPPED}`
- Operation packet template result: `{OPERATION_PACKET_TEMPLATE_RESULT_OR_SKIPPED}`
- Source-of-truth registry result: `{SOURCE_OF_TRUTH_REGISTRY_RESULT}`
- Consistency-map result: `{CONSISTENCY_MAP_RESULT_OR_SKIPPED}`
- Task-specific maturity result: `{TASK_SPECIFIC_MATURITY_RESULT}`
- Operation help and routing result: `{OPERATION_HELP_ROUTING_RESULT}`
- Bridge capability matrix result: `{BRIDGE_CAPABILITY_MATRIX_RESULT}`
- Adapter drift checks result: `{ADAPTER_DRIFT_CHECKS_RESULT}`
- Local path leakage result: `{LOCAL_PATH_LEAKAGE_RESULT}`
- Target-local checker status: `{TARGET_LOCAL_CHECKER_STATUS_OR_UNRESOLVED}`
- Validation run: `{TARGET_VALIDATION_RUN_OR_MANUAL_REVIEW}`
- Validation skipped or unresolved: `{VALIDATION_SKIPPED_OR_UNRESOLVED}`
- Post-update message result: `{POST_UPDATE_MESSAGE_SENT_OR_SKIPPED}`
- Final evidence: `{FINAL_EVIDENCE}`
- Residual risk: `{RESIDUAL_RISK}`

## Contract: `adapter-recheck-output`

Use after read-only, adapter-only, or maturity-focused rechecks of an installed
adapter.

- Operation id: `{OPERATION_ID}`
- Operation type: `{ADAPTER_RECHECK_OR_MATURITY_REVIEW}`
- Recheck trigger: `{RECHECK_TRIGGER}`
- Allowed actions: `{READ_ONLY_DOCS_ONLY_ADAPTER_ONLY_CODE_AND_TESTS_OR_FULL_WITH_APPROVAL}`
- Manifest path: `.ai/alatyr.yaml`
- Installation note status: `{INSTALLATION_NOTE_STATUS}`
- Framework version: `{ALATYR_CORE_VERSION}`
- Adapter schema version: `{ALATYR_ADAPTER_SCHEMA_VERSION}`
- Template version: `{ALATYR_TEMPLATE_VERSION}`
- Approval records used: `{APPROVAL_RECORDS_USED_OR_NOT_REQUIRED}`
- Surfaces created: `{SURFACES_CREATED_OR_NONE}`
- Surfaces updated: `{SURFACES_UPDATED_OR_NONE}`
- Surfaces skipped: `{SURFACES_SKIPPED_AND_REASON}`
- Existing files preserved: `{EXISTING_FILES_PRESERVED}`
- Required core profile result: `{REQUIRED_CORE_PROFILE_RESULT}`
- Optional module profile result: `{OPTIONAL_MODULE_PROFILE_RESULT}`
- Context profiles result: `{CONTEXT_PROFILES_RESULT}`
- Large-task orchestration result: `{LARGE_TASK_ORCHESTRATION_RESULT_OR_SKIPPED}`
- Operation packet template result: `{OPERATION_PACKET_TEMPLATE_RESULT_OR_SKIPPED}`
- Source-of-truth registry result: `{SOURCE_OF_TRUTH_REGISTRY_RESULT}`
- Consistency-map result: `{CONSISTENCY_MAP_RESULT_OR_SKIPPED}`
- Task-specific maturity result: `{TASK_SPECIFIC_MATURITY_RESULT}`
- Bridge capability matrix result: `{BRIDGE_CAPABILITY_MATRIX_RESULT}`
- Operation help and routing result: `{OPERATION_HELP_ROUTING_RESULT}`
- Approval-record policy result: `{APPROVAL_RECORD_POLICY_RESULT}`
- Adapter drift checks result: `{ADAPTER_DRIFT_CHECKS_RESULT}`
- Local path leakage result: `{LOCAL_PATH_LEAKAGE_RESULT}`
- Target-local checker status: `{TARGET_LOCAL_CHECKER_STATUS_OR_UNRESOLVED}`
- AI infrastructure inventory result:
  `{AI_INFRASTRUCTURE_INVENTORY_RESULT_OR_SKIPPED}`
- Prompt-injection policy result: `{PROMPT_INJECTION_POLICY_RESULT}`
- Validation run: `{TARGET_VALIDATION_RUN_OR_MANUAL_REVIEW}`
- Validation skipped or unresolved: `{VALIDATION_SKIPPED_OR_UNRESOLVED}`
- Recommended next operation: `{RECOMMENDED_NEXT_OPERATION}`
- Final evidence: `{FINAL_EVIDENCE}`
- Residual risk: `{RESIDUAL_RISK}`
