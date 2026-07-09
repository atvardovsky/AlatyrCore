# Example Adapted Skill

This placeholder shows how an imported assistant skill should look after it is
adapted to `{PROJECT_NAME}`.

Replace every placeholder from target evidence before accepting installation.

## Provenance

- Source: `{IMPORTED_SKILL_SOURCE_OR_UNKNOWN}`
- Imported date: `{DATE}`
- Original purpose: `{ORIGINAL_SKILL_PURPOSE}`
- Target purpose: `{TARGET_SKILL_PURPOSE}`
- Supported assistant surfaces: `{SUPPORTED_ASSISTANT_SURFACES}`

## Canonical Target Context

Before using this skill, read:

- `AGENTS.md`
- `AI_ASSISTANTS.md`
- `.ai/README.md`
- `.ai/framework/skill-adaptation.md`
- `.ai/assistant/flows/skill-adaptation.flow.md`
- `.ai/assistant/gates/checklist.md`
- `{TARGET_PROJECT_SOURCE_OF_TRUTH}`

## Normalized Rules

- Use target source-of-truth files only: `{TARGET_SOURCE_OF_TRUTH_DOCS}`.
- Use target validation only: `{TARGET_VALIDATION}`.
- Follow target security/live-service policy: `{TARGET_SECURITY_POLICY}`.
- Do not call live services, run destructive actions, broaden permissions, or
  add dependencies unless the target adapter allows it and approval is present.
- Do not copy source skill commands, paths, fixtures, policies, or project
  facts into `{PROJECT_NAME}`.

## Output Format

```text
Skill: {TARGET_SKILL_NAME}
Source/provenance: {IMPORTED_SKILL_SOURCE_OR_UNKNOWN}
Changed facts: <facts changed or none>
Target files reviewed: <canonical target files>
Actions taken: <changes or recommendation>
Validation: <target checks or manual review>
Approvals: <used or not required>
Residual risk: <skipped or unresolved checks>
```
