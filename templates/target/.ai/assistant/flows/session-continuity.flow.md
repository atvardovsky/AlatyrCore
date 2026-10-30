# Session Continuity Flow

Use for compaction, resume, fork, handoff, client/model changes, context loss,
subagent convergence or installed/selected-context drift.
Owner: `ALATYR-CONTINUITY-001` in `.ai/framework/session-continuity.md`.
Semantic reference: `alatyr:session-continuity@1`.

## Active Session Checkpoint

Compare retained context at entry/resume, new requests, phase changes and before
mutation batches. Coalesce adjacent checks.

```sh
python3 .ai/assistant/tools/alatyr_delegate.py session-context --target . capture --context .ai/project/contour.md --output .ai/.runtime/continuity/SESSION-context.json
python3 .ai/assistant/tools/alatyr_delegate.py session-context --target . check --baseline .ai/.runtime/continuity/SESSION-context.json
```

Use `python` on Windows and your session ID. Repeat `--context` for **every**
still-applicable loaded profile, gate, rule, skill, prompt and owner, beyond the example.
Bootstrap inputs are automatic. Capture cannot acknowledge reading.

When using a ready context plan, pass `--context-plan` with its target-relative
path. This binds selected content and knowledge owners, declared sources and
query/index/shards automatically. Reuse the saved baseline for checks; memory-only
checks repeat the plan argument. Old or incomplete plans must be rebuilt.
Check before material decisions, worker convergence and finalization too.
Changed routing requires reselection even after an empty match; source changes
reopen affected conclusions even if prose is unchanged. Review expiry is checked
with unchanged hashes. `current` does not clear knowledge warnings. Check times
stay session-local; canonical rewrites still require authorization.

Without local-write authorization retain fingerprint/paths in memory:
`check --expected sha256:DIGEST` with the same
`--context` set. Preserve old baselines; after reconciliation capture a new one.
`current` means matching declared content, without authority or acceptance.
Drift/unavailable evidence requires recovery below. Nonaccepted installs keep
peers inspect-only; authorized updaters follow lifecycle adaptation. Without a
helper, obtain equivalent bounded evidence or report context unverified before
mutation. Previously unaware clients need one explicit recheck/restart.

## Prepare

1. Use the packet template; record task/operation, profiles/areas/rules/paths,
   scope and authorization separately, decisions, checks, risks and next action.
2. Increment `packet_sequence`, binding `previous_packet_sha256` (`none` first).
3. Bind available Git evidence/canonical change-set hash, referenced capability
   and context packets by target-relative path and content SHA-256.
4. Bind analysis strategy, model and active-projection paths/digests, projection
   source-model digest/size, open obligations, reviews and invalid assumptions.
   Keep history referenced, not copied; exclude raw chat/reasoning and secrets.
5. Inspect-only storage is host-native/in-memory. Authorized persistent packets
   use `.ai/.runtime/continuity/<task-id>.json`. Hash canonical JSON excluding
   the complete `integrity` object into `integrity.packet_sha256`.
   Keep the context baseline reference/fingerprint in `decisions`; selected
   files remain in `routing.loaded_paths` for recovery.

## Rehydrate

1. Start inspect-only; load bootstrap, policy, packet and this flow.
2. Validate packet shape/digest and current branch/revisions/changed paths,
   canonical change-set hash, approvals and referenced rules. Reload only
   changed or unverifiable owners/evidence.
3. Verify projection/content/model bindings. Full model loading requires stale,
   invalid or insufficient projection evidence; reopen affected obligations.
4. Re-establish newest-request scope/action phases; never restore publish/live
   authority from packets. Reclassify changed risk/approval needs and replace
   stale advice with a verified next action.
5. Run focused validation and pass `.ai/assistant/gates/session-continuity.md`.

Missing/invalid packets require reconstruction from current durable evidence
before mutation. Unknown client capability uses this portable fallback without
native-hook claims. Unavailable Git evidence cannot establish repository
continuity. Neither recovery nor fingerprints require a full-corpus reread,
identify a writer, lock concurrent work or notify idle sessions.
