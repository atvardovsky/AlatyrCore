# Contract Artifacts Gate

Canonical owners: `ALATYR-SOURCE-001`, `ALATYR-RISK-001`,
`ALATYR-INTEGRITY-001`, `ALATYR-CODEDOC-001`, and target testing strategy.
Load full guidance only when the changed fact crosses API, data, event,
generated-reference, or external-boundary contracts.

- Name the changed contract fact before choosing an artifact.
- Identify the canonical owner and derived surfaces for the contract.
- Check whether the project already has a matching OpenAPI, GraphQL, JSON
  Schema, protobuf, migration, fixture, generated reference, event catalog,
  route map, public interface, or equivalent artifact.
- Update existing contract artifacts before adding a new artifact family.
- Keep generated artifacts derived from their target-owned source; do not edit
  generated output as the only source of truth.
- Validate consumers, fixtures, examples, and documentation that rely on the
  changed contract.
- If no contract artifact exists for a cross-boundary fact, record whether the
  project accepts the gap, needs a new artifact, or requires owner review.
- Final evidence names updated artifacts, skipped artifacts, validation, and
  residual consumer or compatibility risk.
