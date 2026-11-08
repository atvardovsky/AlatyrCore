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
- packet/repository continuity verification, selective reload, renewed
  current-scope authorization
- `durable_engineering_evidence`: captured/skipped/blocked,
  ID/path/repository binding, or reason
- `validation_evidence_classes`: declared, locally observed, tool verified,
  CI verified, reviewer verified, production verified, or explicit skipped
  evidence without stronger claims
- selected gate evidence; never imply unselected modules ran

For material/state-changing work, complete
`.ai/assistant/templates/operation-completion-evidence.json` or equivalent fields.

Completion semantics:

- Report `complete` only when current authorization covers performed phases,
  validation passed/is target-not-applicable, integrity/approval are resolved
  and no owner-decision risk remains.
- Any open/failed/blocked/unevidenced proof/review or missing/blocked/unverified
  contour sync prevents a `complete` result.
- Report `partial`, `blocked`, or `unverified` for failed/skipped/unavailable
  checks, missing authority or narrower evidence.
- Bind each check to the semantic scope it proves; structural success proves
  neither semantics nor unverified capabilities. Reconcile original outcomes/open
  duties through canonical selected-task acceptance, never component success.
- Material/recurring work: `.ai/framework/task-state-delivery.md#outcome-qualification`.
  Lead with original outcomes/gaps, not test totals or deployment health.
