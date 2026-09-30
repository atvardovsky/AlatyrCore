# Documentation Gate

Canonical owners: `ALATYR-SOURCE-001`, `ALATYR-INTEGRITY-001`, and
`ALATYR-SUPPORT-001`.

For every code or test change, record one Project Contour Sync Decision:
`updated`, `not-required`, `blocked`, or `unverified`. Check the changed fact
owner plus applicable project orientation, registry, architecture, workflow,
data/API contract, diagram, vocabulary, validation, and known-gap surfaces.
Name checked owners and evidence. A `not-required` decision needs a
fact-specific reason; `blocked` or `unverified` prevents completion.

- Confirm the documentation owner and whether the change is explanatory or
  changes an accepted fact.
- Keep canonical policy and project facts in their owners; link instead of
  creating a second source of truth.
- If behavior, contracts, diagrams, examples, commands, or public promises
  change, activate the semantic-integrity gate.
- Run target documentation, link, example, or generated-output validation that
  exists. Do not invent commands.
- For project-support documentation, verify that a new developer can locate:
  the project purpose, main architectural areas, canonical owner for each
  material fact, primary workflows, validation entry points, and known gaps.
- Require every material claim to link to its canonical owner and distinguish
  observed implementation, proposed intent, accepted decisions,
  contradictions, and unknowns.
- Reject documentation that reports generated or owner-maintained content as
  current without effective source bindings and current generation or review
  evidence.
- Record unanswered orientation questions as gaps. Structural validation does
  not prove documentation truth, completeness, or usefulness.
- Update `.ai/project/contour.md` only when its concise purpose, users, areas,
  owners, workflows, validation entry points, or known gaps changed. Keep
  detailed facts in their canonical owners.
