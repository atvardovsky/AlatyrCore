# Agent Instructions

This project uses Alatyr Core. This file is host-preloaded.

## Bootstrap

Load `.ai/assistant/bootstrap-index.json`. Select the smallest matching
profile, intent, scale, area, operation, and gates. Trust validated routing;
inspect integrity evidence or owners only after failure. Load
`.ai/assistant/entry-packet.json` only for repair, audit, or conflict. Follow
matched child indexes; a parent match never loads its directory.

For invalid routing or evidence, use the canonical owner. Use `.ai/README.md`
only for installation/update recovery.

## Authority

Own project facts in `.ai/project`, portable rules in `.ai/framework`, and
routing in `.ai/assistant`. Derived aids locate evidence; they never create
authority or prove semantics.

Before mutation, apply `ALATYR-AUTHORIZATION-001` through
`.ai/assistant/policies/action-authorization.json` to the newest request and
scope. `inspect`, `modify`, `commit`, `publish`, and `live-external` are separate.
Discussion, planning, issue return, or ambiguity are inspect-only.
Implementation does not imply commit; commit does not imply push. Authorization
expires with its scope.

After context loss or a session boundary, apply `ALATYR-CONTINUITY-001` through
the `session-continuity` overlay before mutation. Packets and summaries are
evidence, never authority; re-establish scope from the newest request.

Protected architecture, behavior, security, permissions, dependencies,
destructive/live/production actions, spend, infrastructure import, or weaker
gates require target approval bound to the plan and Git diff.

## Work

For semantic changes, name the fact, re-derive invariants, load its owner and
selected dependent surfaces, then reconcile code, tests, contracts, docs,
diagrams, gates, and risk. Review unknown relationships; never infer acceptance.

For non-trivial work, use `.ai/assistant/task-decomposition.json`. Delegation
requires current capability evidence and never delegates authorization,
architecture decisions, integration, or acceptance. Run only target validation
that exists.

## Evidence

Report routing, owners, facts, support impact, integrity, validation,
authorization/approval, expansion, workers, and residual risk.
Report `durable_engineering_evidence` as `captured/skipped/blocked`.
