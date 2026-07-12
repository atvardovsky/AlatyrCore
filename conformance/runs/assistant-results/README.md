# Assistant Result Reports

Place actual assistant-run JSON reports here when running fixture conformance.

Each report should be named for the fixture, for example
`backend-api-minimal.json`, and should use
`conformance/runs/assistant-run-report-template.json` as its shape.

Actual reports should record which bridge or root entry file was used, whether
auto-load behavior was observed, whether Alatyr help and the context router
were found, and any assistant-surface limitations.

This directory may stay empty except for this README until a reviewed
assistant conformance run is captured.
