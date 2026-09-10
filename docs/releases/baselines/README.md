# Source Release Checkpoints

These source-maintainer records preserve an incremental migration baseline
when a historical AlatyrCore changelog release was committed but no matching
Git tag was published. A checkpoint binds:

- the exact source commit;
- framework, adapter schema, and template versions at that commit;
- the deterministic framework contract digest;
- the reviewed migration report for that version;
- an explicit `untagged-release-checkpoint` publication status.

New schema-2 checkpoints additionally bind the nearest reviewed prior baseline
and the SHA-256 of the completed migration report. Create them from an existing
reviewed release commit with:

```sh
python3 tools/record_release_checkpoint.py \
  --version <VERSION> \
  --source-commit <COMMIT> \
  --write
```

The helper rejects incomplete reports, version mismatches, non-ancestor
commits, and non-empty `Unreleased` sections. Schema-1 records remain supported
for historical compatibility.

`tools/check_release_drift.py --mode release` validates every selected
checkpoint against Git history and its migration report before using it. A
real reachable `v<VERSION>` tag takes precedence over a checkpoint for the
same version.

A checkpoint is release evidence, not publication evidence. Do not create one
for an invented state, a non-ancestor commit, or a working tree that was never
reviewed as the named version.
