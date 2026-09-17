# AlatyrCore Source Worker Strategy

Scope: AlatyrCore source repository only.

Canonical portable rule: `ALATYR-DELEGATION-001` in
`framework/subagent-delegation.md`.

This source-only policy does not govern an installer, host, vendor, or
dependent repository. Each host adapter owns its worker policy; this document
is passive dependency evidence outside this contour.

## Activation

Select the source profile before evaluating delegation. The provider-neutral
machine policy is `tools/source_worker_policy.json`; it does not prove current
client capability.

Small and standard tasks stay primary-owned unless a justified route says
otherwise. `large-or-resumable` work needs at least two bounded, independent,
read-only packets; otherwise record `workstream-identification-required`.
Dispatch only when expected time or review benefit exceeds preparation,
review, and integration cost. Keeping eligible work local needs a policy
reason ID and task evidence.

Two packets are an activation threshold, not a preferred fan-out. The primary
owns the tree, ledger, branch authorization, decisions, and convergence.
Read-only source workers normally return proposals. With verified nested
transport, a depth-1 coordinator may dispatch depth-2 read-only children inside
an unexpired hash-bound primary envelope. Enforce every worker, child, context,
result, summary, retry, overlap, capability, authority, cancellation, and cost
limit; stop when acceptance, required evidence, and assigned proof obligations
are covered or at the first boundary, then record its reason.

For an explicit `repository-audit`, delegation evaluation is deterministic:

1. Select the profile directly from user intent. Do not let a clean worktree or
   automatic changed-path plan downgrade the audit.
2. Load the reusable candidate workstreams from
   `tools/source_worker_policy.json`.
3. Verify whether the active runtime can launch and receive workers now.
4. Select at least two independent read-only workstreams with bounded context.
   Start from each workstream's compact required context. Load a canonical
   owner from conditional context only when a named finding, rule ID, failed
   check, or evidence conflict requires it.
   If all reusable candidates would exceed the aggregate context cap, select the
   largest valid subset and record omitted candidate IDs with budget reasons.
5. Dispatch eligible packets, or record why each eligible packet stayed local.
6. Keep authoritative checks, conflict resolution, final synthesis, and final
   validation with the primary assistant.

With verified runtime capability and multiple independent candidates, use the
workers unless a concrete policy reason is recorded.

## Capability And Decision Evidence

The active assistant verifies current native-worker, parallel, model-routing,
and result-delivery capability. Source policy never hard-codes a provider,
client, backend, executable, or model.

Record the evaluation status, runtime capability status, selected workstream
IDs, decision, reason, and `skip_reason_id`. The policy defines which decisions
require or forbid a skip reason. When workers are unavailable or unverified,
state that explicitly and continue with the primary assistant. When workers
are available but an eligible packet remains local, use one applicable policy
reason ID and task-specific evidence; a generic statement that delegation was
not useful is not sufficient.

After runtime verification, `tools/alatyr.py plan-work` accepts a provider-
neutral current-session capability record plus workstream, kept-local, skip-
reason, and evidence inputs. Capability evidence binds to the caller's opaque
session ID and verified/expiry timestamps; stale, future-dated, expired,
overlong, or cross-session evidence is rejected. This creates reviewable
preflight evidence, not proof of client probing, dispatch, or result delivery.
Completion is not accepted from preflight evidence. It is validated through the
execution-tree ledger and primary convergence record.

Every packet must carry schema version 6, its parent, depth, remaining worker
budget, unique coverage key, workstream ID, role, objective, bounded and
conditional context, maximum initial, result, and summary words, inherited
context-packet identity and delta, non-goals,
`inspect`-only action mode, no-write scope, semantic scope, changed fact IDs,
assigned proof-obligation IDs,
canonical owner references, surface references, relationship references,
overlap decision, independence evidence, and expected evidence. Policy
validation measures all required file content and rejects a built-in packet
whose initial payload exceeds its declared limit. Task-specific packets are
passed with repeatable `--worker-packet` arguments. Their bounded paths must be
repository-relative, exist inside the repository, and not escape through a
symlink. Workers may expand only through conditional context. Outside a primary
branch envelope they return child proposals for review. Inside one, a
coordinator may dispatch only a narrowed inspect-only depth-2 packet. Expansion
counts against the execution-tree aggregate context budget. Each worker node
binds its context-word count to a measured artifact. Every accepted result uses
measured raw and accepted-summary artifacts, SHA-256 values, tool IDs,
child-result identity, and a deterministic subtree digest. Recursive branches
record a resumable checkpoint. Validate accepted execution evidence with
`python3 tools/alatyr.py validate-delegation-tree ...`; schema-1 and schema-2 ledgers remain
legacy structural records and are not acceptance evidence.

Keep a schema-3 `alatyr-delegation-execution-tree` ledger. Record current
authorization and time, base revision, the canonical policy digest, the hashed capability
artifact, measured budgets, topology, overlap decisions, direct and indirect
result and proof-obligation coverage, stop or cancellation reasons, validation,
primary review, and convergence. Routine primary context loads accepted summaries and the latest
checkpoint, not descendant raw payloads. A missing or inconsistent ledger
blocks integration.

## Model Routing

Choose the least costly verified model that can complete the packet reliably:

- fast, lightweight model: bounded read-only discovery, inventories, log or
  test-output parsing, and mechanical checks
- balanced coding model: scoped implementation or review with objective
  acceptance criteria
- strongest available reasoning model: ambiguous cross-cutting analysis,
  architecture, security, semantic invariants, conflict resolution, and final
  synthesis

Model names alone are not capability evidence. Verify that the current client
can launch the worker and select or report the intended model. Otherwise use a
verified fallback or keep the work with the primary assistant.

## Responsibility

The primary assistant retains project decisions, current-scope authorization,
source-profile selection, capability verification, packet review, integration,
logical integrity review, conflict resolution, final synthesis, final
validation, and completion evidence. Modification, commit, publication, and
live external actions remain primary-owned and separately authorized.

Every worker packet must define bounded context, explicit non-goals, allowed
actions, write ownership, and objective validation. A worker must not broaden
permissions, approval, action phases, or repository scope. Do not dispatch
concurrent overlapping writes. Reject results without inspectable file or
symbol evidence and required validation.

Delegation is an execution choice, not authorization. Worker availability does
not grant a new action phase, protected approval, tool permission, file scope,
or authority to accept architectural conclusions.
