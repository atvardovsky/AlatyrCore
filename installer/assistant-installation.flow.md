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

## Source Bootstrap

Read in this repository first:

- `README.md`
- `AGENTS.md`
- `INSTALL.md`
- `framework/README.md`
- `framework/context-profiles.md`
- `framework/context-router.md`
- `framework/project-adapter-contract.md`
- `framework/portability.md`
- `framework/module-profile.md`
- `framework/rule-ownership.md`
- `framework/rule-registry.md`
- `framework/rule-registry.json`
- `installer/readiness-checklist.md`
- `installer/installation-plan-template.md`

Then inspect the target repository and load additional source files from the
smallest matching installation scope. Read each `framework/*.md` file before
copying or adapting it into the target `.ai/framework`. A full-core
installation or upgrade therefore reads the full framework corpus at the
copy/adaptation stage, not as a default bootstrap.

Load target templates from `templates/target` only for surfaces the plan will
create or compare, and keep them as placeholders until rewritten from target
evidence.

## Rule References

This flow is derived from canonical framework rules. Keep long policy wording
in the owning framework documents and use these IDs for installation routing:

- `ALATYR-CONTEXT-001`
- `ALATYR-SOURCE-001`
- `ALATYR-RISK-001`
- `ALATYR-APPROVAL-001`
- `ALATYR-SAFETY-001`
- `ALATYR-SAFETY-002`
- `ALATYR-ADAPTER-001`
- `ALATYR-MODULE-001`
- `ALATYR-LIFECYCLE-001`
- `ALATYR-EVIDENCE-001`

## Required Target Context

Read in the target repository:

- existing AI instructions and bridge files
- existing CODEOWNERS or equivalent file-owner metadata
- README and public docs
- architecture/design docs
- package/build/dependency files
- tests, fixtures, test helpers, and CI
- local validation commands or manual validation policy
- security, live-service, credential, and destructive-operation policies
- diagram sources, generated files, and visual artifacts
- existing prompts, skills, third-party assistant infrastructure, provenance
  notes, source-access policies, gates, checker rules, operation help, routing
  flows, and assistant chat-message templates
- existing manifests, version notes, context profiles, approval records, and
  prompt-injection or imported-source policies
- existing source-of-truth registry, maturity profile, bridge capability
  matrix, and migration notes

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
2. Optionally use source-repository scaffolding only to preview or create
   placeholder structure. Do not treat scaffolding as installation.
3. Fill `installer/readiness-checklist.md` for the target.
4. Prepare an installation plan from
   `installer/installation-plan-template.md`.
5. Identify protected changes and required approvals.
6. If approval is required, stop until the programmer confirms it.
7. Create or adapt target `AGENTS.md` and `AI_ASSISTANTS.md`.
8. Create or preserve `CODEOWNERS` or equivalent owner metadata when the
   target supports file ownership.
9. Create or adapt target `.ai/alatyr.yaml` or equivalent manifest with
   framework version, adapter schema version, template version, owner,
   backup owner, review cadence, CODEOWNERS or equivalent owner map,
   source-of-truth, validation, known gaps, and local deviations.
10. Create or adapt target `.ai/README.md`.
11. Copy or adapt portable framework files into target `.ai/framework`,
    including `framework/*.md` and `framework/rule-registry.json`.
12. Create target `.ai/project/contour.md` and target project
   source-of-truth docs from target facts.
13. Create target `.ai/assistant/contour.md`, context router, context
    profiles, module profile, task-specific maturity profile, bridge
    capability matrix, and minimal target assistant workflows/gates from
    target facts.
14. Add bridge files only for assistants the target uses.
15. Add installed-operation, operation-help, operation-routing,
    AI-infrastructure-inventory, adapter output contract
    `.ai/assistant/templates/adapter-output-contracts.md`, source-access
    policy, prompt-injection policy, approval-record template, migration-note
    template, blueprint-creation, adapter-recheck, and post-install/update
    chat-message templates when the target wants
    post-install operation requests or AI infrastructure adaptation.
16. Ensure root assistant entry points and supported bridge files point future
    sessions to the installation note, operation help, and routing flow.
17. Add prompts, skills, diagrams, or consistency checks only when they solve
    target friction, can be maintained, and have been adapted to target facts.
18. Run target validation that exists. Do not invent commands.
19. Apply logical integrity review: changed facts, affected contracts,
    source of truth, repair direction, and residual risk.
20. Report final evidence.
21. Send the appropriate post-install or post-update assistant chat message
    using the target template when installed.

## Human Approval Gate

Advice and planning do not require approval.

Use `ALATYR-APPROVAL-001` for protected-change approval. Classify protected
scope with `ALATYR-RISK-001`, `ALATYR-SAFETY-001`, and
`ALATYR-SAFETY-002`, then apply the target adapter's stricter local policy
when it exists.

Preferred approval:

```text
APPROVE ALATYR INSTALLATION: <installation-id>
```

When protected-change scope spans multiple files or plan versions, record the
approval using the target approval-record template.

## Validation Rule

Alatyr Core has no universal validation command.

Use target repository commands only when they are discovered in the target.
If target validation is missing, manual, or unavailable, report the unresolved
check and residual risk.

## Final Evidence

Report:

- installation id and approval used, if any
- framework version, adapter schema version, template version, and manifest
  path
- adapter owner, backup owner, review cadence, and CODEOWNERS or equivalent
  owner map status
- scaffolding helper used or skipped
- target repository inspected
- framework core files installed or adapted
- project adapter files rewritten from target facts
- existing files preserved, skipped, or overwritten with approval
- supported assistant bridges added or skipped
- installed-operation, operation-help, operation-routing,
  AI-infrastructure-inventory, adapter output contract, context router,
  context profiles, module profile, source-of-truth registry, task-specific
  maturity profile, bridge capability matrix, source-access policy,
  prompt-injection policy, approval-record template, migration-note template,
  blueprint-creation, adapter-recheck, and post-install/update chat-message
  templates added or skipped
- root entry-point and bridge bootstrap references checked
- prompts, skills, or third-party assistant infrastructure adapted or skipped
- target validation run and skipped
- unresolved adapter facts
- logical integrity review result
- residual risk
- post-install or post-update assistant chat message sent or skipped with
  reason
