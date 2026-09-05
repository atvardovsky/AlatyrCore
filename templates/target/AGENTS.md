# Agent Instructions

This repository uses Alatyr Core. Treat this file as host-preloaded context.

## Bootstrap

Load `.ai/assistant/bootstrap-index.json`, verify its source digests, and select
the smallest matching profile, intent, scale, area, operation, and gates. Load
`.ai/assistant/entry-packet.json`. Follow matched child indexes only; never load
a directory from a parent match.

Use the referenced canonical owner when a selector, digest, term, relationship,
or fact is missing, stale, ambiguous, cyclic, or contradictory. Use
`.ai/README.md` only for installation or update recovery.

## Authority

Use bootstrap-selected rule owners.

Project facts belong to `.ai/project`; portable rules belong to
`.ai/framework`; assistant routing belongs to `.ai/assistant`. Derived aids
locate evidence; they never create authority or prove semantics.

Before state changes, apply `ALATYR-AUTHORIZATION-001` through
`.ai/assistant/policies/action-authorization.json` to the newest request and
scope. `inspect`, `modify`, `commit`, `publish`, and `live-external` are
separate. Discussion, planning, issue return, and ambiguity are inspect-only.
Implementation does not imply commit; commit does not imply push. Prior
authorization never carries into a new or completed scope.

Protected architecture, behavior, security, permission, dependency,
destructive, live, spend, production, imported-infrastructure, or weakened-gate
changes require target approval bound to the plan and Git diff.

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

Report routes, owners, facts, support impact, integrity, validation,
authorization, approval, expansion, worker evidence, and residual risk.
Report `durable_engineering_evidence` as `captured/skipped/blocked`.
