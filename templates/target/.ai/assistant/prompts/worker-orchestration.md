# Worker Orchestration Prompt

Use after parent operation/profile, changed facts, risk, authorization,
task decomposition and critical path are known. The primary assistant remains responsible
for decisions and convergence. This is the normal authoritative route;
load the full flow only for ambiguity, conflict or repair.

1. Load `.ai/assistant/assistant-capabilities.json` and only the selected
   surface record. Continue only when current evidence verifies worker
   availability and `worker_context_mode` is `isolated-explicit` or
   `inherited-measured`. Keep work local for unknown, unsupported, stale, or
   inherited-unmeasured context.
2. After successful preflight, load `.ai/assistant/task-decomposition.json`,
   `.ai/assistant/delegation-policy.json`, and
   `.ai/assistant/workers/role-catalog.json`.
3. Use `.ai/assistant/templates/worker-execution-plan.md` in a
   target-approved operation evidence path or inline completion evidence.
   Mark `READY` only when Implementation level,
   dependencies, context, acceptance, assigned proof obligations and write scope
   allow it. Strategy and global obligation acceptance remain primary-owned.
4. Prefer primary execution when packet/review overhead outweighs
   benefit. Never delegate non-delegable work.
5. Select an enabled role within its action ceiling. Bind current capability
   evidence, else use suggestion-only or sequential-primary fallback.
6. Use `.ai/assistant/templates/single-read-only-delegation-receipt.json` for
   exactly one depth-one inspect-only worker with no writes, retries, child
   proposals, or overlap. Load the full execution-tree contracts for multiple
   workers, depth two, writes, retries, child proposals, or semantic overlap.
   Resolve and enforce the same target-policy and portable context,
   raw-result, and accepted-summary word ceilings and their 12-times character
   ceilings for either evidence tier;
   missing, unresolved, or exceeded limits fail closed.
7. Dispatch through the verified native or approved external backend. A
   frozen payload measures visible prompt, bootstrap, metadata and content;
   keep stable guidance/sources before variable packet/task data;
   reserve sibling/expansion capacity and recheck before expansion. Missing
   context returns to the primary, not guesses. Native cutoffs remain unverified. A
   provider-specific worker definition is a thin binding to these
   project-owned contracts, not a new policy owner. The primary assistant owns
   branch authorization. A verified coordinator may use nested transport only
   for read-only depth-two packets inside the exact hash-bound envelope;
   otherwise workers return proposals.
8. Normalize every return through `.ai/assistant/templates/worker-result.json`
   and its human view. Measure raw and accepted-summary artifacts, bind them by
   SHA-256, and keep raw payloads lazy. For recursion, validate the branch
   envelope and create a resumable checkpoint.
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

Workers report assigned local proof evidence. They cannot change the primary
strategy, waive obligations, accept primary-owned obligations, or promote a
review pass to operation completion.

Parallelism, model identity, speed, cost and quality claims require matching
capability record and result evidence.
