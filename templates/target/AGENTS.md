# Agent Instructions

This file is host-preloaded.

## Bootstrap

Load `.ai/assistant/bootstrap-index.json`; select its smallest route and gates.
On failure, load the canonical owner. Load `.ai/assistant/entry-packet.json`
only for repair, audit, or conflict. Follow child indexes without
loading directories. Use `.ai/README.md` for recovery.

## Authority

Own project facts in `.ai/project`, portable rules in `.ai/framework`, and
routing in `.ai/assistant`. Derived aids route evidence, not authority.

Before mutation, apply `ALATYR-AUTHORIZATION-001` through
`.ai/assistant/policies/action-authorization.json` to the newest request.
`inspect`, `modify`, `commit`, `publish`, and `live-external` are separate.
Discussion, planning, issue return, or ambiguity are inspect-only.
Implementation does not imply commit; commit does not imply push. Authorization
is scoped.

After context loss or a session boundary, apply `ALATYR-CONTINUITY-001` through
`session-continuity` before mutation. Re-establish scope from the newest
request; packets and summaries are evidence only.

Protected architecture, behavior, security, permissions, dependencies,
destructive/live/production actions, spend, imports, or weaker gates require
plan-and-diff-bound approval.

## Work

For semantic changes, name the fact, re-derive invariants, load its owner and
dependents, then reconcile code, tests, contracts, docs, diagrams, gates, and
risk. Review unknown relationships; do not infer acceptance.

For every code or test change, record a Project Contour Sync Decision:
`updated`, `not-required`, `blocked`, or `unverified`. Name fact IDs, checked
owners, affected surfaces, evidence, and any fact-specific `not-required`
reason. Update `.ai/project/contour.md` only when orientation or routing facts
changed. `blocked` or `unverified` blocks completion.

Non-trivial work uses `.ai/assistant/task-decomposition.json`: one strategy,
bounded model, current projection, and obligations. History is conditional;
small work stays `direct-local`. Delegate with capability evidence. The primary
retains decisions, authorization, integration, and acceptance. Run validation.

## Evidence

Report routing, owners, facts, support impact, integrity, validation,
project-contour sync, authorization/approval, expansion, workers, residual
risk, and `durable_engineering_evidence` as `captured/skipped/blocked`.
