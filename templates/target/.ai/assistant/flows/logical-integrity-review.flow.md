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
   `.ai/project/source-of-truth-registry.md` and
   `.ai/project/consistency-map.json` together. Start from Git changed paths,
   current differences from `.ai/support-state.json`, explicit changed fact
   IDs, and `.ai/assistant/consistency-reverse-index.json`; select only matching
   graph shards. Confirm that every selected
   registry Fact Type points to a node with the exact same `fact_type`, then
   select applicable relationship edges and build a bounded impact closure.
   Record skipped or missing edges. When the map is disabled or incomplete,
   build a compact manual closure from the re-derived invariants and record
   unknown relationships.
6. Treat hashes and graph traversal as routing evidence, not semantic proof.
   Record newly observed relationships in
   `.ai/project/consistency/relationship-candidates.json`; do not traverse them
   as accepted until the target decision owner records that disposition.
7. Map each changed fact to target contracts:
   - business/domain rules
   - use cases or workflows
   - architecture levels or module boundaries
   - object/data contracts
   - diagrams
   - tests and validation
   - prompts, gates, skills, and bridge files
8. Compare only the selected code, docs, tests, diagrams, prompts, skills,
   bridge files, gates,
   generated artifacts, and assistant rules.
9. Choose the source of truth.
10. Repair the smallest coherent set of files that preserves the re-derived
   invariants across all related review items.
11. Run target validation that exists, including observable failure-class
    distinctions when external callers or operators depend on them.
12. For multi-workstream operations, reconcile the combined repair set in one
   global review after local workstream checks. Confirm shared fact owners,
   dependency order, approval scope, and generated artifacts agree.
12. Before completion, apply
    `.ai/assistant/gates/engineering-evidence.md`. Capture compact reusable
    engineering conclusions when triggered and authorized, or report a
    fact-specific skip or blocker. Do not turn capture alone into a change
    package.

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
Durable engineering evidence: <captured ID/path, skipped reason, or blocker>
```
