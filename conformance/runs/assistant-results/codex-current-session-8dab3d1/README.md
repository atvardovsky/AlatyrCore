# Codex Current-Session Pilot

This directory records an actual Codex review of all four conformance fixtures
against AlatyrCore source commit `8dab3d15c6e0dc983096c2aaca89fba75fe6fa14`.
The run started at `2026-07-14T17:25:04+02:00` and completed at
`2026-07-14T17:26:14+02:00`.

The pilot reused the current AlatyrCore maintainer session. It was not four
fresh Codex sessions rooted in the fixture targets. The host supplied the
AlatyrCore source `AGENTS.md`; target bridge auto-loading was not observed.
Host token and per-file context telemetry were also unavailable. The reports
therefore use explicit `unknown` measurements and record the shared-context
limitation instead of inferring cost data.

No fixture was installed or modified, and no target validation is claimed.
The reports capture review and routing behavior only. They establish that the
Codex surface can produce contract-valid evidence for each fixture, while a
fresh target-root run remains necessary to test bridge discovery, isolated
context cost, and real installation behavior.

Validate the reports with:

```sh
python3 tools/check_conformance_reports.py \
  --actual-dir conformance/runs/assistant-results/codex-current-session-8dab3d1 \
  --require-actual-reports \
  --require-all-fixtures
```
