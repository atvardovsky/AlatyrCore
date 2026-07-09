# Framework Maintenance

Use this guide when changing Alatyr Core itself.

## Change Categories

- Framework rule change: update `framework/`, installer docs, target
  templates, README, and changelog when affected.
- Installation process change: update `installer/`, README, target templates,
  and assistant compatibility docs when affected.
- Target template change: update `templates/target`, installer docs, and
  README when the installation contract changes.
- Installed-operation help or chat-message change: update `framework/`,
  `installer/`, `templates/target`, assistant compatibility docs, and
  changelog when affected.
- Source-repository validation change: update `tools/`, maintainer docs,
  `AGENTS.md`, README, and changelog when affected.
- Wording-only change: update only the owning document when no behavior,
  installation step, or adapter requirement changes.

## Self-Application Reviews

When using Alatyr Core to inspect or improve this source repository, treat
generated target-adapter output as scratch unless the task is explicitly to
change tracked templates or docs.

- Put self-installation plans, readiness notes, trial `.ai` trees, copied
  bridge files, and assistant-local adapter folders in ignored paths such as
  `tmp/` or the root-local assistant paths listed in `.gitignore`.
- Do not commit a generated self-installation of Alatyr Core into this source
  repository.
- Promote reusable findings into the canonical owning files: `framework/`,
  `installer/`, `templates/target/`, `docs/`, `README.md`, `INSTALL.md`,
  `AI_ASSISTANTS.md`, `AGENTS.md`, or `CHANGELOG.md`.

## Manual Gate Review

Before accepting a change, check:

- `python3 tools/check_framework_consistency.py` passes when the helper is
  available.
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

The helper is source-repository validation for AlatyrCore only. Do not present
it as a portable framework requirement for target repositories.

## Rejection Criteria

Reject changes that:

- add project-specific behavior as framework core
- add an installer script as the installation mechanism
- make target validation commands universal
- weaken approval gates for overwrites or protected target changes
- make bridge files authoritative instead of pointers
- leave templates with source-project facts instead of placeholders
