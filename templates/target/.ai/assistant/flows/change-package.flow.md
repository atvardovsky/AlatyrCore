# Change Package Flow

Use this flow in `{PROJECT_NAME}` only when the optional `change-packages`
module is enabled and the package activation gate passes. Do not create a
package for an ordinary local task.

## Target Sources

- Framework rule: `.ai/framework/change-packages.md`
- Package index: `.ai/assistant/change-packages/index.json`
- Machine template: `.ai/assistant/templates/change-package-record.json`
- Human report template: `.ai/assistant/templates/change-package-report.md`
- Approval records: `.ai/assistant/approvals/`
- Source-of-truth registry: `.ai/project/source-of-truth-registry.md`
- Target retention and redaction policy: `{TARGET_CHANGE_PACKAGE_POLICY}`
- Target validation: `{TARGET_VALIDATION_OR_MANUAL_REVIEW}`

## Activation Gate

Activate for a coherent material outcome, semantic multi-surface approval,
architecture segment or capability, combined cross-area integrity result, or
audit/publishable provenance need. Record the exact reason.

Skip the package for a small one-profile, one-fact task with ordinary final
evidence. Large-task activation alone is not sufficient.

## Steps

1. Select the normal task profile and changed-fact owners first.
2. Apply the activation gate. If skipped, continue the normal operation flow.
3. Create one machine record and add only its compact identity, status, facts,
   owners, areas, provenance, approvals, active workstream, incident family,
   corrective iteration, latest failed-gate state, and residual risk
   to the package index.
   Each index entry uses `package_id`, `status`, `record`, `changed_fact_ids`,
   `canonical_owners`, `project_areas`, `evidence_quality`, `approval_records`,
   `active_workstream`, `incident_family_id`, `corrective_iteration`,
   `latest_failed_gate_state`, and `residual_risk`.
   Keep those fields as an exact projection of the package record: IDs and
   owners from `changed_facts`, areas from `routing`, evidence quality from
   `provenance`, approvals from `approved_scope`, and workstream from
   `operation`.
   Keep active and recent entries in the root index. When its target budget is
   exceeded, move closed entries into bounded index shards and record each
   shard's target-relative path, SHA-256, and record count in root `shards`.
4. Record the plan version/file/hash and the approved semantic and path scope.
   Bind every active package to the digest of its ignored runtime problem
   model. If this corrects earlier repair work, keep the same incident family
   and add exact predecessor package IDs, record paths, and SHA-256 digests.
   Use `systemic-repair` plus `recurring-correction` from corrective iteration
   two onward. Escaped defects, failed required gates, recurring corrections,
   and systemic repair require the problem model's whole-lifecycle contract.
   Before declaring a correction isolated, inspect explicit predecessors,
   failed required gates, repeated changed-fact IDs, and fresh runtime
   contradictions. Each candidate needs an incident-lineage disposition;
   candidate signals do not prove shared causality.
5. Link explicit machine approval records. Require reapproval for new
   protected fact IDs, areas, behavior categories, external effects, or paths.
6. During implementation, record only material discoveries and corrections.
   Stop when an entry is `reapproval-required`.
7. Decide each applicable companion surface as `updated`, `not-required`, or
   `missing`, with a fact-specific reason and evidence.
   Every newly created package containing code or test changes records a
   `project-contour-sync` companion decision. Historical package records are
   not rewritten solely to add this evidence.
8. When architecture reasoning applies, retain a compact problem,
   alternatives, direction, authority, status, and source summary. Do not keep
    raw chat by default.
   If a durable engineering-evidence record captures the same invariant,
   root-cause, solution, and regression conclusions, link its ID and do not
   duplicate the content.
9. At convergence, record actual facts, areas, behavior categories, external
   effects, and paths; reconcile them with approval and logical integrity.
10. Record validation, skipped checks, residual risks, and before/after
    provenance. Use `git-range`, `pull-request`, `selected-file-snapshot`, or
    `unverified` accurately.
    For public or audit evidence, prefer a dedicated branch/worktree and record
    start/validation tree state plus unrelated-change handling.
11. Produce the redacted Markdown report only when human review, audit, pilot,
    or publication needs it.

## Validation Boundary

The target validator auto-selects active root-index packages and may check
record shape, hashes, refs, incident lineage, problem-model synchronization,
failed-gate and lifecycle state, range paths,
declared semantic scope, companion decisions, corrections, and evidence-grade
requirements. It does not prove domain invariants, semantic completeness, or
architecture correctness.

## Final Evidence

Report package ID, activation reason, incident family, corrective iteration,
latest failed gate, lifecycle coverage, changed facts and owners, approved and
actual semantic/path scope, material corrections, companion decisions,
architecture summary, linked engineering-evidence IDs, validation, provenance
quality, public claim strength, and residual risk.
