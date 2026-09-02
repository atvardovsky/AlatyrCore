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
2. the generated `.ai/assistant/bootstrap-index.json` routing projection
3. the generated `.ai/assistant/entry-packet.json` first-use routing packet
4. the framework semantic-codebook preload closure and three contour root
   context indexes named by that projection
5. only matching recursive section indexes and selected content descriptors
6. the compact workspace-mode catalog when that optional module is enabled
7. one selected mode descriptor and applicable shared root context
8. task classification from compact request, operation, risk, and scale
   signals
9. task decomposition cues for non-trivial work, using one local task for
   small work when compact evidence is enough
10. the selected profile's required context
11. one or more project-area overlays when the task names affected areas
12. task-scale overlays only when the classifier selects small-task for a
   cheap evidence lane, the task is large, resumable, team-active, explicitly
   debug-enabled, at material evidence finalization, or an enabled-team write
   preflight finds possible active-work overlap
13. bounded project-knowledge routing after profile/area selection and again
   after concrete changed facts, paths, symbols, subsystem or architecture
   relationships, dependencies, contracts, or issue lineage become known

Then it expands only when the router or human profile names a boundary,
conflict, approval trigger, or missing source-of-truth fact.

The bootstrap index is a deterministic, hash-bound projection of the target
manifest, compact project map, and context router. It exposes only routing,
operation, gate, enabled-module, version, and known-gap metadata. If a source
hash differs, repair or regenerate the projection before routine routing; load
the named canonical sources only for that repair, ambiguity, or explicit
audit.

The compact router should be an index, not a second policy corpus. Keep full
profile, intent, migration, consistency, and task-scale instructions in lazy
descriptor files. The router may retain short `use_when` signals needed to
choose a descriptor without opening every profile.

The entry packet is generated metadata, not another policy owner. It should
summarize exact installed profile routes, gate fragments, operation routes
when present, allowed-action modes, and support-delta entry points. If the
packet is missing or stale, repair it from canonical adapter sources before
routine routing or fall back to the named owners with an explicit context
receipt.

## Router Contract

A target context router should define:

- schema version
- human reference file
- preloaded context that must not be reread
- generated bootstrap projection and its canonical source hashes
- generated first-use entry packet path and schema version
- framework, project, and assistant recursive context-index roots
- maximum recursive navigation depth and fail-closed index behavior
- semantic-codebook index, preload term IDs, namespace boundary, version and
  digest behavior, conditional shard loading, and canonical-prose fallback
- bootstrap budget plus profile total, portable, and reserved target-context
  budgets
- context receipt fields
- task classification classes, order, ambiguity behavior, expansion triggers,
  and their task-scale overlay mappings
- task decomposition policy path, plan template, load triggers, small-task
  behavior, and executor-selection summary
- routing order
- canonical profile entries
- bounded operation candidates per profile
- compact operation-index and canonical operation-catalog paths, single entry
  alias, health operation, and preview policy without embedding either source
- optional workspace-mode routing to a compact catalog, shared root descriptor,
  one selected mode directory, ambiguity behavior, and preflight
- optional intent overlays that compose with every base profile
- optional project-area overlays
- optional task-scale overlays for large, resumable, team-active, material-
  evidence, or explicitly debug-enabled work
- optional consistency routing from changed fact IDs to applicable
  relationships
- required project-knowledge routing through a compact root index, bounded
  shard selectors, initial/refined packet limits, and authority/freshness rules
- use-when signals
- required context paths
- conditional context paths paired with explicit load conditions
- expansion triggers
- approval gates
- validation or manual review
- final evidence

Schema 10 adds explicit task classification to schema 9's recursive-index,
semantic-codebook, profile, overlay, and budget behavior. Schema changes that
move owned fields between the index and descriptors must advance the target
adapter schema and template version. Every indexed descriptor must exist in
the selected support profile; disabled optional modules must not remain
advertised through paths that scaffolding omitted.

Resolve routing in this order: bootstrap projection, core semantic preload,
contour index branch, profile and overlays, selected canonical owners, then
bounded relationship expansion. Index summaries and codebook definitions do
not replace the selected owner. Record missing indexes, stale digests, unknown
semantic terms, exceeded depth, or budget expansion instead of silently
loading the complete contour.

The bootstrap should contain only enough target-owned context to select a
profile and find project areas. Full blueprints, source-of-truth registries,
operation catalogs, module profiles, policy files, and human profile explanations belong in
selected profile or overlay context.

Keep the bootstrap outside assistant catalog content ownership because it
digests the assistant catalog itself. After installed target files change,
rebuild recursive catalogs first and bootstrap second.

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

Test-first configuration, execution, or a bounded recommendation should use a
separate optional intent overlay. Evaluate its compact trigger from the
selected testing/risk context, then load only the target policy and selected
configuration or change flow. Do not load test-first detail or repeat a
recommendation for every code edit.

Extension lifecycle work should use a separate optional intent overlay. Start
with the extension rule, source-access and prompt-injection policy, and compact
target catalog. Load only one selected lock entry, normalized manifest,
bindings, item set, lifecycle flow, gate, and evidence record. Do not scan or
load every extension, and do not access remote sources outside target policy.

Dependency knowledge work should use a separate optional intent overlay. Start
with the target dependency policy and compact catalog. Load one resolved
package instance, selected normalized fact records, applicable deviations, and
named evidence only after the route requires them. Keep package-manager graphs,
raw vendor documentation, nested adapters, unrelated packages, and historical
snapshots outside routine bootstrap. Use fingerprints for an unchanged fast
path and bounded graph traversal for public transitive references.

When an overlay needs a detailed reference only for a subset of requests, put
the path and its load condition in `conditional_context` instead of the default
`required_context`. Conditional paths must remain machine-visible to routing
checks, but they do not count as loaded until their named condition is true.

Task classification runs before broad context expansion. It should select one
of `small-task`, `standard-task`, `large-or-resumable`, or
`protected-or-sensitive` from compact request, operation, risk, changed-fact,
approval, budget, and validation signals. Ambiguous classification is read-
only: select the smallest plausible class for inspection, ask for the missing
fact, and do not edit until the current scope is authorized.

## Task Decomposition Routing

After task classification, operation routing, profile/area selection,
changed-fact review, risk, authorization, and support-delta signals are known,
select task decomposition for non-trivial work. The router should point to the
target task-decomposition policy and plan template instead of embedding the
full decomposition rule in bootstrap.

For small tasks, record one local task from compact entry-packet cues when one
profile, one local surface or direct neighbor set, and focused validation are
sufficient. Standard, large, protected, or delegated work should load the
target decomposition policy and plan template before implementation or worker
dispatch.

The decomposition plan assigns each subtask one implementation level,
dependencies, bounded context, allowed files or surfaces, validation,
acceptance criteria, and executor decision. Delegation consumes the
primary-owned plan only after task readiness is known; it cannot create
broader authority, approval, or context.

When a new owner, relationship, policy boundary, approval, or validation
failure appears, load only that triggering context and revise the affected
task. Do not respond to one escalation by loading every profile, module, role,
or relationship shard.

The `small-task` class is valid only while one base profile and one local
surface or direct neighbor set are sufficient, no accepted semantic or logical
fact changes, no protected boundary is crossed, and focused validation can
prove the result. It maps to a lazy `small-task` task-scale overlay whose
required context is limited to core/final gates and directly selected owner
evidence. It must not load large-task packets, change packages, Debug Mode,
team history, full help, full gate checklists, or broad project knowledge
unless an expansion trigger appears. Expansion triggers include semantic fact
changes, missing or contradicted owners, approval or safety boundaries,
multi-area scope, failed focused validation, or explicit broad audit.

The router should use the same canonical profile names as
`context-profiles.md` unless the target adapter records a deliberate local
renaming.

Budgets are routing controls, not safety limits. Schema 8 preserves schema 7's
separate maximum total profile words, portable framework/adapter words, and
capacity reserved for target-owned facts. Values must be positive, portable plus reserved must
not exceed total, and source templates should retain meaningful target
headroom. A target may tune them from measured evidence.

Keep a soft bootstrap threshold below its hard maximum so growth is visible
before failure. When required owner, safety, approval, or validation context
exceeds a budget, load it and record the reason, boundary, added files,
measured or explicitly estimated volume, and intentionally omitted context.
Static source estimates are benchmark evidence, not a claim about hidden
client context, billed tokens, exact semantic delivery, or an actual assistant
run. A context packet that supports a cost or context-delivery claim should
separate planned context, repository-resolved context, and observed host or
provider evidence. Provider usage can support token accounting when exposed by
the provider, but only host delivery telemetry can prove the exact semantic
guidance bundle reached the model.

Workspace-mode routing is a separate dimension from task profiles, intent,
project areas, gates, and task scale. When enabled, read the compact mode
catalog after bootstrap, select one accepted mode from explicit user choice or
one unambiguous evidence match, then load only that descriptor and applicable
root support. Ask on ambiguity. Mode selection must not activate nested
adapters or grant permissions, approval, write scope, authority, or gate
bypass. Keep every actual mode in its own target directory and keep the
authoring `_template` outside active catalog entries.

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

A Debug Mode overlay is optional and explicitly scoped. Route it only after a
current task/session activation request or when selected debug evidence needs
status, checkpoint, finalization, repair, or comparison. Start from the compact
index and selected record, keep transcripts and unrelated records out of
context, and expire the overlay at the logical-scope boundary. Debug routing
does not authorize the observed engineering task.

A team-active route should point to a lazy target overlay descriptor outside
bootstrap. In an enabled team project, a state-changing operation reads the
compact active-work index first. It expands the descriptor only for an explicit
team request, a task/backend/branch match, possible changed-fact, owner,
contract, dependency, migration, generated-artifact, or surface overlap, or
unresolved index evidence. The expanded route selects the structured team
policy, registry metadata, backend contract, selected task record, relevant
flow, and gate. Keep unrelated tasks and team history outside context.

When the optional consistency-map module is enabled, the router should point
to its compact reverse index and machine-readable map. Use changed Git paths,
support-state differences, or explicit changed fact IDs to select applicable
shards only after a semantic change or suspected drift. Traverse accepted
relationships within target-owned depth and node limits. Load relationship
candidates, unrelated shards, or the full support tree only for a named
conflict, gap, failed check, or audit.

Project-knowledge routing is a required core route but not bootstrap content.
After selecting a non-trivial profile and project area, load its compact root
index and only descriptors matching the profile plus a stronger area,
dependency, fact, contract, path, symbol, or issue signal. Run an initial
selection before broad orientation and a refined selection after concrete
source evidence appears. Only accepted-current entries may become candidate
constraints after their canonical owners are read. Route stale items as
warnings and contradictions as blockers. Record selected, used, stale,
blocked, inapplicable, and packet-limit-omitted IDs in the context receipt.

Gate routing follows the same principle. Load the compact gate index and the
profile's core, task-specific, and final-evidence fragments. Load the complete
checklist only for ambiguity, gate repair, or an explicit full acceptance
audit. Fragments route obligations; they do not weaken their canonical rule
owners or replace semantic review.

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
