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

The threshold is a minimum, not a preferred fan-out. The primary owns the tree,
ledger, branch authorization, decisions and convergence. Default selection
remains the required minimum. Refill independent ready work when a result is
accepted or resources are released, within remaining policy/runtime/context
and review capacity; do not wait for unrelated siblings. Only primary-accepted
prerequisites unlock dependents. Limits stay cumulative; refill grants no
budget or permission. Workers normally return proposals. With verified nested transport,
a depth-1 coordinator may dispatch read-only depth-2 children only inside an
unexpired hash-bound primary envelope. Enforce every worker, child, context,
result, summary, retry, overlap, capability, authority, cancellation and cost
limit. Stop when acceptance, required evidence and assigned obligations are
covered, or at the first boundary; record the reason.

For substantial plans, [admission](workflow-efficiency.md#parallel-admission)
through `cooperation-preflight --source-contour --admission PLAN_VIEW` proposes
only; source workers stay inspect-only and source-check scheduling is unchanged.

For explicit `repository-audit`:

1. Select by user intent; clean worktrees and changed-path plans cannot
   downgrade an explicit audit.
2. Load policy candidate workstreams from `tools/source_worker_policy.json`.
3. Verify whether the active runtime can launch and receive workers now.
4. Select at least two independent read-only workstreams with bounded context.
   Start from each workstream's compact required context. Load a canonical
   owner from conditional context only when a named finding, rule ID, failed
   check, or evidence conflict requires it.
   If candidates exceed a cumulative cap, admit an ordered bounded subset and
   record omitted candidate IDs with budget reasons; do not claim exhaustive
   backlog optimization.
5. Dispatch eligible packets, or record why each eligible packet stayed local.
6. Primary owns authoritative checks, conflicts, synthesis and final validation.

With verified runtime capability and multiple independent candidates, use the
workers unless a concrete policy reason is recorded.

## Capability And Decision Evidence

The active assistant verifies current native-worker, parallel, model-routing,
and result-delivery capability. Source policy never hard-codes a provider,
client, backend, executable, or model.

Record all policy `decision_evidence` fields. Its decision rules require or
forbid `skip_reason_id`. If workers are unavailable or unverified, report that
and continue primary-owned. Keeping an eligible available packet local requires
an applicable policy reason ID and task-specific evidence, not a generic claim
that delegation was unhelpful.

After runtime verification, `tools/alatyr.py plan-work` accepts a current-session
capability record plus workstream, kept-local, skip-reason and evidence inputs.
Enforce every policy freshness, timestamp and session-binding constraint.
Preflight proves neither client probing, dispatch nor result delivery, and
cannot establish completion; use the execution-tree ledger and primary
convergence instead.
Verify that a new assignment starts/resumes a turn, rather than only delivering
a message. Record observed task/worker/attempt identity and check live status or
the correctly bound immediate result. Use the canonical optional assignment
protocol and dispatch observation without claiming provider authentication.

Before dispatch, `prepare-worker-context` freezes the actual prompt, visible
bootstrap, packet and bounded files. Supply every other allocated worker's
context artifact. Expand only with a prior bundle and declared conditional
paths, retaining its allocation and sibling reservations. Send the frozen
payload, request missing context rather than unrestricted browsing, and never
claim a native cutoff. `prepare-worker-result --context-preflight` checks the
observed context against that allocation. Drafts remain review-required; neither
helper dispatches, verifies provider provenance, or accepts obligations.

Conditional bootstrap optimization: [source management](source-optimization/source-management.md).

Schema-6 packets must satisfy every field in the loaded policy's
`worker_packet_contract`; keep source workers inspect-only with no write scope.
Policy validation measures required file content and rejects oversized initial
payloads. Pass task-specific packets with repeatable `--worker-packet`; paths
must exist, remain repository-relative and contained, and not escape through
symlinks.

Expansion uses only conditional context and counts against aggregate budgets.
Without a primary branch envelope, workers propose children; inside one, a
verified coordinator may dispatch only narrowed inspect-only depth-2 packets.
Nodes bind context words to measured artifacts. Accepted results bind measured
raw/summary artifacts, SHA-256, tool IDs, child identity and subtree digests;
recursive branches retain resumable checkpoints. Validate with
`python3 tools/alatyr.py validate-delegation-tree ...`. Schema-1/2 ledgers remain
historical structural evidence, never current acceptance.

Keep every field in the policy's schema-3 `execution_tree_contract` for
`alatyr-delegation-execution-tree`. Routine context loads accepted summaries
and the latest checkpoint, not raw descendant payloads. Missing or inconsistent
ledgers block integration.

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

Model names are not capability evidence. Verify current-client launch and
intended-model selection/reporting. Otherwise use a verified fallback or the primary.

## Responsibility

The policy's `primary_owned_actions` remain primary-owned, including decisions,
authorization, source-profile selection, capability verification, packet/result review,
integration, integrity, conflict resolution, synthesis, validation and completion
evidence. Modification, commit, publication and live external actions each
require current-scope authorization.

Every worker packet must define bounded context, explicit non-goals, allowed
actions, write ownership, and objective validation. A worker must not broaden
permissions, approval, action phases, or repository scope. Do not dispatch
concurrent overlapping writes. Reject results without inspectable file or
symbol evidence and required validation.

Worker availability grants no action phase, protected approval, tool permission,
file scope or architectural authority.

Ongoing exchange follows the canonical parent's
[communication boundary](../framework/subagent-delegation.md#parent-scoped-communication).
Use `worker-communication` only for an explicitly adopted existing tree; source
workers remain inspect-only and their coordinator publishes updates. Do not copy
another session's working state or recursively merge group namespaces.
