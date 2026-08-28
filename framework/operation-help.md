---
alatyr_doc:
  id: framework.operation-help
  type: framework-rule-owner
  owns_rules:
    - ALATYR-OPERATION-001
  depends_on:
    - ALATYR-CONTEXT-001
    - ALATYR-RISK-001
    - ALATYR-APPROVAL-001
    - ALATYR-AUTHORIZATION-001
    - ALATYR-MODULE-001
  applies_to:
    - all
---
# AI Framework Operation Help

This file defines the portable help and routing pattern for installed Alatyr
Core adapters.

Operation help is not a CLI command, daemon, runtime service, or universal
agent. It is an assistant response pattern backed by target adapter files.
`Alatyr` is the single conversational entry point. When a programmer sends it
without a task, the assistant should report the adapter state and show no more
than three currently relevant actions. When the programmer includes a clear
task, the assistant should route it automatically. When the task cannot be
classified safely, the assistant must show a short set of likely operation
choices instead of guessing.

Concrete operation names, local validation, supported assistants, and final
evidence formats belong to the target repository adapter.

## Goals

Operation help exists to:

- make installed Alatyr usage discoverable after installation or update
- route unclear requests to the right target flow
- prevent assistants from treating vague requests as permission to edit files
- prevent authorization for edits, commits, publication, or live actions from
  leaking across logical task scopes
- distinguish assistant requests from nonexistent universal commands
- expose missing target adapter facts before work starts
- provide one stable entry point across supported assistant surfaces
- make routing deterministic enough to validate without forcing formal user
  syntax
- show a bounded pre-change preview when risk or scope warrants it
- route optional team status, task, conflict, handoff, decision, review, and
  merge-check requests without loading team state for unrelated work
- route diagram discussion to a portable ASCII baseline, with
  capability-checked richer presentation when available
- route architecture inventory, explanation, pattern discussion, comparison,
  review, and documentation through a compact project-owned catalog
- route project terminology lookup, acronym and alias resolution, proposal,
  review, and consistency checks through a compact vocabulary catalog
- route test-first policy assessment and explicit enablement separately from
  enabled RED/GREEN/refactor execution, and suggest assessment only from
  bounded risk evidence
- route extension list, inspection, planning, installation, update,
  disablement, removal, and review through one lifecycle operation while
  keeping source access, approval, and activation separate
- route user-owned workspace-mode listing, evidence-bound suggestion,
  inspection, selection, definition, acceptance, and lifecycle changes without
  confusing a mode with workspace identity, artifact ownership, or authority
- route durable engineering-evidence capture, lookup, explanation, and repair
  while keeping the materiality decision proportional and the evidence corpus
  outside routine context
- route project-knowledge candidate or registered decision-owner guidance
  intake, human promotion review, explicit exception handling, coverage-aware
  bounded lookup, freshness, contradiction, and supersession while keeping
  canonical owners authoritative and unrelated knowledge outside routine
  context
- route optional task-local Debug Mode activation, status, checkpoint,
  finalization, disablement, and comparison without treating observability as
  authority or carrying activation across logical scopes; finalization closes
  the durable Engineering Evidence decision and reports attribution-contract
  and repository-binding lineage
- route cheap support/product change-cost evidence so large support updates,
  product changes, and mixed patches can be measured before deeper semantic
  review

## Canonical Operation Catalog

An installed adapter should keep a machine-readable operation catalog as the
canonical owner of operation identifiers and routing metadata. The catalog
should record, for every operation:

- stable operation ID, title, and short purpose
- matching request signals and aliases
- required module and applicable context profiles
- matching flow and minimum inputs
- permitted allowed-action modes
- whether pre-change preview is never needed or risk-gated
- expected final evidence

The human help reference explains the catalog. Bridge files point to it. They
must not define competing operation lists. Module status determines whether a
catalogued operation is available; catalog presence alone does not enable a
deferred, blocked, disabled, or not-applicable module.

The operation catalog is routing metadata, not universal executable command
metadata. `Alatyr`, `Alatyr status`, `Alatyr doctor`, and other aliases remain
chat or assistant request shortcuts unless the target explicitly owns a local
command.

## Single Entry Point

For a bare `Alatyr` request:

1. Read only the compact target bootstrap and operation-routing metadata.
2. Report whether adapter health has fresh evidence or remains unchecked.
3. Show at most three available operations relevant to current evidence.
4. Ask only the smallest question needed, or wait for a task.
5. Do not modify files or imply that a health check ran when it did not.

For `Alatyr <task>` or an ordinary clear development request, normalize aliases
and select an operation automatically. The user does not need to know or state
the canonical operation ID.

## Automatic Operation Routing

Automatic routing should use this order:

1. Apply explicit operation IDs or unambiguous aliases.
2. Match request intent against catalog signals and enabled modules.
3. Select the smallest context profile and area overlays required by that
   operation.
4. Classify changed facts and approval triggers using the owning risk and
   approval rules.
5. Classify the newest request under the current-scope action-authorization
   policy. A subject switch, issue or backlog return, status, discussion,
   report, analysis, plan, or ambiguous continuation remains `inspect` only.
6. Proceed without a routing confirmation when one operation is clearly
   applicable, its allowed-action scope is sufficient, and the requested phase
   is explicitly authorized.
7. Present two or three candidates and ask one bounded question when multiple
   operations remain plausible or the permitted scope is unclear.
8. Route unsupported or disabled operations to help with the specific missing
   module or adapter fact.

The assistant should state the selected operation and reason briefly before
edits, but must not turn routine low-risk work into a form-filling exchange.
Operation routing selects the process; it does not grant approval or broaden
allowed actions. Allowed actions are a ceiling, not user authorization. Clear
implementation intent may authorize repository edits for the current scope,
but it does not authorize commit or publication. Commit does not authorize
push. A previous scope's phase authorization is never carried forward.

Source conformance may define provider-neutral static routing expectations for
common request shapes such as help, status, architecture discussion, product
change, backlog return, framework update, commit, and push. These fixtures
check protocol alignment with the operation catalog and authorization policy;
they do not prove that a client interpreted an actual conversation correctly.

## Adapter Health

`Alatyr status` and `Alatyr doctor` route to the same read-only adapter-health
operation. The operation should inspect available target evidence for:

- compact bootstrap and context-router agreement
- manifest, catalog, module, and version consistency
- unresolved placeholders, absolute local paths, and stale claims
- bridge routing coverage for supported assistants
- checker availability and the freshness of recorded validation evidence
- approval-scope support and other enabled-module requirements

Health must remain separate from adapter maturity. Health is a current
structural state: `ready`, `attention`, `blocked`, or `unverified`. Maturity is
task-specific capability. A health result must identify evidence time or commit
when known and return at most three prioritized repair operations. It must not
edit files, fetch sources, install dependencies, or silently repair findings.

Each actionable finding should include severity, stable finding code, owning
surface, evidence, proposed repair operation, approval need, and whether the
target explicitly permits automatic repair.

## Pre-Change Preview

A pre-change preview is a bounded decision artifact shown before edits when at
least one of these conditions applies:

- an accepted semantic, business, architecture, data, security, or public
  contract fact may change
- a protected category or explicit approval gate applies
- the work crosses contours, project areas, or multiple workstreams
- destructive, live external, permission, credential, or spend effects are
  possible
- the expected change surface or allowed-action scope remains uncertain

The preview names the operation, changed facts, canonical owners, affected
surfaces, risk classes, expected file or surface scope, allowed actions,
current user authorization, approval needs, validation, unresolved questions,
and the proceed/ask/blocked decision. It is not approval or phase
authorization and must never manufacture certainty about exact files before
discovery supports it.

Routine read-only work and local changes with no semantic or protected effect
may skip the preview. The assistant should record a short skip reason in its
routing evidence. Material scope or risk changes invalidate the preview and
require it to be refreshed before edits continue.

## Help Trigger

Show operation help when:

- the user asks for Alatyr help, commands, actions, or what Alatyr can do
- the requested operation type is missing or ambiguous
- multiple flows could apply and choosing wrong may change project facts
- required target context is missing before the assistant can classify risk
- the assistant cannot tell whether the request is framework, project,
  repository adapter, bridge, generated artifact, or skill/prompt work

Do not show the full operation reference merely because a clear low-risk task
did not use a formal operation name.

An issue, backlog, report, or discussion transition with no clear action must
route to read-only analysis even when an earlier completed task included
implementation, commit, or push authorization.

Showing help does not require approval because it does not change repository
facts.

## Operation Menu Shape

A target adapter help file should list each supported operation with:

- operation name
- short description
- when to use it
- matching target flow
- minimum input needed from the programmer
- related review items plus approved diff base and explicit machine-readable
  approval records when scoped approval applies
- allowed-action modes and context profile when useful
- approval triggers or safety notes
- expected final evidence

The default help response should use progressive disclosure: a status line,
two or three relevant operations, and the smallest next question. Load or show
the full help reference only when requested or when bounded choices do not
resolve ambiguity.

Typical operation categories include:

- help or operation routing
- project blueprint creation or repair
- adapter recheck after installation
- adapter recheck after framework update
- framework upgrade impact review
- target source-of-truth drift review
- project architecture inventory, explanation, pattern discussion,
  alternative comparison, review, and supporting-documentation maintenance
- blueprint-driven product change
- large-task orchestration for cross-boundary, multi-workstream, or resumable
  work
- team coordination for status, start/claim/checkpoint/release, changed-fact
  conflicts, handoffs, decisions, review, and revision-bound merge readiness
- logical integrity review
- durable engineering-evidence capture or lookup
- project-knowledge candidate or registered decision-owner guidance intake,
  review, lookup, exception, revalidation, or supersession
- optional Alatyr Debug Mode activation, status, checkpoint, finalization,
  disablement, or evidence-based comparison
- discussion diagram creation, comparison, or revision with inline, artifact,
  plus a portable ASCII view
- AI infrastructure inventory
- AI infrastructure recommendation for new items or improvements to existing
  items
- skill, prompt, wrapper, or third-party assistant infrastructure adaptation
- documentation, diagram, gate, or bridge synchronization
- support/product change-cost review, contract-artifact review, and visual
  validation evidence when applicable to the selected operation
- source-set code-comment style proposal, structured-comment maintenance, and
  generated-reference documentation when the optional module is enabled
- project term lookup, acronym and alias resolution, vocabulary proposal and
  review, and terminology checks when the optional module is enabled
- adapter maturity review
- optional workspace-mode status, suggestion, inspection, per-task selection,
  definition, acceptance, update, disablement, deprecation, and removal

The target adapter may narrow, rename, or add operations when it records the
local meaning and matching flow.

When a target uses a module profile, operation help should list only operations
whose required module is enabled or required. Deferred, disabled,
not-applicable, or blocked modules should appear as gaps or unavailable
options, not as ready actions.

Target adapters may also define operation type aliases. These aliases can map
natural-language requests such as "Alatyr help", "update Alatyr", "check
integrity", or target-language equivalents to canonical operation names.
Aliases must be documented as assistant request syntax, not portable
executable commands.

For an enabled diagrams module, aliases may include `Alatyr diagram`, `show as
a diagram`, `visualize architecture`, or target-language equivalents. These
route to `diagram-discussion`, not directly to documentation sync. The
assistant must use the current surface's compact recorded presentation
capability and must not claim native rendering when it used an artifact link
or ASCII only. Exact aliases should resolve through the checked compact
operation index rather than loading the full catalog.

For an enabled architecture-knowledge module, aliases may include `Alatyr
architecture`, `Alatyr architecture inventory`, `explain architecture`,
`discuss architecture pattern`, `compare architecture options`, `review
architecture`, or `document architecture`. Route all of them to one
architecture-assistance operation, infer the mode from a clear request, and
start from the compact project catalog. Discussion remains read-only unless
documentation or accepted-decision intent and allowed actions are explicit.

For an enabled code-documentation module, aliases may include `document code`,
`propose comment style`, `generate code docs`, or
`review code documentation`. Route them to `documentation-sync` with the
code-documentation intent overlay, then select one bounded accepted source-set
profile. A missing or ambiguous accepted profile routes to read-only proposal
or repair instead of mass source edits. The operation must not edit generated
output directly or present generator success as semantic proof.

For an enabled project-vocabulary module, aliases may include `Alatyr
glossary`, `Alatyr define term`, `propose glossary entry`, `check terminology`,
or `review project vocabulary`. Route them to `project-vocabulary` through the
vocabulary intent overlay. Start from the compact term, alias, and acronym
catalog; load only selected records and canonical owners. Preserve term state,
ask for bounded domain clarification on ambiguous accepted meanings, and do
not normalize project surfaces from unaccepted records.

For test-first development, aliases may include `Alatyr enable test-first`,
`Alatyr review test-first`, `Alatyr test first`, or `Alatyr TDD`. Configuration
routes through `test-first-configuration`, which remains available while the
optional module is disabled. Execution routes through `test-first-change` only
when the module and target policy are enabled. An automatic recommendation
must name the trigger, mode, likely level, cost, and next action, appear at most
once per task, and remain non-blocking unless an accepted target trigger is
required.

For extensions, aliases may include `Alatyr extensions`, `Alatyr inspect
extension <source>`, `Alatyr add extension <source>`, `Alatyr update extension
<id>`, `Alatyr disable extension <id>`, `Alatyr remove extension <id>`, and
`Alatyr review extension <id>`. These are request shortcuts, not shell
commands. List and inspection default to read-only. Installation and updates
require reviewed immutable source plus target approval; removal follows lock
ownership and stops for local modifications or active dependents.

`Alatyr suggest extensions <scope>` routes to the existing read-only AI
infrastructure recommendation operation. It does not search remote registries,
fetch source, or approve installation unless target source-access policy and a
separate lifecycle request permit those actions.

For an enabled dependency-knowledge module, aliases may include `Alatyr
dependencies`, `Alatyr dependency status`, `Alatyr sync dependencies`,
`Alatyr inspect dependency <package>`, `Alatyr explain dependency <package>`,
and `Alatyr dependency impact <package-or-change>`. Route them to one
dependency-knowledge operation and infer status, discover, inspect, plan, sync,
explain, or impact mode. These requests do not run package managers, update
dependencies, activate nested adapters, or trust raw package text. Projection
sync stays adapter-only; protected or project behavior changes use their normal
operation and approval route.

For an enabled workspace-modes module, aliases may include `Alatyr modes`,
`Alatyr mode status`, `Alatyr suggest modes`, `Alatyr mode <id>`, `Alatyr
define mode`, and `Alatyr accept mode <id>`. Route them to one `workspace-mode`
operation and infer list, status, suggest, inspect, select, define, accept,
update, disable, deprecate, or remove mode. These are chat/request shortcuts,
not shell commands. Listing, status, suggestion, inspection, and selection
preview default to read-only. Suggestions remain proposed until the user
accepts them. Selection must show the workspace, active adapter, relationships,
ownership, selected context, and ordinary task profile before state-changing
work. A mode may narrow actions but cannot grant approval, write scope,
permissions, tools, decision authority, nested-adapter activation, or gate
bypass.

For AI infrastructure, aliases may include `alatyr-ai-inventory`, which routes
to an inventory flow, or `alatyr-adaptation <source>` and
`alatyr-add-ai <source>`, which route to adaptation. The `<source>` may be a
local path, Git URL, HTTPS URL, assistant-native skill or prompt reference,
pasted content, package/plugin reference, or other adapter-defined source.
Target help should state near these aliases that they are chat/request
shortcuts, not shell commands.

Targets may also expose `alatyr-suggest-ai <scope>` for bounded new-item and
existing-item recommendations and `alatyr-improve-ai <item-id>` for a focused
existing-item review. Both route to read-only recommendation before any
adaptation, import, removal, or permission change.

When the optional team module is enabled, target help may expose `Alatyr team
status`, `Alatyr start`, `Alatyr claim`, `Alatyr conflicts`, `Alatyr
checkpoint`, `Alatyr handoff`, `Alatyr decision`, `Alatyr discuss`, `Alatyr
review`, `Alatyr merge check`, and `Alatyr release`. These are request aliases,
not portable commands. Read-only status, conflict, review, and merge-check
operations must not mutate team records. Record-changing team operations stay
bounded to adapter coordination surfaces unless a separate project-change
operation is selected.

When the target provides an AI infrastructure router, help should route the
request to `inventory`, `recommend`, `use-existing`, `adapt-import`,
`gate-checker-change`, `tool-mcp-change`, or `bridge-wrapper-change`, then name
the selected or proposed item ID. Help must not load or activate every item.

## Routing Rules

When routing a request:

1. Treat the target assistant entry point as preloaded, read the compact
   manifest/router bootstrap, and select the smallest profile and area overlays.
2. Resolve exact IDs and aliases through the checked compact operation index.
   Read the full catalog only for bare Alatyr, ambiguity, or repair.
3. Read the full target help reference only when human explanation is needed.
4. Classify the request by contour, task profile, and changed fact.
5. Normalize documented operation aliases before selecting a flow.
6. Choose the matching flow only when the operation is clear enough to proceed
   safely.
7. If the operation is unclear, show the operation menu with short
   descriptions and ask for the smallest missing decision.
8. If the user asks for commands, explain that Alatyr is used through assistant
   requests over Markdown adapter files unless the target adapter defines local
   commands.
9. If the request asks what already exists, route to AI infrastructure
   inventory and do not import anything during inventory-only work.
10. If the request supplies an external source, check target provenance,
   network, dependency, prompt-injection, and approval rules before fetching or
   importing it.
11. Do not edit repository files while only presenting help or resolving
   operation ambiguity.
12. Apply the pre-change preview trigger before a selected operation edits
    files.
13. Add a large-task scale overlay only when the work is cross-boundary,
    multi-workstream, budget-exceeding, or resumable. Keep small tasks on their
    normal flow without an operation packet.
14. When subagent delegation is enabled, identify the primary critical-path
    action first. Add delegated execution only for independently useful,
    locally verifiable packets with disjoint writes or read-only scope and
    current capability evidence. Use the target orchestration prompt, role
    catalog, execution plan, packet, and normalized result. Honor an explicit
    `forbid` preference.
15. In an enabled team project, read the compact active-work index before a
    state-changing operation. Add the team-active overlay for explicit team
    coordination, a task/branch match, possible logical overlap, or unresolved
    index evidence. Load the selected task and relevant overlaps, not all team
    history. Route `set actor`, `who am I`, and `clear actor` through ignored
    local identity without treating selection as authentication.
16. For diagram discussion, load the diagram policy and current compact
    assistant-capability entry, then choose native inline, rendered artifact,
    plus a portable ASCII view without loading the full bridge matrix.

## Evidence Format

Operation routing should be reportable as:

```text
Requested action: <user request>
Matched operation: <operation or unresolved>
Matching flow: <target flow or missing adapter fact>
Reason: <why this operation was selected>
Routing mode: <explicit, automatic, or ambiguity resolution>
Context profile: <profile plus area and scale overlays>
Pre-change preview: <shown, refreshed, or skipped with reason>
Presentation mode: <ascii, native-inline, rendered-artifact, or not applicable>
Missing input: <facts needed before work can proceed>
Next safe action: <help shown, question asked, or flow started>
```

The target adapter may require a stricter format.

## Rejection Criteria

Reject or revise operation routing that:

- invents a universal `alatyr` command
- starts edits from an ambiguous request without selecting a flow
- hides missing target context behind a confident operation choice
- treats bridge files or generated files as the source of operation truth
- omits approval needs for protected operations
- lists operations that the target adapter cannot support or explain
- claims adapter health without fresh evidence
- treats a preview as approval or continues after its scope becomes stale
- requires a formal operation name for an otherwise clear low-risk request
- claims a diagram was rendered without current assistant capability evidence
