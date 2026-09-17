# Agent Instructions

This project uses Alatyr Core. This file is host-preloaded.

## Bootstrap

Load `.ai/assistant/bootstrap-index.json`. Select its smallest route and gates.
Trust validated routing; on failure load the canonical owner. Load
`.ai/assistant/entry-packet.json` only
for repair, audit, or conflict. Follow matched child indexes; selecting a
parent never loads its directory. Use `.ai/README.md` only for
installation/update recovery.

## Authority

Own project facts in `.ai/project`, portable rules in `.ai/framework`, and
routing in `.ai/assistant`. Derived aids route evidence; they grant no
authority.

Before mutation, apply `ALATYR-AUTHORIZATION-001` through
`.ai/assistant/policies/action-authorization.json` to the newest request and
scope. `inspect`, `modify`, `commit`, `publish`, and `live-external` are
separate. Discussion, planning, issue return, or ambiguity are inspect-only.
Implementation does not imply commit; commit does not imply push.
Authorization ends with its scope.

After context loss or a session boundary, apply `ALATYR-CONTINUITY-001` through
the `session-continuity` overlay before mutation. Packets and summaries are
evidence; re-establish scope from the newest request.

Protected architecture, behavior, security, permissions, dependencies,
destructive/live/production actions, spend, infrastructure import, or weaker
gates require target approval bound to the plan and Git diff.

## Work

For semantic changes, name the fact, re-derive invariants, load its owner and
selected dependent surfaces, then reconcile code, tests, contracts, docs,
diagrams, gates, and risk. Review unknown relationships; never infer acceptance.

For non-trivial work, use `.ai/assistant/task-decomposition.json`. Select one
strategy and descriptor; bind evidence-backed proof obligations to a bounded
problem model. Small settled work stays `direct-local` without the catalog.
Delegation requires capability evidence and cannot delegate strategy,
authorization, architecture, obligation acceptance, integration, or final
acceptance. Run only existing validation.

## Evidence

Report routing, owners, facts, support impact, integrity, validation,
authorization/approval, expansion, workers, and residual risk.
Report `durable_engineering_evidence` as `captured/skipped/blocked`.
