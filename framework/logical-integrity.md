---
alatyr_doc:
  id: framework.logical-integrity
  type: framework-rule-owner
  owns_rules:
    - ALATYR-INTEGRITY-001
  depends_on:
    - ALATYR-SOURCE-001
    - ALATYR-RISK-001
  applies_to:
    - all
---
# AI Framework Logical Integrity Review

This file defines the portable logical integrity review used by Alatyr Core.

Logical integrity review is the step where an assistant decides what fact
changed, which source owns that fact, what else must change with it, and what
evidence proves the repository is coherent afterward.

Concrete source-of-truth files, validation commands, diagrams, prompts, skills,
and checker rules belong to the project adapter.

## Goals

Logical integrity review exists to prevent assistants from:

- changing behavior while leaving docs, tests, diagrams, prompts, or gates
  stale
- updating a generated or bridge artifact as if it were the source of truth
- treating a passing script as proof that no semantic fact changed
- hiding missing context behind confident implementation
- repairing drift in a broad or inconsistent way

## Semantic Change Decision

Before editing or finalizing a change, decide whether any semantic or logical
fact changed.

Facts include:

- business or domain rule
- use case, workflow, runtime flow, or state transition
- data structure, field, relation, format, key, retention rule, or persistence
  behavior
- module boundary, dependency direction, interface, port, message, or external
  contract
- security, privacy, permission, credential, destructive-operation, live-service,
  or dependency behavior
- test expectation, validation gate, checker invariant, prompt rule, skill
  instruction, bridge rule, or documentation-sync rule
- diagram edge, actor, state, container, object relation, sequence, or generated
  artifact ownership rule

If no semantic or logical fact changed, final evidence should explain why no
companion update was required.

## Review Steps

Use this sequence when a fact may have changed:

1. State the change intent in concrete language.
2. List changed facts, not only changed files.
3. Classify each changed fact by risk using the framework risk model and the
   target adapter.
4. Identify the source of truth for each fact, using the target
   source-of-truth registry when it exists.
5. Compare code, tests, docs, diagrams, prompts, skills, bridge files, gates,
   generated artifacts, and checker rules that mention the fact.
6. Name conflicts and missing context explicitly.
7. Decide synchronization direction from the registry or owning contour.
8. Choose the smallest coherent repair set.
9. Apply required companion updates or explain why none are needed.
10. Run target validation that exists, or record manual/unresolved checks.
11. Report final evidence and residual risk.

When a target consistency map exists, replace broad surface comparison with a
bounded impact closure: start from changed fact IDs, select applicable
relationship edges, traverse dependent contracts only when they can propagate
the change, and record skipped or missing edges. The map routes review; the
human source-of-truth registry still owns ownership decisions.

For multi-workstream operations, perform local review within each workstream
and one global review over the combined repair set before completion. The
global review reconciles shared facts, canonical owners, approvals,
cross-workstream contracts, and generated artifacts.

## Source-Of-Truth Decision

When files disagree, choose the owner by contour:

- framework rule: portable AI process under `.ai/framework`
- project fact: target product, code, business, data, runtime, security, or
  operation fact under the project contour
- repository adapter fact: local assistant workflow, validation, gate, prompt,
  skill, bridge, checker, or evidence rule
- generated artifact: output whose source must be named by the adapter
- bridge file: short pointer to canonical target files

If the target adapter has a source-of-truth registry, use the registry to
resolve fact type ownership before falling back to contour-level ownership.

Do not choose the source of truth by convenience, recency, or file proximity.
If the owner is missing or unclear, report the missing adapter fact before
claiming the repository is consistent.

## Repair Direction

Repair the smallest coherent set of files that restores the accepted contract.

Typical companion updates may include:

- project source-of-truth docs or blueprint-equivalent docs
- runtime flow or use-case docs
- code and tests
- diagrams and generated visual artifacts
- prompt, skill, gate, bridge, or checker rules
- public docs or maintainer docs

Do not hide architecture, business, security, or approval changes inside
documentation-only, diagram-only, prompt-only, or generated-file-only edits.

## Evidence Format

A logical integrity review should be reportable as:

```text
Change intent: <requested or inferred change>
Changed facts: <concrete facts>
Risk class: <framework and adapter risk>
Source of truth: <owning file or missing adapter fact>
Conflicts found: <what disagreed, if anything>
Repair set: <files or artifacts updated>
Impact closure: <selected/skipped edges, levels, areas, and missing links>
Validation: <target commands or manual checks>
Approvals: <used or not required>
Residual risk: <skipped or unresolved checks>
```

The project adapter may require a stricter format.

## Rejection Criteria

Reject or revise work that:

- changes a logical fact without naming it
- treats generated, bridge, or copied text as canonical without checking its
  owner
- updates only one surface when code, docs, tests, diagrams, prompts, skills,
  gates, or bridges also own the changed fact
- weakens tests, gates, approvals, documentation-sync rules, or checker rules
  to make a change pass
- claims validation passed without target evidence
- copies another repository's facts into framework core
