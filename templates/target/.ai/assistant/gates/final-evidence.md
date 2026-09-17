# Final Evidence Gate

Owner: `ALATYR-EVIDENCE-001`.

Before completion, report:

- profile, task class, areas, facts/files, owners, selected gates, and
  synchronized surfaces
- `current_user_authorization`: source/scope, allowed phases, invalidation,
  latest commit/publish/live confirmation/effects
- invariant/review reconciliation
- primary analysis strategy, problem-model reference, required review results,
  and proof-obligation acceptance status
- validation outcomes/unresolved checks
- approval scope and avoided protected actions
- context index chain, required obligation IDs, selected item IDs/digests,
  semantic term IDs/versions, packet digest or canonical-prose fallback, and
  budget expansions
- after a continuity boundary, packet/repository verification, selectively
  reloaded context, and current-scope authorization re-established after the
  boundary
- `durable_engineering_evidence`: captured/skipped/blocked,
  ID/path/repository binding, or reason
- `validation_evidence_classes`: declared, locally observed, tool verified,
  CI verified, reviewer verified, production verified, or explicit skipped
  evidence without overclaiming stronger classes
- every selected gate's gate-specific final evidence; do not report evidence
  for an unselected optional module as though it ran
- residual risk and next owner/action

For material operations that change files, commit, publish, use live-external
actions, or close a large package, fill
`.ai/assistant/templates/operation-completion-evidence.json` or report the same
fields.

Completion semantics:

- Report `complete` only when current authorization covers performed phases,
  required validation passed or is target-not-applicable, logical integrity and
  required approval scope are resolved, and no owner-decision risk remains.
- A required proof obligation or analysis review that is open, failed,
  blocked, or unevidenced prevents a `complete` result.
- Report `partial`, `blocked`, or `unverified` when validation failed, was
  skipped or unavailable, authorization/approval is missing, or evidence is
  narrower than the changed facts.
- Tie every test/check to the semantic scope it proves; structural success does
  not prove unrelated invariants.

Structural checks do not prove semantics; unverified capabilities are not
observed evidence.
