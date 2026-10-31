# Optional Lifecycle Checkpoints

Load only when the project explicitly adopts lifecycle hooks or needs to review
their behavior. Canonical rules remain in `.ai/framework/task-state-delivery.md`,
`.ai/framework/action-authorization.md` and `.ai/framework/session-continuity.md`.

1. Inspect the current client, existing hook definitions, trust policy and source
   locator. Ask for adoption approval; preserve disabled/absent policy by default.
2. Review `.ai/assistant/policies/lifecycle-hooks.json`. Begin observe-only and
   unverified. Never auto-trust, install a plugin or change global client settings.
3. Exercise harmless native event/denial/cancellation/timeout fixtures before
   recording exact client evidence. Unknown coverage means procedural fallback,
   not an enforcement claim. Recheck after client or definition changes.
4. Select hook delivery only for an existing registered task; small settled work
   keeps its ordinary lightweight path. At a new request/resume, review the task
   and newest authorized phases. Resume never clears interruption/end boundaries. Capture
   current context including the lifecycle policy, canonical active-task index,
   selected model/projection and applicable owners. Policy edits require renewed
   review and capture. Explicitly bind the current request via the portable
   delegate's `lifecycle-checkpoint` operation. The binding grants no authority.
5. Before mutation, reconcile changed/expired selected context and check current
   approval, scope and permissions. After changes, review documentation and
   companion surfaces before rebinding. Use selective mutating-tool hooks only.
6. Before completion, inspect unresolved original outcomes and independent ready
   duties. Bounded reminders do not execute work or replace canonical acceptance.
   A blocker, pause, interruption, completed scope or missing authority wins.
7. Report configured/adopted/exercised/intercepted states separately. Keep native
   errors, missing coverage and procedural checks visible. Never infer success
   from a configuration file or validator result alone.

Runtime session state stays ignored under `.ai/.runtime/lifecycle-hooks/` and
contains no conversation, approval record or duplicate project task inventory.
