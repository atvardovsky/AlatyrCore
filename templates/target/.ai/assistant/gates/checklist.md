# AI Acceptance Gates

This file is the target repository adapter for gate execution.

Replace placeholders with target validation facts. Do not copy validation
commands from another project.

## Mandatory Gates

- Rule references checked: `ALATYR-CONTEXT-001`, `ALATYR-SOURCE-001`,
  `ALATYR-RISK-001`, `ALATYR-APPROVAL-001`, `ALATYR-SAFETY-001`,
  `ALATYR-SAFETY-002`, `ALATYR-INTEGRITY-001`, `ALATYR-CHANGE-001`,
  `ALATYR-ADAPTER-001`, `ALATYR-MODULE-001`, and `ALATYR-EVIDENCE-001`.
- `AGENTS.md` treated as preloaded; compact bootstrap loaded from
  `.ai/alatyr.yaml`, `.ai/README.md`, and
  `.ai/assistant/context-router.json`.
- Source-of-truth registry checked when a changed fact has multiple possible
  owners or derived surfaces.
- Task context profile selected and required framework, project, assistant,
  flow, gate, policy, and validation files loaded.
- Large-task scale overlay and operation packet used only when activation
  conditions apply; active workstream context, checkpoints, dependencies, and
  global convergence checked when used.
- Module profile checked before relying on optional Alatyr capabilities.
- Semantic/logical change decision and logical integrity review made.
- Documentation sync checked.
- Tests or validation selected from target stack and risk.
- Diagram sync checked when diagram-relevant facts changed.
- Security/live-service policy checked when sensitive surfaces changed.
- Skill/provenance/safety policy checked when prompts, skills, wrappers, or
  third-party assistant infrastructure changed.
- AI infrastructure inventory checked before adding, importing, replacing, or
  removing assistant infrastructure.
- AI infrastructure source access checked when the request uses a local path,
  Git URL, HTTPS URL, assistant-native reference, pasted content, package, or
  plugin.
- Prompt-injection policy checked before trusting or adapting imported,
  external, remote, package/plugin, pasted, or unknown AI infrastructure.
- Installed-operation or adapter-recheck scope checked when the task asks for
  blueprint creation, framework update review, or adapter drift review.
- Task-specific maturity checked when the task is broad, risky, post-install,
  post-upgrade, or unclear.
- Bridge capability matrix checked when bridge files or supported assistant
  behavior may be affected.
- Migration note created or updated when a framework update requires target
  adapter actions.
- Operation help and routing checked when the user asks for Alatyr help,
  commands, available actions, or the requested operation is unclear.
- Adapter drift checks performed during installation, framework update, or
  adapter recheck: no hard-coded local machine paths, no stale checker
  existence claims, no duplicate context-profile references, context router
  references are present where bootstrap routing is described, unresolved owner
  placeholders remain known gaps, and any target-local adapter checker evidence
  matches the repository.
- Human approvals verified when required; approval records created when
  protected-change scope needs durable evidence.
- Final evidence reports run checks, skipped checks, assumptions, and residual
  risk.

## Target Validation

List actual target commands or manual checks:

- `{TARGET_VALIDATION_COMMAND_OR_REVIEW}`

If a validation command does not exist, write a manual review item or mark it
unresolved.

## Semantic Change Decision Gate

Decide whether any behavior, field, relation, dependency, flow, state,
diagram edge, prompt rule, gate rule, skill instruction, bridge rule, or
checker invariant changed.

If a semantic/logical fact changed, update the owning code, docs, tests,
diagrams, prompts, skills, bridge files, or checker rules in the same change.

If no semantic/logical fact changed, final evidence must explain why no
companion update was needed.
