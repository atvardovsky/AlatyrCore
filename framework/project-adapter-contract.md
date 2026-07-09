# Alatyr Core Project Adapter Contract

A project adapter binds the portable AI framework to one concrete repository.

The adapter is what lets the framework guarantee useful AI behavior on a real
project. Without an adapter, the framework only describes process concepts.

## Adapter Must Provide

Every project using this framework must define:

- project contour: what product facts the project owns
- framework contour: what reusable AI operating rules are being adopted
- repository adapter contour: what local assistant operating rules and
  validation own
- canonical project blueprint or equivalent source-of-truth docs
- blueprint-driven change or equivalent product-change workflow owners
- use-case, business-rule, data-model, architecture, and runtime-flow sources
  when those concerns exist in the project
- context discovery map: canonical entry points, source-of-truth owners,
  generated artifacts, and missing-context escalation rules
- change-risk and approval model adapted from the framework risk classes
- concrete test strategy: test levels, folder conventions, fixtures, fakes,
  isolation rules, commands, CI jobs, and high-risk change coverage
- security and safety policy: secrets, live-service boundaries, destructive
  operations, privacy/compliance constraints, dependency approval, and
  credential/log-redaction rules
- local validation plan: commands, CI checks, manual reviews, or unresolved
  checks
- documentation-sync rules for project facts
- diagram and generated-file policy when diagrams or generated docs exist,
  including source format, visual format, ownership, render/manual-review
  process, and drift checks
- supported assistant bridge files
- project-specific skills or prompt wrappers when recurring work needs them
- AI infrastructure inventory, source access, provenance, adaptation,
  output-format, safety, and wrapper rules when skills or third-party assistant
  infrastructure are used
- adapter maturity gaps, framework baseline/deviations, and lifecycle or
  upgrade notes
- installed-operation request, blueprint-creation, adapter-recheck, and
  framework-update review flows when the repository wants post-install
  operations
- operation help, operation-routing, and post-install/update chat-message
  templates when the repository wants discoverable assistant requests
- final evidence format for that project

## Adapter May Provide

An adapter may provide:

- deterministic checker scripts
- security/dependency/license scanners or manual review checklists
- project-specific test-generation prompts or skills
- skill import or normalization notes
- AI infrastructure source access allowlists, approval notes, or manual review
  checklists
- AI infrastructure inventories, compatibility reports, and add/adapt/remove
  recommendations
- installed-operation request templates or adapter audit reports
- operation help menus, routing flows, or assistant chat-completion message
  templates
- generated visual artifacts
- local pre-commit hooks
- assistant-specific skill wrappers
- project-specific rejection criteria
- public docs that mirror AI-facing docs

These are adapter details. They are not portable framework core.

## Adapter Must Not

The adapter must not:

- redefine framework portability rules as project facts
- copy another project's business logic, commands, or diagrams as if they were
  framework requirements
- copy another project's test tools, folder structure, fixtures, or CI jobs as
  framework requirements
- copy another project's security policy, live-service boundaries,
  dependency-review tools, diagram tooling, or lifecycle format as framework
  requirements
- import third-party assistant infrastructure into canonical files without
  provenance, target adaptation, and required approval
- hide architecture changes inside repository-adapter edits
- weaken approval or validation requirements without explicit programmer
  confirmation
- let bridge files become divergent sources of truth
- advertise operations, commands, or chat messages that the target adapter does
  not define or cannot validate

## Typical Target Adapter

In a target repository, the adapter usually includes:

- `AGENTS.md` and `AI_ASSISTANTS.md`
- `.ai/assistant`
- optional `.agents/skills`
- optional assistant-native wrappers such as `.claude`, `.cursor`, or
  `.github/prompts`
- assistant bridge files for supported tools
- local consistency checks, validation commands, or manual-review rules owned
  by that repository

Those files apply Alatyr Core to one project. They are not portable framework
core and must be rewritten from target repository facts.
