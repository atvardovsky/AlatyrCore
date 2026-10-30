# Session Continuity Flow

Use for compaction, resume, fork, handoff, client/model changes, context loss,
worker convergence or installed/selected-context drift.
Owner: `ALATYR-CONTINUITY-001` in `.ai/framework/session-continuity.md`.
Semantic reference: `alatyr:session-continuity@1`.

## Active Session Checkpoint

Apply the owner's Active Session Freshness gate at request/resume, phase,
material-decision, convergence, finalization and pre-mutation boundaries;
coalesce adjacent checks without polling.

```sh
python3 .ai/assistant/tools/alatyr_delegate.py session-context --target . capture --context .ai/project/contour.md --output .ai/.runtime/continuity/SESSION-context.json
python3 .ai/assistant/tools/alatyr_delegate.py session-context --target . check --baseline .ai/.runtime/continuity/SESSION-context.json
```

Use `python` on Windows and your session ID. Repeat `--context` for every
still-applicable loaded file; bootstrap is automatic. Pass a used ready plan's
target-relative `--context-plan` to bind selected content, knowledge owners,
sources and routing. Rebuild stale/incomplete plans. Expiry and empty-result
rerouting remain applicable; `current` never clears knowledge warnings.

Without write authorization, retain fingerprint/paths in memory and use
`check --expected sha256:DIGEST` with identical selectors. Capture is not reading
acknowledgement. Preserve the old baseline until reconciliation; checks alone
never rewrite canonical knowledge or authorize work.

## Prepare And Rehydrate

1. Start inspect-only. Use the packet template for task, scope, authorization,
   decisions, evidence and next action. Bind sequence/previous hash, Git,
   capability, model and projection evidence; reference history instead of
   copying it. Exclude secrets, raw chat and private reasoning.
2. Authorized packets use `.ai/.runtime/continuity/<task-id>.json`; hash canonical
   JSON excluding `integrity`. Retain baseline in `decisions` and selected paths
   in `routing.loaded_paths`.
3. For new worktrees, use available `worktree-preflight`. Follow the owner's
   Worktree Prerequisites And Active Handoffs section: explicitly configured
   Git-common source locators are optional; `publish-task --retention-review`
   retains reviewed bytes and `restore-task --task-id ID` previews exact recovery.
   Separately authorize `--write`; preserve conflicts and missing-history blockers.
4. Validate packet/digests against current branch, diff, approvals and owners.
   Reconcile changed sources, expired reviews, assumptions and worker results;
   load full models only for stale, invalid or insufficient projection evidence.
5. Re-establish newest-request action phases, reopen affected obligations and
   pass `.ai/assistant/gates/session-continuity.md`. Recovery restores no
   publish/live authority. Nonaccepted installations keep peers inspect-only.

Unknown client capability uses this portable fallback. Missing helpers need
equivalent bounded evidence or an unverified-context blocker; previously unaware
clients require one explicit recheck/restart. No full-corpus reread, lock,
writer identification or idle-session notification is implied.
