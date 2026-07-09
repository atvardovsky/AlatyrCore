# AI Acceptance Gates

This file is the target repository adapter for gate execution.

Replace placeholders with target validation facts. Do not copy validation
commands from another project.

## Mandatory Gates

- Context loaded from `AGENTS.md`, `.ai/README.md`, framework docs, contours,
  and target source-of-truth docs.
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
- Installed-operation or adapter-recheck scope checked when the task asks for
  blueprint creation, framework update review, or adapter drift review.
- Operation help and routing checked when the user asks for Alatyr help,
  commands, available actions, or the requested operation is unclear.
- Human approvals verified when required.
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
