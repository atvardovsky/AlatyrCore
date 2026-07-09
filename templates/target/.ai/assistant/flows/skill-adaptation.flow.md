# Skill Adaptation Flow

Use this flow when adding, importing, changing, or reviewing assistant skills,
prompts, wrappers, bridges, rules, MCP/tool configs, gates, checkers, flows,
templates, or third-party assistant infrastructure for `{PROJECT_NAME}`.

The request may arrive as `skill-adaptation` or as the target alias
`alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}` or
`alatyr-add-ai {AI_INFRASTRUCTURE_SOURCE}`.

Replace placeholders with target facts before accepting installation.

## Target Sources

- Canonical assistant instructions: `AGENTS.md`, `AI_ASSISTANTS.md`,
  `.ai/README.md`
- Framework skill guidance: `.ai/framework/skill-adaptation.md`
- Target assistant contour: `.ai/assistant/contour.md`
- AI infrastructure inventory flow:
  `.ai/assistant/flows/ai-infrastructure-inventory.flow.md`
- Target gates: `.ai/assistant/gates/checklist.md`
- AI infrastructure source-access policy:
  `.ai/assistant/policies/ai-infrastructure-source-access.md`
- Target validation: `{TARGET_VALIDATION}`
- Target security/live-service policy: `{TARGET_SECURITY_POLICY}`
- Target AI infrastructure source/access policy:
  `{TARGET_AI_INFRASTRUCTURE_SOURCE_ACCESS_POLICY}`

## Steps

1. Run `.ai/assistant/flows/ai-infrastructure-inventory.flow.md` or load a
   current inventory result for the affected assistant surfaces.
2. Read `.ai/assistant/policies/ai-infrastructure-source-access.md` when it
   exists; otherwise record source-access policy as missing and keep the work
   review-only.
3. Record the item source, source type, item type, provenance, intended task,
   non-goals, integration mode, and supported assistant surfaces.
4. Classify the source as local path, Git URL, HTTPS URL, assistant-native
   reference, pasted content, package/plugin reference, or unknown.
5. Check target source-access, network, dependency, safety, and approval rules
   before reading remote content or importing the item into canonical files.
6. Check whether an equivalent or conflicting item already exists.
7. Classify the item as framework guidance, project fact, repository adapter
   workflow, bridge wrapper, or external assistant infrastructure.
8. Compare the item against target context, approval, validation, safety, and
   documentation-sync rules.
9. Remove or rewrite assumptions copied from another project.
10. Normalize file paths, source-of-truth references, validation, output format,
   and final evidence to target adapter facts.
11. Restrict live, destructive, spend-affecting, credential, dependency, or
   permission behavior unless the target adapter explicitly allows it and
   approval is present.
12. Keep assistant-specific wrappers short and pointing to canonical target
   files.
13. Update target validation or manual review expectations when the item
    changes recurring work.
14. Run target validation that exists. Do not invent commands.
15. Report approvals, skipped checks, and residual risk.

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

- inventory result used
- item source and provenance
- item type
- source type and source-access decision
- classification and target surfaces changed
- conflicts found and normalization performed
- safety review
- validation run or unresolved
- approvals used
- skipped checks and residual risk
