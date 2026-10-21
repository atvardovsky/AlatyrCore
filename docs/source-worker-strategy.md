# AlatyrCore Source Worker Strategy

Scope: AlatyrCore source repository only.

Canonical portable rule: `ALATYR-DELEGATION-001` in
`framework/subagent-delegation.md`.

Outside AlatyrCore this is passive evidence; installer, host, vendor and
dependent adapters retain their own worker policies.

## Activation

Select the source profile first. `tools/source_worker_policy.json` owns
provider-neutral policy, not runtime capability.

Small/standard tasks stay primary-owned unless justified. Large work requires
the policy's independent read-only minimum, otherwise
`workstream-identification-required`. Dispatch only when benefit exceeds
coordination cost; keeping eligible work local requires a policy reason and
task evidence.

The policy threshold is not a preferred fan-out. The primary
owns the tree, ledger, branch authorization, decisions, and convergence.
Candidate inventory may exceed simultaneous capacity: explicit selected work
is planned in waves bounded by policy and verified runtime parallelism. Default
selection remains the required minimum. Total, parent, context and retry limits
remain cumulative; a wave boundary is not a new budget or permission grant.
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
   If candidates exceed a cumulative cap, admit an ordered bounded subset and
   record omitted candidate IDs with budget reasons; do not claim exhaustive
   backlog optimization.
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

After runtime verification, `tools/alatyr.py plan-work` accepts a current-session
capability record plus workstream, kept-local, skip-reason and evidence inputs.
Enforce every policy freshness, timestamp and session-binding constraint.
Preflight proves neither client probing, dispatch nor result delivery, and
cannot establish completion; use the execution-tree ledger and primary
convergence instead.

Before dispatch, `prepare-worker-context` freezes the actual prompt, visible
bootstrap, packet and bounded files. Supply every other allocated worker's
context artifact. Expand only with a prior bundle and declared conditional
paths, retaining its allocation and sibling reservations. Send the frozen
payload, request missing context rather than unrestricted browsing, and never
claim a native cutoff. `prepare-worker-result --context-preflight` checks the
observed context against that allocation. Drafts remain review-required; neither
helper dispatches, verifies provider provenance, or accepts obligations.

Schema-6 packets must satisfy the policy's complete `worker_packet_contract`:
ancestry and budgets, unique coverage/workstream identity, objective/non-goals,
bounded/conditional context and provenance, inspect-only/no-write scope,
facts/owners/surfaces/relationships, proof obligations, independence, overlap
and expected evidence. Policy validation measures required file content and
rejects initial payloads above their declared limits. Pass task-specific packets
with repeatable `--worker-packet`; paths must exist, remain repository-relative
and contained, and never escape through symlinks.

Expansion uses only conditional context and counts against aggregate budgets.
Without a primary branch envelope, workers propose children; inside one, a
verified coordinator may dispatch only narrowed inspect-only depth-2 packets.
Nodes bind context words to measured artifacts. Accepted results bind measured
raw/summary artifacts, SHA-256, tool IDs, child identity and subtree digests;
recursive branches retain resumable checkpoints. Validate with
`python3 tools/alatyr.py validate-delegation-tree ...`. Schema-1/2 ledgers remain
historical structural evidence, never current acceptance.

Keep the policy's complete schema-3 `alatyr-delegation-execution-tree` contract:
authorization/time, revision, policy/capability digests, topology, budgets,
scope/coverage, evidence/checkpoints, validation and primary convergence.
Routine context loads accepted summaries and the latest checkpoint, not raw
descendant payloads. Missing or inconsistent ledgers block integration.

The result helper's `handoff.json` is a derived node-update candidate, not a
complete node or accepted summary. `--compact` loads that view only. Review the
listed missing primary bindings and reconcile runtime packet identity before
integration. Optional `--metrics` records bounded explicit preparation, worker,
review and rework observations outside canonical result hashing. Missing is
unobserved, not zero; timings never waive a gate or establish cost savings.

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

Worker availability grants no action phase, protected approval, tool permission,
file scope or architectural authority.
