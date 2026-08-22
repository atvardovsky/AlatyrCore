# Debug Mode Gate

Owner: `ALATYR-DEBUG-001`.

When Debug Mode is requested or active, verify:

- current task/session activation is explicit and has not expired
- record writes are within current `adapter-only` authorization
- engineering actions retain their independent authorization and approval gates
- records are non-canonical observability evidence
- events are material, normalized, evidenced, ordered, and causally attributable
- derived-after-human events have an earlier human intervention ancestor
- Alatyr-initiated findings have no human-intervention ancestor
- new events state decision effect and structured architectural impacts
- human or external-maintainer architectural impacts set
  `architectural_supervision: true`, while non-human events do not claim human
  architectural supervision
- a direction-changing correction is followed by a rejected hypothesis with
  counter-evidence and a replacement invariant or architecture event in its
  causal chain
- timing and metric evidence kinds are honest
- capture coverage, missing intervals, observer effect, and overhead are stated
- raw conversations, chain-of-thought, prompts, secrets, credentials, unrelated
  personal data, complete diffs, verbose logs, and unused speculation are absent
- final result and clean-upstream projection are bound to evidence
- every durable engineering-evidence ID resolves exactly once in the target
  Engineering Evidence index; Debug event IDs and temporary IDs are not used
- the compact index and selected record agree
- activation expires when the logical scope completes or changes, or through
  explicit disablement or abandonment

Deterministic checks cannot prove event completeness, semantic attribution,
result quality, or reduced human supervision.
