# AI Framework Context Discovery

This file defines how an assistant should discover project context before
changing code, docs, tests, diagrams, or AI instructions.

Context discovery is portable. Concrete file paths, commands, and source of
truth documents are supplied by the project adapter.

## Goal

The assistant should understand enough of the target repository to avoid
inventing behavior, duplicating policy, or editing the wrong contour.

## Discovery Order

Before acting, inspect the target adapter for:

- canonical assistant entry points
- framework, project, and repository adapter contours
- project README and public docs
- source-of-truth blueprint or equivalent project docs, architecture,
  use-case, business-rule, data, and runtime-flow documents
- package/build files that reveal language, framework, dependency manager, and
  commands
- existing tests, fixtures, fakes, and CI jobs
- source-of-truth relationship map when the target provides one
- generated files, diagram sources, and generated visual artifacts
- security, live-service, credential, and destructive-operation policies
- skill, prompt, third-party assistant infrastructure, provenance, and wrapper
  policies
- existing assistant bridge files, prompts, skills, flows, gates,
  installed-operation requests, operation catalog, help, routing flows,
  adapter health/recheck
  reports, AI infrastructure inventory reports, chat-completion message
  templates, and checker manifests

Use the smallest context set that can answer the task, then expand only when
changed facts cross module, data, runtime, security, or assistant-governance
boundaries.

## Source Of Truth Decision

For each important fact, identify its owner:

- framework rule: portable AI process rule under `.ai/framework`
- project fact: product, code, data, business, runtime, or operation fact under
  the project contour
- repository adapter fact: local AI workflow, validation, bridge, prompt, gate,
  skill, checker, or command fact
- installed-operation fact: adapter-owned request, blueprint-creation,
  adapter-recheck, framework-update review, or drift-review fact
- operation-help fact: adapter-owned operation catalog, help menu, automatic
  routing, read-only health, pre-change preview, local
  command alias, or post-install/update chat-message fact
- skill or prompt fact: adapter-owned assistant infrastructure that may need
  provenance, wrapper, permission, and evidence review
- AI infrastructure inventory fact: adapter-owned record of existing skills,
  prompts, wrappers, bridge files, rules, MCP/tool configs, gates, checkers,
  and generated assistant artifacts
- bridge fact: short assistant-specific pointer to canonical files
- generated artifact: visual or built output whose source is elsewhere

When the target adapter provides a source-of-truth registry, use it before
choosing ownership. The registry should map fact types to canonical owners,
derived surfaces, synchronization direction, validation, and conflict
resolvers.

When the target also provides a consistency map, start from changed fact IDs
and load only applicable relationship targets. Expand transitively for
dependent contracts, cross-area effects, conflicts, failed validation, or
approval boundaries. Record skipped edges instead of scanning all surfaces.

When two sources disagree, do not choose by convenience. Use logical integrity
review to name the conflict, choose the source of truth, and repair the
smallest coherent set of files.

## Missing Context

If required context is missing:

- state which adapter fact is missing
- avoid inventing commands, APIs, business rules, security policy, diagrams, or
  test structure
- avoid importing or adapting skills, prompts, wrappers, or third-party
  assistant infrastructure without source and target-adapter context
- continue only with a clearly bounded assumption when the task can remain safe
- stop for programmer input when the missing fact affects architecture,
  business behavior, spend, live external calls, security, destructive changes,
  or validation claims

## Context Budget

For large projects:

- start from the task goal, non-goal, changed files, and relevant contour
- prefer context packs, module ownership maps, data dictionaries, glossaries,
  and ADR indexes when the adapter provides them
- read full canonical policy files before acting on them
- avoid loading unrelated modules just because they exist
- document any context intentionally not inspected when it leaves residual risk
- treat host-loaded entry instructions as preloaded instead of rereading them
- use the machine router before loading human profile explanations
- compose a task profile with only affected project-area overlays
- prefer changed-fact relationship traversal over broad repository search when
  an adapted consistency map exists
- record loaded paths, expansion reasons, approximate volume, and omissions in
  a context receipt for large or cross-boundary work

## Rejection Criteria

Reject assistant work that:

- edits before reading the mandatory adapter context
- treats generated files as source of truth without checking their sources
- assumes local commands or tools exist in another project
- hides missing context behind confident language
- changes project facts from framework files
- changes framework guarantees from project-specific needs without updating
  framework docs and adapter sync targets
