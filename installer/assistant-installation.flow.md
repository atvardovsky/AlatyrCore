# Alatyr Core Assistant Installation Flow

## Purpose

Guide an assistant through installing Alatyr Core into a target repository
without relying on an installer script.

The flow is portable and assistant-neutral. The target project adapter must be
rewritten from target repository facts.

## Use When

Use this flow when:

- a programmer asks to install Alatyr Core into a project
- a project needs framework/project/repository-adapter contour separation
- an existing AI instruction setup needs to be upgraded to Alatyr Core
- a target repository needs assistant-neutral flows, gates, prompts, skills,
  bridge files, or documentation-sync rules

## Required Source Context

Read in this repository:

- `README.md`
- `AGENTS.md`
- `INSTALL.md`
- `framework/README.md`
- `framework/contour.md`
- `framework/guarantees.md`
- `framework/project-adapter-contract.md`
- `framework/portability.md`
- `framework/context-discovery.md`
- `framework/change-risk-model.md`
- `framework/logical-integrity.md`
- `framework/blueprint-driven-change.md`
- `framework/security-safety-guidance.md`
- `framework/diagram-guidance.md`
- `framework/testing-guidance.md`
- `framework/skill-adaptation.md`
- `framework/adapter-maturity.md`
- `framework/lifecycle.md`
- `framework/installed-operations.md`
- `framework/operation-help.md`
- `installer/readiness-checklist.md`
- `installer/installation-plan-template.md`
- `templates/target`

## Required Target Context

Read in the target repository:

- existing AI instructions and bridge files
- README and public docs
- architecture/design docs
- package/build/dependency files
- tests, fixtures, test helpers, and CI
- local validation commands or manual validation policy
- security, live-service, credential, and destructive-operation policies
- diagram sources, generated files, and visual artifacts
- existing prompts, skills, third-party assistant infrastructure, provenance
  notes, gates, checker rules, operation help, routing flows, and assistant
  chat-message templates

## Ownership Classification

Classify every proposed target file:

- framework core: portable Alatyr Core rules copied or adapted into
  `.ai/framework`
- project fact: target product/code/business/data/runtime fact
- repository adapter fact: local assistant workflow, prompt, gate, skill,
  bridge, validation, or final-evidence rule
- bridge/wrapper: assistant-specific pointer to canonical target files
- skill or prompt artifact: adapter-owned assistant infrastructure that must be
  normalized to target facts before becoming canonical
- generated/visual artifact: output whose source must be named
- existing target-owned file: preserve unless approval permits overwrite

## Steps

1. Inspect the target repository before creating files.
2. Fill `installer/readiness-checklist.md` for the target.
3. Prepare an installation plan from
   `installer/installation-plan-template.md`.
4. Identify protected changes and required approvals.
5. If approval is required, stop until the programmer confirms it.
6. Create or adapt target `AGENTS.md` and `AI_ASSISTANTS.md`.
7. Create or adapt target `.ai/README.md`.
8. Copy or adapt `framework/*.md` into target `.ai/framework`.
9. Create target `.ai/project/contour.md` and target project
   source-of-truth docs from target facts.
10. Create target `.ai/assistant/contour.md` and minimal target assistant
    workflows/gates from target facts.
11. Add bridge files only for assistants the target uses.
12. Add installed-operation, operation-help, operation-routing,
    AI-infrastructure-inventory, blueprint-creation, adapter-recheck, and
    post-install/update chat-message templates when the target wants
    post-install operation requests.
13. Add prompts, skills, diagrams, or consistency checks only when they solve
    target friction, can be maintained, and have been adapted to target facts.
14. Run target validation that exists. Do not invent commands.
15. Apply logical integrity review: changed facts, affected contracts,
    source of truth, repair direction, and residual risk.
16. Report final evidence.
17. Send the appropriate post-install or post-update assistant chat message
    using the target template when installed.

## Human Approval Gate

Advice and planning do not require approval.

Explicit approval is required before:

- overwriting existing target AI instructions
- changing target architecture or accepted business behavior
- weakening target gates, tests, documentation-sync rules, or approval rules
- adding production dependencies or external services
- enabling live, destructive, spend-affecting, or data-loss side effects
- importing third-party assistant infrastructure into canonical target files

Preferred approval:

```text
APPROVE ALATYR INSTALLATION: <installation-id>
```

## Validation Rule

Alatyr Core has no universal validation command.

Use target repository commands only when they are discovered in the target.
If target validation is missing, manual, or unavailable, report the unresolved
check and residual risk.

## Final Evidence

Report:

- installation id and approval used, if any
- target repository inspected
- framework core files installed or adapted
- project adapter files rewritten from target facts
- existing files preserved, skipped, or overwritten with approval
- supported assistant bridges added or skipped
- installed-operation, operation-help, operation-routing,
  AI-infrastructure-inventory, blueprint-creation, adapter-recheck, and
  post-install/update chat-message templates added or skipped
- prompts, skills, or third-party assistant infrastructure adapted or skipped
- target validation run and skipped
- unresolved adapter facts
- logical integrity review result
- residual risk
- post-install or post-update assistant chat message sent or skipped with
  reason
