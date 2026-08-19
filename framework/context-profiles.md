---
alatyr_doc:
  id: framework.context-profiles
  type: framework-rule-owner
  owns_rules:
    - ALATYR-CONTEXT-001
  depends_on:
    - ALATYR-ADAPTER-001
  applies_to:
    - all
---
# Context Profiles

Context profiles limit the required reading set for an Alatyr task.

They preserve the minimum sufficient context rule: use host-preloaded
instructions, read the compact routing bootstrap, choose the closest task
profile, read that profile's required sources, and expand only when boundaries
or conflicts require it.

When an installed adapter includes a machine-readable context router, it must
use the same canonical profile names and stay aligned with this Markdown
contract. The router is the default cheap routing surface. This human-readable
file is loaded when rationale, conflicts, missing entries, or adapter repair
require it; it is not mandatory bootstrap context.

The compact router should index one lazy descriptor per canonical profile.
Load only the selected descriptor. Intent, migration, consistency, and
task-scale descriptors compose with that profile when their trigger applies;
they do not belong inline in every profile or in mandatory bootstrap.

Architecture inventory, explanation, pattern discussion, comparison, review,
and documentation use an intent overlay over the smallest base profile. Start
with the compact project architecture catalog and selected item evidence. Do
not load the full `architecture-change` profile until an accepted decision or
crossed boundary requires change execution context.

Code-comment style proposals, documentation review, structured-comment work,
and generated-reference requests use a separate optional intent overlay. Start
with the compact code-documentation catalog and profile selector, then compose
with `docs-local`, `code-local`, or a higher-risk base profile according to the
changed fact. Different source sets may select different accepted profiles.

Project term, alias, acronym, glossary, and terminology-consistency requests
use a separate optional intent overlay. Start with the compact vocabulary
catalog, then load only selected full term records, data-dictionary links, and
named canonical owners. Ordinary tasks should not load the full vocabulary.

Explicit test-first configuration or execution and bounded recommendation
triggers use a separate optional intent overlay. Evaluate recommendation from
already selected changed-fact and risk context first; load target policy,
selected flow, gate, skill, and evidence only when the result is required or
recommended, or the user explicitly requests test-first work.

Extension list, inspection, installation, update, disablement, removal, or
review uses a separate optional intent overlay. Load the compact extension
catalog first, then only the selected lock entry, normalized manifest, target
bindings, items, lifecycle flow, gates, and evidence. Do not load all installed
extensions or search remote sources during ordinary tasks.

## Canonical Profiles

Use these profile names unless a target adapter deliberately renames them:

- `docs-local`
- `code-local`
- `business-change`
- `architecture-change`
- `data-change`
- `security-sensitive`
- `ai-infrastructure`
- `framework-upgrade`

Target adapters may add local profiles, but they should not remove the
canonical names unless the target documents the replacement.

The `framework-upgrade` profile should be migration-first. Its initial context
contains lifecycle, migration-diff, installed baseline, and recheck evidence;
changed rule IDs, categories, profiles, canonical sources, template surfaces,
and local deviations select later context. A framework file may be listed as
candidate context without being loaded for every upgrade.

## Profile Contract

Each target profile should define:

- use when
- bounded operation candidates for cheap automatic routing
- required context
- conditional context paths with explicit load conditions
- expansion triggers
- approval gates
- validation or manual review
- expected final evidence
- a context budget or the router's default budget

The profile should list concrete target paths after installation. Placeholder
paths are acceptable only before the adapter is accepted.

## Bootstrap Context

Every installed adapter should keep a compact bootstrap set:

- target root assistant entry point as host-preloaded context
- `.ai/alatyr.yaml`
- `.ai/README.md` or an equivalent compact project/context map
- `.ai/assistant/context-router.json`

Do not put the full blueprint, source-of-truth registry, operation catalog,
module profile, project contour, assistant contour, human context profiles, or
task-owned source files in mandatory bootstrap. Route them after task
classification.

Framework documents, flows, gates, and policies should be loaded through the
selected task profile instead of being mandatory for every task.

## Context Budgets And Receipts

The router should define maximum bootstrap files/words and default profile
files, total words, portable words, and words reserved for target-owned facts.
A target may tune them from measured repository evidence, but portable plus
reserved capacity must not exceed the total.

Record both a soft bootstrap threshold and a hard maximum. Rebaseline the
static estimate when bootstrap files change. For an actual assistant run,
record loaded paths or sections and distinguish observed, assistant-reported,
estimated, and unavailable context rather than presenting source byte counts
as exact model-token usage.

If sufficient context exceeds a budget, continue safely and record:

- selected profile, task-scale overlay, and project areas
- files loaded and why
- boundary or conflict that required expansion
- approximate context volume
- context intentionally not loaded
- residual risk

Source-template estimates must charge unresolved target references against the
reserved target capacity. Accepted adapters resolve and measure concrete target
paths. Budgets reduce accidental overloading; they never justify skipping an
owner, approval rule, safety policy, or validation fact required by changed
behavior.

## Project-Area Overlays

Large repositories should route module or domain context through compact area
overlays. Each overlay names its trigger, required context, and expansion
conditions. Compose one base task profile with only the overlays that own the
changed facts.

## Consistency Relationship Routing

Targets with many project areas or competing surfaces may enable a compact
consistency map. Load it after a semantic change or suspected drift, resolve
changed fact IDs, and follow only applicable relationship edges. Expand to
dependent contracts for propagation, conflicts, failed validation, or approval
boundaries. The human source-of-truth registry remains the owner explanation.

## AI Infrastructure Item Routing

For skill, prompt, gate, checker, tool/MCP, bridge, or wrapper work, load the
target AI infrastructure router first. Select one route and the smallest item
set, then load only the selected canonical sources, required context,
permissions, gates, validation, and output contracts. Load import and protected
tool policy only for routes that need them.

For recommendation, load only the bounded project area and owner, relevant
inventory and existing item contracts, the compact target development evidence
index when present, and recommendation evidence. Inspect only references for
selected patterns. Do not load the index for unrelated tasks or load external-
source policy until an accepted candidate enters a later adaptation route.

## Large Or Resumable Tasks

Use a task-scale overlay when work has multiple independently verifiable
workstreams, crosses profiles or project areas, exceeds the profile budget,
needs separate approval or validation checkpoints, or must survive a context
reset. Route that overlay to `large-task-orchestration.md` and a target-owned
operation packet.

The overlay does not authorize loading every profile. Resume from the compact
bootstrap, packet, active workstream context, changed-fact owners, and
dependencies. Do not create a packet for a small task that fits one profile.

## Change-Package Tasks

Use the optional `change-package` overlay only for a coherent material outcome,
semantic multi-surface approval, architecture segment or capability, audit, or
publishable provenance need. It composes with the smallest base profile and is
independent from `large-or-resumable`.

Load the compact package index and active package identity first. Load the
machine template, discussion summary, companion decisions, corrections, plan,
or validation evidence only when the current phase needs them. Do not create
or load a package for an ordinary local task.

## Team-Active Tasks

When the optional team module is enabled, run a compact active-work-index
preflight before state-changing operations. Use a `team-active` task-scale
overlay for identity selection, team status, claims, concurrent-work checks,
checkpoints, handoffs, team review, merge readiness, or a write operation that
matches or may overlap active work. Load the structured team policy, registry
metadata, backend contract, selected task projection, relevant team flow and
gate, and only the selected task's changed-fact owners and dependencies.

Compose `team-active` with `large-or-resumable` only when the task satisfies
both activation gates. Do not load the full team history or all active tasks
when active-index metadata proves they cannot overlap the selected facts,
contracts, dependencies, or surfaces.

## Expansion Rules

Expand context when:

- a semantic or logical fact changes
- multiple review items share a fact, invariant, or contract
- source-of-truth evidence conflicts
- a change crosses architecture, business, data, security, lifecycle, or
  assistant-infrastructure boundaries
- approval scope is unclear
- validation evidence contradicts the proposed change
- a bridge, prompt, skill, checker, or gate may be affected
- the selected profile exceeds its budget and an owner must be chosen more
  precisely

If the profile is ambiguous, use the smallest likely profile, report the
assumption, and ask only for the missing decision that blocks safe routing.
