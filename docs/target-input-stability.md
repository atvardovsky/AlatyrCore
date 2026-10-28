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
