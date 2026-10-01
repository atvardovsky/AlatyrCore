# Worker Orchestration Prompt

Use this only after the parent operation, context profile, changed facts, risk,
authorization, task decomposition, and primary critical path are known. The
primary assistant remains responsible for all decisions and convergence. This
prompt is the normal authoritative route for delegated-execution. You should
load the full flow only when delegation semantics are ambiguous, conflicting,
or under repair.

1. Load `.ai/assistant/assistant-capabilities.json` and only the selected
   surface record. Continue only when current evidence verifies worker
   availability and `worker_context_mode` is `isolated-explicit` or
   `inherited-measured`. Keep work local for unknown, unsupported, stale, or
   inherited-unmeasured context.
2. After successful preflight, load `.ai/assistant/task-decomposition.json`,
   `.ai/assistant/delegation-policy.json`, and
   `.ai/assistant/workers/role-catalog.json`.
3. Instantiate `.ai/assistant/templates/worker-execution-plan.md` into a
   target-approved operation evidence path or inline completion evidence. Mark
   `READY` only when Implementation level, dependencies, context, acceptance,
   assigned proof obligations, and write scope allow it. The primary selects
   the operation strategy and retains global obligation acceptance.
4. Prefer primary execution when packet/review overhead outweighs likely
   benefit. Never delegate non-delegable work.
5. Select an enabled role whose action ceiling contains the packet action.
   Bind it through current capability evidence, else use suggestion-only or sequential-primary fallback.
6. Use `.ai/assistant/templates/single-read-only-delegation-receipt.json` for
   exactly one depth-one inspect-only worker with no writes, retries, child
   proposals, or overlap. Load the full execution-tree contracts for multiple
   workers, depth two, writes, retries, child proposals, or semantic overlap.
7. Dispatch through the verified native or approved external backend. A
   provider-specific worker definition is a thin binding to these
   project-owned contracts, not a new policy owner. The primary assistant owns
   branch authorization. A verified coordinator may use nested transport only
   for read-only depth-two packets inside the exact hash-bound envelope;
   otherwise workers return proposals.
8. Normalize every return through `.ai/assistant/templates/worker-result.json`
   and its human view. Measure raw and accepted-summary artifacts, bind them by
   SHA-256, and keep raw payloads lazy. For recursive work, validate the branch
   envelope and create a resumable branch checkpoint.
   Reject scope violations, stale baselines, unsupported claims, and missing
   validation. Retry only under policy without expanding scope or authorization.
   Require structured findings with canonical-owner, surface, evidence, and
   proof-obligation references so the primary can merge results without loading
   every raw transcript.
9. Integrate accepted evidence or changes against current repository state.
   Re-run combined validation and primary-owned logical integrity,
   authorization, approval, commit, and publish gates.
10. Stop when acceptance/evidence are covered or a depth, worker, context,
   result, primary-summary, retry, overlap, capability, envelope, checkpoint,
   validation, authority, or cost boundary is reached. Record
   the policy stop-reason ID for every branch.

A worker may return evidence for assigned local proof obligations. It must not
change the primary strategy, waive an obligation, accept a primary-owned
obligation, or turn a review pass into operation completion.

Do not claim parallelism, model identity, speed, cost, or quality unless the
selected capability record and result contain matching evidence.
