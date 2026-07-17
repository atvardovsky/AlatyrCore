# Adapter Maturity Profile

Use this file in `{PROJECT_NAME}` to report adapter readiness by task type.

Replace placeholders with target facts before accepting installation.

## Overall Summary

Overall adapter state: `{INCOMPLETE_MINIMAL_USABLE_OR_MATURE}`
Last reviewed: `{LAST_REVIEW_DATE}`
Reviewed by: `{REVIEWER_OR_ROLE}`
Blocking gaps:

- `{BLOCKING_GAP}`

## Task-Specific Maturity

### Task Area: `documentation`

Task area: `documentation`
Maturity: `{INCOMPLETE_MINIMAL_USABLE_OR_MATURE}`
Supported work: `{DOCUMENTATION_SUPPORTED_WORK}`
Required context:

- `{DOCUMENTATION_REQUIRED_CONTEXT}`

Required owners present: `{YES_NO_DETAILS}`
Validation or manual review: `{DOCUMENTATION_VALIDATION_OR_REVIEW}`
Approval needs: `{DOCUMENTATION_APPROVAL_NEEDS}`
Blocking criteria: `{DOCUMENTATION_BLOCKERS_OR_NONE}`
Residual risks: `{DOCUMENTATION_RESIDUAL_RISKS}`
Final evidence: `{DOCUMENTATION_FINAL_EVIDENCE}`

### Task Area: `code-changes`

Task area: `code-changes`
Maturity: `{INCOMPLETE_MINIMAL_USABLE_OR_MATURE}`
Supported work: `{CODE_CHANGES_SUPPORTED_WORK}`
Required context:

- `{CODE_CHANGES_REQUIRED_CONTEXT}`

Required owners present: `{YES_NO_DETAILS}`
Validation or manual review: `{CODE_CHANGES_VALIDATION_OR_REVIEW}`
Approval needs: `{CODE_CHANGES_APPROVAL_NEEDS}`
Blocking criteria: `{CODE_CHANGES_BLOCKERS_OR_NONE}`
Residual risks: `{CODE_CHANGES_RESIDUAL_RISKS}`
Final evidence: `{CODE_CHANGES_FINAL_EVIDENCE}`

### Task Area: `architecture`

Task area: `architecture`
Maturity: `{INCOMPLETE_MINIMAL_USABLE_OR_MATURE}`
Supported work: `{ARCHITECTURE_SUPPORTED_WORK}`
Required context:

- `{ARCHITECTURE_REQUIRED_CONTEXT}`

Required owners present: `{YES_NO_DETAILS}`
Validation or manual review: `{ARCHITECTURE_VALIDATION_OR_REVIEW}`
Approval needs: `{ARCHITECTURE_APPROVAL_NEEDS}`
Blocking criteria: `{ARCHITECTURE_BLOCKERS_OR_NONE}`
Residual risks: `{ARCHITECTURE_RESIDUAL_RISKS}`
Final evidence: `{ARCHITECTURE_FINAL_EVIDENCE}`

### Task Area: `data`

Task area: `data`
Maturity: `{INCOMPLETE_MINIMAL_USABLE_OR_MATURE}`
Supported work: `{DATA_SUPPORTED_WORK}`
Required context:

- `{DATA_REQUIRED_CONTEXT}`

Required owners present: `{YES_NO_DETAILS}`
Validation or manual review: `{DATA_VALIDATION_OR_REVIEW}`
Approval needs: `{DATA_APPROVAL_NEEDS}`
Blocking criteria: `{DATA_BLOCKERS_OR_NONE}`
Residual risks: `{DATA_RESIDUAL_RISKS}`
Final evidence: `{DATA_FINAL_EVIDENCE}`

### Task Area: `security`

Task area: `security`
Maturity: `{INCOMPLETE_MINIMAL_USABLE_OR_MATURE}`
Supported work: `{SECURITY_SUPPORTED_WORK}`
Required context:

- `{SECURITY_REQUIRED_CONTEXT}`

Required owners present: `{YES_NO_DETAILS}`
Validation or manual review: `{SECURITY_VALIDATION_OR_REVIEW}`
Approval needs: `{SECURITY_APPROVAL_NEEDS}`
Blocking criteria: `{SECURITY_BLOCKERS_OR_NONE}`
Residual risks: `{SECURITY_RESIDUAL_RISKS}`
Final evidence: `{SECURITY_FINAL_EVIDENCE}`

### Task Area: `ai-infrastructure`

Task area: `ai-infrastructure`
Maturity: `{INCOMPLETE_MINIMAL_USABLE_OR_MATURE}`
Supported work: `{AI_INFRASTRUCTURE_SUPPORTED_WORK}`
Required context:

- `{AI_INFRASTRUCTURE_REQUIRED_CONTEXT}`

Required owners present: `{YES_NO_DETAILS}`
Validation or manual review: `{AI_INFRASTRUCTURE_VALIDATION_OR_REVIEW}`
Approval needs: `{AI_INFRASTRUCTURE_APPROVAL_NEEDS}`
Blocking criteria: `{AI_INFRASTRUCTURE_BLOCKERS_OR_NONE}`
Residual risks: `{AI_INFRASTRUCTURE_RESIDUAL_RISKS}`
Final evidence: `{AI_INFRASTRUCTURE_FINAL_EVIDENCE}`

### Task Area: `framework-upgrade`

Task area: `framework-upgrade`
Maturity: `{INCOMPLETE_MINIMAL_USABLE_OR_MATURE}`
Supported work: `{FRAMEWORK_UPGRADE_SUPPORTED_WORK}`
Required context:

- `{FRAMEWORK_UPGRADE_REQUIRED_CONTEXT}`

Required owners present: `{YES_NO_DETAILS}`
Validation or manual review: `{FRAMEWORK_UPGRADE_VALIDATION_OR_REVIEW}`
Approval needs: `{FRAMEWORK_UPGRADE_APPROVAL_NEEDS}`
Blocking criteria: `{FRAMEWORK_UPGRADE_BLOCKERS_OR_NONE}`
Residual risks: `{FRAMEWORK_UPGRADE_RESIDUAL_RISKS}`
Final evidence: `{FRAMEWORK_UPGRADE_FINAL_EVIDENCE}`

## Blocking Criteria

Security-sensitive work is blocked unless `{TARGET_SECURITY_OWNER}`,
`{TARGET_SECURITY_POLICY}`, validation, credential handling, and approval rules
are defined.

Data work is blocked unless `{TARGET_DATA_OWNER}`, migration or rollback
policy, validation, and approval rules are defined when destructive or live
data changes are possible.

AI infrastructure integration is blocked unless inventory, source access,
prompt-injection policy, provenance, permissions, and approval rules are
defined. When multiple items exist, stable item IDs, canonical sources,
activation triggers, gates, validation, output contracts, and adaptation
records must also be discoverable through the AI infrastructure router.
Recommendation maturity additionally requires bounded project-contour evidence,
existing-item-first comparison, labeled quality/context/maintenance estimates,
acceptance criteria, and a read-only handoff to protected change routes.
When recommendations claim cross-task patterns, maturity also requires the
target development-evidence index, owner, retention/privacy policy, bounded
references, lazy capture flow, and framework non-mutation boundary.

Framework upgrade work is blocked unless `.ai/alatyr.yaml`, installation note,
context profiles, module profile, bridge files, operation help, and
adapter-recheck flow are discoverable.

Broad cross-area consistency claims must report whether the optional
`consistency-map` module is enabled. If it is enabled, stale or missing fact
IDs and relationships are blockers for the affected closure; if it is not
enabled, report the additional discovery cost and residual coverage risk.

## Evidence

Report task area, maturity, blockers, missing facts, validation, approval
needs, and residual risk before broad work.
