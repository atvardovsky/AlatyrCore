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
- mapping changed facts to affected docs, diagrams, tests, gates, prompts, and
  skills
- carrying accepted product changes through blueprint-equivalent docs, flows,
  implementation, validation, diagrams, and final evidence
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
- using an installed adapter for post-install blueprint creation, drift review,
  framework update recheck, and adapter maturity review
- separating required core from optional modules so targets do not carry
  unused Alatyr surfaces as mandatory process
- bounding installed-operation requests by allowed actions before editing files
- showing operation help and routing ambiguous requests before guessing or
  editing files
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
- manifest, approval, prompt-injection, help, and policy templates contain
  required fields

Machine checks do not prove the assistant understood the target project or
that project facts are correct.

Machine-readable validator output can make adapter evidence cheaper to reuse in
CI, assistant rechecks, or final reports, but it remains structural evidence.
It does not decide source-of-truth correctness or replace logical integrity
review.

## Target-Dependent Guarantees

An installed adapter can provide stronger guarantees only when the target
defines:

- source-of-truth registry entries for relevant fact types
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
- AI infrastructure inventory, source access, provenance, adaptation, wrapper,
  and approval rules when skills or third-party assistant infrastructure are
  used
- installed-operation request, blueprint-creation, adapter-recheck, and
  framework-update review flows when the target wants post-install operations
- allowed-action meanings for installed-operation requests
- adapter output contract templates for installation, framework update, and
  recheck evidence when durable operation records are expected
- operation help, operation-routing, and post-install/update chat-message
  templates when the target wants discoverable assistant requests
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
