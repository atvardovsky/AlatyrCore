# Framework Maintenance

Use this guide when changing Alatyr Core itself.

## Change Categories

- Framework rule change: update `framework/`, installer docs, target
  templates, README, and changelog when affected.
- Installation process change: update `installer/`, README, target templates,
  and assistant compatibility docs when affected.
- Target template change: update `templates/target`, installer docs, and
  README when the installation contract changes.
- Wording-only change: update only the owning document when no behavior,
  installation step, or adapter requirement changes.

## Manual Gate Review

Before accepting a change, check:

- `framework/` contains no target business facts.
- `framework/` contains no required local commands, scripts, package managers,
  CI jobs, test folders, fixture helpers, security policies, or diagram tools.
- `installer/assistant-installation.flow.md`,
  `installer/readiness-checklist.md`, and
  `installer/installation-plan-template.md` agree.
- `templates/target` remains placeholder-based.
- `README.md` still gives an assistant enough context to install the
  framework into a target repository.
- `CHANGELOG.md` records framework behavior or installation contract changes.

## Rejection Criteria

Reject changes that:

- add project-specific behavior as framework core
- add an installer script as the installation mechanism
- make target validation commands universal
- weaken approval gates for overwrites or protected target changes
- make bridge files authoritative instead of pointers
- leave templates with source-project facts instead of placeholders

