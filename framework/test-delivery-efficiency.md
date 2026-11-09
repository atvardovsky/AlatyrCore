# Delivery Efficiency

Conditional detail of [exact execution controls](test-execution-selection.md),
not a new policy owner, scheduler, runner or permission source.

For costly, uncertain or recurring work, propose explicit target adoption; never
enable controls during upgrade. Keep one request/model/history, original outcome
inventory and smallest representative end-to-end slice. Challenge unnecessary
prerequisites. Preflight runner selection, fixture inputs, actual backend and
producer-to-consumer wiring before expensive qualification. Fixture/syntax failures
are not expected RED. Useful progress closes an obligation or resolves a named
uncertainty, not merely a larger test count, plan version or refreshed timestamp.

Optional `delivery_control.execution_review` is null or an exact object:
`max_task_seconds` (1..604800), `max_no_progress_seconds` (1..86400), and
`max_observation_age_seconds` (1..3600). It requires history schema 2; schemas 1
and absent/null adoption retain their existing path. Time exhaustion or stale
observations request reassessment before mutation, completion or validation;
read-only investigation/answers remain possible. Budgets never grant authority,
stop a running process, waive proofs or turn unfinished work into completion.

History schema 2 retains all schema-1 fields and adds `previous` and `progress`.
`previous` is null only for an empty initial snapshot, otherwise a separate
immutable `{path, sha256}` preceding snapshot. Preserve its exact attempt prefix
and task start; timestamps cannot regress. Verification covers this one bound
predecessor, not an authenticated or exhaustively traversed archive. Never reset
history/identity to evade limits. Retain old schema-1 evidence unchanged; adopt
the new lane by retaining exact legacy attempt rows as the predecessor prefix;
only appended runs require receipts. Legacy rows stay explicitly unverified by
receipt checks and still count toward existing run/time/failure budgets.
The existing lifecycle binding retains the last history digest: rebinding the
same request must retain that snapshot, not select an arbitrary empty predecessor.
Stateless review reports unanchored continuity and cannot approve schema-2
validation/mutation/completion; use a bound procedural/native checkpoint.
After resume, retain original receipt IDs/bytes and cumulative attempts through
the last-bound predecessor; only newly appended receipts use the new request ID.

`progress` has offset-aware `started_at <= last_progress_at <= observed_at`,
an exact `phase` (`investigation`, `implementation`, `validation`, `coordination`,
`infrastructure-wait`, `approval-wait`), bound `evidence: {path, sha256}` and
1..32 existing `obligation_ids`. Advancing declared progress requires different
evidence content, not a new path/alias for the same bytes.
Future observations or observation age above the adopted ceiling need review.
These are declared timestamps, not executor active time or proof of useful work;
independently review meaning, dependency necessity and original-request coverage.

Each new schema-2 attempt adds `command_id` and `receipt: {path, sha256}`. A receipt
is schema 1, kind `alatyr-delivery-run-receipt`, with exact request/task/command
IDs, offset-aware `started_at`/`finished_at`, `result` (`passed`, `failed`,
`interrupted`), `exit_code`, 1..32 literal `input_sha256` entries and bound
`result_artifact`. Passed means exit 0; failed means exit 1..255; interrupted
requires null. Attempt duration equals the rounded-up receipt window (0..86400s),
and `evidence_ref` selects its result artifact. Expected RED maps to a failed
receipt and still needs the existing required linked proof. Duplicate receipts,
changed bytes and out-of-window runs fail. History, predecessor, progress and
receipt metadata are each bounded to 64 KiB; outputs retain 4 MiB/file and share
the selected target's 16 MiB aggregate ceiling with metadata and cached inputs.
Bind every selected input in lifecycle
context. Missing/changed bytes require reconciliation, not fabricated receipts.
Ordinary read-only review returns delivery diagnostics for recovery. Bound
execution still requires complete baseline freshness. Delivery-only inspection
may omit failed receipt inputs while
rechecking every other retained owner, task binding, policy and authorization
boundary. Knowledge-aware baselines keep their complete closure. Ordinary review
remains available to diagnose and then reconcile a binding; no exemption permits
validation, mutation, completion or automatic continuation.

Receipts account for retained runs; they do not authenticate execution, prove
history completeness or establish current test acceptance. Historical input
hashes are not compared with today's repaired source and cannot qualify reuse.
Use canonical current test evidence for its exact policy, selection, material
inputs, configuration, fixtures/environment, resources and proof boundary.
One equivalent coverage execution may supply its assertions too; choose a wrapper
or its children only with actual child results. Skipped/blocked children remain
unverified. Never skip required baselines, cold acceptance or fresh environment
checks. No automatic execution cache or universal scheduler is introduced.

Keep logical commits distinct from small authorized release batches. Batch only
completed validated scopes of the same request, verify combined effects and
retain environment order, rollback boundaries, explicit per-scope instructions
and separate commit/publish/live authority. Run independent work concurrently
only within verified file/resource isolation and a combined CPU/RAM/worker
budget. A busy publication resource must not freeze unrelated safe local work.
Reuse warm owned artifacts only with matching build inputs and configuration;
different environments do not automatically share an equivalent image.
Keep the primary on the critical integration path; workers own complete bounded
deliverables, not duplicated discovery. Reassess at phase boundaries or failed
experiments, not every command. Measure delivery, rework, coordination and wait
separately; agent counts or growing records do not demonstrate faster completion.
