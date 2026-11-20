# Context Closure After Update

Source-only rule for updates that change context-bearing surfaces. It closes
correctness, coverage, and compaction evidence without turning an update into an
unbounded optimization project.

## When It Applies

Run context closure when an update changes one or more of:

- `AGENTS.md`, `AI_ASSISTANTS.md`, bootstrap, or entry packet
- source or target context routers, profiles, catalogs, or semantic codebook
- `templates/target/.ai/assistant/context*`
- assistant capability records, especially `context_compaction`
- support state, operation index/catalog, or generated context projections
- adapter schema or template version
- or the measured first-use/profile cost moves beyond the reviewed threshold

Skip it for wording-only changes, updates with no context-bearing surface, or a
target with no installed context contract. Record the skip reason; do not claim
closure from an empty report.

## Required Evidence

Use the existing context-impact note; do not create a second receipt system.

```sh
python3 tools/alatyr.py context-closure \
  --before tmp/context-costs-before.json \
  --after tmp/context-costs-after.json \
  --capability .ai/assistant/assistant-capabilities.json --surface opencode \
  --ledger-status .ai/.runtime/reads/SESSION/status.json \
  --epoch-file .ai/.runtime/reads/SESSION/epoch.json \
  --omissions tmp/context-omissions.json \
  --output tmp/context-closure.json --write
```

The inputs are:

- before/after `context-costs` reports for the same target and profile shape
- the selected assistant capability record with complete `context_compaction`
- a current read-ledger status and epoch, or an explicit TTL fallback
- omissions with a reason for every removed mandatory path or profile
- the rollback target already required by the context-impact note

## Pass Conditions

- first-use, operational-entry, and per-profile words and characters do not
  grow beyond the threshold; lost files are rejected by the coverage checks
- `missing_paths` are empty after the update
- no mandatory path or profile disappears without a recorded omission
- the ledger is current, has no pending compaction, and is not invalid
- the epoch matches the ledger generation
- a supported post-boundary signal has an epoch, not only a TTL fallback
- `context_compaction.fallback` is `session-continuity`

## Fail Conditions

Stop the update and report it blocked when:

- mandatory coverage is lost
- a context-bearing change has no before/after measurement
- a context cost grows beyond the reviewed threshold
- the ledger still has pending compaction or an invalid epoch
- the capability claims a supported boundary signal but no epoch exists
- a capability record still contains placeholders
- the closure hides an unresolved blocker or removes evidence to pass a budget

Never refresh the baseline merely to make a regression pass. Never delete an
owner, gate, or evidence record to satisfy a size target.

## Update As A Context Boundary

A framework update may restart the host, reload instructions, compact the
session, or change the provider cache. Treat it as a boundary:

```sh
python3 tools/alatyr.py read-ledger --target . epoch \
  --session SES --epoch N --event framework-update
```

If the session is discarded, start a new ledger instead. If the host exposes no
boundary signal, declare a positive TTL fallback and record retention as
`unknown`; do not reuse delivered receipts across the update.

## Boundaries

This is a source-maintenance helper and an enforceable closure check. It is not
a new always-loaded portable policy, does not grant authority, and does not
replace lifecycle, adapter validation, or acceptance. Promoting it into the
portable framework would require a lifecycle/version update and target template
migration; until then it remains an optional source tool with a manual fallback.
