# Golden Expectations

Golden expectations describe the minimum expected Alatyr response for each
fixture.

They combine prose-first expectations with machine-readable report contracts
under `fixture-reports/` and scaffolded-adapter snapshots under
`scaffolded-adapters/`.

The report contracts and scaffold snapshots are source-repository conformance
artifacts. They are not assistant transcripts, completed installations, or
real target validation results.

## Shared Golden Requirements

Every fixture result should include:

- installation or recheck operation type
- target facts inspected
- files proposed, created, preserved, or skipped
- protected changes and approval needs
- manifest/version handling
- context profile used
- source-of-truth registry status
- task-specific maturity result
- bridge capability status
- operation help status
- adapter output contract status
- AI infrastructure inventory status
- validation run or unresolved
- residual risk

Validate report contracts with:

```sh
python3 tools/check_conformance_reports.py
```

Validate captured assistant-run reports against the same fixture contracts
with:

```sh
python3 tools/check_conformance_reports.py --actual-dir conformance/runs/assistant-results
```

Use `--require-actual-reports` when the run should fail if no captured reports
exist. Use `--require-all-fixtures` when the run should cover every fixture.

Validate scaffolded-adapter snapshots with:

```sh
python3 tools/run_conformance_scaffold.py
```

## Non-Goals

Golden outputs must not:

- require a universal installer command
- claim target validation commands that were not discovered
- fill project facts from fixture names
- overwrite existing AI instructions without approval
