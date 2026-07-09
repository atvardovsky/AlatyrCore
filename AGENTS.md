# Agent Instructions

This repository is Alatyr Core, a portable Markdown-first AI assistant
framework.

Agents working here must preserve the separation between:

- portable framework core under `framework/`
- assistant installation materials under `installer/`
- target repository templates under `templates/target/`
- explanatory maintainer docs under `docs/`

## Mandatory Context

Before changing framework docs, installer docs, templates, or assistant
instructions, read:

- `README.md`
- `INSTALL.md`
- `framework/README.md`
- `framework/contour.md`
- `framework/guarantees.md`
- `framework/project-adapter-contract.md`
- `framework/portability.md`
- `framework/context-discovery.md`
- `framework/change-risk-model.md`
- `framework/security-safety-guidance.md`
- `framework/diagram-guidance.md`
- `framework/testing-guidance.md`
- `framework/adapter-maturity.md`
- `framework/lifecycle.md`
- `installer/assistant-installation.flow.md`
- `installer/readiness-checklist.md`
- `installer/installation-plan-template.md`

## Operating Rules

- Keep Alatyr Core assistant-neutral and Markdown-first.
- Do not add project-specific business facts to framework core.
- Do not add local validation commands as framework requirements.
- Do not add installer scripts as the installation mechanism.
- Do not copy another project's commands, test folders, fixtures, security
  policy, diagram tooling, lifecycle notes, or assistant bridge wording into
  framework core.
- Templates under `templates/target` must contain placeholders, not accepted
  facts for a real project.
- Bridge templates must stay short and point to canonical target files.
- Installation docs must tell assistants to inspect the target repository and
  rewrite adapter facts from target evidence.

## Documentation Sync

When framework behavior changes, check and update:

- `README.md`
- `INSTALL.md`
- `AI_ASSISTANTS.md`
- `framework/*.md`
- `installer/*.md`
- `templates/target`
- `docs/*.md`
- `CHANGELOG.md`

When only wording changes and no framework behavior changes, say that no
installation, template, or adapter-contract update was needed.

## Validation

This repository intentionally has no universal runtime validation command.
For Alatyr Core changes, perform a manual gate review:

- no source-project facts in `framework/`
- no hard-coded project commands as framework requirements
- installer flow, readiness checklist, and plan template agree
- target templates remain placeholders
- README still lets an assistant install the framework without external
  explanation

If project-specific validation is later added to this repository, document it
as this repository's adapter validation, not as a framework requirement.

