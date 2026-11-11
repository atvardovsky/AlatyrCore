# Reviewed Historical Task Evidence Loss

An optional schema-2 active-task index can retain `historical-evidence-missing`
tasks without marking them complete, resumable or accepted. Schema 1 retains
its original active/closed contract. This compatibility path is deliberately
different from restoring a reviewed active handoff.

`tools/historical_task_evidence.py` validates the exact original committed task
header, ancestor registration/index digest, retained owner review, bounded search
and dependency witnesses, unresolved original facts and canonical owners.
Duplicate JSON fields, unsafe paths, symlinks, changed witnesses, missing or
ambiguous approval, recovered/conflicting runtime models and active transitive
dependents fail closed. A retained loss cannot be removed, reopened or retargeted;
its committed header and disposition binding remain immutable history.

Current-task views expose unresolved outcomes with no execution advice. Worktree
readiness refuses to resume that task. A historical blocked package may refer to
the exact reviewed loss only if it was included in the dependency review; a
selected/current, nonblocked or complete package cannot borrow this exception.

Tests: `tests/test_historical_task_loss.py`. The forward port preserves newer
selected-context, repair-policy and active-retention validation in current Core.
No historical record grants new execution, approval, publication or completion.
Recovery or reconciliation requires a separately reviewed explicit task.
