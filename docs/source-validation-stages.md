# Staged Source Validation

Scope: AlatyrCore source tooling, not target installation or portable framework
policy. Read this procedure when preparing a pending migration note under the
[release process](release-process.md).

Prepare release evidence without claiming a future validation result:

1. Run `python3 tools/check_all.py --profile full --stage source --jobs 4
   --cache-mode timing --report tmp/source-validation.json`. This cold stage
   retains versioning, evidence-status and change-drift checks. It defers only
   checks explicitly marked `requires_release_evidence` in the manifest,
   reports their IDs and cannot produce acceptance evidence. Result reuse is
   forbidden; timing hints may affect order only.
2. Only after the command succeeds against the intended source tree, record
   its actual command, results, revision and completion time in the migration
   note. `Source validation: passed` refers to these completed source checks,
   not final release acceptance. Change only release-evidence text between
   stages; other input changes require fresh source validation.
3. Run the default cold `python3 tools/check_all.py --profile full --jobs 4
   --cache-mode timing --report tmp/final-validation.json`. It includes the
   deferred release checks and remains the complete acceptance gate. Preserve
   failed reports and do not relabel preflight results as final acceptance.

Source-stage success does not authorize commit, publication, tags or deployment.
