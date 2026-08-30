# Subagent Delegation Flow

Use this optional overlay in `{PROJECT_NAME}` only when the
`subagent-delegation` module is enabled and the selected operation has a
bounded delegation candidate.

Selected task-scale overlay: `delegated-execution`

## Target Sources

- Portable rule: `.ai/framework/subagent-delegation.md`
- Target policy: `.ai/assistant/delegation-policy.json`
- Role catalog: `.ai/assistant/workers/role-catalog.json`
- Orchestration prompt: `.ai/assistant/prompts/worker-orchestration.md`
- Capability index: `.ai/assistant/assistant-capabilities.json`
- Selected surface capability:
  `.ai/assistant/assistant-capabilities/{SELECTED_ASSISTANT_SURFACE}.json`
- Packet template: `.ai/assistant/templates/subagent-task-packet.md`
- Execution-plan template:
  `.ai/assistant/templates/worker-execution-plan.md`
- Result template: `.ai/assistant/templates/worker-result.md`
- Parent operation or large-task packet: `{PARENT_OPERATION_OR_PACKET}`
- Target validation: `{TARGET_VALIDATION}`

## Activation Gate

1. Select the parent operation, task profile, changed facts, risk, source-of-
   truth owners, allowed actions, and primary critical-path next action first.
   Record the parent's current logical scope and authorized phases. A delegated
   packet can narrow but never broaden them.
2. Respect request preference `auto`, `allow`, `forbid`, or
   `require-supported`. `require-supported` still does not bypass capability,
   permission, approval, or safety gates.
3. Confirm the candidate is independently useful, non-blocking, locally
   verifiable, and disjoint from concurrent writes and semantic ownership.
4. Skip delegation when preparation, coordination, or review is likely to cost
   more than primary execution.
5. Keep semantic, architecture, security, migration, approval, external-
   effect, and final-convergence work with the primary assistant.
6. Read the selected surface `surface_state`. Proceed only when the state is
   selected for the target, not unsupported, and backed by current evidence.
   Unknown, stale, expired, or unverified state falls back to primary
   execution or explicit user review.

## Capability And Role Selection

1. Load the target policy and capability index, then only the current
   assistant-surface record.
2. Select the surface's verified dispatch backend: `native`, `external`,
   `suggestion-only`, or `unsupported`. An external backend must reference an
   approved target AI-infrastructure dispatcher with provenance, permissions,
   privacy, approval, and failure behavior.
3. Confirm exact client/runtime, explicit or automatic delegation, project
   worker definitions, tool restrictions, write isolation, background/nested
   behavior, model override, parallelism, actual-model evidence, client
   version, verification, expiry, permissions, and target role binding.
4. Select `fast-focused-worker` only for small, focused, reversible, context-
   bounded work with objective local validation.
5. If the requested model is unavailable, unsupported, unknown, expired,
   rate-limited, or not selectable by the client, apply the recorded fallback.
   Never report a model as used without evidence.

## Task Graph And Readiness

1. Create or update
   `.ai/assistant/templates/worker-execution-plan.md` before dispatch.
2. Use `PLANNED`, `BLOCKED`, `READY`, `RUNNING`, `REVIEW_REQUIRED`, `DONE`,
   `FAILED`, or `CANCELLED`. Only the primary assistant marks readiness.
3. Reject dependency cycles and concurrent overlapping writes. Keep shared
   semantic owners in a primary-owned convergence task.
4. Mark a task `READY` only after dependencies, context, scope, role,
   acceptance, validation, capability, and authorization are resolved.

## Packet And Dispatch

1. Create one packet per delegate from
   `.ai/assistant/templates/subagent-task-packet.md`.
2. Include only required context and name excluded context, files, actions,
   tools, dependencies, acceptance criteria, validation, and return format.
3. Keep the primary agent on the immediate critical path. Dispatch only
   independent sidecars or workstreams that materially reduce wall-clock time.
4. Use parallel dispatch only for disjoint write scopes. Stop a packet when
   risk, ambiguity, permissions, dependencies, or scope expand.
5. Provider-native worker definitions are thin target bindings. Generate or
   update them only for a verified supported surface and record their paths in
   that surface's capability record.

## Result Review And Convergence

1. Normalize the return through
   `.ai/assistant/templates/worker-result.md`; record actual surface, role,
   model or unverified status, base revision, files touched, tools used,
   validation, findings, boundary evidence, and residual risk.
2. Reject output outside packet scope or output that changed a prohibited
   fact, action, permission, or surface.
3. Review the result against current repository state; do not assume the
   delegate's fork, context, or baseline is current.
4. Run or repeat target validation required by combined risk.
5. Reconcile changed facts, approvals, companion surfaces, and workstreams in
   the primary operation or large-task packet.
6. The primary assistant performs final logical integrity review and reports
   completion. Delegate-local success is not final success. The primary
   rechecks the newest user instruction before integrating writes, committing,
   publishing, or performing a live external action.
7. Retry only target-declared transient or locally repairable failures. Reject
   scope violations, return contradictions to the primary, and revalidate
   stale results against current repository state.

## Final Evidence

Report:

- activation decision and expected benefit
- packets dispatched or skipped and why
- assistant surface, selected role, requested model, actual model or
  unverified status, and capability freshness
- context, actions, tools, write scope, and isolation
- delegate validation and primary review result
- fallback, rejected output, rework, and residual risk
- measured latency or cost only when comparable evidence was captured

## Rejection Criteria

Reject or revise delegation that overlaps writes, delegates unresolved project
decisions, broadens permissions or approval, accepts unvalidated output,
silently substitutes models, or skips primary convergence.
