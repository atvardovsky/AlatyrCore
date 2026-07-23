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
5. task-scale overlays only when the task is large, resumable, or team-active

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
- bounded operation candidates per profile
- operation-catalog path, single entry alias, health operation, and preview
  policy without embedding the full catalog
- optional project-area overlays
- optional task-scale overlays for large, resumable, or team-active work
- optional consistency routing from changed fact IDs to applicable
  relationships
- use-when signals
- required context paths
- expansion triggers
- approval gates
- validation or manual review
- final evidence

The bootstrap should contain only enough target-owned context to select a
profile and find project areas. Full blueprints, source-of-truth registries,
operation catalogs, module profiles, policy files, and human profile explanations belong in
selected profile or overlay context.

Profile operation candidates make common routing cheap. Load the full target
operation catalog only for the explicit `Alatyr` entry, adapter health,
ambiguity resolution, operation handoff, or adapter repair. A clear request may
route automatically when one enabled operation matches and its allowed-action
scope is sufficient.

The router should use the same canonical profile names as
`context-profiles.md` unless the target adapter records a deliberate local
renaming.

Budgets are routing controls, not safety limits. When sufficient work requires
more context, the assistant records the reason, changed boundary, and added
files in the context receipt before expanding.

A large-task overlay should route to the orchestration flow and operation
packet without adding those files to every normal task profile. While a packet
is active, load only the active workstream's required context, fact owners, and
dependencies. The packet remains coordination evidence, not a source of truth.

A team-active route should point to a lazy target overlay descriptor outside
bootstrap. That descriptor selects the optional team contract, target
operating model, compact work registry or selected task, and relevant team
flow and gate. Compare changed-fact IDs and canonical owners before file paths,
and keep unrelated tasks and team history outside the selected context.

When the optional consistency-map module is enabled, the router should point
to its machine-readable map. Use it only after a semantic change or suspected
drift: resolve changed fact IDs, select applicable direct edges, and expand to
dependent contracts only when the map or conflicting evidence requires it.

When the map is disabled or incomplete, route logical review to canonical fact
owners and the smallest target surfaces needed to re-derive scope, identity,
ownership, lifecycle, persistence, caller, and dependency invariants. Multiple
review comments that share a fact or contract are one expansion trigger, not
independent local tasks.

For AI infrastructure work, route first to the target AI infrastructure router
instead of loading every skill, prompt, gate, tool, bridge, and import policy.
The selected route decides whether inventory, ordinary target-owned item use,
read-only recommendation, adaptation, protected tool policy, or bridge
compatibility context is needed. Recommendation loads one bounded project area
and relevant existing-item evidence rather than broad project or import policy.
Load target development-pattern evidence only for lazy capture,
recommendation, adapter recheck, or explicit effectiveness review, then inspect
only selected pattern references.

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
