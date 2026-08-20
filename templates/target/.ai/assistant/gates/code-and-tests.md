# Code And Tests Gate

Canonical owners: `ALATYR-RISK-001`, `ALATYR-INTEGRITY-001`, and target test
strategy. Load full testing guidance only when selecting unfamiliar test
levels, isolation, or cross-boundary validation.

- State the observable contract and re-derived invariant before implementation.
- Prefer the smallest deterministic test level that proves that contract.
- Cover relevant failure, boundary, ownership, idempotency, persistence, or
  external-error behavior; expand only for applicable risks.
- Use target-owned commands, fixtures, isolation, and CI evidence.
- Do not weaken assertions or delete useful coverage to make a change pass.
