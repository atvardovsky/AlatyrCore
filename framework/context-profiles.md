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
- optional context triggers
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

The router should define maximum bootstrap and default profile file/word
budgets. A target may tune them from measured repository evidence.

If sufficient context exceeds a budget, continue safely and record:

- selected profile, task-scale overlay, and project areas
- files loaded and why
- boundary or conflict that required expansion
- approximate context volume
- context intentionally not loaded
- residual risk

Budgets reduce accidental overloading; they never justify skipping an owner,
approval rule, safety policy, or validation fact required by changed behavior.

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

## Team-Active Tasks

When the optional team module is enabled, use a `team-active` task-scale
overlay for team status, claims, concurrent-work checks, checkpoints, handoffs,
team review, or merge readiness. Load the target team operating model, compact
work registry or selected task projection, relevant team flow and gate, and
only the selected task's changed-fact owners and dependencies.

Compose `team-active` with `large-or-resumable` only when the task satisfies
both activation gates. Do not load the full team history or all active tasks
when registry metadata proves they cannot overlap the selected facts,
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
