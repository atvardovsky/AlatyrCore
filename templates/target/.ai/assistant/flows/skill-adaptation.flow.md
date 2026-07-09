# Skill Adaptation Flow

Use this flow when adding, importing, changing, or reviewing assistant skills,
prompts, wrappers, or third-party assistant infrastructure for `{PROJECT_NAME}`.

Replace placeholders with target facts before accepting installation.

## Target Sources

- Canonical assistant instructions: `AGENTS.md`, `AI_ASSISTANTS.md`,
  `.ai/README.md`
- Framework skill guidance: `.ai/framework/skill-adaptation.md`
- Target assistant contour: `.ai/assistant/contour.md`
- Target gates: `.ai/assistant/gates/checklist.md`
- Target validation: `{TARGET_VALIDATION}`
- Target security/live-service policy: `{TARGET_SECURITY_POLICY}`

## Steps

1. Record the skill source, provenance, intended task, non-goals, and supported
   assistant surfaces.
2. Classify the skill as framework guidance, project fact, repository adapter
   workflow, bridge wrapper, or external assistant infrastructure.
3. Compare the skill against target context, approval, validation, safety, and
   documentation-sync rules.
4. Remove or rewrite assumptions copied from another project.
5. Normalize file paths, source-of-truth references, validation, output format,
   and final evidence to target adapter facts.
6. Restrict live, destructive, spend-affecting, credential, dependency, or
   permission behavior unless the target adapter explicitly allows it and
   approval is present.
7. Keep assistant-specific wrappers short and pointing to canonical target
   files.
8. Update target validation or manual review expectations when the skill changes
   recurring work.
9. Run target validation that exists. Do not invent commands.
10. Report approvals, skipped checks, and residual risk.

## Approval Gate

Require explicit programmer approval before:

- importing third-party assistant infrastructure into canonical target files
- broadening tool access, permissions, live-service access, or destructive
  capabilities
- weakening gates, approval rules, validation, documentation-sync, redaction, or
  final evidence
- adding production dependencies or external services
- changing accepted architecture, business behavior, security behavior, or
  privacy handling

## Final Evidence

Report:

- skill source and provenance
- classification and target surfaces changed
- conflicts found and normalization performed
- safety review
- validation run or unresolved
- approvals used
- skipped checks and residual risk
