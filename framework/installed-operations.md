# AI Framework Installed Operations

This file defines how to use an installed Alatyr Core adapter after the initial
installation.

Installed operations are requests to an assistant working inside a target
repository that already has Alatyr Core files and adapter facts. They include
creating or repairing project blueprints, rechecking adapter maturity after a
framework update, reviewing drift, inventorying, recommending, or adapting AI
infrastructure, discussing project architecture and patterns, coordinating
team tasks, or running a guided product-change workflow.

Concrete project facts, validation commands, reports, prompts, and update
cadence belong to the target repository adapter.

## Operation Types

An installed adapter should support these operation categories:

- single conversational entry, automatic routing, and compact help
- read-only current adapter health
- project blueprint creation or repair
- adapter recheck after Alatyr Core installation or upgrade
- framework upgrade impact review
- target source-of-truth drift review
- optional architecture inventory, explanation, pattern discussion,
  alternative comparison, review, and supporting-documentation maintenance
- optional project term lookup, acronym and alias resolution, vocabulary
  proposal and review, and terminology consistency checks
- optional test-first policy assessment, enablement, review, and bounded
  RED/GREEN/refactor execution
- optional extension listing, inspection, planning, installation, update,
  disablement, ownership-aware removal, and review
- optional user-owned workspace-mode listing, evidence-bound suggestion,
  inspection, per-task selection, definition, acceptance, update, disablement,
  deprecation, removal, and review
- blueprint-driven product change
- large-task orchestration for cross-boundary, multi-workstream, or resumable
  work
- optional team status, task start/claim/checkpoint/release, concurrent-work
  conflict review, handoff, decision, team review, and merge readiness
- logical integrity review
- durable engineering-evidence capture, lookup, explanation, or repair for
  material tasks and prior compact decision records, including binding-state
  finalization and explicit lineage-preserving rebinds
- Project Development Model guidance intake from reviewed engineering discovery
  or verified decision-owner directive, bounded automatic delivery, exception
  and coverage review, freshness review, contradiction resolution, and supersession
- optional Debug Mode activation, checkpoint, finalization, and comparison with
  versioned attribution and a required durable-evidence decision
- discussion diagram creation, comparison, or revision with a portable ASCII
  baseline
- AI infrastructure inventory for existing skills, prompts, wrappers, bridge
  files, rules, MCP/tool configs, gates, checkers, and prompts
- AI infrastructure recommendation for adding new items or improving,
  consolidating, replacing, retiring, or keeping existing items
- skill, prompt, wrapper, or third-party assistant infrastructure adaptation
- documentation, diagram, gate, or bridge synchronization
- adapter maturity review

The target adapter may define narrower or stricter operations.

## Request Contract

A post-install request should state:

- target repository path
- operation type
- goal and non-goals
- known changed facts or framework update source
- AI infrastructure source when the operation is adaptation or add, including
  local path, Git URL, HTTPS URL, assistant-native reference, pasted content,
  package/plugin reference, or unknown source type
- AI recommendation scope, selected project area, observed problem, or current
  item IDs when the operation is recommendation
- target source-of-truth docs to inspect
- validation commands or manual checks known to the target
- approval constraints
- current logical scope and the action phases explicitly authorized by the
  newest user request
- related review comments or defect reports
- approved Git diff base and explicitly selected machine-readable approval
  records when scoped approval applies
- allowed actions: `read-only`, `docs-only`, `adapter-only`,
  `code-and-tests`, or `full-with-approval`
- context profile when known
- task scale and existing operation packet when known
- team task, actor, coordination backend, and current evidence revision when
  team collaboration applies
- pre-change preview state when risk-gated preview applies
- diagram purpose, target assistant surface, persistence intent, and preferred
  presentation mode when diagram discussion applies
- architecture question, scope, non-goals, decision intent, and selected
  catalog items when architecture assistance applies
- requested term, acronym, alias, domain, or bounded terminology-check scope
  when project vocabulary applies
- test-first configuration mode, changed fact or defect, policy trigger,
  preferred mode, and exception context when test-first work applies
- extension lifecycle mode, source or extension ID, immutable revision when
  known, allowed actions, and source-access boundary when extension work applies
- workspace-mode action, explicit mode ID when known, workspace scope, artifact
  relationship, and user decision evidence when workspace modes apply
- expected final evidence
- output contract when the target adapter requires a durable installation,
  framework-update, or adapter-recheck evidence shape

## Allowed Actions

Allowed actions bound the surfaces an assistant may change for one installed
operation request:

- `read-only`: inspect target files and report only; no file changes.
- `docs-only`: change documentation, blueprint-equivalent docs, and diagram
  sources, including proposed code-documentation profiles and vocabulary term
  records, only; do not
  change source comments, code, tests, runtime config, or assistant
  infrastructure, and do not mark a profile or semantic term accepted.
- `adapter-only`: change adapter-owned `.ai/*` surfaces and bridge files,
  including assistant templates, flows, gates, policies, checker rules, and
  normalized project-process or adapter-effectiveness evidence; do not change
  product code, tests, or accepted business, domain, architecture, data,
  runtime, or product-behavior facts.
- `code-and-tests`: change code, tests, and required documentation or diagram
  sync, including source comments and target-recorded local generation under
  one accepted profile; do not install dependencies, change CI, publish
  externally, perform live or destructive actions, or broaden permissions.
- `full-with-approval`: the request may include protected surfaces, but each
  protected change still requires explicit programmer approval before it is
  made.

If the requested operation exceeds the allowed actions, the assistant should
stop before editing and ask for a narrower operation or explicit approval.

Allowed actions are a maximum surface, not authorization to use that surface.
Apply `ALATYR-AUTHORIZATION-001` separately for `inspect`, `modify`, `commit`,
`publish`, and `live-external`. The latest request must authorize each
state-changing phase in the current logical scope. `Fix` or `implement` may
authorize `modify`, but not commit or push. `Commit` does not authorize push.
A direct current request may authorize multiple named phases together.

A subject-only transition such as returning to an issue or backlog item,
switching discussion topics, asking for status, reviewing a report, requesting
analysis, or asking what comes next defaults to `inspect`. Prior phase
authorization expires after completion, redirection, material scope expansion,
pause, cancellation, or replacement. Ambiguous `continue` inherits phases only
for one clearly unfinished current scope; otherwise it remains read-only.

If a request says `Alatyr`, "ask Alatyr", or similar, interpret that as "ask an
assistant to use the installed Alatyr Core adapter in this repository." A bare
`Alatyr` request returns compact adapter state and up to three relevant
operations. `Alatyr status` and `Alatyr doctor` route to read-only adapter
health; status returns compact state and counts, while doctor may include
prioritized repair routes. Do not assume a runtime service, CLI, agent daemon,
or universal command exists.

Route a clear request automatically through the target operation catalog and
enabled module profile; do not require the user to provide an operation ID. If
the requested operation is materially unclear, show only the closest two or
three choices before changing files.

If the request uses an alias such as `alatyr-ai-inventory`, interpret it as an
AI infrastructure inventory request. If it uses `alatyr-adaptation <source>` or
`alatyr-add-ai <source>`, interpret it as the skill-adaptation operation with
`<source>` as untrusted input until the target adapter's provenance, network,
dependency, and approval rules have been checked.

If the request uses `alatyr-suggest-ai <scope>` or
`alatyr-improve-ai <item-id>`, interpret it as a read-only AI infrastructure
recommendation. Use project-contour facts as need and outcome evidence, but
keep recommendation records and item mechanics in the assistant contour.

If the request uses `Alatyr team status`, `Alatyr start`, `Alatyr claim`,
`Alatyr conflicts`, `Alatyr checkpoint`, `Alatyr handoff`, `Alatyr decision`,
`Alatyr discuss`, `Alatyr review`, `Alatyr merge check`, or `Alatyr release`,
route through the optional target team module. These remain assistant request
aliases, not shell commands.

If the request uses `Alatyr diagram`, `show as a diagram`, `visualize
architecture`, or an adapted target-language alias, route to
`diagram-discussion` when the diagrams module is available. Keep exploratory
discussion read-only unless the user asks to persist the source or visual
artifact and the allowed actions permit it.

If the request uses `Alatyr architecture`, `Alatyr architecture inventory`,
`explain architecture`, `discuss architecture pattern`, `compare architecture
options`, `review architecture`, `document architecture`, or an adapted
target-language alias, route to `architecture-assistance` when the project
architecture knowledge module is available. Start from the compact catalog
and infer inventory, explain, discuss, compare, review, or document mode.

## Required Flow

For installed operations:

1. Treat the target assistant entry point as preloaded, then read only
   `.ai/assistant/bootstrap-index.json` as compact bootstrap and
   `.ai/assistant/entry-packet.json` as the first-use routing packet. If their
   canonical source hashes differ, repair the stale derived file from the named
   manifest, project map, context router, gate index, support policy, action
   policy, operation index, and semantic-codebook index before routine
   operation routing. Use the embedded core semantic definitions by exact ID
   and version.
2. Read the installation note and post-install/update message templates when
   the request follows an installation, framework update, or unclear adapter
   state.
3. Select the smallest matching context profile and project-area overlays from
   the bootstrap projection and context router, then read their required
   framework, project, assistant, flow, routed gate fragments, policy, and
   validation context. Resolve them from the applicable contour root
   `context-index.json`, following only selected child entries and rejecting
   stale digests, cycles, duplicate paths, or depth violations. Resolve lazy
   semantic references through the installed codebook and use canonical prose
   fallback when resolution is not exact. Load the complete gate checklist and
   human rationale only for ambiguity or drift and record index chains, item
   IDs/digests, term IDs/versions, packet digest, and budget exceptions in the
   context receipt.
   When workspace modes are enabled, read the compact mode catalog before this
   selection, resolve at most one accepted mode, and load only that descriptor
   plus applicable shared root context. Ask the user when selection is
   ambiguous.
4. Resolve exact IDs and aliases through the checked compact operation index.
   Use bounded profile candidates and intent overlays for routine routing.
   Load the full catalog only for the bare `Alatyr` entry, ambiguity, or
   operation/adapter repair.
5. Normalize an explicit operation or alias, or match request intent against
   catalog signals and enabled module state. Route one clear match
   automatically; ask one bounded question when multiple plausible operations
   remain.
6. Classify the current logical scope and authorized phases from the newest
   user request. Treat issue/backlog returns, status, discussion, reports,
   analysis, planning, and ambiguous continuation as read-only. Do not reuse
   authorization from a completed or redirected operation.
7. Identify whether the request is framework-core, target-project, repository
   adapter, bridge, generated-artifact, or skill/prompt work.
8. Classify changed facts, risk, approval triggers, and allowed-action scope.
   Before edits, show a bounded pre-change preview when semantic or protected
   risk, boundary crossing, external effects, or unclear scope triggers it.
   Record why preview was skipped for routine read-only or local non-semantic
   work. A preview is not approval.
9. Before every state-changing phase, recheck the newest instruction,
   current-scope authorization, allowed actions, protected approval, and tool
   permissions. Stop before `modify`, `commit`, `publish`, or `live-external`
   when that phase is not explicit.
10. Apply logical integrity review before claiming consistency. Re-derive
   invariants and reconcile related review items over the combined repair set.
   When the optional consistency map is enabled, build a bounded impact closure
   from changed fact IDs before loading related surfaces.
11. Activate the large-task scale overlay only when work is cross-boundary,
   multi-workstream, budget-exceeding, or resumable. Use a target operation
   packet and bounded active-workstream context when activated.
12. When optional subagent delegation is enabled, identify the primary
    critical-path next action first. Activate delegated execution only for
    independently useful, locally verifiable packets with disjoint writes or
    read-only scope and current capability evidence. Keep project decisions,
    approval, integration, and final convergence with the primary assistant.
13. Activate the team-active overlay only for enabled team coordination.
    Compare active tasks by changed facts and owners before secondary file
    overlap; keep unrelated tasks and history outside context.
14. Use architecture assistance for architecture inventory, explanation,
    pattern discussion, alternative comparison, review, or supporting docs.
    Start from the compact catalog, keep observed and intended architecture
    distinct, and route accepted decisions separately.
15. Use blueprint-driven change when accepted project facts may change.
16. Evaluate the compact test-first recommendation gate for implementation,
    defect, invariant, contract, and risky-refactor work. Route configuration
    or enablement separately from execution; do not impose TDD from a disabled
    module or repeat a declined recommendation without new evidence.
17. Use extension management for explicit extension list, inspect, plan,
    install, update, disable, remove, or review requests. Keep source review
    read-only until immutable provenance, compatibility, bindings, permissions,
    approval, ownership, and validation are resolved.
18. Use AI infrastructure recommendation when the user asks what should be
   added or improved, or when bounded evidence shows a recurring capability
   gap. Use selected target development-pattern evidence, evaluate existing
   items before proposing a new one, and do not promote target observations
   directly into portable framework changes.
19. Use skill adaptation when prompts, skills, wrappers, or third-party
   assistant infrastructure change.
   Select the target AI infrastructure route and item IDs before loading item
   content, permissions, gates, validation, or import policy.
20. Use prompt-injection policy for imported, external, remote, pasted, package,
   plugin, or unknown AI infrastructure.
21. Use AI infrastructure inventory before adding, importing, replacing, or
   removing assistant infrastructure.
22. Use adapter maturity review when the request is broad, post-install, or
    post-upgrade.
23. Use workspace-mode flow for mode listing, suggestion, inspection,
    per-task selection, definition, acceptance, update, disablement,
    deprecation, or removal. Keep suggestions proposed until the user accepts
    them, show a compact mode preflight before changes, and reject any mode
    that grants permission or activates a nested adapter.
24. Use diagram discussion when the user asks to see or iteratively revise a
    visual model. Select presentation mode from the target diagram policy and
    current compact assistant-capability entry, keep drafts non-canonical,
    preserve stable ID/revision lineage, classify sensitive content and
    external rendering, and always retain a bounded portable ASCII view.
25. Record approval evidence when protected-change scope requires it. When
    scoped approval is used, enforce the complete changed path set against
    explicitly selected machine-readable records bound to the approved diff
    base.
26. Use the target adapter output contract when the operation follows
    installation, framework update, or adapter recheck.
27. Run target validation that exists, or record unresolved checks.
28. Report current user authorization, changed facts, re-derived invariants,
   files inspected, files changed, approval-scope enforcement, validation,
   skipped checks, and residual risk.

## Workspace Modes

Workspace modes are an optional project-contour capability for repositories
where application, framework, library, skeleton, dependency, or workspace
roles require different support context. Installation and framework-update
review may suggest zero or more evidence-bound modes, but installation approval
does not accept those suggestions. The user owns acceptance and lifecycle
decisions.

Each actual mode has its own target directory. Optional root support contains
only context shared across applicable modes. For each task, keep workspace
identity, artifact relationship, and selected mode separate; load the compact
catalog first and only one selected descriptor. If selection is ambiguous,
remain read-only and ask one bounded question. A mode selects and narrows
context. It never grants write scope, approval, permissions, tools, decision
authority, nested-adapter activation, or validation bypass.

## Blueprint Creation

Blueprint creation is a target-project operation. The assistant may draft or
repair blueprint-equivalent docs only from target evidence:

- README and public docs
- architecture, design, use-case, business-rule, data, and runtime-flow docs
- code structure and package/build files
- tests, fixtures, and CI
- diagrams and generated artifacts
- security, live-service, destructive-operation, and dependency policy
- existing prompts, skills, gates, bridge files, and checker rules

Missing facts must stay marked as missing. The assistant must not invent
business rules, architecture, security policy, validation commands, diagrams,
or lifecycle notes.

## Diagram Discussion

Diagram discussion is an optional target operation. It may explain current
facts, compare proposed alternatives, or revise a draft interactively. It must
use the target's diagram source and presentation policy and the current
assistant surface's recorded capabilities.

Read-only diagram discussion returns the presentation in chat without creating
files. A persisted source or generated visual requires `docs-only` or broader
allowed actions. A proposal that changes accepted project facts must hand off
to the applicable decision or product-change operation before those facts are
treated as accepted.

The result reports draft/source-of-truth status, source revision, presentation
mode, source or artifact path when present, assumptions, validation, and the
portable ASCII view. Native inline rendering and file attachment remain client
capabilities, not framework guarantees.

## Architecture Assistance

Architecture assistance is an optional target operation. It inventories,
explains, discusses, compares, reviews, or documents selected project
architecture items from a compact project-owned catalog and repository
evidence.

Read-only work may recommend reuse, adaptation, introduction, restriction, or
retirement of a pattern, but the recommendation remains proposed. Under
`docs-only`, supporting docs may record observed, proposed, contradicted, or
unknown items; they must not accept architecture. Accepted, preferred,
restricted, or deprecated status requires the target decision owner and
approval policy, then handoff to blueprint-driven change and logical integrity
review.

Architecture discussion should identify the problem and common drivers,
separate observed from intended architecture, and evaluate no-change, reuse,
adaptation, and new-pattern options before adding another approach. The result
reports selected evidence, catalog revision, states, alternatives, pattern-
proliferation result, documentation or change handoff, validation, and residual
risk.

## Code Documentation

Code documentation is an optional project-contour capability routed through
the existing documentation-sync operation. The assistant inventories or
proposes source-set profiles from target evidence, permits different frontend,
backend, shared-library, and infrastructure conventions, and uses only one
unambiguous accepted profile for routine comment or generation work.

Structured comments may explain bounded symbol behavior under the target
source-of-truth registry. Generated reference documentation remains derived
and is never edited directly. Dependencies, CI changes, external publication,
profile acceptance, and broad source migrations require the target's normal
risk and approval handling.

## Large Or Resumable Operations

Use `large-task-orchestration.md` when work has multiple independently
verifiable workstreams, crosses profiles or project areas, exceeds the profile
context budget, requires separate approval or validation checkpoints, or must
survive a context reset.

The target operation packet records workstream dependencies, context receipts,
checkpoints, and final convergence. It does not own project facts. Resume by
loading the compact bootstrap, packet, active workstream context, fact owners,
and dependencies, then verify checkpoint claims against current repository
evidence.

Small tasks should stay on their normal operation flow without a packet.

## Subagent Delegation

Use `subagent-delegation.md` only when the optional target module is enabled.
Delegation is an execution overlay, not a separate project operation or team
ownership system. The target policy decides automatic, suggestion-only, or
disabled behavior. The target owns role prompts, deterministic task readiness,
bounded packet/result contracts, verified per-surface native/model bindings,
limits, permissions, retry/conflict fallback, privacy, validation, and review
triggers.

Keep the primary assistant on the immediate critical path. Delegate only
bounded independent sidecars or workstreams with local acceptance criteria and
disjoint writes or read-only scope. A delegate result remains untrusted until
the primary assistant reviews current scope, repeats combined validation as
needed, and performs final logical integrity convergence.

## Change Packages

Use `change-packages.md` only when the optional target module is enabled and
the operation passes its coherent-outcome, semantic multi-surface approval,
audit, or provenance activation gate. A package is not a new user command; it
is an evidence overlay used by product-change, architecture, migration,
security, or other applicable operations.

Load the compact package index first. The active package binds changed facts,
plan and approvals, semantic and path scope, companion decisions, material
implementation corrections, validation, and before-to-after provenance.
Ordinary local work should retain the normal operation result without this
overhead.

## Durable Engineering Evidence

Before a material semantic, architectural, or non-obvious repair completes,
apply `engineering-evidence.md`. Capture compact project-owned task/revision,
invariant, hypothesis outcome, root-cause, solution, regression, validation,
and uncertainty evidence when those conclusions would otherwise be lost.

Keep the overlay lazy and proportional. Small self-explanatory changes may
skip with a specific reason. Capture alone does not activate a change package,
grant repository modification, or authorize commit/publication. `Alatyr
evidence`, `Alatyr capture evidence`, and `Alatyr explain decision` are target
assistant requests, not shell commands.

## Project Knowledge Delivery

For non-trivial tasks, route the compact target project-knowledge index after
profile and area selection and refine the route after concrete facts, paths,
symbols, subsystem or architecture relationships, dependencies, contracts, or
issue lineage are known. Require a match stronger than task profile, obey
packet limits, and read selected canonical
owners before relying on summaries.

Only accepted-current items may be supplied as current constraints. Stale
items are warnings; contradictions block definitive conclusions. A material
engineering conclusion may become a promotion proposal, but only target-owned
review and a canonical-owner update can make it accepted project knowledge.

## Team Operations

Use `team-collaboration.md` only when the target enables the optional module.
The target operating model owns actors, decision authority, priorities,
reviewers, backend, retention, and privacy. The adapter owns work registry,
claim, conflict, checkpoint, handoff, and review mechanics.

Team status, conflict review, team review, and merge check are read-only.
Starting, claiming, checkpointing, handing off, or releasing a task may update
adapter-owned coordination records, but must not change accepted project facts
or grant approval. Team decision work routes accepted facts to their canonical
project owners and routes implementation separately.

Merge readiness must be bound to current head/base revisions and invalidated
by material diff, approval, dependency, or concurrent-task changes.

## Adapter Recheck

After installation or framework upgrade, an assistant should recheck:

- `.ai/alatyr.yaml`, framework version, adapter schema version, template
  version, and target adapter references
- required core profile and optional module states
- context profiles and their framework/project/assistant references
- source-of-truth registry, task-specific maturity profile, bridge capability
  matrix, migration notes, and effectiveness reports
- consistency-map module state, relationship coverage, and stale edge evidence
- change-package module, index, record schema, semantic approval scope,
  provenance policy, and target validator support
- durable engineering-evidence owner, storage/publication policy, compact
  index, record schema, routing, existing records, and validator support
- project-knowledge owner, review/retention/redaction policy, promotion records,
  sharded route index, two-stage delivery, freshness/conflict/supersession
  evidence, packet limits, and validator support
- operation catalog, single entry, automatic routing, read-only health,
  pre-change preview, compact help, operation-routing flow, and
  post-install/update chat-message templates
- team module operating model, work registry schema, coordination backend,
  operation routes, stale claims, active overlaps, checkpoints, handoffs,
  decisions, reviews, and revision-bound merge readiness when enabled
- adapter output contracts for installation, framework update, and recheck
  evidence
- adapter drift hazards: hard-coded local machine paths, stale checker
  existence statements, duplicate context-profile or router references,
  missing context-router bootstrap references, unresolved owner placeholders,
  and target-local checker coverage
- root assistant entry points and supported bridge files point to the
  installation note, operation catalog, health, help, and routing flow
- source-of-truth and blueprint ownership
- logical integrity and blueprint-driven change flows
- gates, prompts, skills, bridge files, checker rules, and final evidence
- AI infrastructure inventory, recommendation, source access, provenance, and
  compatibility status
- prompt-injection policy and approval-record template
- dependency knowledge policy, catalog, exact package-instance lock,
  deviations, retention state, passive export routing, and stale or modified
  evidence when the optional module is enabled
- security, live-service, destructive-operation, and dependency boundaries
- diagram and generated-artifact policy
- diagram discussion flow, presentation template, per-assistant presentation
  capability, ASCII readability, and stale-view evidence when the diagrams
  module is enabled
- validation commands or manual checks
- adapter maturity gaps, local deviations, and lifecycle notes

If a framework update adds requirements, the assistant should identify whether
the target adapter needs migration, approval, new placeholders, or manual
follow-up.

## Effectiveness Review

When the programmer asks whether Alatyr is helping, use effectiveness metrics
to compare similar tasks across adapter states. Report context load,
clarification count, approvals, validation, missed companion updates, rework,
residual risks, and outcome. Do not claim improvement from one incomparable
task.

When the optional `debug-mode` module is enabled, route explicit activation,
status, checkpoint, finalization, disablement, and comparison through the
canonical `debug-mode` operation. Activation is task/session-local, authorizes
only target-approved debug evidence writes under `adapter-only`, and expires
at the logical-scope boundary. It never implies implementation, commit, push,
publication, live action, approval, or canonical project authority.

A completed record is immutable. Related later work requires a new explicit
activation and linked continuation record. Finalization verifies lifecycle-
bounded timestamps, typed supporting-event roles, complete materiality,
registry-backed preservation for skips, and exact versus partial validation
claims before synchronizing the compact index.

Use normalized event and outcome records rather than raw conversations. A
completed result reports evidence-based timing, capture quality, independent
executor findings, human interventions, derived-after-human consequences,
validation expansion, corrections, final result binding, and external
projection. Cross-task comparison must account for task class, capture quality,
observer effect, and independent result quality.

## Rejection Criteria

Reject or revise installed-operation work that:

- treats Alatyr Core as a universal executable command or service
- guesses an operation instead of showing bounded help when material ambiguity
  remains
- requires a formal operation ID for a clear routine request
- edits during adapter health or treats a pre-change preview as approval
- updates target blueprints from guesses instead of target evidence
- copies source-repository facts into target project docs
- overwrites existing target instructions without approval
- claims adapter recheck success without inspecting the installed target
  adapter
- claims validation without target commands or manual-review evidence
- hides missing project facts, approvals, or residual risk
- claims a visible diagram without providing a supported presentation mode or
  portable ASCII baseline
