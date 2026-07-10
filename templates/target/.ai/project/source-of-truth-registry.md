# Source Of Truth Registry

Use this registry in `{PROJECT_NAME}` to decide which file owns each fact type.

Replace placeholders with target facts before accepting installation.

## Baseline Registry Entries

Resolve these entries from target evidence or mark the owner as missing before
accepting installation. Add target-specific entries when other fact types can
have competing owners or derived surfaces.

### Fact Type: `product behavior`

Fact type: `product behavior`
Canonical owner: `{PRODUCT_BEHAVIOR_CANONICAL_OWNER}`
Derived surfaces:

- `{PRODUCT_BEHAVIOR_DERIVED_SURFACE}`

Sync direction: `{PRODUCT_BEHAVIOR_SYNC_DIRECTION}`
Validation or manual review: `{PRODUCT_BEHAVIOR_VALIDATION_OR_REVIEW}`
Conflict resolver: `{PRODUCT_BEHAVIOR_CONFLICT_RESOLVER}`
Approval trigger: `{PRODUCT_BEHAVIOR_APPROVAL_TRIGGER}`
Final evidence: `{PRODUCT_BEHAVIOR_FINAL_EVIDENCE}`

### Fact Type: `business rule`

Fact type: `business rule`
Canonical owner: `{BUSINESS_RULE_CANONICAL_OWNER}`
Derived surfaces:

- `{BUSINESS_RULE_DERIVED_SURFACE}`

Sync direction: `{BUSINESS_RULE_SYNC_DIRECTION}`
Validation or manual review: `{BUSINESS_RULE_VALIDATION_OR_REVIEW}`
Conflict resolver: `{BUSINESS_RULE_CONFLICT_RESOLVER}`
Approval trigger: `{BUSINESS_RULE_APPROVAL_TRIGGER}`
Final evidence: `{BUSINESS_RULE_FINAL_EVIDENCE}`

### Fact Type: `architecture decision`

Fact type: `architecture decision`
Canonical owner: `{ARCHITECTURE_DECISION_CANONICAL_OWNER}`
Derived surfaces:

- `{ARCHITECTURE_DECISION_DERIVED_SURFACE}`

Sync direction: `{ARCHITECTURE_DECISION_SYNC_DIRECTION}`
Validation or manual review: `{ARCHITECTURE_DECISION_VALIDATION_OR_REVIEW}`
Conflict resolver: `{ARCHITECTURE_DECISION_CONFLICT_RESOLVER}`
Approval trigger: `{ARCHITECTURE_DECISION_APPROVAL_TRIGGER}`
Final evidence: `{ARCHITECTURE_DECISION_FINAL_EVIDENCE}`

### Fact Type: `data model`

Fact type: `data model`
Canonical owner: `{DATA_MODEL_CANONICAL_OWNER}`
Derived surfaces:

- `{DATA_MODEL_DERIVED_SURFACE}`

Sync direction: `{DATA_MODEL_SYNC_DIRECTION}`
Validation or manual review: `{DATA_MODEL_VALIDATION_OR_REVIEW}`
Conflict resolver: `{DATA_MODEL_CONFLICT_RESOLVER}`
Approval trigger: `{DATA_MODEL_APPROVAL_TRIGGER}`
Final evidence: `{DATA_MODEL_FINAL_EVIDENCE}`

### Fact Type: `validation command`

Fact type: `validation command`
Canonical owner: `{VALIDATION_COMMAND_CANONICAL_OWNER}`
Derived surfaces:

- `{VALIDATION_COMMAND_DERIVED_SURFACE}`

Sync direction: `{VALIDATION_COMMAND_SYNC_DIRECTION}`
Validation or manual review: `{VALIDATION_COMMAND_VALIDATION_OR_REVIEW}`
Conflict resolver: `{VALIDATION_COMMAND_CONFLICT_RESOLVER}`
Approval trigger: `{VALIDATION_COMMAND_APPROVAL_TRIGGER}`
Final evidence: `{VALIDATION_COMMAND_FINAL_EVIDENCE}`

### Fact Type: `security policy`

Fact type: `security policy`
Canonical owner: `{SECURITY_POLICY_CANONICAL_OWNER}`
Derived surfaces:

- `{SECURITY_POLICY_DERIVED_SURFACE}`

Sync direction: `{SECURITY_POLICY_SYNC_DIRECTION}`
Validation or manual review: `{SECURITY_POLICY_VALIDATION_OR_REVIEW}`
Conflict resolver: `{SECURITY_POLICY_CONFLICT_RESOLVER}`
Approval trigger: `{SECURITY_POLICY_APPROVAL_TRIGGER}`
Final evidence: `{SECURITY_POLICY_FINAL_EVIDENCE}`

### Fact Type: `assistant operation`

Fact type: `assistant operation`
Canonical owner: `{ASSISTANT_OPERATION_CANONICAL_OWNER}`
Derived surfaces:

- `{ASSISTANT_OPERATION_DERIVED_SURFACE}`

Sync direction: `{ASSISTANT_OPERATION_SYNC_DIRECTION}`
Validation or manual review: `{ASSISTANT_OPERATION_VALIDATION_OR_REVIEW}`
Conflict resolver: `{ASSISTANT_OPERATION_CONFLICT_RESOLVER}`
Approval trigger: `{ASSISTANT_OPERATION_APPROVAL_TRIGGER}`
Final evidence: `{ASSISTANT_OPERATION_FINAL_EVIDENCE}`

### Fact Type: `AI infrastructure item`

Fact type: `AI infrastructure item`
Canonical owner: `{AI_INFRASTRUCTURE_ITEM_CANONICAL_OWNER}`
Derived surfaces:

- `{AI_INFRASTRUCTURE_ITEM_DERIVED_SURFACE}`

Sync direction: `{AI_INFRASTRUCTURE_ITEM_SYNC_DIRECTION}`
Validation or manual review: `{AI_INFRASTRUCTURE_ITEM_VALIDATION_OR_REVIEW}`
Conflict resolver: `{AI_INFRASTRUCTURE_ITEM_CONFLICT_RESOLVER}`
Approval trigger: `{AI_INFRASTRUCTURE_ITEM_APPROVAL_TRIGGER}`
Final evidence: `{AI_INFRASTRUCTURE_ITEM_FINAL_EVIDENCE}`

## Conflict Handling

When sources disagree:

1. Identify the fact type.
2. Use this registry to find the canonical owner and derived surfaces.
3. If ownership is missing, report `{MISSING_SOURCE_OF_TRUTH_POLICY}`.
4. Repair only the smallest coherent set of derived surfaces.
5. Report validation, skipped checks, approvals, and residual risk.
