---
alatyr_test_execution:
  policy: .ai/project/testing/test-first-policy.json
  timing: target-policy
  red_evidence: target-policy
  coverage_writes: canonical-owner
---
# Test-First Evidence

Operation ID: `{OPERATION_ID}`
Policy revision: `{TARGET_POLICY_REVISION}`
Policy state: `{ENABLED_OR_BLOCKED}`
Recommendation result: `{REQUIRED_RECOMMENDED_NOT_INDICATED_OR_BLOCKED}`
Trigger ID and evidence: `{TARGET_TRIGGER_AND_EVIDENCE}`
Selected mode: `{STRICT_TDD_REGRESSION_FIRST_CHARACTERIZATION_FIRST_CONTRACT_FIRST_OR_TEST_AFTER_WITH_REASON}`
Changed fact or defect: `{CHANGED_FACT_DEFECT_INVARIANT_OR_CONTRACT}`
Canonical owner: `{TARGET_FACT_OWNER}`
Test level: `{TARGET_TEST_LEVEL_ID}`
Acceptance examples: `{OBSERVABLE_EXAMPLES_AND_BOUNDARIES}`
Canonical testing policy/matrix: `{TARGET_OWNERS_NOT_DERIVED_MIRRORS}`
Execution timing and authorization source: `{CURRENT_SCOPE_EVIDENCE_OR_PENDING}`
Availability/prerequisites: `{AVAILABLE_UNAVAILABLE_OR_UNKNOWN_AND_REASON}`
Environment/effects/filter: `{ACTUAL_ENVIRONMENT_EFFECTS_AND_VERIFIED_FILTER_OR_UNSUPPORTED}`
Evidence state: `{AUTHORED_DISCOVERED_PASSED_FAILED_SKIPPED_OR_BLOCKED}`
Proof boundary: `{STATIC_UNIT_MOCKED_REAL_PERSISTENCE_BROWSER_OR_END_TO_END}`
Selected/executed/excluded files and reasons: `{ACTUAL_SELECTION}`
Discovered/executed/passed/failed/skipped/not-run counts: `{MEASURED_COUNTS_NOT_CASE_ID_MATCHES}`
Current machine record, when used: `{PATH_BOUND_IN_POLICY_EXECUTION_CONTRACT_OR_NONE}`

## RED

Test reference: `{TARGET_TEST_PATH_AND_CASE}`
Command ID: `{TARGET_COMMAND_ID}`
Command: `{TARGET_COMMAND_OR_REDACTED_REFERENCE}`
Result: `{FAILED_AS_EXPECTED_INVALID_RED_OR_NOT_RUN_WITH_REASON}`
Expected failure reason: `{EXPECTED_BEHAVIOR_FAILURE}`
Observed failure reason: `{OBSERVED_FAILURE}`
Evidence revision or artifact: `{RED_EVIDENCE_REFERENCE}`

## GREEN

Command ID: `{TARGET_COMMAND_ID}`
Command: `{TARGET_COMMAND_OR_REDACTED_REFERENCE}`
Result: `{PASSED_FAILED_OR_UNRESOLVED}`
Evidence revision or artifact: `{GREEN_EVIDENCE_REFERENCE}`

## Refactor And Validation

Refactor: `{PERFORMED_OR_SKIPPED_WITH_REASON}`
Focused test after refactor: `{PASSED_FAILED_OR_NOT_RUN_WITH_REASON}`
Broader validation: `{COMMANDS_RESULTS_SKIPS_AND_REASONS}`
Companion updates: `{DOCS_DIAGRAMS_CONTRACTS_PROMPTS_SKILLS_GATES_OR_NONE_WITH_REASON}`
Exception ID and authority: `{EXCEPTION_APPROVAL_OR_NONE}`
Approvals: `{APPROVAL_REFERENCES_OR_NONE}`
Residual risk: `{RESIDUAL_RISK}`
