# AlatyrCore Source Worker Strategy

Scope: AlatyrCore source repository only.

Canonical portable rule: `ALATYR-DELEGATION-001` in
`framework/subagent-delegation.md`.

This policy applies only while the AlatyrCore source repository is active. It
neither becomes a portable target rule nor governs a repository that installs,
vendors, or depends on AlatyrCore. The host's active adapter owns its worker
policy; this document is passive dependency evidence outside this contour.

## Activation

Select the source task profile before evaluating delegation. The machine-
readable source policy is `tools/source_worker_policy.json`; this document
explains how the active assistant applies it. The policy is provider-neutral
and does not prove that the current client can launch workers.

For ordinary source work, first classify the task. Small and standard tasks
remain with the primary assistant unless an independently justified route says
otherwise. For `large-or-resumable` work, identify at least two bounded,
independent, read-only packets. Until those packets exist, record
`workstream-identification-required`; do not treat a broad task description as
a dispatchable packet. Use workers when the packets are likely to reduce
wall-clock time or provide materially stronger review after accounting for
preparation, review, and integration cost. Keep eligible work local only with
a policy reason ID and concrete task evidence.

The two-packet minimum is an activation threshold, not a preferred fan-out.
The primary assistant owns the complete execution tree, ledger, and every
dispatch. Source workers are depth-1 read-only auditors; they may propose
narrower follow-up packets but cannot launch them. Apply the policy limits for
parallel workers, total workers, children, aggregate context, and retries. Stop
at evidence saturation or at the first depth, budget, overlap, capability,
authority, cancellation, or cost boundary and record the corresponding
normalized stop-reason ID.

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

Runtime verification and multiple independent candidates do not make
delegation optional by silence. Use the workers unless a concrete capability,
dependency, overlap, coordination-cost, client-policy, or user-scope reason is
recorded.

## Capability And Decision Evidence

The active assistant owns runtime capability verification because only the
current client knows whether native workers, parallel execution, model routing,
and result delivery are available. Do not hard-code a provider, client,
backend, executable, or model in source policy.

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

Every packet must carry schema version 4, its parent, depth, remaining worker
budget, unique coverage key, workstream ID, role, objective, bounded and
conditional context, maximum initial and result words, non-goals,
`inspect`-only action mode, no-write scope, semantic scope, changed fact IDs,
canonical owner references, surface references, relationship references,
overlap decision, independence evidence, and expected evidence. Policy
validation measures all required file content and rejects a built-in packet
whose initial payload exceeds its declared limit. Task-specific packets are
passed with repeatable `--worker-packet` arguments. Their bounded paths must be
repository-relative, exist inside the repository, and not escape through a
symlink. Workers may expand only through conditional context or return a child
proposal for primary review. Expansion counts against the execution-tree
aggregate context budget. `max_result_words` is an instruction ceiling.
The primary must measure or conservatively estimate the returned result before
integration and reject or request a narrower result when it exceeds the packet
limit. The current source execution-tree schema does not independently prove
result word count, so it must not be presented as machine-enforced evidence.
Workers never dispatch descendants.

When delegation runs, maintain an execution-tree ledger compatible with the
source policy: schema version 1, `alatyr-delegation-execution-tree` kind,
current authorization, base revision, policy revision, capability evidence,
aggregate budget use, node and edge topology, semantic overlap decisions, stop
and cancellation reasons, delegated validation, primary review, and primary
convergence. Treat a missing or inconsistent ledger as an integration failure,
even when individual worker packets look valid.

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
