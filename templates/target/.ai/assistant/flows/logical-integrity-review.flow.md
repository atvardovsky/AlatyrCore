# Logical Integrity Review Flow

## Purpose

Tell an assistant how to reason about logical integrity before using target
validation as evidence.

This flow adapts `.ai/framework/logical-integrity.md` to `{PROJECT_NAME}`.

## Steps

1. Apply the Semantic Change Decision Gate.
2. List changed facts in concrete language.
3. Resolve each changed fact's stable ID and canonical owner from
   `.ai/project/source-of-truth-registry.md`.
4. Re-derive testable scope, identity, ownership, lifecycle, persistence,
   dependency, caller, and external-boundary invariants from target evidence.
   If the task starts from multiple review comments or defects, cluster them
   by fact and contract before choosing local repairs.
5. When the `consistency-map` module is enabled, use
   `.ai/project/consistency-map.json` to select applicable relationship edges
   and build a bounded impact closure. Record skipped or missing edges. When
   the map is disabled or incomplete, build a compact manual closure from the
   re-derived invariants and record unknown relationships.
6. Map each changed fact to target contracts:
   - business/domain rules
   - use cases or workflows
   - architecture levels or module boundaries
   - object/data contracts
   - diagrams
   - tests and validation
   - prompts, gates, skills, and bridge files
7. Compare only the selected code, docs, tests, diagrams, prompts, skills,
   bridge files, gates,
   generated artifacts, and assistant rules.
8. Choose the source of truth.
9. Repair the smallest coherent set of files that preserves the re-derived
   invariants across all related review items.
10. Run target validation that exists, including observable failure-class
    distinctions when external callers or operators depend on them.
11. For multi-workstream operations, reconcile the combined repair set in one
   global review after local workstream checks. Confirm shared fact owners,
   dependency order, approval scope, and generated artifacts agree.

## Explanation Format

```text
Logical issue: <short category>
Changed fact: <what changed>
Re-derived invariants: <testable scope, identity, ownership, lifecycle, and dependency statements>
Review-item reconciliation: <clusters, shared contracts, and combined repair decision>
Expected contract: <which target source says otherwise>
Conflict: <what disagrees with what>
Source of truth: <code/docs/proposal/manifest and why>
Impact closure: <selected/skipped edges, levels, areas, and missing links>
External failure distinction: <typed/result/status/other contract or not applicable>
Repair: <files or behavior to change>
Gate: <target validation or manual review>
Workstream convergence: <global result or not applicable>
```
