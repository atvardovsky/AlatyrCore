# Fixture: Minimal Backend API

This fixture describes a backend API target shape.

## Target Shape

- README exists
- API routes or controllers exist
- Tests exist
- API contract source is missing or ambiguous
- No diagram policy exists
- No AI infrastructure inventory exists

## Expected Alatyr Behavior

- Do not invent API contract ownership.
- Add missing source-of-truth registry entries for public API, data model, and
  validation.
- Select `architecture-change` or `business-change` profiles for accepted API
  contract changes.
- Require approval for architecture, public contract, data, security, or live
  external boundary changes.
- Keep AI infrastructure integration review-only until inventory, provenance,
  source access, prompt-injection policy, and approval are present.
