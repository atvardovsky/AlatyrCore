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
   owners, areas, provenance, approvals, active workstream, and residual risk
   to the package index.
   Each index entry uses `package_id`, `status`, `record`, `changed_fact_ids`,
   `canonical_owners`, `project_areas`, `evidence_quality`, `approval_records`,
   `active_workstream`, and `residual_risk`.
4. Record the plan version/file/hash and the approved semantic and path scope.
5. Link explicit machine approval records. Require reapproval for new
   protected fact IDs, areas, behavior categories, external effects, or paths.
6. During implementation, record only material discoveries and corrections.
   Stop when an entry is `reapproval-required`.
7. Decide each applicable companion surface as `updated`, `not-required`, or
   `missing`, with a fact-specific reason and evidence.
8. When architecture reasoning applies, retain a compact problem,
   alternatives, direction, authority, status, and source summary. Do not keep
   raw chat by default.
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

The target validator may check record shape, hashes, refs, range paths,
declared semantic scope, companion decisions, corrections, and evidence-grade
requirements. It does not prove domain invariants, semantic completeness, or
architecture correctness.

## Final Evidence

Report package ID, activation reason, changed facts and owners, approved and
actual semantic/path scope, material corrections, companion decisions,
architecture summary, validation, provenance quality, public claim strength,
and residual risk.
