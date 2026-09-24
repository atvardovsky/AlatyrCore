# Source Of Truth Registry

Use this registry in `{PROJECT_NAME}` to decide which file owns each fact type.

Replace placeholders with target facts before accepting installation.

## Baseline Registry Entries

Resolve each entry from target evidence before acceptance; mark unresolved
owners missing and add target-specific fact types when needed. Applicable facts
require accepted authority, decision source, evidence revision, review date,
and gap severity. Other authority states are noncanonical. `not-applicable`
requires target evidence and decision authority.

Section-local compact fields retain evidence at lower context cost. Replace
each placeholder within its Fact Type section:

- `Authority`: `ap` applicability, `st` authority state, `ds` decision source,
  `er` evidence revision, `at` reviewed-at date, `gs` gap severity.
- `Routing`: `cl` consistency level, `pa` project area, `cn` consistency node,
  `rc` relationship coverage.

With `consistency-map` enabled, every live Fact Type entry names one unique
resolved node whose `fact_type` matches the heading. Extra nodes may represent
derived surfaces. Each relationship candidate requires owner review; it is
neither an accepted edge nor a source of truth.

### Fact Type: `product behavior`

Fact type: `product behavior`
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `{PRODUCT_BEHAVIOR_CANONICAL_OWNER}`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
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
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `{BUSINESS_RULE_CANONICAL_OWNER}`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
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
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `{ARCHITECTURE_DECISION_CANONICAL_OWNER}`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
Invariant and dependency constraints: `{ARCHITECTURE_DECISION_INVARIANTS_AND_DEPENDENCIES}`
Derived surfaces:

- `{ARCHITECTURE_DECISION_DERIVED_SURFACE}`

Sync direction: `{ARCHITECTURE_DECISION_SYNC_DIRECTION}`
Validation or manual review: `{ARCHITECTURE_DECISION_VALIDATION_OR_REVIEW}`
Conflict resolver: `{ARCHITECTURE_DECISION_CONFLICT_RESOLVER}`
Approval trigger: `{ARCHITECTURE_DECISION_APPROVAL_TRIGGER}`
Final evidence: `{ARCHITECTURE_DECISION_FINAL_EVIDENCE}`

### Fact Type: `architecture pattern`

Fact type: `architecture pattern`
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `{ARCHITECTURE_PATTERN_CANONICAL_OWNER}`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
Invariant and dependency constraints: `{ARCHITECTURE_PATTERN_INVARIANTS_AND_DEPENDENCIES}`
Derived surfaces:

- `{ARCHITECTURE_PATTERN_DERIVED_SURFACE}`
- `.ai/project/architecture/catalog.json`

Sync direction: `{ARCHITECTURE_PATTERN_SYNC_DIRECTION}`
Validation or manual review: `{ARCHITECTURE_PATTERN_VALIDATION_OR_REVIEW}`
Conflict resolver: `{ARCHITECTURE_PATTERN_CONFLICT_RESOLVER}`
Approval trigger: `{ARCHITECTURE_PATTERN_APPROVAL_TRIGGER}`
Final evidence: `{ARCHITECTURE_PATTERN_FINAL_EVIDENCE}`

### Fact Type: `data model`

Fact type: `data model`
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `{DATA_MODEL_CANONICAL_OWNER}`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
Invariant and dependency constraints: `{DATA_MODEL_INVARIANTS_AND_DEPENDENCIES}`
Derived surfaces:

- `{DATA_MODEL_DERIVED_SURFACE}`

Sync direction: `{DATA_MODEL_SYNC_DIRECTION}`
Validation or manual review: `{DATA_MODEL_VALIDATION_OR_REVIEW}`
Conflict resolver: `{DATA_MODEL_CONFLICT_RESOLVER}`
Approval trigger: `{DATA_MODEL_APPROVAL_TRIGGER}`
Final evidence: `{DATA_MODEL_FINAL_EVIDENCE}`

### Fact Type: `dependency public contract and target use`

Fact type: `dependency public contract and target use`
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Upstream public fact owner: `{DEPENDENCY_PUBLIC_FACT_OWNER_OR_MISSING}`
Target configuration, restriction, wrapper, or patch owner: `{TARGET_DEPENDENCY_USE_OWNER_OR_MISSING}`
Cross-package integration owner: `{DEPENDENCY_INTEGRATION_OWNER_OR_MISSING}`
Dependency knowledge policy: `.ai/project/dependencies/policy.json`
Dependency knowledge catalog: `.ai/project/dependencies/catalog.json`
Target deviations: `.ai/project/dependencies/deviations.json`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
Invariant and dependency constraints: `{PACKAGE_IDENTITY_PUBLIC_CONTRACT_TARGET_USE_PATCH_APPLICABILITY_AND_INTEGRATION_CONSTRAINTS}`
Derived surfaces:

- `.ai/project/dependencies/knowledge-lock.json`
- `{DEPENDENCY_FACT_DERIVED_TARGET_SURFACE_OR_NONE}`

Sync direction: `{UPSTREAM_EXPORT_TO_REVIEWED_PROJECTION_AND_TARGET_DECISION_TO_DEVIATION}`
Validation or manual review: `{DEPENDENCY_IDENTITY_EXPORT_PROJECTION_AND_TARGET_VALIDATION}`
Conflict resolver: `{DEPENDENCY_FACT_CONFLICT_RESOLVER}`
Approval trigger: `{DEPENDENCY_TARGET_FACT_OR_PROTECTED_CHANGE_TRIGGER}`
Final evidence: `{PACKAGE_INSTANCE_FACT_STATES_DEVIATIONS_IMPACT_VALIDATION_AND_RESIDUAL_RISK}`

### Fact Type: `workspace identity and development mode relationship`

Fact type: `workspace identity and development mode relationship`
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `.ai/project/workspace-modes/catalog.json` and the selected
`.ai/project/workspace-modes/modes/{MODE_ID}/mode.json`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
Invariant and dependency constraints: `{WORKSPACE_IDENTITY_MODE_RELATIONSHIP_ADAPTER_ROLE_OWNERSHIP_SELECTION_AND_NO_GRANTS_CONSTRAINTS}`
Derived surfaces:

- `.ai/assistant/context-router.json`
- `.ai/assistant/templates/workspace-mode-preflight.md`
- `{WORKSPACE_MODE_DERIVED_TASK_OR_OPERATION_EVIDENCE}`

Sync direction: `{USER_DECISION_AND_REPOSITORY_EVIDENCE_TO_CATALOG_DESCRIPTOR_AND_ROUTED_EVIDENCE}`
Validation or manual review: `{WORKSPACE_MODE_VALIDATION_OR_REVIEW}`
Conflict resolver: `{TARGET_WORKSPACE_MODE_DECISION_OWNER}`
Approval trigger: `{WORKSPACE_MODE_PROJECT_FACT_OR_PROTECTED_CHANGE_TRIGGER}`
Final evidence: `{WORKSPACE_MODE_SELECTION_RELATIONSHIPS_CONTEXT_DECISION_VALIDATION_AND_RESIDUAL_RISK}`

### Fact Type: `validation command`

Fact type: `validation command`
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `{VALIDATION_COMMAND_CANONICAL_OWNER}`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
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
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `{SECURITY_POLICY_CANONICAL_OWNER}`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
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
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `{ASSISTANT_OPERATION_CANONICAL_OWNER}`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
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
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `.ai/project/development-evidence.json`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
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
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `{AI_INFRASTRUCTURE_ITEM_CANONICAL_OWNER}`
AI infrastructure router item: `{AI_INFRASTRUCTURE_ITEM_ID}`
Adaptation record: `{AI_INFRASTRUCTURE_ADAPTATION_RECORD_OR_NOT_APPLICABLE}`
Project-contour need and outcome owner: `{AI_INFRASTRUCTURE_PROJECT_NEED_AND_OUTCOME_OWNER}`
Recommendation record: `{AI_INFRASTRUCTURE_RECOMMENDATION_RECORD_OR_NOT_APPLICABLE}`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
Invariant and dependency constraints: `{AI_INFRASTRUCTURE_ITEM_INVARIANTS_AND_DEPENDENCIES}`
Derived surfaces:

- `{AI_INFRASTRUCTURE_ITEM_DERIVED_SURFACE}`

Sync direction: `{AI_INFRASTRUCTURE_ITEM_SYNC_DIRECTION}`
Validation or manual review: `{AI_INFRASTRUCTURE_ITEM_VALIDATION_OR_REVIEW}`
Conflict resolver: `{AI_INFRASTRUCTURE_ITEM_CONFLICT_RESOLVER}`
Approval trigger: `{AI_INFRASTRUCTURE_ITEM_APPROVAL_TRIGGER}`
Final evidence: `{AI_INFRASTRUCTURE_ITEM_FINAL_EVIDENCE}`

### Fact Type: `code documentation profile`

Fact type: `code documentation profile`
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `.ai/project/documentation/profiles.json`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
Invariant and dependency constraints: `{CODE_DOCUMENTATION_PROFILE_SELECTION_SOURCE_OWNER_AND_GENERATION_CONSTRAINTS}`
Derived surfaces:

- `{TARGET_GENERATED_CODE_REFERENCE_OR_NONE}`
- `.ai/project/documentation/catalog.json`
- `.ai/project/documentation/README.md`

Sync direction: `{ACCEPTED_PROFILE_AND_SOURCE_COMMENTS_TO_GENERATED_OUTPUT}`
Validation or manual review: `{TARGET_COMMENT_GENERATION_AND_OUTPUT_VALIDATION}`
Conflict resolver: `{TARGET_DOCUMENTATION_PROFILE_DECISION_AUTHORITY}`
Approval trigger: `{DEPENDENCY_CI_PUBLICATION_BROAD_REWRITE_OR_PROFILE_ACCEPTANCE_TRIGGER}`
Final evidence: `{SELECTED_PROFILE_COMMENTS_GENERATION_OUTPUT_AND_RESIDUAL_RISK}`

### Fact Type: `project vocabulary`

Fact type: `project vocabulary`
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `.ai/project/vocabulary/terms.json`
Compact lookup catalog: `.ai/project/vocabulary/catalog.json`
Data dictionary links: `.ai/project/vocabulary/data-dictionary-links.json`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
Invariant and dependency constraints: `{TERM_SCOPE_STATE_OWNER_ALIAS_AMBIGUITY_AND_CANONICAL_LINK_CONSTRAINTS}`
Derived surfaces:

- `{TARGET_DOCS_CODE_DIAGRAMS_PROMPTS_SKILLS_TESTS_OR_NONE}`

Sync direction: `{ACCEPTED_TERM_TO_DERIVED_SURFACES_AND_LINKED_OWNER_REVIEW}`
Validation or manual review: `{TARGET_VOCABULARY_LINK_AND_TERMINOLOGY_VALIDATION}`
Conflict resolver: `{TARGET_TERM_DECISION_AUTHORITY}`
Approval trigger: `{TERM_ACCEPTANCE_DEPRECATION_SEMANTIC_NORMALIZATION_OR_BROAD_REWRITE_TRIGGER}`
Final evidence: `{SELECTED_TERM_IDS_STATES_OWNERS_SOURCES_LINKS_VALIDATION_AND_RESIDUAL_AMBIGUITY}`

### Fact Type: `test strategy and test-first policy`

Fact type: `test strategy and test-first policy`
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `.ai/project/testing/test-first-policy.json`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
Invariant and dependency constraints: `{TEST_LEVEL_COMMAND_TRIGGER_ISOLATION_EXCEPTION_AND_EVIDENCE_CONSTRAINTS}`
Derived surfaces:

- `{TARGET_TEST_FLOWS_GATES_SKILLS_CI_OR_NONE}`

Sync direction: `{ACCEPTED_TEST_POLICY_TO_ADAPTER_AND_VALIDATION_SURFACES}`
Validation or manual review: `{TARGET_TEST_POLICY_AND_ROUTE_VALIDATION}`
Conflict resolver: `{TARGET_TEST_FIRST_DECISION_AUTHORITY}`
Approval trigger: `{POLICY_ACCEPTANCE_DEPENDENCY_CI_MERGE_GATE_PERMISSION_OR_VALIDATION_CHANGE}`
Final evidence: `{POLICY_STATE_TRIGGER_MODES_COMMANDS_ISOLATION_EXCEPTIONS_VALIDATION_AND_RESIDUAL_RISK}`

### Fact Type: `team policy`

Fact type: `team policy`
Authority: ap=`{AP}`; st=`{ST}`; ds=`{DS}`; er=`{ER}`; at=`{AT}`; gs=`{GS}`
Canonical owner: `.ai/project/team-policy.json`
Human explanation: `.ai/project/team-operating-model.md`
Routing: cl=`{CL}`; pa=`{PA}`; cn=`{CN}`; rc=`{RC}`
Invariant and dependency constraints: `{ACTOR_AUTHORITY_PRIORITY_REVIEW_TRANSITION_BACKEND_AND_IDENTITY_CONSTRAINTS}`
Derived surfaces:

- `.ai/assistant/team/active-work-index.json`
- `.ai/assistant/team/work-registry.json`
- `.ai/assistant/team/backend-contract.json`
- `{TARGET_TRACKER_ROLE_OR_REVIEW_CONFIGURATION_OR_NONE}`

Sync direction: `{TEAM_POLICY_TO_COORDINATION_AND_REVIEW_SURFACES}`
Validation or manual review: `{TARGET_TEAM_POLICY_AND_BACKEND_VALIDATION}`
Conflict resolver: `{TEAM_POLICY_OWNER_ACTOR_ID}`
Approval trigger: `{ACTOR_AUTHORITY_REVIEW_MERGE_BACKEND_PERMISSION_OR_IDENTITY_POLICY_CHANGE}`
Final evidence: `{POLICY_REVISION_ACTORS_AUTHORITY_BACKEND_TASK_REVISIONS_VALIDATION_AND_RESIDUAL_RISK}`

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
