# Agent Instructions

This file is host-preloaded.

## Bootstrap

Load `.ai/assistant/bootstrap-index.json`; select minimal routes/gates.
On failure: canonical owner. Repair/audit/conflict only:
`.ai/assistant/entry-packet.json`. Follow matching indexes, not directories.
Recovery: `.ai/README.md`. Check `session_presence` at entry; if enabled,
follow its flow before overlap and on scope changes/completion.

## Authority

Project facts: `.ai/project` (target-only names); rules: `.ai/framework`;
routes: `.ai/assistant`. Derived aids lack authority.

Before mutation: `ALATYR-AUTHORIZATION-001` via
`.ai/assistant/policies/action-authorization.json` for the newest request.
Separate phases: `inspect`, `modify`, `commit`, `publish`, `live-external`.
Discussion, planning, issue return, or ambiguity are inspect-only.
Implementation does not imply commit; commit does not imply push.
Scoped authorization.

At request/phase/pre-mutation compare `session-context`; coalesce.
For drift/context loss use `session-continuity` (`ALATYR-CONTINUITY-001`).
Recheck newest-request scope; packets/summaries lack authority.

Protected architecture, behavior, security, permissions, dependencies,
destructive/live/production actions, spend, imports, or weaker gates require
plan-and-diff-bound approval.

## Work

For semantic changes, name facts, re-derive invariants, load owners/dependents,
reconcile code/tests/contracts/docs/diagrams/gates/risk, and review unknown
relationships. Do not infer acceptance.

For every code or test change, record a Project Contour Sync Decision:
`updated`, `not-required`, `blocked`, or `unverified`. Name fact IDs, checked
owners, affected surfaces, evidence, and any fact-specific `not-required`
reason. Update `.ai/project/contour.md` only when orientation/routing changes.
`blocked`/`unverified` blocks completion.

Non-trivial work: `.ai/assistant/task-decomposition.json`, one strategy,
bounded model/projection/obligations. History is conditional; small work:
`direct-local`. Delegate with capability evidence. Primary retains
decisions, authorization, integration, and acceptance. Validate.

## Evidence

Report routing/owners/facts, support impact/integrity/validation,
project-contour sync, authorization/approval, expansion, workers, residual
risk, and `durable_engineering_evidence` as `captured/skipped/blocked`.
