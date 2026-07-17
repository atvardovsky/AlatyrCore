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
Consistency level: `{PRODUCT_BEHAVIOR_CONSISTENCY_LEVEL}`
Project area: `{PRODUCT_BEHAVIOR_PROJECT_AREA}`
Consistency map node: `{PRODUCT_BEHAVIOR_FACT_ID_OR_MISSING}`
Relationship coverage: `{PRODUCT_BEHAVIOR_RELATIONSHIP_COVERAGE_OR_GAP}`
Invariant and dependency constraints: `{PRODUCT_BEHAVIOR_INVARIANTS_AND_DEPENDENCIES}`
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
Consistency level: `{BUSINESS_RULE_CONSISTENCY_LEVEL}`
Project area: `{BUSINESS_RULE_PROJECT_AREA}`
Consistency map node: `{BUSINESS_RULE_FACT_ID_OR_MISSING}`
Relationship coverage: `{BUSINESS_RULE_RELATIONSHIP_COVERAGE_OR_GAP}`
Invariant and dependency constraints: `{BUSINESS_RULE_INVARIANTS_AND_DEPENDENCIES}`
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
Consistency level: `{ARCHITECTURE_DECISION_CONSISTENCY_LEVEL}`
Project area: `{ARCHITECTURE_DECISION_PROJECT_AREA}`
Consistency map node: `{ARCHITECTURE_DECISION_FACT_ID_OR_MISSING}`
Relationship coverage: `{ARCHITECTURE_DECISION_RELATIONSHIP_COVERAGE_OR_GAP}`
Invariant and dependency constraints: `{ARCHITECTURE_DECISION_INVARIANTS_AND_DEPENDENCIES}`
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
Consistency level: `{DATA_MODEL_CONSISTENCY_LEVEL}`
Project area: `{DATA_MODEL_PROJECT_AREA}`
Consistency map node: `{DATA_MODEL_FACT_ID_OR_MISSING}`
Relationship coverage: `{DATA_MODEL_RELATIONSHIP_COVERAGE_OR_GAP}`
Invariant and dependency constraints: `{DATA_MODEL_INVARIANTS_AND_DEPENDENCIES}`
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
Consistency level: `{VALIDATION_COMMAND_CONSISTENCY_LEVEL}`
Project area: `{VALIDATION_COMMAND_PROJECT_AREA}`
Consistency map node: `{VALIDATION_COMMAND_FACT_ID_OR_MISSING}`
Relationship coverage: `{VALIDATION_COMMAND_RELATIONSHIP_COVERAGE_OR_GAP}`
Invariant and dependency constraints: `{VALIDATION_COMMAND_INVARIANTS_AND_DEPENDENCIES}`
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
Consistency level: `{SECURITY_POLICY_CONSISTENCY_LEVEL}`
Project area: `{SECURITY_POLICY_PROJECT_AREA}`
Consistency map node: `{SECURITY_POLICY_FACT_ID_OR_MISSING}`
Relationship coverage: `{SECURITY_POLICY_RELATIONSHIP_COVERAGE_OR_GAP}`
Invariant and dependency constraints: `{SECURITY_POLICY_INVARIANTS_AND_DEPENDENCIES}`
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
Consistency level: `{ASSISTANT_OPERATION_CONSISTENCY_LEVEL}`
Project area: `{ASSISTANT_OPERATION_PROJECT_AREA}`
Consistency map node: `{ASSISTANT_OPERATION_FACT_ID_OR_MISSING}`
Relationship coverage: `{ASSISTANT_OPERATION_RELATIONSHIP_COVERAGE_OR_GAP}`
Invariant and dependency constraints: `{ASSISTANT_OPERATION_INVARIANTS_AND_DEPENDENCIES}`
Derived surfaces:

- `{ASSISTANT_OPERATION_DERIVED_SURFACE}`

Sync direction: `{ASSISTANT_OPERATION_SYNC_DIRECTION}`
Validation or manual review: `{ASSISTANT_OPERATION_VALIDATION_OR_REVIEW}`
Conflict resolver: `{ASSISTANT_OPERATION_CONFLICT_RESOLVER}`
Approval trigger: `{ASSISTANT_OPERATION_APPROVAL_TRIGGER}`
Final evidence: `{ASSISTANT_OPERATION_FINAL_EVIDENCE}`

### Fact Type: `development process pattern`

Fact type: `development process pattern`
Canonical owner: `.ai/project/development-evidence.json`
Consistency level: `{DEVELOPMENT_PATTERN_CONSISTENCY_LEVEL}`
Project area: `{DEVELOPMENT_PATTERN_PROJECT_AREA}`
Consistency map node: `{DEVELOPMENT_PATTERN_CONSISTENCY_MAP_NODE_OR_NONE}`
Relationship coverage: `{DEVELOPMENT_PATTERN_RELATIONSHIP_COVERAGE}`
Invariant and dependency constraints: `{DEVELOPMENT_PATTERN_CONSTRAINTS}`
Derived surfaces:

- `{DEVELOPMENT_PATTERN_RECOMMENDATIONS_OR_NONE}`

Sync direction: `{DEVELOPMENT_EVIDENCE_TO_RECOMMENDATION_REVIEW}`
Validation or manual review: `{DEVELOPMENT_EVIDENCE_VALIDATION_OR_REVIEW}`
Conflict resolver: `{DEVELOPMENT_EVIDENCE_CONFLICT_RESOLVER}`
Approval trigger: `{DEVELOPMENT_EVIDENCE_APPROVAL_TRIGGER}`
Final evidence: `{DEVELOPMENT_EVIDENCE_FINAL_EVIDENCE}`

### Fact Type: `AI infrastructure item`

Fact type: `AI infrastructure item`
Canonical owner: `{AI_INFRASTRUCTURE_ITEM_CANONICAL_OWNER}`
AI infrastructure router item: `{AI_INFRASTRUCTURE_ITEM_ID}`
Adaptation record: `{AI_INFRASTRUCTURE_ADAPTATION_RECORD_OR_NOT_APPLICABLE}`
Project-contour need and outcome owner: `{AI_INFRASTRUCTURE_PROJECT_NEED_AND_OUTCOME_OWNER}`
Recommendation record: `{AI_INFRASTRUCTURE_RECOMMENDATION_RECORD_OR_NOT_APPLICABLE}`
Consistency level: `{AI_INFRASTRUCTURE_ITEM_CONSISTENCY_LEVEL}`
Project area: `{AI_INFRASTRUCTURE_ITEM_PROJECT_AREA}`
Consistency map node: `{AI_INFRASTRUCTURE_ITEM_FACT_ID_OR_MISSING}`
Relationship coverage: `{AI_INFRASTRUCTURE_ITEM_RELATIONSHIP_COVERAGE_OR_GAP}`
Invariant and dependency constraints: `{AI_INFRASTRUCTURE_ITEM_INVARIANTS_AND_DEPENDENCIES}`
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
3. Use `.ai/project/consistency-map.json` to build the applicable relationship
   closure when that optional module is enabled.
4. Re-derive the invariant and dependency constraints. If the optional map is
   disabled or incomplete, use those constraints for a compact manual closure.
5. If ownership or relationship coverage is missing, report
   `{MISSING_SOURCE_OF_TRUTH_OR_RELATIONSHIP_POLICY}`.
6. Repair only the smallest coherent set of selected relationship surfaces.
7. Report invariant results, selected and skipped edges, validation,
   approvals, and residual risk.
