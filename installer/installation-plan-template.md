# Alatyr Core Installation Plan

Installation id: `ALATYR-YYYYMMDD-short-name`

## Target Repository

- Path:
- New install or upgrade:
- Primary stack:
- Existing AI instructions:
- Supported assistants:

## Goal

Describe what the installation should enable.

## Non-Goals

List what must not be changed.

## Target Facts Collected

- Product purpose:
- Architecture/module facts:
- Blueprint or equivalent source-of-truth docs:
- Business/domain rules:
- Data model facts:
- Runtime flows:
- Test strategy and existing test surface:
- Source-of-truth/context map:
- Blueprint-driven change or equivalent product-change workflow:
- Risk and approval model:
- Security, privacy, live-service, destructive-operation, dependency, and
  credential/log-redaction policies:
- Diagram sources, visual artifacts, render/manual-review process, and drift
  checks:
- Skills, prompts, third-party assistant infrastructure, provenance, wrappers,
  permissions, and output formats:
- Target validation commands:
- Source commands/scripts not copied:
- Source test tools/fixtures/CI jobs not copied:
- Source security policies, diagram tooling, lifecycle notes, and adapter owner
  facts not copied:
- Source skill files, assistant-native formats, tool permissions, and
  third-party assistant infrastructure not copied:
- Missing facts:

## Framework Core Files

List reusable framework files to create or adapt in target `.ai/framework`.

Do not include source-repository commands, scripts, generated-file tools,
checker paths, test commands, fixtures, folder conventions, security policies,
diagram tooling, lifecycle notes, skill sources, assistant-native formats,
tool permissions, third-party assistant infrastructure, or CI jobs as framework
core.

## Project Adapter Files

List target-specific files to rewrite from target facts.

## Context, Risk, Safety, Testing, And Diagram Adaptation

- Target context entry points:
- Source-of-truth owners:
- Blueprint or equivalent owner:
- Generated artifacts and owning sources:
- Missing-context escalation:
- Risk classes and approval triggers:
- Security and live-service boundaries:
- Destructive-operation and dependency approval rules:
- Credential, privacy, and log-redaction rules:
- Recommended test levels:
- Target validation commands or manual checks:
- Skill adaptation, provenance, wrapper, and output-format rules:
- Diagram source format:
- Human visual format:
- Render or manual-review policy:
- Drift checks:
- Adapter maturity level:
- Maturity gaps:
- Framework baseline or source:
- Local deviations:
- Upgrade or migration notes:

## Contour Plan

- Framework contour:
- Project contour:
- Repository adapter contour:
- Mixed artifacts to split:

## Bridge File Plan

List assistant-specific bridge files to create, update, skip, or preserve.

## Existing File Preservation

| File | Action | Approval needed |
| --- | --- | --- |

## Rejected Source Facts

List source or example facts that must not be copied into the target project.

## Validation Plan

| Check | Command or review | Required | Notes |
| --- | --- | --- | --- |

Validation commands must come from the target repository. If no command exists,
write a manual review item or mark the check unresolved.

## Approval Required

State whether approval is required and why.

Preferred approval:

```text
APPROVE ALATYR INSTALLATION: ALATYR-YYYYMMDD-short-name
```

## Risks

List drift, overwrite, unsupported-assistant, gate, security, diagram,
maturity, lifecycle, skill-adaptation, and validation risks.
