# Alatyr Module Profile

Use this file in `{PROJECT_NAME}` to record which Alatyr Core capabilities are
required, enabled, deferred, disabled, not applicable, or blocked.

Replace placeholders with target facts before accepting installation.
An optional module owner may be absent from a selective framework pack; install
it through reviewed pack expansion before enabling that module.

## Required Core Profile

Core profile state: `{COMPLETE_OR_MISSING_GAPS}`
Framework pack: `{CORE_STANDARD_OR_COMPLETE}`
Pack inventory: `.ai/framework/file-inventory.json`
Required pack expansion: `{NONE_OR_MODULE_OWNERS_TO_ADD}`
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

- `.ai/assistant/flows/blueprint-driven-change.flow.md`
- `.ai/assistant/flows/project-blueprint-creation.flow.md`

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

Module: `architecture-knowledge`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/project/architecture/README.md`
Required files:

- `.ai/project/architecture/README.md`
- `.ai/project/architecture/catalog.json`
- `.ai/assistant/flows/architecture-assistance.flow.md`
- `.ai/assistant/templates/architecture-pattern.md`
- `.ai/assistant/templates/architecture-area.md`
- `.ai/assistant/templates/architecture-discussion-result.md`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{ARCHITECTURE_KNOWLEDGE_APPROVAL_NEEDS}`
Residual risk: `{ARCHITECTURE_KNOWLEDGE_RESIDUAL_RISK}`
Next action: `{ARCHITECTURE_KNOWLEDGE_NEXT_ACTION}`

Module: `code-documentation`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/project/documentation/README.md`
Required files:

- `.ai/framework/code-documentation.md`
- `.ai/project/documentation/README.md`
- `.ai/project/documentation/catalog.json`
- `.ai/project/documentation/profiles.json`
- `.ai/assistant/context/intents/code-documentation.json`
- `.ai/assistant/flows/documentation-sync.flow.md`
- `.ai/assistant/templates/code-documentation-profile-review.md`
- `.ai/assistant/skills/code-documentation/SKILL.md`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{CODE_DOCUMENTATION_APPROVAL_NEEDS}`
Residual risk: `{CODE_DOCUMENTATION_RESIDUAL_RISK}`
Next action: `{CODE_DOCUMENTATION_NEXT_ACTION}`

Module: `project-vocabulary`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/project/vocabulary/README.md`
Required files:

- `.ai/framework/project-vocabulary.md`
- `.ai/project/vocabulary/README.md`
- `.ai/project/vocabulary/catalog.json`
- `.ai/project/vocabulary/terms.json`
- `.ai/project/vocabulary/data-dictionary-links.json`
- `.ai/assistant/context/intents/vocabulary-request.json`
- `.ai/assistant/flows/project-vocabulary.flow.md`
- `.ai/assistant/templates/vocabulary-term-review.md`
- `.ai/assistant/skills/project-vocabulary/SKILL.md`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{PROJECT_VOCABULARY_APPROVAL_NEEDS}`
Residual risk: `{PROJECT_VOCABULARY_RESIDUAL_RISK}`
Next action: `{PROJECT_VOCABULARY_NEXT_ACTION}`

Module: `test-first-development`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/project/testing/test-first-policy.json`
Required files:

- `.ai/framework/test-first-development.md`
- `.ai/project/testing/README.md`
- `.ai/project/testing/test-first-policy.json`
- `.ai/assistant/context/intents/test-first-request.json`
- `.ai/assistant/flows/test-first-configuration.flow.md`
- `.ai/assistant/flows/test-first-change.flow.md`
- `.ai/assistant/gates/test-first-development.md`
- `.ai/assistant/templates/test-first-evidence.md`
- `.ai/assistant/skills/test-first-development/SKILL.md`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{TEST_FIRST_DEVELOPMENT_APPROVAL_NEEDS}`
Residual risk: `{TEST_FIRST_DEVELOPMENT_RESIDUAL_RISK}`
Next action: `{TEST_FIRST_DEVELOPMENT_NEXT_ACTION}`

Module: `extensions`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/assistant/extensions/README.md`
Required files:

- `.ai/framework/extensions.md`
- `.ai/assistant/extensions/README.md`
- `.ai/assistant/extensions/catalog.json`
- `.ai/assistant/extensions/lock.json`
- `.ai/assistant/context/intents/extension-request.json`
- `.ai/assistant/flows/extension-lifecycle.flow.md`
- `.ai/assistant/gates/extensions.md`
- `.ai/assistant/templates/extension-review.md`
- `.ai/assistant/templates/extension-lifecycle-record.md`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{EXTENSIONS_APPROVAL_NEEDS}`
Residual risk: `{EXTENSIONS_RESIDUAL_RISK}`
Next action: `{EXTENSIONS_NEXT_ACTION}`

Module: `diagrams`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `{TARGET_DIAGRAM_MODULE_OWNER_OR_FILE}`
Required files:

- `{TARGET_DIAGRAM_POLICY_OR_SOURCE_OWNER}`
- `.ai/assistant/flows/diagram-discussion.flow.md`
- `.ai/assistant/templates/diagram-presentation.md`
- `.ai/assistant/templates/ascii-diagram.md`
- `.ai/assistant/assistant-capabilities.json`
- `.ai/assistant/assistant-capabilities/{SUPPORTED_ASSISTANT}.json`
- `.ai/assistant/bridge-capability-matrix.md`

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
- `.ai/assistant/flows/ai-infrastructure-recommendation.flow.md`
- `.ai/assistant/flows/development-evidence-capture.flow.md`
- `.ai/assistant/flows/skill-adaptation.flow.md`
- `.ai/assistant/templates/ai-infrastructure-recommendation.md`
- `.ai/assistant/templates/ai-infrastructure-adaptation-record.md`
- `.ai/project/development-evidence.json`

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
- `.ai/assistant/assistant-capabilities.json`
- `.ai/assistant/assistant-capabilities/{SUPPORTED_ASSISTANT}.json`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{MULTI_ASSISTANT_BRIDGES_APPROVAL_NEEDS}`
Residual risk: `{MULTI_ASSISTANT_BRIDGES_RESIDUAL_RISK}`
Next action: `{MULTI_ASSISTANT_BRIDGES_NEXT_ACTION}`

Module: `installed-operations`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/assistant/operation-catalog.json`
Required files:

- `.ai/assistant/operation-index.json`
- `.ai/assistant/operation-catalog.json`
- `.ai/assistant/help.md`
- `.ai/assistant/help-reference.md`
- `.ai/assistant/flows/operation-routing.flow.md`
- `.ai/assistant/flows/adapter-health.flow.md`
- `.ai/assistant/templates/pre-change-preview.md`

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

Module: `subagent-delegation`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/assistant/delegation-policy.json`
Required files:

- `.ai/assistant/delegation-policy.json`
- `.ai/assistant/context/task-scales/delegated-execution.json`
- `.ai/assistant/flows/subagent-delegation.flow.md`
- `.ai/assistant/templates/subagent-task-packet.md`
- `.ai/assistant/assistant-capabilities.json`
- `.ai/assistant/bridge-capability-matrix.md`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{SUBAGENT_DELEGATION_APPROVAL_NEEDS}`
Residual risk: `{SUBAGENT_DELEGATION_RESIDUAL_RISK}`
Next action: `{SUBAGENT_DELEGATION_NEXT_ACTION}`

Module: `change-packages`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/assistant/change-packages/index.json`
Required files:

- `.ai/framework/change-packages.md`
- `.ai/assistant/change-packages/index.json`
- `.ai/assistant/context/task-scales/change-package.json`
- `.ai/assistant/flows/change-package.flow.md`
- `.ai/assistant/templates/change-package-record.json`
- `.ai/assistant/templates/change-package-report.md`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{CHANGE_PACKAGES_APPROVAL_NEEDS}`
Residual risk: `{CHANGE_PACKAGES_RESIDUAL_RISK}`
Next action: `{CHANGE_PACKAGES_NEXT_ACTION}`

Module: `team-collaboration`
State: `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
Owner or file: `.ai/project/team-policy.json`
Required files:

- `.ai/framework/team-collaboration.md`
- `.ai/.gitignore`
- `.ai/project/team-policy.json`
- `.ai/project/team-operating-model.md`
- `.ai/assistant/team/context-overlay.json`
- `.ai/assistant/team/work-registry.json`
- `.ai/assistant/team/active-work-index.json`
- `.ai/assistant/team/backend-contract.json`
- `.ai/assistant/team/task-record-template.json`
- `.ai/assistant/flows/team-identity.flow.md`
- `.ai/assistant/flows/team-task-coordination.flow.md`
- `.ai/assistant/flows/team-handoff.flow.md`
- `.ai/assistant/flows/team-decision.flow.md`
- `.ai/assistant/flows/team-review.flow.md`
- `.ai/assistant/gates/team-collaboration.md`
- `.ai/assistant/templates/team-checkpoint.md`
- `.ai/assistant/templates/team-handoff.md`
- `.ai/assistant/templates/team-decision-record.md`
- `.ai/assistant/templates/team-identity.example.json`
- `.ai/assistant/templates/team-collaboration-review.md`
- `.ai/assistant/skills/team-collaboration/SKILL.md`

Reason: `{REASON}`
Validation or review: `{VALIDATION_OR_REVIEW}`
Approval needs: `{TEAM_COLLABORATION_APPROVAL_NEEDS}`
Residual risk: `{TEAM_COLLABORATION_RESIDUAL_RISK}`
Next action: `{TEAM_COLLABORATION_NEXT_ACTION}`

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
