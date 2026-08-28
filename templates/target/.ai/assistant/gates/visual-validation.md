# Visual Validation Gate

Canonical owners: `ALATYR-DIAGRAM-001`, `ALATYR-RISK-001`, target testing
strategy, and target UI or diagram policy. Load full diagram guidance only
when source format, rendering, or presentation capability is uncertain.

- Apply this gate when UI behavior, visual layout, accessibility-relevant
  state, generated diagram output, or discussion diagram presentation changes.
- Use the target-owned visual validation method: screenshot review, component
  test, accessibility check, local render, generated artifact check, or manual
  review.
- Always keep the portable ASCII diagram baseline for discussion diagrams.
- Check important desktop/mobile or relevant output sizes when layout can
  shift.
- Verify text fit, overlap, contrast-sensitive states, empty/loading/error
  states, and changed visual artifacts when applicable.
- Do not claim native rendering, screenshot evidence, or artifact generation
  unless that evidence was produced in the current scope.
- If visual validation cannot run, record the skipped command or review,
  reason, and residual visual risk.
