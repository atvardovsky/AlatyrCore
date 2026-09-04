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

After the generated bootstrap, an installed adapter may provide a generated
`.ai/assistant/entry-packet.json`. This first-use packet is the routine
machine surface for exact installed profile descriptors, default gate
fragments, operation routes when installed, allowed-action modes, support
delta entry points, and the cheapest sufficient support-profile policy. It is
generated from canonical adapter sources and must be checked or regenerated
after install or update. Human prose such as context profiles, module
profiles, help references, and full support state remains lazy unless the
packet is missing, stale, disputed, or insufficient for the selected task.

## Recursive Context Navigation

Every substantial framework, project, and assistant contour should expose a
recursive `context-index.json` tree. Treat it like site navigation: start from
the contour root, open only the matching section index, continue through
matching child indexes, and load selected content only after an exact task,
operation, owner, area, fact, path, symbol, contract, dependency, risk, or
conflict signal selects it.

Each index entry must retain a stable ID, content or child-index path, bounded
summary, selectors, explicit load condition, semantic references, owner
references, static word estimate, and content digest. Index paths are relative
to one contour root. Navigation must be acyclic, depth-bounded, repository-
contained, and free of duplicate content ownership. Cross-area relationships
belong in consistency or knowledge graphs; they must not create recursive
navigation loops.

The index is a generated routing projection, not a source of project or
framework truth. Human `README.md` files may explain a section, while the
machine index points to canonical owners. A folder may contain further
subfolders without imposing a universal physical depth, but routine traversal
must stop at the router's configured depth and context budgets.

The generated bootstrap is the preloaded entry point and must not be indexed
as assistant content: it digests the assistant catalog, so indexing it would
create a circular digest dependency. Rebuild project and assistant catalogs
before rebuilding bootstrap whenever installed target files change.

The generated `framework/file-inventory.json` is packaging and upgrade
evidence, not recursively routed framework content. It hashes
`framework/context-index.json`; indexing the inventory from that tree would
create the same circular digest dependency. Load the inventory explicitly only
for installation, update, packaging, or drift comparison.

## Context-Loaded Semantic Codebook

Compact machine records may reference versioned semantic terms instead of
repeating stable framework sentences. Resolve those references through the
installed framework semantic-codebook index before interpreting the compact
record. Load the small `preload` closure before other compact records and load
domain shards only when selected records reference their terms.

Framework terms use the `alatyr:*` namespace. Target project vocabulary uses
the `project:*` namespace and cannot replace or redefine a framework term.
Every semantic term must provide a complete definition, version, owning rule,
canonical owner, scope, explicit non-meanings when needed, dependency IDs, and
replacement state. Dependencies must resolve once in acyclic order.

Semantic compression is lossless only when every referenced term resolves at
the expected version and digest. On a missing, stale, conflicting, cyclic, or
unsupported term, load the named canonical owner and do not infer the compact
meaning. Keep canonical human policies complete and readable; use compact
terms primarily in indexes, descriptors, gates, records, and resolved context
packets where repeated definitions produce measured savings.

The resolved packet should contain selected item identities and digests,
required semantic definitions once, budget accounting, and a deterministic
packet digest. A term name is not assumed to be one provider token. Measure
word or provider-token effects and retain compression only when the definition
plus resolution overhead costs less than the repeated prose it replaces.

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

## Task Classification

Before loading profile-owned source files, classify the request by task scale.
The classifier is a routing gate, not approval and not a substitute for
logical review.

Use these canonical classes unless a target adapter records an equivalent
local naming map:

- `small-task`: one base profile is sufficient, one local surface or directly
  linked neighbor set is affected, no accepted semantic or logical fact
  changes, no protected boundary is crossed, and focused validation can prove
  the result.
- `standard-task`: one base profile is sufficient, but semantic, validation,
  source-of-truth, or non-obvious repair reasoning is needed.
- `large-or-resumable`: multiple profiles, project areas, workstreams,
  approval checkpoints, budget exceptions, or resumable phases are needed.
- `protected-or-sensitive`: approval, safety, security, credential,
  permission, destructive, spend, production, public-contract, or
  live-external boundaries may apply.

Classification happens after host preload and compact bootstrap, then before
loading broad profile prose, operation catalogs, full gate checklists, change
packages, or large-task packets. If classification is ambiguous, stay
read-only, select the smallest plausible class for inspection, and ask for the
missing fact before edits.

The `small-task` class is the cheapest path. It must not load a large-task
packet, change package, Debug Mode record, team history, full help reference,
or full gate checklist unless one of these expansion triggers appears:

- semantic or logical fact changes
- source-of-truth owner is missing, disputed, or contradicted
- approval, safety, security, data, architecture, public-contract, or
  live-external boundary appears
- multiple project areas, profiles, workstreams, or changed-fact owners are
  required
- focused validation fails or cannot prove the changed contract
- the user asks for broad audit, large-task orchestration, change package, or
  debug evidence

When `small-task` remains valid through finalization, use compact evidence:
classification, selected profile, direct owner or edited surface, loaded and
intentionally omitted context, preview/package/large-task skip reasons,
focused validation, broader checks skipped, and residual risk. If a trigger
fires, stop using small-task evidence and route through the broader selected
profile or overlay.

## Bootstrap Context

Every installed adapter should keep a compact bootstrap set:

- target root assistant entry point as host-preloaded context
- generated `.ai/assistant/bootstrap-index.json`
- generated `.ai/assistant/entry-packet.json` as the first post-bootstrap
  routing packet

The bootstrap index points to the three contour context indexes and the
semantic-codebook index. Its projected `preload` term IDs are resolved before
selected compact records; the complete project vocabulary and non-applicable
domain codebooks remain lazy.

The generated index must carry source hashes for `.ai/alatyr.yaml`,
`.ai/README.md`, and `.ai/assistant/context-router.json`. Those canonical files
are recovery and audit inputs, not routine bootstrap. A stale or missing index
must be repaired before it is trusted for routing.

Do not put the full blueprint, source-of-truth registry, operation catalog,
module profile, project contour, assistant contour, human context profiles, or
task-owned source files in mandatory bootstrap. Route them after task
classification.

Framework documents, flows, gate fragments, and policies should be loaded
through the selected task profile instead of being mandatory for every task.
The complete gate checklist remains lazy unless ambiguity or a full audit
requires it.

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

Use one normalized context receipt with separate layers:

- `planned`: paths selected before loading and their static word estimate
- `resolved`: paths actually resolved by routing and their static word estimate
- `observed`: files and tokens exposed by host or provider telemetry

For a resolved context packet, also record the traversed index chain, selected
item IDs and digests, resolved semantic term IDs and versions, packet digest,
dictionary fallback or expansion events, and intentionally omitted branches.
This evidence proves packet identity and routing behavior, not model
comprehension.

When selected project guidance can affect changed facts, approval, validation,
or a material decision, extend that receipt with `semantic_guidance` schema 1.
Record three distinct identity sets:

- `planned`: guidance selected before canonical-owner resolution
- `resolved`: the ordered guidance actually resolved for the task, with exact
  canonical-owner SHA-256 digests
- `observed`: only guidance identities whose delivery is supported by host or
  provider evidence; use `partial` or `unavailable` honestly

Each semantic identity contains a stable guidance ID, canonical-owner path and
digest, authority, freshness, and applicability. A planned identity may use
`unknown` for an owner digest; a resolved or reported observed identity may
not. Preserve delivery order because narrower or later selected guidance may
depend on that order. For project-knowledge routes, normalize `knowledge_id` as
the receipt `guidance_id` and `canonical_owner_sha256` as lowercase
`sha256:<digest>`; record only the authority state, freshness state, and
applicability result needed to identify the selected guidance.

For each identity set, record a bundle digest with digest schema version `1`
and algorithm `sha256`. Compute it over the UTF-8 JSON array of the ordered
identity objects using sorted object keys, ASCII escaping, and compact
separators. The array order is significant. The empty applicable-guidance set
has its own valid digest and is different from unavailable evidence.

Only exact host or provider telemetry supports observed context or token-cost
comparisons. Planned and resolved estimates remain routing evidence even when
observed telemetry is partial or unavailable; they must not be relabeled as
actual model context.

A semantic bundle digest proves only which identity metadata was planned,
resolved, or observably delivered at the stated evidence level. It does not
prove that a model read, understood, remembered, or followed the guidance.
Use resolved bundle comparison for deterministic revalidation; do not make
safe progress depend on unavailable model-comprehension evidence.

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

After profile and area selection for a non-trivial task, apply the compact
project-knowledge preflight. Read the root routing index, then only shard
descriptors matching the profile plus at least one area, subsystem,
architecture item, dependency, fact, contract, path, symbol, or issue signal.
Perform an initial route before broad
orientation and one refined route after concrete changed facts or source
surfaces become known. Load only bounded accepted-current entries and their
canonical owners; stale items are warnings, contradictions are blockers, and
unrelated knowledge remains lazy.

## Consistency Relationship Routing

Targets with many project areas or competing surfaces may enable a compact
consistency map. After a semantic change or suspected drift, load the target
source-of-truth registry and consistency map together, resolve changed fact
IDs, and follow only applicable relationship edges. Keep the portable
consistency-model explanation conditional unless relationship semantics,
adapter repair, or conflicting evidence requires it. Expand to dependent
contracts for propagation, conflicts, failed validation, or approval
boundaries. The human source-of-truth registry remains the owner explanation.

Measure this composed semantic route as a target context-cost scenario. Do not
remove either target-owned surface to recover budget; move redundant portable
explanation to conditional context or record a justified expansion receipt.

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
Keep semantic identity metadata in the packet, but load guidance content only
for initially selected owners or identities changed by later revalidation.
Keep the identity set inside the selected knowledge route's packet limits and
record omitted applicable identities and the expansion decision.

## Change-Package Tasks

Use the optional `change-package` overlay only for a coherent material outcome,
semantic multi-surface approval, architecture segment or capability, audit, or
publishable provenance need. It composes with the smallest base profile and is
independent from `large-or-resumable`.

Load the compact package index and active package identity first. Load the
machine template, discussion summary, companion decisions, corrections, plan,
or validation evidence only when the current phase needs them. Do not create
or load a package for an ordinary local task.

## Durable Engineering-Evidence Tasks

Apply the `engineering-evidence` overlay lazily at finalization when a material
semantic, architectural, or non-obvious repair may leave reusable knowledge
only in the current session, or when a user explicitly asks to capture or
inspect a record.

Load the compact target index, capture gate, and portable owner first. Load
only the selected record for lookup, and load the capture flow/template only
for an authorized write or repair. Small self-explanatory changes may skip
with a specific reason. Do not load the full evidence history, raw session
content, or a change package solely because this overlay applies.

When captured evidence contains a reusable conclusion, hand off a bounded
candidate to the project-knowledge promotion flow. Do not promote it or add it
to routine task routing without target-owned review and canonical-owner
update.

## Debug Mode Tasks

Use the optional `debug-mode` task-scale overlay only after explicit activation
for the current task or session, or for status, finalization, repair, or
comparison of selected existing debug evidence. It composes with the ordinary
task profile; it does not replace that profile or grant engineering actions.

Load the compact debug index, gate, and portable owner first. Load only the
active or explicitly selected record. Load the flow and templates for an
authorized checkpoint, finalization, repair, or summary. Do not load unrelated
records, raw conversations, or session history. Checkpoint only material events
so observation does not materially distort the task.

At finalization, load the source-of-truth registry only when a skipped durable-
evidence decision claims canonical preservation. Load the exact reproducer or
validation owner only when claim fidelity is being classified; do not broaden
to unrelated project validation.

Expire the overlay when the logical scope completes, changes, is abandoned, or
is explicitly disabled. Cross-task comparison should read compact index
metrics first and expand only to selected records when task class, capture
quality, timing evidence, or quality evidence requires it.

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
