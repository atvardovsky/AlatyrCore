## Context Costs

`first_use` is bootstrap-only; `operational_entry` adds policy-selected session
presence. Scenario `end_to_end` includes explicitly activated conditional files.
Hidden client context and unobserved helper output are not measured. Word and
character counts are structural bounds, not tokenizer or billing evidence.

Broad changed-scope routing is bounded before materialization. When path-pattern
candidates exceed the profile's resolved file budget, the changed paths remain
enumerated but their content is omitted with an explicit expansion blocker.

## Ignored Runtime Artifact Store

Raw process artifacts belong in the ignored runtime store, not in model context.
`runtime-store` writes content-addressed blobs under
`.ai/.runtime/store/blobs/` and keeps only compact metadata in
`.ai/.runtime/store/index.json`. `put` requires `--write`; `index` is read-only;
`get` returns a bounded excerpt unless an exact `--output` write is explicitly
authorized.

Store a validation log or profiler report once, then keep only its digest,
summary and a retrieval handle in the task working set. The store is evidence
storage, not canonical project authority, and it never replaces tracked owners,
approvals or acceptance records.

## Bounded File Slicing

`context-slice` reads only the selected Markdown heading, Python symbol, or
line range. `list` returns offsets and word costs without content; `read`
returns the slice plus path, digest, range, and the share of the whole file.
A slice above `--max-words` fails closed instead of truncating.

For example, `tools/validate_target_adapter.py` is 8,090 lines. Slicing the
`check_change_packages` function returns 565 lines instead of the whole file;
`framework/lifecycle.md` can be read by heading instead of its full 31 KB.
Use this for large tools and owner documents where the task names the exact
function, heading, or range. Structural checks and canonical owners remain
authoritative; a slice is a bounded delivery mechanism, not a summary or an
acceptance claim.

## Read Ledger

`read-ledger` records what exact file ranges were delivered to a session and
answers whether unchanged content can be reused. Receipts bind the session,
task, path, file SHA-256, line coverage, and ledger generation. `check` returns
`reused`, `partial`, `changed`, `redeliver`, or `miss`; `record` merges
coverage; `compact` invalidates every receipt because delivery is not memory.

The ledger is session state under ignored `.ai/.runtime/reads`, not project
knowledge. It carries no authority, never spans tasks or sessions by default,
and never replaces drift, approval, or validation checks. Use it only where a
task genuinely reopens the same unchanged content: measured broad sessions can
show near-zero exact repeats, while repeat-heavy owner reads gain 5-20%.
