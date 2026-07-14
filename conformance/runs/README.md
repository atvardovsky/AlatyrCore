# Conformance Runs

This directory is for captured assistant-run conformance reports.

Committed files here should be schemas, templates, and documentation only
unless the project intentionally records a reviewed conformance run. Real run
reports may include assistant surface, source commit, fixture name, evidence,
adapter output contract status, operation help status, AI infrastructure
inventory status, bridge behavior evidence, and residual-risk details, but
must not contain secrets or real project facts.

Captured reports should also distinguish measured or assistant-reported
context cost from unknown values and record logical-integrity evidence:
changed fact IDs, selected/skipped relationships, companion surfaces, and
unresolved gaps.

Supported conformance assistant surface IDs are listed in
`assistant-surfaces.json`. Use `--allow-custom-surface` only for an explicitly
reviewed assistant outside that list.

Validate captured reports with:

```sh
python3 tools/check_conformance_reports.py --actual-dir conformance/runs/assistant-results
```

For a completed full fixture run, require reports for every fixture:

```sh
python3 tools/check_conformance_reports.py --actual-dir conformance/runs/assistant-results --require-actual-reports --require-all-fixtures
```

Summarize one or more captured run directories with:

```sh
python3 tools/summarize_conformance_reports.py --actual-dir conformance/runs/assistant-results --require-all-fixtures
```

To prepare identical seed repositories for an assistant run:

```sh
python3 tools/materialize_conformance_fixtures.py --output tmp/conformance-targets
```

To prepare a full run workspace with targets, prompts, and report directory:

```sh
python3 tools/prepare_conformance_run.py --output tmp/conformance-run --assistant-surface codex
```

Give each prompt under `tmp/conformance-run/prompts` to the selected assistant.
The prompt tells the assistant where to inspect the fixture target and where to
write the JSON report.

The command compares actual reports with fixture contracts and golden report
expectations. It does not run an assistant and does not validate a real target
adapter.
