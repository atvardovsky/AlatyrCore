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
- timing and metric evidence kinds are honest
- capture coverage, missing intervals, observer effect, and overhead are stated
- raw conversations, chain-of-thought, prompts, secrets, credentials, unrelated
  personal data, complete diffs, verbose logs, and unused speculation are absent
- final result and clean-upstream projection are bound to evidence
- the compact index and selected record agree
- activation expires when the logical scope completes or changes, or through
  explicit disablement or abandonment

Deterministic checks cannot prove event completeness, semantic attribution,
result quality, or reduced human supervision.
