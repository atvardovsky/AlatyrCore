# Exact Execution Controls

Conditional details of [test-first development](test-first-development.md),
not a second policy, test runner, installation mechanism or permission source.
Load only for adopted controls or a named selection/qualification conflict.
Resource semantics remain owned by [testing guidance](testing-guidance.md).

## Target Adoption

Execution schema 3 allows each canonical command to set `selection_contract`
or `timing_qualification` to `required` or `not-required`. Omission means not
adopted. Required controls need schema-3 policy and evidence; frozen schema-2
records remain historical/legacy evidence, never proof of new controls.
Targets decide whether to adopt. Never mutate their policy automatically.

## Selection

The target runner normalizes a complete user request into a bounded
`target-test-selection-request` JSON object: schema version 1, command ID,
exact target-relative `files`, and command-scoped `cases` with `file`/`id`.
Preserve unresolved requested selectors as misses; do not drop them while
normalizing the request. Core never guesses framework-specific filter syntax.

Discovery/result JSON contains a `target-test-selection-observation`: schema
version 1, the same command ID, `discovered_files`, `executed_files`, and exact
`cases` with `file`, `id`, and observed `status` (`discovered`, `passed`,
`failed`, `skipped`, or `not-run`). Requests have at most 256 files and 4096
cases; JSON artifacts are bounded to 512 KiB. IDs are unique per file.

The evidence's `selection_evidence` binds `request: {path, sha256}` and a
non-root `observations_pointer` inside its existing digest-bound JSON result
artifact. Bind the request in `input_sha256` too. The canonical resolver
reconciles actual target files, request scope, observed identities, counts,
and existing file evidence. Missing identities, partial requested execution,
or count discrepancies cannot establish a successful requested-scope claim.
The read-only selection preflight and registered validator reuse that resolver.
Discovery itself remains a separately authorized target action.

## Timing Qualification

Required timing qualification declares an enclosing exclusive target resource.
Executed evidence's `qualification_window` binds a non-root
`observations_pointer` into its existing hash-bound JSON result artifact. The
actual observed object contains offset-aware `started_at`, `finished_at`, a comparable `clock_id`, `peer_coverage:
complete-observed-set`, and at most 64 `peer_windows`. Each peer names
`run_id`, the same timestamp/clock fields, and canonical resource claims.
Positive overlap on a conflicting resource invalidates qualification. Missing,
future, unordered or incomparable boundaries cannot establish exclusivity.
The resource resolver retains its read/read and verified namespace exceptions.
Overlapping diagnostics cannot establish isolated timing or a sole production
cause.

Targets serialize selected qualification in their own runners. Strict
cooperation preflight may refuse known conflict or uncertainty, but is never
an atomic reservation, execution service, liveness proof or protection against
an unreported session. A declared complete observed set cannot prove that no
unobserved work existed. Contaminated runs remain diagnostic; a process exit
alone cannot establish timing qualification or current incident acceptance.
The target runner must capture the whole enclosing resource-use interval, not
a convenient subwindow. Core checks the artifact's declared interval and peer
conflicts; it cannot independently prove that the runner's instrumentation is
honest or complete. Do not report this structural check as measured exclusivity.
