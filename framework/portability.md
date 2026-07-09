# Alatyr Core Portability Boundary

This file defines which AI-governance facts are portable framework core and
which facts are repository adapter details.

## Portable Framework Core

Portable framework core may describe reusable assistant operating patterns:

- framework, project, and repository adapter contour separation
- context discovery, source-of-truth decision, and missing-context handling
- architecture discussion and approval workflow shape
- documentation-sync workflow shape
- semantic/logical consistency review workflow shape
- change-risk classes and protected approval trigger categories
- security/safety reasoning categories for secrets, live services,
  destructive operations, permissions, dependencies, and privacy
- stack-aware testing analysis concepts
- gate and final-evidence categories
- prompt, skill, and bridge-file wrapper patterns
- diagram-as-code and visual-artifact synchronization concepts
- consistency-manifest concept
- framework core versus target project adapter installation planning
- adapter maturity levels and framework lifecycle/upgrade concepts

Portable framework core must stay Markdown-first and assistant-neutral.

## Not Framework Core

Portable framework core must not depend on source-repository or environment details,
including:

- concrete package-manager, test, build, script, CI job, or local hook
  commands from one repository
- source-repository checker scripts or generated-file tools as required
  framework mechanisms
- source project business facts, architecture facts, data models, diagrams,
  rejection criteria, or production assumptions
- language, framework, database, queue, or cloud-provider choices from the
  source repository
- source-repository test commands, test folders, fixture helpers, CI jobs, or
  framework-specific testing tools
- source repository bridge text that names project-specific files as target
  facts
- source-repository security policy, live-service allowlists, dependency
  scanners, secret names, incident procedures, or destructive-command rules
- source-repository diagram formats, render commands, generated-file paths, or
  visual artifact tooling as required mechanisms
- source-repository framework versioning format, release notes, or local
  adapter owner names

Those facts are project or repository adapter details.

## Repository Adapter

A repository adapter owns the concrete facts for one project:

- project-specific blueprint, business logic, data model, diagrams, and docs
- target project commands, tests, CI checks, local scripts, hooks, and
  generated-file tools
- target context discovery map, source-of-truth map, risk model, approvals,
  and security/live-service policies
- target diagram formats, visual artifacts, render or manual-review process,
  and drift checks
- target assistant bridge files selected for the assistants the project uses
- target consistency checks that are deterministic and maintainable in that
  repository
- target adapter maturity gaps, framework baseline, local deviations, and
  lifecycle notes
- target final-evidence requirements for commands that actually exist there

Each project using Alatyr Core has its own adapter and local gates. Those
local gates can verify that repository, but they must not be copied as
portable framework requirements for another project.

## Installation Rule

When installing or upgrading the assistant framework in another repository:

1. Copy or adapt only the framework structure and wording that is portable.
2. Rewrite every project adapter file from target repository facts.
3. Replace source-repository commands with a target validation plan discovered
   from the target repository.
4. Mark unknown validation as manual or unresolved; do not invent commands.
5. Rewrite target context, risk, security, diagram, maturity, and lifecycle
   facts from target repository evidence.
6. Do not add an installer script as the framework mechanism.

If a source artifact mixes portable framework rules with repository adapter
details, split or rewrite it before using it as framework core.
