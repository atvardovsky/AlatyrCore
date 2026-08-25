# Debug Mode Gate

Owner: `ALATYR-DEBUG-001`.

When Debug Mode is requested or active, verify:

- current task/session activation is explicit and has not expired
- record writes are within current `adapter-only` authorization
- engineering actions retain their independent authorization and approval gates
- records are non-canonical observability evidence
- events are material, normalized, evidenced, ordered, and causally attributable
- the initial task request remains activation metadata and is not counted as a
  human intervention without a specific investigative effect
- new schema-version-4 events separate actor role, target-local identity,
  provenance, causal class, intervention kind, correction disposition,
  contribution kind, and category
- actor roles distinguish `human`, `executor`, `alatyr-system`,
  `external-maintainer`, and `automation`; executor work is not attributed to
  Alatyr system behavior, and provider/model/runtime facts remain provenance
- versions 1 through 3 retain their historical attribution semantics and
  legacy `alatyr_independent_*` metric names without reinterpretation
- derived events have the matching earlier human or external intervention
  ancestor; independent findings have no intervention ancestor
- every human or external-maintainer intervention has one correction
  disposition with compact evidence
- known-guidance routing and compliance failures name the applicable guidance
  IDs; new-guidance candidates remain non-canonical until normal review
- scope changes trigger authorization review; validation requests and scope
  changes are not counted as implementation corrections, and external input is
  not counted as a maintainer correction unless typed as one
- new events state decision effect and structured architectural impacts
- human or external-maintainer architectural impacts set
  `architectural_supervision: true`, while non-human events do not claim human
  architectural supervision
- a direction-changing correction is followed by a rejected hypothesis with
  counter-evidence and a replacement invariant or architecture event in its
  causal chain
- timing and metric evidence kinds are honest
- completed events lie inside the Debug lifecycle interval and event sequence,
  causal order, and timestamps agree
- capture coverage, missing intervals, observer effect, and overhead are stated
- raw conversations, chain-of-thought, prompts, secrets, credentials, unrelated
  personal data, complete diffs, verbose logs, and unused speculation are absent
- final result and clean-upstream projection are bound to evidence with valid
  binding state, Git object type, ancestry, and preserved prior bindings
- finalized historical snapshot drift is reported without rewriting or
  invalidating the original record
- completed records close the Engineering Evidence decision; supporting event
  roles match referenced events, every materiality condition is evaluated, and
  a skip has registry-backed canonical preservation for each applicable result
- validation fidelity distinguishes exact reproduction from representative,
  partial, unavailable, or not-applicable evidence and retains unresolved gaps
- completed records are immutable; continued work uses a newly activated record
  with one closed predecessor
- every durable engineering-evidence ID resolves exactly once in the target
  Engineering Evidence index; Debug event IDs and temporary IDs are not used
- the compact index and selected record agree
- activation expires when the logical scope completes or changes, or through
  explicit disablement or abandonment

Deterministic checks cannot prove event completeness, semantic attribution,
domain claim correctness, result quality, or reduced human supervision.
