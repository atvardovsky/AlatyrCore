# Alatyr Module Profile

Use this file in `{PROJECT_NAME}` to record which Alatyr Core capabilities are
required, enabled, deferred, disabled, not applicable, or blocked.

Replace placeholders with target facts before accepting installation.

## Required Core Profile

Core profile state: `{COMPLETE_OR_MISSING_GAPS}`
Last reviewed: `{LAST_REVIEW_DATE}`
Reviewed by: `{REVIEWER_OR_ROLE}`

Core item: `contours`
State: `{REQUIRED_ENABLED_OR_BLOCKED}`
Owner or file: `{TARGET_OWNER_OR_FILE}`
Required files:

- `{CONTOURS_REQUIRED_FILE}`

Evidence: `{EVIDENCE_OR_GAP}`
Validation or review: `{CONTOURS_VALIDATION_OR_REVIEW}`
Approval needs: `{CONTOURS_APPROVAL_NEEDS}`
Residual risk: `{CONTOURS_RESIDUAL_RISK}`

Core item: `manifest-and-versioning`
State: `{REQUIRED_ENABLED_OR_BLOCKED}`
Owner or file: `.ai/alatyr.yaml`
Required files:

- `.ai/alatyr.yaml`

Evidence: `{EVIDENCE_OR_GAP}`
Validation or review: `{MANIFEST_VERSIONING_VALIDATION_OR_REVIEW}`
Approval needs: `{MANIFEST_VERSIONING_APPROVAL_NEEDS}`
Residual risk: `{MANIFEST_VERSIONING_RESIDUAL_RISK}`

Core item: `adapter-ownership`
State: `{REQUIRED_ENABLED_OR_BLOCKED}`
Owner or file: `.ai/alatyr.yaml` and `{CODEOWNERS_OR_EQUIVALENT_OWNER_MAP}`
Required files:

- `.ai/alatyr.yaml`
- `{CODEOWNERS_OR_EQUIVALENT_OWNER_MAP}`

Evidence: `{EVIDENCE_OR_GAP}`
Validation or review: `{ADAPTER_OWNERSHIP_VALIDATION_OR_REVIEW}`
Approval needs: `{ADAPTER_OWNERSHIP_APPROVAL_NEEDS}`
Residual risk: `{ADAPTER_OWNERSHIP_RESIDUAL_RISK}`

Core item: `context-profiles`
State: `{REQUIRED_ENABLED_OR_BLOCKED}`
Owner or file: `.ai/assistant/context-profiles.md`
Required files:

- `.ai/assistant/context-profiles.md`

Evidence: `{EVIDENCE_OR_GAP}`
Validation or review: `{CONTEXT_PROFILES_VALIDATION_OR_REVIEW}`
Approval needs: `{CONTEXT_PROFILES_APPROVAL_NEEDS}`
Residual risk: `{CONTEXT_PROFILES_RESIDUAL_RISK}`

Core item: `source-of-truth-registry`
State: `{REQUIRED_ENABLED_OR_BLOCKED}`
Owner or file: `.ai/project/source-of-truth-registry.md`
Required files:

- `.ai/project/source-of-truth-registry.md`

Evidence: `{EVIDENCE_OR_GAP}`
Validation or review: `{SOURCE_OF_TRUTH_REGISTRY_VALIDATION_OR_REVIEW}`
Approval needs: `{SOURCE_OF_TRUTH_REGISTRY_APPROVAL_NEEDS}`
Residual risk: `{SOURCE_OF_TRUTH_REGISTRY_RESIDUAL_RISK}`

Core item: `risk-approval-integrity`
State: `{REQUIRED_ENABLED_OR_BLOCKED}`
Owner or file: `{TARGET_RISK_APPROVAL_INTEGRITY_OWNER}`
Required files:

- `{RISK_APPROVAL_INTEGRITY_REQUIRED_FILE}`

Evidence: `{EVIDENCE_OR_GAP}`
Validation or review: `{RISK_APPROVAL_INTEGRITY_VALIDATION_OR_REVIEW}`
Approval needs: `{RISK_APPROVAL_INTEGRITY_APPROVAL_NEEDS}`
Residual risk: `{RISK_APPROVAL_INTEGRITY_RESIDUAL_RISK}`

Core item: `validation-and-final-evidence`
State: `{REQUIRED_ENABLED_OR_BLOCKED}`
Owner or file: `{TARGET_VALIDATION_OR_EVIDENCE_OWNER}`
Required files:

- `{VALIDATION_AND_EVIDENCE_REQUIRED_FILE}`

Evidence: `{EVIDENCE_OR_GAP}`
Validation or review: `{VALIDATION_AND_EVIDENCE_VALIDATION_OR_REVIEW}`
Approval needs: `{VALIDATION_AND_EVIDENCE_APPROVAL_NEEDS}`
Residual risk: `{VALIDATION_AND_EVIDENCE_RESIDUAL_RISK}`

## Optional Modules

Module: `blueprint-change`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `{TARGET_BLUEPRINT_MODULE_OWNER_OR_FILE}`
Required files:

- `{BLUEPRINT_CHANGE_REQUIRED_FILE}`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{BLUEPRINT_CHANGE_APPROVAL_NEEDS}`
Residual risk: `{BLUEPRINT_CHANGE_RESIDUAL_RISK}`
Next action: `{BLUEPRINT_CHANGE_NEXT_ACTION}`

Module: `consistency-map`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/project/consistency-map.json`
Required files:

- `.ai/project/source-of-truth-registry.md`
- `.ai/project/consistency-map.json`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{CONSISTENCY_MAP_APPROVAL_NEEDS}`
Residual risk: `{CONSISTENCY_MAP_RESIDUAL_RISK}`
Next action: `{CONSISTENCY_MAP_NEXT_ACTION}`

Module: `diagrams`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `{TARGET_DIAGRAM_MODULE_OWNER_OR_FILE}`
Required files:

- `{DIAGRAM_MODULE_REQUIRED_FILE}`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{DIAGRAM_MODULE_APPROVAL_NEEDS}`
Residual risk: `{DIAGRAM_MODULE_RESIDUAL_RISK}`
Next action: `{DIAGRAM_MODULE_NEXT_ACTION}`

Module: `ai-infrastructure`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `{TARGET_AI_INFRASTRUCTURE_MODULE_OWNER_OR_FILE}`
Required files:

- `.ai/assistant/ai-infrastructure-router.json`
- `.ai/assistant/flows/ai-infrastructure-inventory.flow.md`
- `.ai/assistant/flows/skill-adaptation.flow.md`
- `.ai/assistant/templates/ai-infrastructure-adaptation-record.md`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{AI_INFRASTRUCTURE_MODULE_APPROVAL_NEEDS}`
Residual risk: `{AI_INFRASTRUCTURE_MODULE_RESIDUAL_RISK}`
Next action: `{AI_INFRASTRUCTURE_MODULE_NEXT_ACTION}`

Module: `multi-assistant-bridges`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/assistant/bridge-capability-matrix.md`
Required files:

- `.ai/assistant/bridge-capability-matrix.md`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{MULTI_ASSISTANT_BRIDGES_APPROVAL_NEEDS}`
Residual risk: `{MULTI_ASSISTANT_BRIDGES_RESIDUAL_RISK}`
Next action: `{MULTI_ASSISTANT_BRIDGES_NEXT_ACTION}`

Module: `installed-operations`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/assistant/help.md`
Required files:

- `.ai/assistant/help.md`
- `.ai/assistant/help-reference.md`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{INSTALLED_OPERATIONS_APPROVAL_NEEDS}`
Residual risk: `{INSTALLED_OPERATIONS_RESIDUAL_RISK}`
Next action: `{INSTALLED_OPERATIONS_NEXT_ACTION}`

Module: `large-task-orchestration`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/assistant/flows/large-task-orchestration.flow.md`
Required files:

- `.ai/assistant/flows/large-task-orchestration.flow.md`
- `.ai/assistant/templates/large-task-operation-packet.md`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{LARGE_TASK_ORCHESTRATION_APPROVAL_NEEDS}`
Residual risk: `{LARGE_TASK_ORCHESTRATION_RESIDUAL_RISK}`
Next action: `{LARGE_TASK_ORCHESTRATION_NEXT_ACTION}`

Module: `durable-approvals`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/assistant/approvals/approval-template.md`
Required files:

- `.ai/assistant/approvals/approval-template.md`
- `.ai/assistant/approvals/approval-record-template.json`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{DURABLE_APPROVALS_APPROVAL_NEEDS}`
Residual risk: `{DURABLE_APPROVALS_RESIDUAL_RISK}`
Next action: `{DURABLE_APPROVALS_NEXT_ACTION}`

Module: `migration-diff`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/assistant/templates/migration-note.md`
Required files:

- `.ai/assistant/templates/migration-note.md`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{MIGRATION_DIFF_APPROVAL_NEEDS}`
Residual risk: `{MIGRATION_DIFF_RESIDUAL_RISK}`
Next action: `{MIGRATION_DIFF_NEXT_ACTION}`

Module: `effectiveness-metrics`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/assistant/templates/effectiveness-report.md`
Required files:

- `.ai/assistant/templates/effectiveness-report.md`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{EFFECTIVENESS_METRICS_APPROVAL_NEEDS}`
Residual risk: `{EFFECTIVENESS_METRICS_RESIDUAL_RISK}`
Next action: `{EFFECTIVENESS_METRICS_NEXT_ACTION}`

Module: `scaffolding`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `{TARGET_SCAFFOLDING_EVIDENCE_OR_NONE}`
Required files:

- `{SCAFFOLDING_REQUIRED_FILE_OR_NONE}`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{SCAFFOLDING_APPROVAL_NEEDS}`
Residual risk: `{SCAFFOLDING_RESIDUAL_RISK}`
Next action: `{SCAFFOLDING_NEXT_ACTION}`

## Evidence

Report enabled modules, deferred modules, blocked modules, files created or
skipped, validation, approvals, and residual risk before claiming adapter
maturity.
