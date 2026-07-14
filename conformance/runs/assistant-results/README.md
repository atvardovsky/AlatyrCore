# Assistant Result Reports

Place actual assistant-run JSON reports here when running fixture conformance.

Each report should be named for the fixture, for example
`backend-api-minimal.json`, and should use
`conformance/runs/assistant-run-report-template.json` as its shape.

Replace every `run_provenance` placeholder or use an explicit `unknown` value;
do not infer provider, model, version, timing, or operator evidence.

Actual reports should record which bridge or root entry file was used, whether
auto-load behavior was observed, whether Alatyr help and the context router
were found, and any assistant-surface limitations.

Record loaded context, approximate volume, budget expansion, receipt reuse,
changed facts, relationship traversal, companion surfaces, and unresolved
consistency gaps. Use `unknown` with a reason instead of inventing measurements.

This directory may stay empty except for this README until a reviewed
assistant conformance run is captured.

Captured runs:

- `codex-current-session-8dab3d1/` records a constrained Codex pilot against
  all four fixtures. It is useful assistant-produced evidence, but it did not
  run in fresh sessions rooted in each fixture and did not observe target
  bridge auto-loading or host token telemetry.
