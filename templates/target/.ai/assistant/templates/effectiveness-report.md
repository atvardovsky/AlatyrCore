# Alatyr Effectiveness Report

Use this report in `{PROJECT_NAME}` when comparing Alatyr-assisted work across
adapter states or repeated task runs.

Replace placeholders with target facts before accepting the report.

Task: `{TASK_NAME}`
Task profile: `{TASK_PROFILE}`
Adapter mode: `{NONE_MINIMAL_FULL_OR_OTHER}`
Operation ID: `{OPERATION_ID}`
Date: `{DATE}`

## Metrics

Context files loaded: `{CONTEXT_FILES_LOADED_OR_UNKNOWN}`
Approximate context volume: `{CONTEXT_VOLUME_OR_UNKNOWN}`
Input tokens: `{INPUT_TOKEN_COUNT_OR_UNKNOWN}`
Output tokens: `{OUTPUT_TOKEN_COUNT_OR_UNKNOWN}`
Estimated cost and currency: `{COST_AND_CURRENCY_OR_UNKNOWN}`
Cost evidence: `{BILLING_EXPORT_HOST_ESTIMATE_OR_UNKNOWN}`
Context expansions: `{CONTEXT_EXPANSION_COUNT_OR_UNKNOWN}`
Context receipt reused: `{YES_NO_OR_UNKNOWN}`
Context budget exceeded: `{YES_NO_OR_UNKNOWN}`
Clarifications: `{CLARIFICATION_COUNT}`
Approvals requested: `{APPROVAL_COUNT}`
Validation: `{VALIDATION_RUN_SKIPPED_OR_UNRESOLVED}`
Hallucinated commands avoided or produced: `{COMMAND_HALLUCINATION_RESULT}`
Hallucinated command count: `{COUNT_OR_UNKNOWN}`
Validation error count: `{COUNT_OR_UNKNOWN}`
Missed companion updates: `{MISSED_COMPANION_UPDATES_OR_UNKNOWN}`
Rework count: `{REWORK_COUNT_OR_UNKNOWN}`
Changed facts identified: `{CHANGED_FACT_COUNT_OR_UNKNOWN}`
Consistency relationships reviewed: `{RELATIONSHIPS_REVIEWED_OR_UNKNOWN}`
Companion surfaces checked: `{COMPANION_SURFACE_COUNT_OR_UNKNOWN}`
Unresolved consistency gaps: `{UNRESOLVED_CONSISTENCY_GAP_COUNT_OR_UNKNOWN}`
Duration seconds: `{DURATION_SECONDS_OR_UNKNOWN}`
Human active-attention seconds: `{COUNT_OR_UNKNOWN}`
Human attention evidence state: `{OBSERVED_MANUAL_ESTIMATED_OR_UNAVAILABLE}`
Human attention evidence or unavailable reason: `{EVIDENCE}`
Review cycles: `{COUNT_OR_UNKNOWN}`
Review-cycle evidence state: `{OBSERVED_MANUAL_ESTIMATED_OR_UNAVAILABLE}`
Review-cycle evidence or unavailable reason: `{EVIDENCE}`
Executor active-time seconds: `{COUNT_OR_UNKNOWN}`
Executor-time evidence state: `{OBSERVED_OR_UNAVAILABLE}`
Executor-time telemetry or unavailable reason: `{EVIDENCE}`
Protected changes blocked before approval: `{PROTECTED_CHANGES_BLOCKED}`
Residual risks: `{RESIDUAL_RISKS}`
Outcome: `{ACCEPTED_REWORK_BLOCKED_OR_OTHER}`

Executor active time must be host- or provider-observed. Do not substitute
wall-clock duration, human recollection, or an estimate.

## Classified Interventions

Record a count, evidence state, and source or unavailable reason for each
applicable classification:

- Intervention total: `{COUNT_STATE_AND_EVIDENCE}`
- New guidance candidate: `{COUNT_STATE_AND_EVIDENCE}`
- Known-guidance routing failure: `{COUNT_STATE_AND_EVIDENCE}`
- Known-guidance compliance failure: `{COUNT_STATE_AND_EVIDENCE}`
- Task-local input: `{COUNT_STATE_AND_EVIDENCE}`
- Scope change: `{COUNT_STATE_AND_EVIDENCE}`
- Validation request: `{COUNT_STATE_AND_EVIDENCE}`
- Other: `{COUNT_STATE_AND_EVIDENCE}`

Do not promote an intervention into project authority from this report. Use
the target's normal ownership and acceptance process.

## Later-Linked Evidence

Delayed outcomes at task completion: `{NONE_YET_OR_EXISTING_RECORD_IDS}`
Adapter maintenance record IDs: `{RECORD_IDS_OR_NOT_APPLICABLE}`

Record a later accepted direction, pull request, merge, rejection, regression,
revert, or follow-up in a new delayed-outcome evidence record. Do not modify
this completed report or a completed Debug record to add the later event.

## Notes

Comparable baseline: `{COMPARABLE_BASELINE_OR_NONE}`
Limitations: `{LIMITATIONS}`
Next measurement: `{NEXT_MEASUREMENT}`

Do not calculate precise productivity, output-per-minute, or percentage-saving
claims from these fields alone. Compare only compatible tasks with accepted
outcomes, non-regressing quality evidence, and compatible measurement states.
