# Worker Orchestration Prompt

Use this only after the parent operation, context profile, changed facts, risk,
authorization, task decomposition, and primary critical path are known. The
primary assistant remains responsible for all decisions and convergence. This
prompt is the normal authoritative route for delegated-execution. You should
load the full flow only when delegation semantics are ambiguous, conflicting,
or under repair.

1. Load `.ai/assistant/task-decomposition.json`,
   `.ai/assistant/delegation-policy.json`,
   `.ai/assistant/workers/role-catalog.json`, and the selected capability
   record.
2. Instantiate `.ai/assistant/templates/worker-execution-plan.md` into a
   target-approved operation evidence path or inline completion evidence. Mark
   `READY` only when Implementation level, dependencies, context, acceptance,
   and write scope allow it. Assign parent, depth, coverage key, and remaining
   tree budget.
3. Prefer primary execution when packet/review overhead outweighs likely
   benefit. Never delegate non-delegable work.
4. Select an enabled role whose action ceiling contains the packet action.
   Bind it through current capability evidence, else use suggestion-only or sequential-primary fallback.
5. Dispatch through the verified native or approved external backend. A
   provider-specific worker definition is a thin binding to these
   project-owned contracts, not a new policy owner. The primary assistant owns
   every dispatch; workers may propose children but never launch or authorize.
6. Normalize every return by instantiating
   `.ai/assistant/templates/worker-result.md` into per-operation result
   evidence.
   Reject scope violations, stale baselines, unsupported claims, and missing
   validation. Retry only under policy without expanding scope or authorization.
7. Integrate accepted evidence or changes against current repository state.
   Re-run combined validation and primary-owned logical integrity,
   authorization, approval, commit, and publish gates.
8. Stop when acceptance/evidence are covered or a depth, worker, context,
   retry, overlap, capability, authority, or cost boundary is reached. Record
   the policy stop-reason ID for every branch.

Do not claim parallelism, model identity, speed, cost, or quality unless the
selected capability record and result contain matching evidence.
