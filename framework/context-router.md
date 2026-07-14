# Context Router

The context router is the machine-readable companion to context profiles.

Context profiles remain the human-readable source for task routing rationale.
The router gives assistants and deterministic checks a compact map from task
profile to required context, expansion triggers, validation, approval, and
final evidence.

## Purpose

Use a context router to reduce repeated prose parsing before routine work.

A target adapter can load:

1. assistant instructions that the host already preloaded
2. the compact bootstrap, including `.ai/assistant/context-router.json`
3. the selected profile's required context
4. one or more project-area overlays when the task names affected areas

Then it expands only when the router or human profile names a boundary,
conflict, approval trigger, or missing source-of-truth fact.

## Router Contract

A target context router should define:

- schema version
- human reference file
- preloaded context that must not be reread
- bootstrap context
- bootstrap and profile context budgets
- context receipt fields
- routing order
- canonical profile entries
- optional project-area overlays
- use-when signals
- required context paths
- expansion triggers
- approval gates
- validation or manual review
- final evidence

The bootstrap should contain only enough target-owned context to select a
profile and find project areas. Full blueprints, source-of-truth registries,
module profiles, policy files, and human profile explanations belong in
selected profile or overlay context.

The router should use the same canonical profile names as
`context-profiles.md` unless the target adapter records a deliberate local
renaming.

Budgets are routing controls, not safety limits. When sufficient work requires
more context, the assistant records the reason, changed boundary, and added
files in the context receipt before expanding.

## Ownership

The router is adapter-owned in a target repository. It must be rewritten from
target evidence before installation is accepted.

Framework core owns the router shape and canonical profile names, not concrete
target source files, commands, or policies.

## Markdown Relationship

The router does not replace Markdown context profiles. It narrows the first
routing decision. Load the human profile only when routing is ambiguous, the
router and evidence conflict, or a missing entry must be repaired.

When the router and Markdown profile disagree, the assistant should report
adapter drift and use the human-readable context profile as the explanation
surface until the target adapter repairs the conflict.

## Safety

The router must not be used to bypass:

- logical integrity review
- source-of-truth decisions
- approval records for protected changes
- target validation or unresolved validation evidence
- prompt-injection policy for imported AI infrastructure

If a task crosses a boundary not covered by the selected profile, expand
context and report why. Do not satisfy cross-boundary work by loading every
profile in full; compose the smallest profile and area overlays that own the
changed facts.
