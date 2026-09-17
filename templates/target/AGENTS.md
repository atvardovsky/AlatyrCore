# Agent Instructions

This project uses Alatyr Core. This file is host-preloaded.

## Bootstrap

Load `.ai/assistant/bootstrap-index.json`; select its smallest route and gates.
On routing failure, load the canonical owner. Load
`.ai/assistant/entry-packet.json` only for repair, audit, or conflict. Follow
matched child indexes; a parent does not load its directory. Use `.ai/README.md`
only for installation/update recovery.

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

Non-trivial work uses `.ai/assistant/task-decomposition.json`: one strategy,
bounded model, current projection, and obligations. Full history is
conditional. Small work stays `direct-local`. Delegate only with capability
evidence; the primary retains decisions, authorization, integration, and
acceptance. Run existing validation.

## Evidence

Report routing, owners, facts, support impact, integrity, validation,
authorization/approval, expansion, workers, and residual risk.
Report `durable_engineering_evidence` as `captured/skipped/blocked`.
