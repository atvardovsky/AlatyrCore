# Source Session Presence

Scope: AlatyrCore source contour only. Canonical owners are
[session continuity](../framework/session-continuity.md#concurrent-session-presence)
and [authorization](../framework/action-authorization.md#own-presence-housekeeping).
This source route does not activate a target, dependency, or vendor adapter.

At request/phase and pre-mutation checkpoints, also compare the source session's
retained context with `python3 tools/alatyr.py session-context --target .
--source-contour check --expected sha256:DIGEST`, repeating `--context` for
loaded files. Obtain a candidate with `capture`; use `--baseline` for a saved
authorized report. This works independently of presence enablement. A changed
binding requires selective reconciliation, not a full-corpus reload.

The source policy is `tools/source_session_presence_policy.json`. By default it enables
bounded own-entry housekeeping, including inspection, unless an explicit
no-writes request, worker envelope, or host restriction prohibits it. Workers
remain read-only; their coordinator reports aggregate scope. Independent
sessions/forks register once per work period, not once per prompt.

```sh
python3 tools/alatyr.py session-presence --target . --source-contour register --write --task "Review presence contract" --scope "path:tools/session_presence_contract.py" --activity reviewing
python3 tools/alatyr.py session-presence --target . --source-contour status --session-uid <returned-uuid>
python3 tools/alatyr.py session-presence --target . --source-contour status --scope "path:tools/"
python3 tools/alatyr.py cooperation-preflight --target . --source-contour --scope "resource:git-state"
python3 tools/alatyr.py session-presence --target . --source-contour leave --write --session-uid <returned-uuid> --expected-version 1
```

Use `python` on Windows. Keep the returned UID/version in session state. Forks
get fresh UIDs; established resumes retain their own. Lost identity is uncertain,
never authority to adopt another entry. The helper requires the worktree root
and fixed source policy; source routing is explicit, never directory-name based.

Follow the [presence flow](../templates/target/.ai/assistant/flows/session-presence.flow.md)
for checkpoints, typed scope, refresh, overlap, omitted peer inspection,
completion, and targeted crash recovery, using the source command above.
Before local Git or publication activity, include `resource:git-state` in own
scope and recheck peers; this does not grant commit/push permission.

The store is inside Git's common directory, outside version control; linked
worktrees share it. There is no timer, daemon, message history, or build lock.
Source validators only inspect policy; they never register or delete sessions.
Unavailable helpers require an honest cooperation warning, not manual JSON edits.

Prospective status and cooperation preflight do not register, refresh or delete
sessions. Preflight returns `coordinate-before-work`, `unknown`, or
`no-reported-conflict`, never an exclusivity or authorization grant. When a
target testing policy is available, repeat `--command <registered-id>` to add
its declared test resources. `plan-test-resources` exposes matching
`presence_scope_refs` for reporting while those resources are in use. Namespace
isolation does not split these conservative whole-resource identities.
