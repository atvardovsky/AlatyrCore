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
4. List changed fact IDs and canonical owners, re-derive testable invariants,
   and cluster related review items by shared fact or contract. When the `consistency-map`
   module is enabled, resolve exact registry-to-node identity from
   `.ai/project/source-of-truth-registry.md` and
   `.ai/project/consistency-map.json`, then derive affected contracts, areas,
   and surfaces and record selected/skipped edges.
5. Update target blueprint or equivalent source-of-truth docs when accepted
   facts change.
6. Update project flow, use-case, data, runtime, architecture, or public docs
   when those facts change.
7. Prepare an implementation plan that names affected boundaries, tests,
   diagrams, approvals, machine-readable scope records, and validation.
   Apply `.ai/assistant/flows/change-package.flow.md` when coherent material
   outcome, semantic multi-surface approval, audit, or publishable provenance
   needs pass its activation gate.
8. Evaluate the target test-first recommendation gate. When an enabled required
   trigger applies, or a recommendation is accepted, run
   `.ai/assistant/flows/test-first-change.flow.md` and preserve valid
   RED/GREEN/refactor evidence before completing implementation. Otherwise
   record why test-first was not indicated or was declined when material.
9. Change remaining code, tests, diagrams, prompts, skills, bridge files,
   gates, or checker rules as required by the accepted fact change.
10. Run target validation that exists. Do not invent commands.
11. When approval was used, compare the complete Git change set with the
    explicitly selected machine-readable approval scope and fail on uncovered
    or excluded paths.
12. Perform a final consistency check across changed surfaces and related
    review-item clusters.
13. Apply `.ai/assistant/gates/engineering-evidence.md` and preserve compact
    reusable task knowledge when triggered and authorized, or record a
    fact-specific skip or blocker.
14. Report final evidence, skipped checks, approvals, and residual risk.

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
- re-derived invariants and reconciled review-item clusters
- relationship impact closure, missing links, and areas reached
- source-of-truth or blueprint updates
- implementation, test, diagram, prompt, skill, gate, bridge, or checker updates
- validation run or unresolved
- test-first policy result, RED/GREEN/refactor evidence, accepted exception, or
  reason not indicated when the recommendation gate was materially evaluated
- approvals used
- changed-path approval scope enforcement result
- skipped checks and residual risk
- for large tasks, workstream convergence, context receipts, and checkpoints
- for activated change packages, semantic and path scope, companion decisions,
  material corrections, provenance quality, and public claim strength
- durable engineering-evidence status, record ID/path and repository binding,
  or a fact-specific skip or blocker
