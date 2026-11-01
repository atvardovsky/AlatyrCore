# Target Input Stability

Source-tool explanation, not a second framework rule owner. The implementation
is [the coherent target view](../tools/target_adapter_validation/context.py);
the public reporting path is [the target validator](../tools/validate_target_adapter.py).
Usage and diagnostic semantics remain in the [tools reference](../tools/README.md).

## Confirmed And Unknown

The alpha.112 field report recorded a blocking `TARGET_INPUT_MUTATED` on an
approvals directory. Its timestamps moved backwards. A later explicit replay
and three acceptance runs passed. Hash equality was measured on the replay,
not on the failed run. Those observations neither prove a false positive nor
identify the original writer. The original target and process trace were not
available for this investigation.

The alpha.115 review separately observed an interrupted migration finalizer on
`.ai/assistant`: directory timestamps changed, bounded entry fingerprints did
not, and directory content was not measured. A separately requested replay
passed. No failed-run writer trace or deterministic reproduction was supplied;
the original cause remains unresolved. Neither that replay nor injected-mutation
regressions establish that the first failure was harmless or fixed. Preserve the
first failure and transaction outcome before investigating a recurrence.

The confirmed product limitation was missing directory-entry evidence. The
existing regression intentionally expected `content: not-measured`; it checked
that a timestamp change blocked validation, not whether a subsequent report
could distinguish entry changes from a metadata-only observation. Passing
tests and CI therefore did not settle the field incident's cause.

The validator's output write occurs after input finalization. The inspected
finalizer waits for its subprocesses; its support transaction does not restore
directory timestamps. This rules out neither other tool paths nor external
writers, and is not attribution for the incident.

## Repair Boundary

Directory mutations now carry a separate fingerprint of immediate child names
and `lstat` metadata: device, inode, mode, size and nanosecond modification time.
The capture does not follow child symlinks, read child contents, or recurse.
It is bounded to 1,024 entries and 64 KiB of encoded names; limits, I/O failures
and a changed directory identity during capture produce explicit incomplete
states, not a digest of a supposedly complete snapshot. Reports contain only
digests, counts and states, not entry names or raw filesystem errors.

Only first observations scan a directory; stable finalization does not rescan.
A detected mutation triggers the comparison capture. These are diagnostic
samples, not new acceptance evidence: unchanged entries do not clear a
timestamp mismatch, failed captures do not suppress it, and equal samples do
not exclude transient changes between observations. Existing file-content,
containment, schema, Git and approval checks remain applicable. There is no
automatic retry, metadata suppression, recursive freeze or writer tracing.

No framework, adapter-schema, template or migration change is required:
accepted input contracts and mutation decisions are unchanged. Only optional
diagnostic details and bounded observation work are added.

## Regression Obligations

- Forward and backward directory timestamps remain detectable; identical
  entry metadata never becomes a reason to accept the failed run.
- Creation, deletion, rename and replacement produce different fingerprints.
- Below/at/above capture limits, permission failures and in-scan mutation
  cannot produce a misleading complete or unchanged result.
- Child symlinks are not followed; diagnostics reveal neither contents nor
  external paths. Rendering performs no filesystem reads.
- The public CLI rejects an injected backward approvals-directory timestamp
  and preserves its report across a separately requested stable replay.
- Repeated full CLI validation preserves the synthetic target's paths,
  contents and relevant metadata. This checks validator non-mutation, not
  stability against arbitrary concurrent writers.

The focused suites are `tests.test_target_mutation_diagnostics`,
`tests.test_validation_context` and `tests.test_adapter_record_integration`.
They are already included in source unit routing; mutation and adapter-record
regressions also run in the existing Windows/macOS workflow steps.

## Recurrence Investigation

### Confirmed Cache Writer Boundary

A controlled source-tool reproduction identified a separate unsafe writer:
`conformance_artifacts.materialize_support_profile` could merge cached scaffold
content into an existing target. `copytree` restored older directory timestamps
even when file bytes matched. This reproduces the reported *mechanism*, not the
original alpha.112/115 incidents; their cache use and writer remain unproved.

Run-local cache materialization now requires unpublished destinations: every
artifact-owned top-level path must be absent before copying. Existing files,
directories and dangling links fail before any copy. Direct and recursive file
copies share exclusive creation: an entry arriving before a destination file
is opened makes the operation fail rather than overwrite, follow a destination
link, or copy into a peer directory. Source/artifact/destination overlap is
rejected. Fresh private fixtures retain cache reuse, while normal target
validation performs no extra work. This is not a lock against arbitrary
writers, protection against parent/path replacement after creation, or an
atomic transaction for a shared target. Failure may leave partial private
output; it is neither a successful scaffold nor an installed adapter. Do not
delete peer entries as cleanup or publish an interrupted copy.

The new regression first failed on the backwards timestamp itself. Companion
tests cover collisions, overlap and the public validator rejecting the cache
write attempt without input changes. Existing real-mutation negatives remain
blocking. No framework, schema, template or installation behavior changed.

### Recursive Copy Regression

The follow-up reproduction exposed a depth-dependent repair: top-level files
used exclusive creation, but `copytree` still used an overwriting file copier.
The earlier late-collision test exercised only the direct path. Its success
could not establish the stated recursive no-overwrite invariant.

One file writer now owns that invariant at every depth. Regression tests
introduce files, directories, links and dangling links immediately after parent
creation at three nested depths. They require an exception instead of a copied
count and preserve peer contents and entry timestamps. Positive tests compare
fresh file/directory content, mode and timestamps across direct and recursive
copies. Keep these invariant-level tests alongside the existing top-level,
overlap, backwards-timestamp and canonical input-mutation negatives; a passing
single-path test is not evidence for another writer's behavior. The replacement
copier also rejects nonregular sources before opening their streams; a FIFO
regression preserves the old copier's failure instead of introducing a hang.

### Field Attribution Still Required

Retain the first failed report, command and timing before an explicit replay.
Compare metadata and entry fingerprints independently from file hashes. Pause
known writers or use a frozen disposable copy, keeping reports outside the
target. If attribution is needed, collect filesystem/process tracing in the
affected environment; do not infer a writer from a backwards timestamp or
discard failures because subsequent runs pass.

This repair uses `hypothesis-driven` analysis: original writer, false-positive
classification and original entry stability remain unproved. Work stayed
primary-owned (`coordination-cost-exceeds-benefit`): one shared observation
primitive and its public reporting tests form a coupled local workstream.
