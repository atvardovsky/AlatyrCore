# Exact Execution Controls

Conditional details of [test-first development](test-first-development.md),
not a second policy, test runner, installation mechanism or permission source.
Load only for adopted controls or a named selection/qualification conflict.
Resource semantics remain owned by [testing guidance](testing-guidance.md).

## Target Adoption

Execution schemas 3 and 4 allow each canonical command to set `selection_contract`
or `timing_qualification` to `required` or `not-required`. Omission means not
adopted. Required controls need schema-3/4 policy and evidence; frozen schema-2
records remain historical/legacy evidence, never proof of new controls.
Targets decide whether to adopt. Never mutate their policy automatically.

## Harness And Case Accounting

Schema 4 optionally adds `execution.harness_inputs`: 1..64 unique exact
target-relative material input files, such as CSS, virtual runner configuration
or fixture generators. Include configuration paths in the identity too. The
union is bounded to 256 files, 1 MiB per file and 8 MiB total. Missing, escaped,
oversized or stale inputs fail closed; decompose rather than truncate.

Executed evidence binds `harness_identity: {sha256, observations_pointer}` into
the existing hash-bound JSON result artifact. The shared digest is SHA-256 of
compact ASCII JSON `["alatyr-harness-inputs-v1", current_policy_sha256,
command_id, sorted_path_digest_pairs]`. Bind every material file in
`input_sha256`; validation rechecks actual bytes and the canonical policy.
Use distinct identities for materially different harness inputs. This detects
input reuse, not whether an external runner actually evicted its caches; it is
not a complete cache key, execution proof or substitute for a layout precondition.

Optional `execution.behavioral_accounting: required` binds executed evidence's
`case_accounting: {observations_pointer}` to exactly two result partitions:
`behavioral` and `supporting`. Each has nonnegative integer `discovered`,
`executed`, `passed`, `failed`, `skipped`, and optional `not_run` (default zero).
Each partition conserves cases and their sums equal the unchanged aggregate
evidence counters. Supporting means setup, harness checks or no-op scaffolding;
those cases alone cannot establish a focused/suite/full behavioral claim.
Project owners classify cases; Core cannot infer whether an assertion is useful.
Do not relabel cases to manufacture a passing behavioral count.

Both controls require schema-4 policy and evidence. Older records do not prove
them; no historical rewrite, automatic enablement or extra bootstrap is needed.

## Source Stability

Schema 4 optionally adds `execution.source_stability: required`, with explicit
`harness_inputs` covering the material source, fixture and build inputs. Omission
or `not-required` does not adopt this control. Installing newer templates never
changes a target decision.

Capture those inputs, configuration and selected test files immediately before
and after the authorized run. Existing executed evidence binds
`input_stability: {observations_pointer}` into its digest-bound JSON result.
That object contains exactly `before` and `after` maps of exact paths to SHA-256;
both maps must cover the complete selected union, agree with each other and
match current bytes and the record's `input_sha256`. Reuse the harness limits.
Missing, changed or malformed observations invalidate this proof even if the
test process passed. Unexecuted work remains unexecuted.

The optional read-only `test-input-state` source helper captures this bounded
scope or compares it with a retained UTF-8 JSON capture using `--before`.
The authorized target runner retains/embeds its output; the helper writes no
files and starts no tests. It grants neither permission nor acceptance.
Coordinate relevant edits while a run uses those inputs; unrelated scopes can
continue. Matching endpoint snapshots do not prove OS isolation, instrumentation
honesty, completeness of declared dependencies, or absence of a change reverted
between observations. Never claim they do.

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
