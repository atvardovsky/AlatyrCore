# Final Evidence Gate

Owner: `ALATYR-EVIDENCE-001`.

Before completion:

- profile, task class, areas, facts/files, owners, gates, synchronized
  surfaces
- `current_user_authorization`: source/scope, allowed phases, invalidation,
  latest commit/publish/live confirmation/effects
- Project Contour Sync Decision: invariant/review reconciliation, status, fact
  IDs, checked owners, affected/unchanged surfaces, evidence, support-state
  result, risk
- analysis strategy, problem model, required reviews, accepted proof
  obligations
- rule authority, original-case acceptance, retained task witnesses, selected
  task acceptance; distinguish implementation/tests/deployment/publication
- validation/unresolved checks, approval scope, avoided protected actions,
  residual risk, and next owner/action
- context index chain, obligation and selected-item IDs/digests, semantic term
  versions, packet/fallback, and budget expansion
- continuity verification of packet and repository, selective reload and
  renewed current-scope authorization
- `durable_engineering_evidence`: captured/skipped/blocked,
  ID/path/repository binding, or reason
- `validation_evidence_classes`: declared, locally observed, tool verified,
  CI verified, reviewer verified, production verified, or explicit skipped
  evidence without stronger claims
- selected gate evidence; never imply unselected modules ran

For material changes or state-changing phases, complete
`.ai/assistant/templates/operation-completion-evidence.json` or equivalent fields.

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
- Bind each check to the semantic scope it proves; structural checks cannot prove semantics
  or turn unverified capabilities into observed evidence.
