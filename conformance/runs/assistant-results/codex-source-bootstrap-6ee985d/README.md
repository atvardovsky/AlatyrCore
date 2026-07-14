# Codex Source-Bootstrap Baseline

This baseline records one fresh Codex CLI `0.144.4` process for the backend API
fixture against source commit `6ee985df3e6e65507cda175944b2b3ea4be630ae`.
The fixture was seed-only, so the assistant used AlatyrCore source installation
guidance rather than an installed target router.

The report passed actual-report validation and made no installation or target
validation claim. It observed 33 loaded files and approximately 26,631 words.
The CLI completion event reported:

- input tokens: `1,076,542`
- cached input tokens: `999,680`
- output tokens: `10,236`
- reasoning output tokens: `3,802`

This baseline demonstrates why source-guided conformance should not be the
default runtime path. The staged core-profile run is the comparable optimized
path. Raw JSONL was not retained, so this record includes the captured report
and completion-event measurements but not a replayable event stream.
The captured usage fields are stored in `evidence/execution-summary.json`.
