# AI Infrastructure Recommendation

Use this template in `{PROJECT_NAME}` to record evidence-based recommendations
for new AI infrastructure or changes to existing items.

Recommendation is read-only decision evidence. It does not approve fetching,
installation, execution, canonical edits, removal, permission changes, or item
activation.

## Recommendation Scope

- Operation ID: `{OPERATION_ID}`
- Recommendation record path: `{TARGET_RECORD_PATH_OR_REPORT_ONLY}`
- Recommendation date: `{RECOMMENDATION_DATE}`
- Requested by: `{REQUESTER_OR_ROLE}`
- Allowed actions: `{READ_ONLY_OR_ADAPTER_ONLY}`
- Recommendation scope: `{PROJECT_AREA_PROBLEM_OR_ITEM_SCOPE}`
- Target assistant surfaces: `{TARGET_ASSISTANT_SURFACES}`
- Project contour: `.ai/project/contour.md`
- Project area and canonical owner: `{PROJECT_AREA_AND_CANONICAL_OWNER}`
- Project-contour evidence: `{PROJECT_FACTS_CONSTRAINTS_OR_OUTCOMES}`
- Evidence sources inspected: `{TASK_REVIEW_INCIDENT_VALIDATION_REWORK_COST_OR_MATURITY_EVIDENCE}`
- Evidence quality: `{MEASURED_OBSERVED_ANECDOTAL_MISSING_OR_CONFLICTING}`
- Inventory source and freshness: `{INVENTORY_PATH_DATE_OR_BOUNDED_INSPECTION}`
- Router: `.ai/assistant/ai-infrastructure-router.json`

## Candidate Record

Repeat this block for each bounded candidate.

- Recommendation ID: `{RECOMMENDATION_ID}`
- Recommendation kind:
  `{ADD_NEW_IMPROVE_EXISTING_CONSOLIDATE_REPLACE_RETIRE_KEEP_OR_UNRESOLVED}`
- Status: `{PROPOSED_DEFERRED_REJECTED_OR_UNRESOLVED}`
- Priority: `{TARGET_DEFINED_PRIORITY_OR_NOT_RANKED}`
- Existing item IDs: `{AI_INFRASTRUCTURE_ITEM_IDS_OR_NONE}`
- Proposed item type:
  `{SKILL_PROMPT_GATE_CHECKER_FLOW_TOOL_MCP_BRIDGE_WRAPPER_TEMPLATE_OR_OTHER}`
- Observed problem: `{OBSERVED_PROBLEM}`
- Recurrence or high-impact exception: `{RECURRENCE_FREQUENCY_OR_IMPACT_EVIDENCE}`
- Existing coverage and why keep is insufficient:
  `{CURRENT_COVERAGE_OVERLAP_AND_GAP_OR_KEEP_JUSTIFICATION}`
- Proposed contract change:
  `{PURPOSE_TRIGGERS_CONTEXT_PERMISSIONS_GATES_VALIDATION_OUTPUT_AND_SURFACES}`
- Non-goals: `{NON_GOALS}`
- Expected quality or consistency effect:
  `{MEASURED_EFFECT_OR_LABELED_ESTIMATE}`
- Acceptance criteria: `{MEASURABLE_ACCEPTANCE_CRITERIA}`
- Expected context-load effect: `{MEASURED_EFFECT_OR_LABELED_ESTIMATE}`
- Implementation cost: `{MEASURED_COST_OR_LABELED_ESTIMATE}`
- Ongoing maintenance cost and owner:
  `{MAINTENANCE_COST_AND_TARGET_OWNER_OR_UNRESOLVED}`
- Permission, safety, dependency, and compatibility impact:
  `{PERMISSION_SAFETY_DEPENDENCY_AND_ASSISTANT_SURFACE_IMPACT}`
- Build, adapt, or source strategy:
  `{BUILD_TARGET_OWNED_ADAPT_KNOWN_SOURCE_SEARCH_LATER_OR_NOT_APPLICABLE}`
- Validation plan: `{TARGET_VALIDATION_OR_MANUAL_REVIEW}`
- Rollback, retirement, or supersession path:
  `{ROLLBACK_RETIREMENT_OR_SUPERSESSION_PLAN}`
- Approval needed for later operation:
  `{APPROVAL_TRIGGER_OR_NOT_REQUIRED_FOR_RECOMMENDATION}`
- Next route and operation:
  `{ADAPT_IMPORT_GATE_CHECKER_CHANGE_TOOL_MCP_CHANGE_BRIDGE_WRAPPER_CHANGE_OR_NONE}`
- Residual risk: `{RESIDUAL_RISK}`

## Existing Item Review Summary

- Items kept without change: `{KEPT_ITEM_IDS_AND_REASON_OR_NONE}`
- Items proposed for improvement: `{IMPROVE_ITEM_IDS_AND_REASON_OR_NONE}`
- Items proposed for consolidation or replacement:
  `{CONSOLIDATE_OR_REPLACE_ITEM_IDS_AND_REASON_OR_NONE}`
- Items proposed for retirement: `{RETIRE_ITEM_IDS_AND_REASON_OR_NONE}`
- New items proposed: `{NEW_ITEM_IDS_AND_REASON_OR_NONE}`

## Decision Summary

- Candidates proposed: `{PROPOSED_COUNT}`
- Candidates deferred: `{DEFERRED_COUNT}`
- Candidates rejected: `{REJECTED_COUNT}`
- Candidates unresolved: `{UNRESOLVED_COUNT}`
- Actions explicitly not taken:
  `{NO_FETCH_INSTALL_EXECUTE_EDIT_REMOVE_PERMISSION_OR_ACTIVATION_ACTIONS}`
- Recommended next operation: `{NEXT_OPERATION_OR_NONE}`
- Final evidence: `{FINAL_EVIDENCE}`
- Residual risk: `{RESIDUAL_RISK}`
