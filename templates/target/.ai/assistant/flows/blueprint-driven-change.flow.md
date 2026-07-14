# Blueprint-Driven Change Flow

Use this flow when a requested change may affect `{PROJECT_NAME}` accepted
behavior, source-of-truth docs, implementation, tests, diagrams, or assistant
governance.

Replace placeholders with target facts before accepting installation.

## Target Sources

- Project source of truth: `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- Blueprint or equivalent docs: `{TARGET_BLUEPRINT_OR_EQUIVALENT}`
- Project flow docs: `{TARGET_FLOW_DOCS}`
- Test strategy and validation: `{TARGET_TEST_STRATEGY_AND_VALIDATION}`
- Diagram policy: `{TARGET_DIAGRAM_POLICY}`
- Security/live-service policy: `{TARGET_SECURITY_POLICY}`

## Steps

1. State change intent and non-goals.
2. Use `.ai/assistant/context-router.json` to load the smallest matching
   profile and project-area overlays plus the target source-of-truth docs.
   Activate the `large-or-resumable` scale overlay when its conditions apply.
3. Apply `.ai/assistant/flows/logical-integrity-review.flow.md`.
4. List changed fact IDs and canonical owners. When the `consistency-map`
   module is enabled, derive affected contracts, areas, and surfaces from
   `.ai/project/consistency-map.json` and record selected/skipped edges.
5. Update target blueprint or equivalent source-of-truth docs when accepted
   facts change.
6. Update project flow, use-case, data, runtime, architecture, or public docs
   when those facts change.
7. Prepare an implementation plan that names affected boundaries, tests,
   diagrams, approvals, and validation.
8. Change code, tests, diagrams, prompts, skills, bridge files, gates, or
   checker rules as required by the accepted fact change.
9. Run target validation that exists. Do not invent commands.
10. Perform a final consistency check across changed surfaces.
11. Report final evidence, skipped checks, approvals, and residual risk.

For large or resumable changes, use
`.ai/assistant/flows/large-task-orchestration.flow.md` and maintain one packet
from `.ai/assistant/templates/large-task-operation-packet.md`. Complete one
global logical integrity review after workstream-local validation.

## Approval Gate

Require explicit programmer approval before:

- architecture changes
- accepted business behavior changes
- weakened tests, gates, documentation-sync rules, or approval requirements
- new production dependencies, services, permissions, or credentials
- live, destructive, spend-affecting, data-loss, security, or privacy changes
- overwriting existing AI instructions
- integrating third-party assistant infrastructure into canonical target files

## Final Evidence

Report:

- changed facts
- relationship impact closure, missing links, and areas reached
- source-of-truth or blueprint updates
- implementation, test, diagram, prompt, skill, gate, bridge, or checker updates
- validation run or unresolved
- approvals used
- skipped checks and residual risk
- for large tasks, workstream convergence, context receipts, and checkpoints
