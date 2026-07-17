# AI Infrastructure Recommendations

This file defines how an installed Alatyr adapter recommends new AI
infrastructure or changes to existing skills, prompts, gates, checkers, flows,
tools, MCP configurations, bridges, wrappers, and templates.

It composes `ALATYR-CONTEXT-001`, `ALATYR-ADAPTER-001`,
`ALATYR-APPROVAL-001`, `ALATYR-SAFETY-001`, `ALATYR-SAFETY-002`, and
`ALATYR-EVIDENCE-001`. Project facts remain owned by the project contour. The
recommendation, AI item, router entry, and adaptation record are assistant-
contour surfaces.

## Purpose

Inventory says what exists. Adaptation says how an accepted item is reviewed
or integrated. Recommendation fills the decision gap between them: determine
whether recurring project evidence justifies adding, improving, consolidating,
replacing, retiring, or keeping an AI infrastructure item.

Recommendations are read-only decision evidence by default. They do not grant
permission to fetch remote sources, install packages, execute tools, change
permissions, edit canonical files, or activate an item.

## Target Optimization Boundary

This process optimizes development work in the installed target repository.
Target requests, corrections, review findings, rework, and cost evidence may
justify changes to target-owned skills, prompts, gates, checkers, flows,
routers, bridges, wrappers, tools, or templates.

Target evidence must not directly recommend or edit the installed
`.ai/framework` baseline, AlatyrCore source, or portable rule IDs. A suspected
framework defect is a separate unresolved escalation that requires an explicit
framework-maintenance operation. Do not generalize one target's observations
into portable framework policy.

## Recommendation Triggers

Run recommendation when the programmer asks for suggestions, or when bounded
task evidence reveals one of these conditions:

- repeated work that follows the same specialized reasoning or output shape
- recurring review, consistency, validation, or documentation failures
- a deterministic invariant that is repeatedly checked manually
- a protected decision that lacks a clear human approval gate
- repeated broad context loading that a narrow item could avoid
- an existing item that is stale, duplicated, conflicting, unused,
  permission-heavy, expensive, or ineffective for its declared purpose
- an unsupported assistant surface for an otherwise accepted capability
- a maturity, adapter-recheck, effectiveness, or large-task checkpoint gap

Do not interrupt unrelated work with speculative suggestions. Record at most a
small bounded set of candidates tied to observed evidence, then leave weak
candidates unresolved.

## Evidence Boundary

Use the smallest matching project area and canonical owner. Suitable evidence
may include:

- project contour and source-of-truth registry entries
- accepted architecture, business, data, security, validation, or operating
  constraints
- repeated tasks, review findings, incidents, rework, skipped checks, or
  unresolved consistency gaps
- current AI infrastructure inventory, router entries, adaptation records,
  validation results, and supported assistant surfaces
- measured context, duration, rework, or effectiveness evidence when available

Project evidence describes the need, constraints, and expected outcome. It
does not move assistant workflow mechanics or item ownership into the project
contour. Missing or anecdotal evidence must be identified as such.

## Development Pattern Evidence

A target may keep a compact project-contour development evidence index so
recommendations can compare recurring work across tasks without loading chat
history or every historical record. The target manifest should identify the
index, its owner, review date, and retention policy.

Each pattern should record:

- stable pattern ID and normalized category
- bounded project area and canonical owner
- normalized problem statement, not raw chat or prompt content
- occurrence count, first/last observation, and evidence quality
- bounded references to operations, commits, issues, reviews, incidents,
  validation, rework, or effectiveness evidence
- observed outcome signals and affected existing AI infrastructure item IDs
- active, resolved, deferred, or unresolved status

Never store secrets, credentials, personal data, or complete conversation
transcripts in the index. Keep only the minimum normalized signal and target-
permitted evidence references. Apply the target retention policy and keep the
reference set bounded.

Routine successful one-off work should not create an entry. Capture a signal
only when the same friction has independent evidence, when a current task
confirms an existing pattern, or when one high-impact failure justifies review.
A read-only task may report a capture candidate but must not update the index.

Load the compact index only for pattern capture, recommendation, adapter
recheck, or explicit effectiveness review. During recommendation, inspect the
index first and load only evidence referenced by candidate patterns.

## Recommendation Kinds

Classify each candidate as one of:

- `add-new`: no current item covers a recurring, evidenced capability gap
- `improve-existing`: retain an item but change its triggers, context,
  instructions, gates, permissions, validation, output, or assistant coverage
- `consolidate`: combine overlapping items under one canonical contract
- `replace`: an existing item cannot meet the target contract safely or
  economically
- `retire`: an item is unused, superseded, unsafe, or maintenance-only cost
- `keep`: evidence supports the current item without material change
- `unresolved`: ownership, recurrence, outcome, cost, or validation evidence is
  insufficient

Review existing items before recommending `add-new`. Prefer improving or
consolidating a target-owned item when that produces the same outcome with
less context, maintenance, permission, and compatibility cost.

## Item-Type Selection

Choose the narrowest mechanism that addresses the evidenced problem:

- skill: recurring specialized reasoning or domain workflow
- prompt or template: stable request, response, or evidence shape
- gate: a decision that requires explicit human or policy approval
- checker: a deterministic invariant that can be validated mechanically
- flow or checklist: a recurring ordered process without new execution power
- tool or MCP configuration: a capability unavailable through repository
  context, only after permission and execution review
- bridge or wrapper: assistant-specific discovery or compatibility routing

Do not use a prompt for a deterministic rule that should be a checker. Do not
use a tool when a bounded repository workflow is sufficient. Do not create a
skill for a one-off task.

## Cost And Quality Gate

A recommendation is actionable only when it records:

- observed problem and evidence source
- recurrence or trigger frequency, or an explicit high-impact exception
- existing coverage, overlap, and why `keep` is insufficient
- expected quality effect and a measurable acceptance criterion
- expected context-load effect and activation scope
- implementation and ongoing maintenance cost
- permissions, safety, dependency, and assistant-compatibility impact
- validation, rollback or retirement path, and residual risk

Prefer a candidate only when expected quality, consistency, or safety value
justifies its context, implementation, and maintenance cost. Do not invent
percentages or token savings without measurements. Qualitative estimates must
be labeled as estimates.

## Existing-Item Review

For `improve-existing`, `consolidate`, `replace`, `retire`, or `keep`:

1. Select the current router item ID and canonical source.
2. Confirm its declared purpose, activation triggers, project-contour scope,
   permissions, gates, validation, output contract, and assistant surfaces.
3. Compare observed outcomes with the declared contract.
4. Identify stale assumptions, unnecessary context, missing gates, weak output
   evidence, permission excess, duplicated policy, or assistant drift.
5. Propose the smallest coherent contract change and its validation.
6. Preserve the current item until a separately approved adaptation or removal
   operation completes.

## Recommendation Process

1. Select the `recommend` AI infrastructure route and bounded project area.
2. Inspect the compact development evidence index when the target provides it,
   then load only candidate pattern references.
3. Load a current inventory or inspect only relevant router-declared items.
4. Read the project-contour owner for the observed need and record missing
   owner evidence.
5. Cluster evidence by recurring problem or target outcome.
6. Evaluate current items before proposing new ones.
7. Select the narrowest recommendation kind and item type.
8. Apply the cost and quality gate and reject speculative candidates.
9. Record ranked, independent candidates without changing target files.
10. Route an accepted candidate to the existing adaptation,
   gate/checker-change, tool/MCP-change, or bridge/wrapper-change flow.
11. Require normal source-access, prompt-injection, permission, approval, and
    validation handling during that later operation.

## Evidence

Report for each candidate:

```text
Recommendation ID: <stable target-owned ID>
Kind: <add-new/improve-existing/consolidate/replace/retire/keep/unresolved>
Project area and owner: <bounded contour evidence>
Problem and evidence: <observed need, recurrence, and evidence quality>
Development pattern IDs: <target pattern IDs or none>
Existing item IDs: <IDs or none>
Proposed item type: <skill/prompt/gate/checker/flow/tool/MCP/bridge/wrapper/template>
Proposed contract change: <purpose, triggers, context, permissions, gates, validation, output>
Expected quality effect: <measured or labeled estimate>
Expected context and maintenance cost: <measured or labeled estimate>
Acceptance criteria: <observable result>
Safety and approval: <risks and later approval needs>
Status and next operation: <proposed/deferred/rejected/unresolved and route>
```

## Rejection Criteria

Reject, defer, or mark unresolved a recommendation that:

- has no project-contour evidence or target-owned problem statement
- recommends a new item without checking current inventory and overlap
- treats anecdotal preference as measured quality or cost improvement
- duplicates canonical framework or project policy in a skill or prompt
- proposes broader permissions, remote access, dependencies, or execution
  without identifying the protected follow-up route
- fetches, installs, edits, removes, or activates infrastructure during a
  read-only recommendation
- changes `.ai/framework`, AlatyrCore source, or portable rules from target
  development evidence
- records raw conversations, secrets, credentials, or personal data as pattern
  evidence
- moves assistant workflow ownership into the project contour
- cannot name acceptance criteria, maintenance ownership, or residual risk
