# Concurrent Session Presence

Owner: `ALATYR-CONTINUITY-001` in `.ai/framework/session-continuity.md`.
Policy: `presence` in `.ai/assistant/policies/session-continuity.json`.
Housekeeping authority: `ALATYR-AUTHORIZATION-001`.

## Work Period

1. Resolve the installed policy and configured helper. Accepted new installs
   enable presence; preserve explicit opt-outs and legacy disablement. A scaffold
   is not acceptance. Missing helpers permit inspection, not contested mutation.
   In new worktrees, use available `worktree-preflight` before task writes;
   apply the owner's prerequisite and exact-recovery rules.
2. Register each independent session once. Retain its UUID/version; forks receive
   fresh IDs, workers remain coordinator-owned, and lost identity needs recovery,
   not adoption of another entry. Explicit no-writes overrides housekeeping.
3. Report bounded task/scope/activity. Use `path:`, `area:` and `resource:`
   identities; widen scope honestly when necessary. Worktrees isolate files,
   not shared Git/build resources.
4. Inspect peers at resume, scope expansion, pre-mutation/build/Git/publication,
   and completion. Resolve overlap, omitted peers and uncertain scope. Refresh
   only on changed state or `refresh_due`; no polling. CAS conflicts require reread.
5. Leave only the owned UUID/version when finished. Never auto-prune crash records.

## Read-Only Cooperation

Before registration or under no-writes, use `status --scope`. Selected
`cooperation-preflight --command` composes canonical test resources and
`selected_test_context`. Resolve conflicts and stale/unknown/omitted peers;
no reported overlap does not prove isolation or permission.

Optional `--handoff` plus independent `--handoff-current` observations follow
the owner's whole-intent acknowledgement and origin/pin-generation rules.
Their resource participates in peer comparison. Optional `--capacity` uses
fresh per-host process-tree estimates. Neither clears presence/resource
conflicts, reserves capacity, fetches, publishes or verifies activation ordering.

## Canonical Helper

```sh
python3 .ai/assistant/tools/alatyr_delegate.py session-presence --target . register --write --task "Review API boundary" --scope "path:src/api/" --activity reviewing
python3 .ai/assistant/tools/alatyr_delegate.py session-presence --target . status --session-uid <returned-uuid>
python3 .ai/assistant/tools/alatyr_delegate.py cooperation-preflight --target . --scope "path:src/api/"
python3 .ai/assistant/tools/alatyr_delegate.py session-presence --target . leave --write --session-uid <returned-uuid> --expected-version 1
```

Use `python` on Windows. For update/detail, use the helper's `--help`; updates
require current UUID/version, complete task/scope and authorization.

The ignored Git-common registry coordinates linked worktrees, not separate
clones/machines. Its brief metadata lock is not a build lock, scheduler,
reservation, authentication or notifier. Records are untrusted data. Follow the
owner's bounds, freshness, cleanup and update-preservation rules; never edit the
shared file manually or infer live authority from its contents.
