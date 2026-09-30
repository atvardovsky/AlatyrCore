# Code And Tests Gate

Canonical owners: `ALATYR-RISK-001`, `ALATYR-INTEGRITY-001`, and target test
strategy. Load full testing guidance only for unfamiliar levels, isolation, or
cross-boundary validation.

- State the observable contract and re-derived invariant before implementation.
- Prefer the smallest deterministic test level that proves that contract.
- Cover applicable failure, boundary, ownership, idempotency, persistence, and
  external-error risks.
- Apply contract-artifacts for public interfaces, schemas, fixtures, generated
  references, events, APIs, or external boundaries.
- Apply visual-validation for UI, rendered diagrams/artifacts, screenshots, or
  accessibility behavior.
- Use target-owned commands, fixtures, isolation, and CI evidence.
- Do not weaken assertions or delete useful coverage to make a change pass.
- Record the final-evidence Project Contour Sync Decision even when no
  documentation file changed.

Test evidence classes:

- `passed`: ran and proves its named scope.
- `failed`: ran and remains evidence.
- `skipped`: policy permits omission; record reason/risk.
- `unavailable`: required execution is unavailable; validation is incomplete.
- `not-applicable`: the fact needs no such evidence.

Completion guard:

- Code changes without runnable or explicitly not-applicable target validation
  are `partial` or `unverified`, not complete.
- Passing tests prove only their declared scope; they do not replace integrity,
  approval, contract-artifact, or visual gates.
