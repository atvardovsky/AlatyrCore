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

## Bounded Delivery Review

For uncertain, costly or repeatedly rejected work, use the existing request
checkpoint with a schema-2 request brief. `delivery_control: null` retains the
ordinary path; schema 1 stays readable. An adopted object names original
`pilot_outcome_ids`, an exact `validation_history` path, `max_expensive_runs`
(1..32) and `max_validation_seconds` (1..86400). No new bootstrap, runner or
automatic adoption is implied. Keep outcomes small enough to demonstrate a
real representative slice; do not bundle an entire subsystem into its pilot.

Pilot proofs must be required and passed before modifying non-pilot outcomes
or starting broad validation. Derive the oracle from the source request and a
rejected substitute, not the implementation. For visual work inspect actual
content and relevant states, not just wrapper geometry or matching controls.
Source review, browser results and human acceptance remain different evidence.

The history is bounded JSON: `schema_version: 1`, exact `request_id`, `task_id`
and at most 32 ordered `attempts`. Each attempt records `evidence_ref`, exact
`result` (`passed`, `failed`, `interrupted`, `expected-red`), `scope` (`focused`
or `broad`), nonnegative integer `duration_seconds`, and nullable
`expected_red_proof_id`. Expected RED needs a passed required proof referencing
that attempt; syntax, fixture and infrastructure failures are not expected RED.
Retain every attempt for this change, including interrupted runs. Do not reset
history, budgets or incident identity to evade reassessment. Overflow stops
execution for reviewed decomposition, never silent truncation.

Before each test invocation, pass a work/inspect action with `validation`:
`command_id`, `scope`, positive integer `estimated_seconds`, and nullable
`diagnosis_proof_id` and `independent_review_proof_id`. One unexpected failure
requires a passed required diagnosis proof linked to the latest failure. Two
require a distinct passed required independent-review proof too. Three stop
broad execution until a later passed focused diagnostic is linked by both proofs.
Focused diagnostics still require review and remaining budget.
The estimate plus all recorded duration must fit the time budget; every prior
broad attempt counts against the expensive-run budget, regardless of result.
After correction, rerun affected cases and dependencies, not a matrix merely
to obtain one prettier green report. Completion cannot hide a non-passing last
attempt. Preserve canonical required coverage and timing; budgets waive no gate.

Read-only `lifecycle-checkpoint review` evaluates these declared relationships.
Retain the brief and history in the lifecycle context baseline; changes require
reconciliation and a fresh binding. The helper does not run tests, authenticate
reviewers, measure duration, infer arbitrary shell commands or discover omitted
runs. Record actual receipts and independently review history completeness,
causality, estimates and original-request fidelity. A procedural success is not
native interception, execution permission or semantic acceptance.
Use [outcome qualification](task-state-delivery.md#outcome-qualification) when
backend/topology, representative volume, omitted surfaces or unreached assertions
can make a green suite narrower than the requested result. A test correctly
describing missing evidence does not establish that the evidence gap is repaired.

### Delivery Efficiency

For costly/repeated work, use the conditional
[delivery-efficiency contract](test-delivery-efficiency.md). It reuses the same
request/history and review entry point; null controls add no reads or bootstrap.

## Current And Historical Evidence

Schema 4 optionally selects `historical_evidence_records` as at most 64 exact
`{path, sha256}` bindings, unique and disjoint from current `evidence_records`.
The validator verifies retained bytes, not compatibility with today's policy,
source, commands or suite inventory. History supplies no current acceptance.
Existing current evidence still receives every freshness and behavior check.
Missing or changed history remains a finding; do not rehash it to erase a failure.

At task transition or update, review the selected task, original run and retained
repair obligations before proposing a move from current to history. Preserve
failures and their original policy/results. Never automatically archive active
or unresolved obligations, disable a gate, rewrite old evidence or migrate a
schema-2/3 policy merely to make validation green. Target owners approve adoption.

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
