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
- Target validation: `{TARGET_VALIDATION}`
- Target security/live-service policy: `{TARGET_SECURITY_POLICY}`
- Target AI infrastructure source/access policy:
  `{TARGET_AI_INFRASTRUCTURE_SOURCE_ACCESS_POLICY}`

## Steps

1. Run `.ai/assistant/flows/ai-infrastructure-inventory.flow.md` or load a
   current inventory result for the affected assistant surfaces.
2. Record the item source, source type, item type, provenance, intended task,
   non-goals, integration mode, and supported assistant surfaces.
3. Classify the source as local path, Git URL, HTTPS URL, assistant-native
   reference, pasted content, package/plugin reference, or unknown.
4. Check target source-access, network, dependency, safety, and approval rules
   before reading remote content or importing the item into canonical files.
5. Check whether an equivalent or conflicting item already exists.
6. Classify the item as framework guidance, project fact, repository adapter
   workflow, bridge wrapper, or external assistant infrastructure.
7. Compare the item against target context, approval, validation, safety, and
   documentation-sync rules.
8. Remove or rewrite assumptions copied from another project.
9. Normalize file paths, source-of-truth references, validation, output format,
   and final evidence to target adapter facts.
10. Restrict live, destructive, spend-affecting, credential, dependency, or
   permission behavior unless the target adapter explicitly allows it and
   approval is present.
11. Keep assistant-specific wrappers short and pointing to canonical target
   files.
12. Update target validation or manual review expectations when the item
    changes recurring work.
13. Run target validation that exists. Do not invent commands.
14. Report approvals, skipped checks, and residual risk.

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
