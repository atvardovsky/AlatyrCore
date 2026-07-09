# Project Blueprint Creation Flow

Use this flow when creating, repairing, or rechecking `{PROJECT_NAME}` blueprint
or equivalent source-of-truth docs.

Replace placeholders with target facts before accepting installation.

## Target Sources

- Project source of truth: `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- Existing blueprint or equivalent docs: `{TARGET_BLUEPRINT_OR_EQUIVALENT}`
- Public docs: `{TARGET_PUBLIC_DOCS}`
- Architecture/design docs: `{TARGET_ARCHITECTURE_DOCS}`
- Tests and validation: `{TARGET_TEST_STRATEGY_AND_VALIDATION}`
- Security/live-service policy: `{TARGET_SECURITY_POLICY}`
- Diagram policy: `{TARGET_DIAGRAM_POLICY}`

## Steps

1. Load `AGENTS.md`, `.ai/README.md`, framework docs, target contours, and
   existing target source-of-truth docs.
2. Identify blueprint scope and non-goals.
3. Collect target evidence from docs, code structure, tests, validation, CI,
   diagrams, prompts, skills, gates, and bridge files.
4. Classify facts by owner: framework, project, repository adapter, bridge,
   skill/prompt, or generated artifact.
5. Draft or repair only facts supported by target evidence.
6. Mark missing or contradictory facts explicitly.
7. Apply `.ai/assistant/flows/logical-integrity-review.flow.md`.
8. Update blueprint or equivalent docs, project contour, flow docs, diagrams,
   gates, prompts, skills, or bridge files only when their owned facts change.
9. Run target validation that exists. Do not invent commands.
10. Report final evidence, unresolved facts, skipped checks, approvals, and
    residual risk.

## Rejection Criteria

Reject or revise blueprint work that:

- invents business rules, architecture, data model, runtime flows, security
  policy, validation commands, or diagram tooling
- copies source-project facts from Alatyr Core or another repository
- treats generated artifacts or bridge files as canonical without checking
  their owning source
- claims blueprint completion while placeholders or missing facts remain
- changes accepted architecture or business behavior without approval
