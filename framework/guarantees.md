---
alatyr_doc:
  id: framework.guarantees
  type: framework-rule-owner
  owns_rules:
    - ALATYR-EVIDENCE-001
  depends_on: []
  applies_to:
    - all
---
# AI Framework Guarantees And Limits

The framework defines process commitments. Markdown instructions alone cannot
technically force an assistant to read every file, understand every rule, or
perform a flawless logical integrity review.

Use this document to distinguish declarative process commitments,
machine-checkable expectations, target-dependent guarantees, and
non-guarantees.

## Declarative Process Commitments

The framework commits to giving an assistant a defined process for:

- finding task-specific project context before editing
- separating portable framework rules, project facts, and repository adapter
  rules
- discovering missing context and choosing source-of-truth owners or registry
  entries before repairing drift
- classifying changed facts by risk before choosing approval, test,
  documentation, diagram, and evidence scope
- applying portable security and safety reasoning before secrets, live
  services, dependencies, destructive operations, or permissions are changed
- detecting whether a semantic or logical fact changed
- performing logical integrity review before claiming consistency
- re-deriving testable invariants and reconciling related review items before
  accepting a combined repair set
- mapping changed facts to affected docs, diagrams, tests, gates, prompts, and
  skills
- traversing adapted fact relationships to bound multi-level impact review in
  large repositories
- carrying accepted product changes through blueprint-equivalent docs, flows,
  implementation, validation, diagrams, and final evidence
- coordinating large or resumable changes through bounded workstreams,
  context receipts, checkpoints, and final convergence evidence
- analyzing the target stack and risk profile before recommending test levels
  or structure
- reasoning about diagram source/visual synchronization without hard-coding a
  universal diagram tool
- requiring explicit programmer approval for protected changes
- keeping architecture discussion separate from architecture mutation
- keeping documentation and diagrams synchronized with code and project facts
- recording what was checked, what changed, what was skipped, and what risk
  remains
- adapting the same process across supported assistants through thin bridge
  files and wrappers
- recording bridge capability differences when supported assistant behavior can
  diverge
- adapting skills, prompts, wrappers, and third-party assistant infrastructure
  without letting them bypass framework or target adapter rules
- inventorying existing AI infrastructure before adding, replacing, or
  importing new assistant infrastructure
- recommending new AI infrastructure or changes to existing items only from
  bounded project-contour, quality, cost, overlap, and validation evidence
- retaining recurring target development friction in a compact, privacy-
  bounded project evidence index without promoting it directly into framework
  policy
- selecting target AI infrastructure by stable item ID and loading only its
  canonical source, permissions, gates, validation, and output contract
- using an installed adapter for post-install blueprint creation, drift review,
  framework update recheck, and adapter maturity review
- separating required core from optional modules so targets do not carry
  unused Alatyr surfaces as mandatory process
- bounding installed-operation requests by allowed actions before editing files
- routing clear requests automatically through a target operation catalog,
  showing bounded help before guessing on ambiguity, keeping adapter health
  read-only, and previewing risk-gated changes before edits
- suggesting framework or documentation improvements when the process becomes
  hard to manage
- assessing whether a project adapter is incomplete, minimal, usable, or mature
  enough for the requested task area
- recording framework lifecycle, upgrade, deprecation, and migration facts in
  an adapter-owned format

## Machine-Checkable Expectations

Machine checks can verify only deterministic repository facts, such as:

- required source files and template files exist
- indexes reference required framework files
- templates remain placeholder-based before installation
- bridge files stay short and point to canonical target files
- target profiles route every framework document somewhere
- target context routers match the profile template and route known framework
  documents somewhere
- static bootstrap/profile file and word costs remain within declared template
  budgets
- supported bridge templates expose the same compact bootstrap, operation
  catalog, single entry, health, help, and operation-routing entry points
- manifest, operation catalog, approval, prompt-injection, help, and policy
  templates contain required fields
- explicitly selected machine-readable approvals can be checked so the
  complete Git changed-path set is allowed, not excluded, and bound to the
  selected diff base

Machine checks do not prove the assistant understood the target project or
that project facts are correct. Prepared prompts and static bridge checks also
do not prove a vendor actually auto-loaded instructions or stayed within a
runtime context budget.

Machine-readable validator output can make adapter evidence cheaper to reuse in
CI, assistant rechecks, or final reports, but it remains structural evidence.
It does not decide source-of-truth correctness or replace logical integrity
review.

Classify evidence before making a claim:

- `current-state` records what can be observed in the repository now
- `historical-record` records a dated operation, approval, validation run, or
  migration event with its source and repository revision when available
- `mixed` combines current-state observations with named historical records

The presence of a file in the current tree does not prove who created it,
which installer or assistant action ran, whether approval preceded the change,
or whether historical validation passed. Mark those claims unverifiable unless
dated records provide the evidence.

## Target-Dependent Guarantees

An installed adapter can provide stronger guarantees only when the target
defines:

- source-of-truth registry entries for relevant fact types
- consistency-map nodes and relationship coverage when the target uses bounded
  impact traversal
- task context profiles
- context router or equivalent machine-readable profile map when cheaper
  startup is expected
- module profile for required core and optional capabilities
- project validation or explicit manual review
- approval rules and approval records when durable evidence is needed
- adapter output contracts for installation, framework update, and recheck
  evidence when the target wants durable operation records
- bridge capability matrix for supported assistants
- task-specific maturity and blocking criteria
- migration notes for framework upgrades
- prompt-injection and source-access policies for imported AI infrastructure

## Required Project Adapter

The framework can only provide useful process commitments when the project adapter
defines:

- project source-of-truth files
- project contours
- blueprint-equivalent source-of-truth docs and product-change workflow owners
- project-specific flows, prompts, gates, and skills
- project validation commands or manual validation checks
- project-specific test levels, tools, commands, fixtures, and isolation rules
- project-specific context map and source-of-truth documents
- project-specific context router or equivalent profile map when the adapter
  uses one for startup routing
- source-of-truth registry or equivalent owner map when multiple project
  surfaces can claim ownership
- project-specific risk/approval rules that extend the framework risk model
- project-specific security, live-service, dependency, destructive-operation,
  privacy, and credential-handling policies
- project-specific diagram source format, visual artifact format, render or
  manual-review policy, and drift checks when diagrams exist
- project-specific framework baseline, local deviations, maturity gaps, and
  upgrade notes
- supported assistant bridge files and bridge capability matrix when multiple
  assistant surfaces are supported
- AI infrastructure inventory, recommendation, source access, provenance,
  adaptation, wrapper, and approval rules when skills or third-party assistant
  infrastructure are used
- target development-evidence owner, retention/privacy policy, and lazy capture
  flow when recommendations should learn across project tasks
- AI infrastructure router and adaptation-record policy when multiple skills,
  prompts, gates, checkers, tools, MCP configs, bridges, or wrappers are used
- installed-operation request, blueprint-creation, adapter-recheck, and
  framework-update review flows when the target wants post-install operations
- allowed-action meanings for installed-operation requests
- adapter output contract templates for installation, framework update, and
  recheck evidence when durable operation records are expected
- operation packet, storage policy, workstream boundaries, and checkpoint
  evidence when large or resumable operations are expected
- operation catalog, single entry, automatic routing, read-only health,
  risk-gated preview, help, and post-install/update chat-message templates when
  the target wants discoverable assistant requests
- task-specific maturity profile and blocking criteria
- module profile for required core gaps and optional module states
- migration-note template or equivalent upgrade evidence when framework
  updates are expected
- consistency checks that are deterministic for the project
- final evidence expected for that project

## Does Not Guarantee

The framework does not guarantee:

- correctness of project facts that are missing, stale, or contradictory
- that an assistant can infer business policy without programmer input
- that local commands exist in another project
- that generated files can be produced without the target repository tooling
- that architecture changes are safe without explicit approval and validation
- that unsupported assistants will auto-load the right files without a bridge
  or user instruction
- that missing security, live-service, or diagram policy can be inferred from
  another project
- that imported skills or third-party assistant infrastructure are safe,
  current, or compatible without target adapter review
- that "ask Alatyr" implies a runtime service, CLI, daemon, or universal
  command instead of an assistant using installed Markdown instructions
- that help wording or operation menus are current when the target adapter does
  not maintain them
- that a project adapter is mature enough for broad work unless its local
  facts support that claim

## Failure Rule

If the framework cannot find current project facts, adapter gates, or approval
evidence, the assistant must stop or report the missing adapter piece instead
of inventing behavior or claiming validation passed.
