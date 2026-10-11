# Current Task Evidence Validation

This source-tooling reference explains the implementation of
[task decomposition](../framework/task-decomposition.md),
[engineering evidence](../framework/engineering-evidence.md), and
[architecture review](../framework/architecture-knowledge.md). Those documents
remain the rule owners. None of these records grants action authorization.

## Selection

The kernel's `.ai/assistant/active-tasks.json` selects registered active models
and ended-task closure receipts without walking ignored runtime folders.
Pass `--task-id` for current-task acceptance and `--task-class` from independent
request classification (default `standard-task` when a task is selected).
Absent registration is an error, not proof that there is no current task.
Eligible inline small tasks need no durable registration unless explicitly
selected for this check. The installed delegate accepts these bindings too;
`validate-current` still requires its canonical approval/change-package inputs.

Headers and closures share the shipped JSON schemas and exact projections.
Record paths use forward-slash separators on every platform.
Header fact IDs match the validated model, not only an agreeing closure.
Predecessor tasks retain matching model IDs and earlier incident iterations.
An active header cannot disappear from changed-scope validation without an
explicit terminal closure; partial/blocked work may retain unresolved proof
obligations but cannot support current-task final acceptance.
The task index and each selected artifact are limited to 512 KiB and 128 task
headers. Changed scope does not reopen unchanged closed-task models just because
the root index changed; full scope checks every retained header. Retain selected
models or explicitly retire headers after preserving durable evidence.

## Closure

Captured receipts must match task, operation, and result. A material capture
skip maps every changed fact to its fact-type-specific registry owner; the
maintainer still verifies that the conclusion was actually preserved there.
Publication receipts validate a locally observed remote-tracking revision, not
live remote freshness or permission to push. Keep implementation completion,
evidence finalization, and publication independent.
Historical receipts retain their immutable observed revision when a remote ref
advances; current-task publication still requires a matching local observation.

Selected final commit/tree results must match the claimed implementation and
owner files in the current worktree; snapshots must cover those files. Historical
records remain historical. Comparisons cap source reads at 16 MiB/file and
64 MiB total; unavailable or oversized scope cannot establish current evidence.
The closure itself is post-result metadata, checked through its registered hash
and schema rather than its own result hash. Index-maintenance tasks use a
commit/tree: compare every registration field except the selected task's state
and completion pointer, which are checked by the closure contract. Other task
headers remain bound exactly. Snapshots must exclude registration metadata and
cannot establish index-maintenance scope. Empty files add no byte-budget cost.

## Review And Discovery

Schema-2 architecture catalogs bind review input digests separately from support
state. Review reads are deduplicated and capped at 1 MiB/file, 8 MiB total, and
256 unique files per pass. Unavailable, oversized, or changed sources require
revalidation. An explicitly selected final closure checks related catalog items;
routine unrelated history does not acquire new current-review obligations.

Project-knowledge suggestions exclude portable `.ai/framework` owners and may
report bounded, registered recent-task recurrence signals. Missing/corrupt task
evidence leaves package candidates available and reports incomplete discovery;
neither matching headers nor hashes prove repair correctness.
