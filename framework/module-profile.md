---
alatyr_doc:
  id: framework.module-profile
  type: framework-rule-owner
  owns_rules:
    - ALATYR-MODULE-001
  depends_on:
    - ALATYR-ADAPTER-001
  applies_to:
    - framework-upgrade
---
# Module Profile

Module profiles keep Alatyr Core from treating every capability as mandatory
for every target repository.

The framework has a required core profile and optional modules. A target
adapter records which modules are enabled, deferred, disabled, or not
applicable from target evidence.

## Required Core Profile

Every accepted installation should provide:

- contour separation for framework, project, and repository adapter facts
- adapter manifest with framework version, adapter schema version, template
  version, owner, supported assistants, known gaps, and local deviations
- adapter ownership metadata with responsible owner, backup owner, review
  cadence, last review date, and CODEOWNERS or equivalent file-owner map when
  supported
- context profiles with a small bootstrap context and task-specific expansion
  rules
- source-of-truth registry or explicit missing owner records for important
  fact types
- change-risk classification and approval triggers
- logical integrity review for changed semantic or logical facts
- validation or manual-review evidence, including unresolved checks
- final evidence format

If any required core item is missing, the adapter can still exist, but it must
report the missing item as a gap before claiming maturity.

## Optional Modules

Optional modules are enabled only when the target repository needs and can
maintain them:

- `blueprint-change`: blueprint-driven product-change workflow and project
  blueprint creation or repair.
- `diagrams`: diagram source, visual artifact, render or manual-review, and
  drift policy.
- `ai-infrastructure`: inventory, source access, prompt-injection handling,
  skill or prompt adaptation, wrappers, and provenance.
- `multi-assistant-bridges`: bridge capability matrix and assistant-specific
  wrappers for multiple supported assistants.
- `installed-operations`: post-install operation requests, operation help,
  routing, adapter recheck, and chat-message templates.
- `large-task-orchestration`: task-scale routing, operation packets,
  workstreams, resumable checkpoints, and final convergence evidence for
  repositories that need large or multi-session changes.
- `durable-approvals`: approval-record storage for protected changes that need
  plan, scope, or file evidence.
- `migration-diff`: migration notes and framework baseline comparisons for
  upgrades.
- `effectiveness-metrics`: comparable task reporting for measuring framework
  usefulness.
- `scaffolding`: optional source-repository scaffolding helpers used only to
  create placeholder structure.

Targets may add local modules when they record the owner, enabled state,
required files, validation, and residual risk.

## Module States

Use these states in target adapters:

- `required`: part of the required core profile.
- `enabled`: installed and maintained for the target.
- `deferred`: useful, but intentionally postponed with a recorded reason.
- `disabled`: not used by the target.
- `not-applicable`: irrelevant to the target's current shape.
- `blocked`: needed, but missing owner, policy, approval, or validation.

Do not hide missing adapter facts by marking a needed module as disabled.

## Installation Use

During installation or update:

1. Establish the required core profile first.
2. Select optional modules from target needs, not from source-repository
   availability.
3. Record module states in the target adapter manifest and module profile.
4. Create only the target templates needed for enabled or required modules.
5. Leave deferred, disabled, not-applicable, or blocked modules in evidence
   with the reason and next safe action.

Optional modules must not add target project facts from guesses or from another
repository.

## Evidence

A module profile review should report:

```text
Core profile state: <complete/missing gaps>
Adapter ownership: <owner/cadence/CODEOWNERS or equivalent/gaps>
Enabled modules: <modules>
Deferred modules: <modules and reasons>
Blocked modules: <modules and missing owners/policies/validation>
Files created or skipped: <target adapter surfaces>
Validation: <target checks or manual review>
Residual risk: <unresolved module gaps>
```

## Rejection Criteria

Reject module-profile work that:

- treats optional modules as mandatory for every target
- claims a module is enabled without owner, context, validation, and evidence
- copies source-repository helper behavior into target requirements
- installs bridge, diagram, skill, or operation-help surfaces the target does
  not use
- hides blocked core gaps behind a broad maturity claim
