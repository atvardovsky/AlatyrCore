# Worker Orchestration Prompt

Use this prompt only after the parent operation, context profile, changed
facts, risk, current-scope authorization, task decomposition, and primary
critical path are known.
The primary assistant remains responsible for all decisions and convergence.

1. Load `.ai/assistant/task-decomposition.json`,
   `.ai/assistant/delegation-policy.json`,
   `.ai/assistant/workers/role-catalog.json`, and only the selected assistant
   capability record.
2. Create or update `.ai/assistant/templates/worker-execution-plan.md`. Mark a
   task `READY` only when its implementation level permits worker execution,
   dependencies are complete, its context and acceptance criteria are bounded,
   and its write scope is disjoint.
3. Prefer primary execution when packet and review overhead outweigh likely
   benefit. Never delegate non-delegable work.
4. Select an enabled role whose action ceiling contains the packet action.
   Bind it through current capability evidence. If no supported route exists,
   use the recorded suggestion-only or sequential-primary fallback.
5. Dispatch the task packet through the verified native or approved external
   backend. A provider-specific worker definition is a thin binding to these
   project-owned contracts, not a new policy owner.
6. Normalize every return with `.ai/assistant/templates/worker-result.md`.
   Reject scope violations, stale baselines, unsupported claims, and missing
   validation. Retry only under the target retry policy without expanding
   scope or authorization.
7. Integrate accepted evidence or changes against current repository state.
   Re-run combined validation and perform primary-owned logical integrity,
   authorization, approval, commit, and publish gates.

Do not claim parallelism, model identity, speed, cost, or quality unless the
selected capability record and result contain matching evidence.
