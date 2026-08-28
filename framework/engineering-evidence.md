---
alatyr_doc:
  id: framework.engineering-evidence
  type: framework-rule-owner
  owns_rules:
    - ALATYR-ENGINEERING-EVIDENCE-001
  depends_on:
    - ALATYR-RISK-001
    - ALATYR-INTEGRITY-001
    - ALATYR-EVIDENCE-001
  applies_to:
    - architecture-change
    - business-change
    - code-local
    - data-change
    - security-sensitive
---
# Durable Engineering Evidence

Durable engineering evidence preserves the compact conclusions that a future
developer or assistant needs to understand a material change. It is
project-owned historical evidence, not a transcript of the assistant session
and not a replacement for canonical business, architecture, data, code, test,
or policy owners.

## Capture Decision

Before completing a material semantic, architectural, or non-obvious repair,
ask:

> Would reusable engineering knowledge be lost when this session ends?

Capture a record when one or more supported triggers apply:

- the task exposes an undocumented invariant
- a material hypothesis was rejected and avoids a plausible wrong repair
- a non-obvious side effect or dependency changed the solution
- the repair crosses multiple architecture areas or canonical owners
- a broader regression matrix is needed to protect one invariant
- backward compatibility, architecture, or public-contract reasoning affects
  the chosen solution
- a reviewer correction or implementation discovery changes the understood
  root cause or validation scope
- the result contains reusable knowledge that a fresh agent could not recover
  cheaply from canonical sources and the patch alone

Do not force a small, self-explanatory local change into a large artifact. A
small task may skip capture with one short fact-specific reason. Task size,
file count, or a successful test run alone does not decide materiality.

When the active operation exposes structured materiality evaluation, assess
every supported condition as `applicable`, `not-applicable`, or `unknown`.
Keep supporting implementation and validation events separate from the reason
capture is material. An implementation event does not become a durable-capture
trigger merely because code changed, and a large test count does not prove that
the originally reported scenario was reproduced.

Do not accept `skipped` while materiality is unknown. When one or more
conditions are applicable, skipping requires each reusable conclusion to name
an existing project-owned canonical source and matching fact type in the
source-of-truth registry. Issues, commit messages, tests, and Debug records may
support that decision but do not become canonical owners merely by being
detailed. If canonical preservation cannot be established, capture the record
or mark capture blocked with the next safe action.

## Compact Record

A durable record should normalize this chain:

```text
task -> observed failure -> affected architecture -> invariant -> hypotheses
     -> confirming/rejecting evidence -> chosen solution and rationale
     -> impact -> regression matrix -> validation -> residual uncertainty
```

Record:

- stable evidence ID, status, owner, task or issue references, and capture time
- base and result repository binding, including an explicit binding kind
- observed failure and affected project architecture areas
- the invariant, whether it was observed, proposed, accepted, or unknown, and
  its canonical owner or unresolved ownership gap
- compact confirmed, rejected, and unresolved hypotheses with evidence
- root cause, chosen solution, why it fits the invariant, and material rejected
  alternatives
- changed facts, code and companion surfaces, and knowledge-owner updates
- regression cases, each tied to the invariant or risk that justifies it
- validation results, skipped checks, and residual uncertainty
- validation evidence class for each material claim when the active operation
  exposes structured validation evidence
- links to an active change package, approval, architecture decision, or
  development-evidence pattern when applicable
- Debug session IDs when the evidence was produced under Debug Mode

The record contains decision outcomes and evidence references, not private
chain-of-thought. Do not store raw chat, prompts, credentials, secrets,
personal data, unrelated session history, complete diffs, or verbose test logs.

New schema-version-3 records link related Debug sessions bidirectionally. Every
listed Debug ID must resolve exactly once, share a task or issue reference, and
link back to the engineering-evidence ID. An empty Debug ID list is valid when
Debug Mode was not active. Schema versions 1 and 2 remain readable without
invented Debug lineage. A schema-version-3 record requires the schema-version-4
index so the reciprocal Debug projection cannot be silently omitted.

## Repository Binding

Bind a completed record to one of:

- `commit`: an exact result commit and base revision
- `pull-request`: a stable review reference plus exact base and head revisions
- `tree`: an exact Git tree object when the working result is not yet committed
- `selected-file-snapshot`: a bounded path set and deterministic digest
- `unverified`: no reproducible result binding is available

Use `unverified` honestly and report the resulting limitation. A later commit,
review, or snapshot may finalize the record without rewriting its engineering
conclusions.

Version-2 bindings distinguish `provisional` from `final` and retain every
replaced binding in `prior_bindings`. A final commit or pull-request binding
uses immutable object IDs and an ancestor-ordered base/result range. A tree
binding resolves the result as a Git tree object. Equal base and result commits
cannot support a claim that implementation surfaces changed.

A finalized selected-file snapshot describes the files at capture time, not a
permanent assertion about the current worktree. Later edits or deletion make
the snapshot not currently reproducible and should produce a warning, not
retroactively corrupt the historical record. If the recorded digest matches a
Git commit, the assistant may suggest a stronger commit binding, but rebinding
is explicit and appends the replaced binding to lineage.

## Publication Boundary

Evidence storage is target-owned. A target may keep records in its normal
repository, an internal support branch, an ignored local store, or an approved
external system. The compact index must state the selected policy and whether
records may enter external contribution patches.

For a clean upstream contribution, keep Alatyr support records outside the
upstream patch unless the upstream project accepts them. The record must still
be discoverable in the target's selected project-memory surface; an ignored
local record alone is not durable team evidence unless another approved store
retains it.

## Relationship To Other Evidence

- A change package coordinates a coherent material outcome across scope,
  approvals, companion surfaces, and provenance. A durable evidence record is
  smaller and may exist without a change package.
- Development evidence tracks repeated process friction for later AI
  infrastructure improvement. It does not replace task-specific engineering
  evidence.
- An ADR, blueprint, contract, or source-of-truth document owns accepted
  project facts. The durable record links to those owners and explains the
  historical decision; it does not become their canonical owner.
- The project-knowledge flow may propose one reusable conclusion for promotion.
  A decision owner must accept, narrow, reject, or defer it. Only an accepted
  canonical owner update plus a reviewed route entry can make the conclusion
  available as a current constraint to later tasks.

When a change package is active, link the evidence ID from the package instead
of duplicating the normalized reasoning. When a durable record reveals a new
accepted fact, update the canonical owner in the same repair set or report the
missing owner as a blocker or residual risk.

Finalizing engineering evidence does not promote it. Record the project-
knowledge candidate and disposition separately so an archive remains
historical even when its conclusion is useful.

## Finalization Gate

Before completion:

1. classify capture as `captured`, `skipped`, or `blocked`
2. for `captured`, validate the record and compact index, bind it to the task
   and repository result, finalize the binding, preserve any prior binding,
   confirm the publication boundary, and reconcile reciprocal Debug links when
   Debug Mode was active
3. for `skipped`, state a short task-specific reason
4. for `blocked`, name the missing owner, policy, authorization, revision, or
   storage surface and the next safe action
5. report the evidence ID and path, or the skip/block reason, in final evidence

Deterministic validation can check record shape, references, revision syntax,
index synchronization, and prohibited fields. It cannot prove the invariant,
root cause, solution quality, regression sufficiency, or semantic completeness.
When validation evidence is classified, local command output, CI, reviewer,
and production evidence remain separate evidence strengths. Do not summarize
local validation as CI-verified or reviewer-verified without an actual source
record from that class.

## Rejection Criteria

Reject or repair evidence that:

- consists mainly of file lists, chat excerpts, or chronological narration
- omits the task reference or repository result binding
- states an invariant or root cause without evidence or an ownership status
- lists tests without explaining the invariant or risk each regression covers
- hides a material rejected hypothesis that would prevent a future wrong fix
- claims a canonical decision without linking its project-owned authority
- includes secrets, raw reasoning, unrelated session history, or an external
  patch contrary to the target publication policy
- skips a material task without a fact-specific reason
- skips applicable materiality without proving canonical preservation for each
  applicable conclusion
- treats a commit message, issue, test, or Debug record as a canonical owner
  without source-of-truth registry evidence
- uses a reversed Git range, a symbolic name as a final immutable binding, or
  silently replaces repository-binding lineage
- treats later worktree drift as proof that finalized historical evidence was
  corrupt when it was captured
