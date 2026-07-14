# Alatyr Effectiveness Benchmark Summary

Benchmark: `codex-docs-local-0619871`
Source commit: `061987108d8e7ecd15625953d7c41683ee7fe497`
Tasks: 1
Repetitions: 1
Reviewed reports: 3 of 3
Comparable context-cost evidence: no
Comparable token evidence: yes
Comparable monetary-cost evidence: no
Comparable timing evidence: yes

## Adapter Modes

Mode: `none`
- Reports: 1
- Accepted/rework/blocked: 1/0/0
- Criteria pass/fail/unresolved: 4/0/0
- Average input_tokens: 101313.00
- Average output_tokens: 2736.00
- Average estimated_cost: unknown
- Average context_files_loaded: 4.00
- Average approximate_context_volume: unknown
- Average context_expansions: unknown
- Average clarifications: 0.00
- Average approvals_requested: 0.00
- Average hallucinated_command_count: 0.00
- Average validation_error_count: 0.00
- Average missed_companion_updates: 0.00
- Average rework_count: 0.00
- Average changed_fact_count: 0.00
- Average relationships_reviewed: 2.00
- Average companion_surfaces_checked: 2.00
- Average unresolved_consistency_gaps: 0.00
- Average duration_seconds: 73.00
- Average protected_changes_blocked: 0.00

Mode: `minimal`
- Reports: 1
- Accepted/rework/blocked: 1/0/0
- Criteria pass/fail/unresolved: 4/0/0
- Average input_tokens: 102040.00
- Average output_tokens: 2375.00
- Average estimated_cost: unknown
- Average context_files_loaded: 9.00
- Average approximate_context_volume: unknown
- Average context_expansions: 0.00
- Average clarifications: 0.00
- Average approvals_requested: 0.00
- Average hallucinated_command_count: 0.00
- Average validation_error_count: 0.00
- Average missed_companion_updates: 0.00
- Average rework_count: 0.00
- Average changed_fact_count: 0.00
- Average relationships_reviewed: 0.00
- Average companion_surfaces_checked: 2.00
- Average unresolved_consistency_gaps: 0.00
- Average duration_seconds: 55.00
- Average protected_changes_blocked: 0.00

Mode: `full`
- Reports: 1
- Accepted/rework/blocked: 1/0/0
- Criteria pass/fail/unresolved: 4/0/0
- Average input_tokens: 170433.00
- Average output_tokens: 3371.00
- Average estimated_cost: unknown
- Average context_files_loaded: 11.00
- Average approximate_context_volume: unknown
- Average context_expansions: 0.00
- Average clarifications: 0.00
- Average approvals_requested: 0.00
- Average hallucinated_command_count: 0.00
- Average validation_error_count: 0.00
- Average missed_companion_updates: 0.00
- Average rework_count: 0.00
- Average changed_fact_count: 0.00
- Average relationships_reviewed: 0.00
- Average companion_surfaces_checked: 2.00
- Average unresolved_consistency_gaps: 0.00
- Average duration_seconds: 81.00
- Average protected_changes_blocked: 0.00

## Relative To None

Mode: `minimal`
- Total-token reduction: -0.4%
- Estimated-cost reduction: not-computable
- Context-volume reduction: not-computable
- Loaded-file reduction: -125.0%
- Duration reduction: 24.7%
- Rework reduction: not-computable
- Unresolved-gap reduction: not-computable
Mode: `full`
- Total-token reduction: -67.0%
- Estimated-cost reduction: not-computable
- Context-volume reduction: not-computable
- Loaded-file reduction: -175.0%
- Duration reduction: -11.0%
- Rework reduction: not-computable
- Unresolved-gap reduction: not-computable

## Interpretation Boundary

Negative reductions mean the adapter mode used more of that metric than the no-adapter mode. `not-computable` means evidence was unknown or the reference was zero. This summary reports reviewed measurements; it does not by itself prove broad cost or quality improvement.
