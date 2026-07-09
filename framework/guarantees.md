# AI Framework Guarantees

The framework guarantees a normal AI work process only when the project adapter
is present and current.

## Guarantees

The framework guarantees that an assistant has a defined process for:

- finding mandatory project context before editing
- separating portable framework rules, project facts, and repository adapter
  rules
- discovering missing context and choosing source-of-truth owners before
  repairing drift
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
- adapting skills, prompts, wrappers, and third-party assistant infrastructure
  without letting them bypass framework or target adapter rules
- suggesting framework or documentation improvements when the process becomes
  hard to manage
- assessing whether a project adapter is incomplete, minimal, usable, or
  mature enough for the requested task
- recording framework lifecycle, upgrade, deprecation, and migration facts in
  an adapter-owned format

## Required Project Adapter

The framework can only provide those guarantees when the project adapter
defines:

- project source-of-truth files
- project contours
- blueprint-equivalent source-of-truth docs and product-change workflow owners
- project-specific flows, prompts, gates, and skills
- project validation commands or manual validation checks
- project-specific test levels, tools, commands, fixtures, and isolation rules
- project-specific context map and source-of-truth documents
- project-specific risk/approval rules that extend the framework risk model
- project-specific security, live-service, dependency, destructive-operation,
  privacy, and credential-handling policies
- project-specific diagram source format, visual artifact format, render or
  manual-review policy, and drift checks when diagrams exist
- project-specific framework baseline, local deviations, maturity gaps, and
  upgrade notes
- supported assistant bridge files
- skill provenance, adaptation, wrapper, and approval rules when skills or
  third-party assistant infrastructure are used
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
- that a project adapter is mature enough for broad work unless its local
  facts support that claim

## Failure Rule

If the framework cannot find current project facts, adapter gates, or approval
evidence, the assistant must stop or report the missing adapter piece instead
of inventing behavior or claiming validation passed.
