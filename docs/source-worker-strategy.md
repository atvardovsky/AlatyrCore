# AlatyrCore Source Worker Strategy

Scope: AlatyrCore source repository only.

Canonical portable rule: `ALATYR-DELEGATION-001` in
`framework/subagent-delegation.md`.

This source-contour policy applies when AlatyrCore itself is the active project
being inspected or changed. It does not become a portable target rule, alter a
generated target adapter, or govern a host repository merely because that
repository installs, vendors, or depends on AlatyrCore. The host project's
active adapter owns its worker policy; this document is passive dependency
evidence outside the AlatyrCore source contour.

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

For an explicit `repository-audit`, delegation evaluation is deterministic:

1. Select the profile directly from user intent. Do not let a clean worktree or
   automatic changed-path plan downgrade the audit.
2. Load the reusable candidate workstreams from
   `tools/source_worker_policy.json`.
3. Verify whether the active runtime can launch and receive workers now.
4. Select at least two independent read-only workstreams with bounded context.
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

`tools/alatyr.py plan-work` accepts a provider-neutral current-session
capability record plus workstream, kept-local, skip-reason, and concrete-reason
inputs after the active assistant performs runtime verification. Capability
evidence is bound to the caller-supplied opaque session ID, includes timezone-
aware verification and expiry timestamps, and is rejected when stale,
future-dated, expired, overlong, or bound to another session. Those inputs
create reviewable preflight evidence; they do not probe a client, launch
workers, claim past dispatch, or prove that a worker result was delivered.

Every packet must carry its workstream ID, role, objective, bounded and
conditional context, non-goals, `inspect`-only action mode, no-write scope,
independence evidence, and expected evidence. Task-specific packets are passed
with repeatable `--worker-packet` arguments. Their bounded paths must be
repository-relative, exist inside the repository, and not escape through a
symlink. Workers may expand only through the packet's conditional context or
return a request for primary review.

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
