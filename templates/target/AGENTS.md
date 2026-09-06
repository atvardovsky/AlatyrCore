# Agent Instructions

This project uses Alatyr Core. This file is host-preloaded.

## Bootstrap

Load `.ai/assistant/bootstrap-index.json` and select the smallest matching
profile, intent, scale, area, operation, and gates. Trust routing after
deterministic integrity validation; load its evidence and owners only on
failure. Load `.ai/assistant/entry-packet.json` only for repair, audit, or
conflict. Follow matched child indexes; never load a directory from a parent
match.

On missing, stale, ambiguous, cyclic, or contradictory selectors, digests,
terms, relationships, or facts, use the canonical owner. Use
`.ai/README.md` only for installation or update recovery.

## Authority

Use bootstrap-selected owners.

Project facts belong to `.ai/project`, portable rules to `.ai/framework`, and
assistant routing to `.ai/assistant`. Derived aids
locate evidence; they never create authority or prove semantics.

Before state changes, apply `ALATYR-AUTHORIZATION-001` through
`.ai/assistant/policies/action-authorization.json` to the newest request and
scope. `inspect`, `modify`, `commit`, `publish`, and `live-external` are
separate. Discussion, planning, issue return, and ambiguity are inspect-only.
Implementation does not imply commit; commit does not imply push. Prior
authorization never carries into a new or completed scope.

Protected architecture, behavior, security, permissions, dependencies,
destructive/live/production actions, spend, infrastructure import, or weaker
gates require target approval bound to the plan and Git diff.

## Work

For semantic changes, name the fact, re-derive invariants, load its owner and
selected dependency/derived surfaces, and reconcile code, tests, contracts,
docs, diagrams, gates, and risk. Review new or unknown relationships; never
infer them as accepted facts.

For non-trivial work, use `.ai/assistant/task-decomposition.json`. Delegation
requires current capability evidence and never delegates authorization,
architecture decisions, integration, or acceptance. Run only target validation
that exists.

## Evidence

Report routing, owners, facts, support impact, integrity, validation,
authorization/approval, expansion, workers, and residual risk.
Report `durable_engineering_evidence` as `captured/skipped/blocked`.
