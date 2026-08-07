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

The compact router should be an index, not a second policy corpus. Keep full
profile, intent, migration, consistency, and task-scale instructions in lazy
descriptor files. The router may retain short `use_when` signals needed to
choose a descriptor without opening every profile.

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
- compact operation-index and canonical operation-catalog paths, single entry
  alias, health operation, and preview policy without embedding either source
- optional intent overlays that compose with every base profile
- optional project-area overlays
- optional task-scale overlays for large, resumable, or team-active work
- optional consistency routing from changed fact IDs to applicable
  relationships
- use-when signals
- required context paths
- conditional context paths paired with explicit load conditions
- expansion triggers
- approval gates
- validation or manual review
- final evidence

Schema changes that move owned fields between the index and descriptors must
advance the target adapter schema and template version. Every indexed
descriptor must exist in the selected support profile; disabled optional
modules must not remain advertised through paths that scaffolding omitted.

The bootstrap should contain only enough target-owned context to select a
profile and find project areas. Full blueprints, source-of-truth registries,
operation catalogs, module profiles, policy files, and human profile explanations belong in
selected profile or overlay context.

Profile operation candidates make common routing cheap. Resolve exact IDs and
aliases through a checked compact derivative of the operation catalog. Load
the full target catalog only for the bare `Alatyr` entry, ambiguity, or
operation/adapter repair. Intent overlays such as diagram requests may compose
with code, security, or other base profiles without duplicating the operation
candidate in every profile.

Architecture intent should route first to a compact project-owned architecture
catalog. Selected area, pattern, decision, and repository evidence load after
catalog selection; full architecture-change, data, security, diagram, or
blueprint context remains conditional on the question and decision state.

Code-comment style proposals, documentation review, and generated-reference
work should use a separate optional intent overlay. Start from the compact
code-documentation catalog and profile selector, then load only the selected
source-set profile, affected symbols, canonical owners, generator
configuration, and validation. Do not load every profile or generated output.

Project vocabulary lookup, proposal, review, and terminology checks should use
a separate optional intent overlay. Start from the compact term/alias/acronym
catalog, then load only selected term records, applicable data-dictionary
links, and named canonical sources. Do not load the full vocabulary for one
term or an unrelated task.

When an overlay needs a detailed reference only for a subset of requests, put
the path and its load condition in `conditional_context` instead of the default
`required_context`. Conditional paths must remain machine-visible to routing
checks, but they do not count as loaded until their named condition is true.

The router should use the same canonical profile names as
`context-profiles.md` unless the target adapter records a deliberate local
renaming.

Budgets are routing controls, not safety limits. A target should keep a soft
bootstrap threshold below its hard maximum so growth becomes visible before
the router fails its contract. When sufficient work requires more context,
the assistant records the reason, changed boundary, added files, and measured
or explicitly estimated context volume in the context receipt before
expanding. Static source estimates are benchmark evidence; they are not a
claim about hidden client context or an actual assistant run.

A large-task overlay should route to the orchestration flow and operation
packet without adding those files to every normal task profile. While a packet
is active, load only the active workstream's required context, fact owners, and
dependencies. The packet remains coordination evidence, not a source of truth.

A change-package overlay should be equally lazy. Activate it only for a
coherent material outcome, semantic multi-surface approval, audit, or
publishable provenance need. Bootstrap and ordinary local profiles should not
load package templates. During execution, load the compact package index and
active workstream references first; expand to plan, discussion, companion,
correction, or validation evidence only when needed.

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
