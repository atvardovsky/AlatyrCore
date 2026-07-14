# Alatyr Conformance Fixtures

This directory contains small target-repository fixture descriptions and
golden expectations for testing Alatyr installation and adapter recheck
behavior.

Fixtures are not production adapters. They are deterministic evidence for how
Alatyr Core should behave when a target repository has common shapes such as a
CLI, backend API, frontend, monorepo, or pre-existing AI instructions.

## Rules

- Fixtures must not contain real project business facts.
- Each fixture keeps a `fixture.json` target-shape manifest and an
  `expected.json` behavior/evidence contract.
- Golden outputs describe expected adapter surfaces, missing facts, approval
  decisions, and validation evidence.
- Golden assistant-result reports under `conformance/golden/fixture-reports`
  bind fixture expectations to a deterministic evidence shape.
- Golden scaffolded-adapter snapshots under
  `conformance/golden/scaffolded-adapters` bind fixture seed repositories to
  deterministic scaffolder output.
- Golden outputs should not require a universal runtime command.
- Conformance can be checked by assistants or future tools, but installed
  adapters remain target-owned.

Source-repository fixture metadata can be checked with:

```sh
python3 tools/check_conformance_fixtures.py
```

Seed-only fixture repositories can be materialized for actual assistant runs
with:

```sh
python3 tools/materialize_conformance_fixtures.py --output tmp/conformance-targets
```

Full assistant-run workspaces with fixture targets, per-fixture prompts, and a
report directory can be prepared with:

```sh
python3 tools/prepare_conformance_run.py --output tmp/conformance-run --assistant-surface codex
```

Prepare one matrix covering every supported assistant surface and fixture:

```sh
python3 tools/prepare_conformance_matrix.py --output tmp/conformance-matrix
python3 tools/check_conformance_matrix.py --matrix tmp/conformance-matrix/matrix.json
```

The matrix and per-surface run manifests remain `prepared-not-executed` after
preparation. After external assistants produce reports, require every planned
surface/fixture pair with:

```sh
python3 tools/check_conformance_matrix.py --matrix tmp/conformance-matrix/matrix.json --require-reports
python3 tools/summarize_conformance_reports.py --matrix tmp/conformance-matrix/matrix.json
```

Supported assistant surface IDs for conformance runs live in
`conformance/runs/assistant-surfaces.json`.

Golden assistant-result report contracts can be checked with:

```sh
python3 tools/check_conformance_reports.py
```

Temporary fixture repositories can be materialized and checked against the
source scaffolder and golden scaffolded-adapter snapshots with:

```sh
python3 tools/run_conformance_scaffold.py
```

Refresh snapshots only after reviewing scaffold changes:

```sh
python3 tools/run_conformance_scaffold.py --write-golden-snapshots
```

This is scaffold conformance only. It is not an assistant installation test
and does not validate a real target adapter.

The report checker is also source conformance only. It validates expected
assistant-result evidence fields; it does not run an assistant or prove a real
installation.

Captured assistant-run reports can be checked when they exist:

```sh
python3 tools/check_conformance_reports.py --actual-dir conformance/runs/assistant-results
```

Use `conformance/runs/assistant-run-report-template.json` for the report shape.
Use `--require-actual-reports` when a conformance run is expected to have
produced JSON reports. Use `--require-all-fixtures` when a full run should
include one valid report for every fixture.

Captured runs can be summarized by assistant surface and fixture with:

```sh
python3 tools/summarize_conformance_reports.py --actual-dir conformance/runs/assistant-results --require-all-fixtures
```

## Fixture Set

- `python-cli-existing-ai`: small CLI with existing AI instructions.
- `backend-api-minimal`: backend API with docs, tests, and API contract gaps.
- `frontend-app-minimal`: frontend app with docs and UI validation gaps.
- `monorepo-mixed`: multi-package repository with multiple ownership surfaces.

## Expected Checks

For each fixture, compare:

- files that should be created or preserved
- seed-only fixture repositories materialized from `fixture.json`
- prepared assistant-run prompts and report directories for selected assistant
  surfaces
- target source surfaces and missing adapter surfaces
- temporary scaffold output for required placeholder adapter surfaces
- golden scaffolded-adapter snapshots for created, preserved, skipped, and
  placeholder paths
- placeholders that must remain unresolved until target facts exist
- protected changes that require approval
- context profile selection
- module profile status
- source-of-truth registry gaps
- task-specific maturity result
- bridge capability matrix entries
- operation help status
- adapter output contract status
- AI infrastructure inventory status
- validation and residual risk evidence
- golden assistant-result reports for required evidence fields, expected
  behaviors, and forbidden claims
- captured assistant-run reports when a fixture conformance run has been
  reviewed and recorded
- matrix and per-run provenance matching the assistant surface, source commit,
  fixture scope, and expected report count
- loaded context, approximate volume, budget expansion, and context-receipt
  evidence from captured runs
- changed fact IDs, selected and skipped consistency relationships, companion
  surfaces, and unresolved logical-integrity gaps
- assistant-run summaries comparing surface coverage, fixture coverage,
  context cost, consistency evidence, residual risks, and unresolved validation

The deterministic static router baseline is stored at
`conformance/golden/context-cost-baseline.json`. Refresh it only after reviewing
the changed file and word costs reported by:

```sh
python3 tools/report_context_costs.py
```

This baseline is not model token usage. Actual assistant-run reports remain the
source for runtime context and logical-integrity evidence.
