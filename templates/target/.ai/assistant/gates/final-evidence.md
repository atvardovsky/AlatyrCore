# Final Evidence Gate

Owner: `ALATYR-EVIDENCE-001`.

Before completion, report:

- profile, task class, areas, facts/files, owners, gates, and synchronized
  surfaces
- `current_user_authorization`: source/scope, allowed phases, invalidation,
  latest commit/publish/live confirmation/effects
- invariant/review reconciliation and Project Contour Sync Decision with
  status, fact IDs, checked owners, affected/unchanged surfaces, evidence,
  support-state result, and risk
- analysis strategy, problem model, required reviews, and accepted proof
  obligations
- validation/unresolved checks, approval scope, avoided protected actions,
  residual risk, and next owner/action
- context index chain, obligation and selected-item IDs/digests, semantic term
  versions, packet/fallback, and budget expansion
- after continuity, packet/repository verification, selective reload, and
  re-established current-scope authorization
- `durable_engineering_evidence`: captured/skipped/blocked,
  ID/path/repository binding, or reason
- `validation_evidence_classes`: declared, locally observed, tool verified,
  CI verified, reviewer verified, production verified, or explicit skipped
  evidence without stronger claims
- each selected gate's evidence; do not imply an unselected module ran

For material file changes, commits, publication, live-external actions, or
large-package closure, fill
`.ai/assistant/templates/operation-completion-evidence.json` or report the same
fields.

Completion semantics:

- Report `complete` only when current authorization covers performed phases,
  validation passed or is target-not-applicable, integrity and approval scope
  are resolved, and no owner-decision risk remains.
- Open, failed, blocked, or unevidenced proof obligations/reviews prevent a
  `complete` result.
- Missing, blocked, or unverified contour-sync evidence prevents a `complete` result
  after code/test changes.
- Report `partial`, `blocked`, or `unverified` when validation failed, was
  skipped/unavailable, authorization/approval is missing, or evidence is
  narrower than changed facts.
- Tie each check to the semantic scope it proves; structure does not prove
  unrelated invariants.

Structural checks do not prove semantics; unverified capabilities are not
observed evidence.
