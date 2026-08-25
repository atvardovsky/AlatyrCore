# Effectiveness Benchmarks

These contracts support paired comparisons of the same task under `none`,
`minimal`, and `full` adapter modes.

`benchmark-task-suite.json` defines the minimum task-class coverage expected
before broad effectiveness or cost claims: narrow documentation, local code
repair, business invariants, architecture boundaries, data contracts,
protected security work, large resumable changes, framework upgrades, and
team-active coordination. It is a coverage contract, not evidence that those
runs have occurred. Use at least three repetitions per task class when model
variability matters.

Reviewed paired results enforce a quality floor: minimal and full modes must
not increase failed acceptance criteria, hallucinated commands, validation
errors, missed companion updates, rework, or unresolved consistency gaps
relative to the no-adapter run. Cost, token, context, or duration reductions
are useful only after that non-regression condition holds.

Each task supplies three repository snapshots. Their project files must match;
only paths covered by `adapter_surface_patterns` may differ. Preparation copies
each snapshot into an isolated run workspace so one run cannot mutate another.

The source tooling prepares prompts and report paths. It does not run an
assistant, decide that an adapter mode is mature, or prove that Alatyr is
cheaper. A reviewer must evaluate the same acceptance criteria for every mode.
Token and monetary comparisons are shown only when every paired report uses a
comparable measurement source and currency; otherwise they remain unknown or
non-computable.

Version-2 run reports contain a normalized context receipt with three separate
layers:

- `planned`: context selected before loading
- `resolved`: files actually resolved by routing
- `observed`: telemetry reported by the client or provider

Planned and resolved word counts are estimates. They must not be presented as
actual model context or token savings. Actual context comparisons require an
`observed` receipt with `exact` host or provider telemetry. Assistant-reported,
manual, partial, and unavailable measurements remain useful evidence, but they
do not support actual-cost claims. Historical version-1 reports remain
readable and retain their original evidence limits.

```sh
python3 tools/prepare_effectiveness_benchmark.py --plan benchmark.json --output tmp/benchmark
python3 tools/check_effectiveness_benchmark.py --benchmark tmp/benchmark/benchmark.json
python3 tools/check_effectiveness_benchmark.py --benchmark tmp/benchmark/benchmark.json --require-reports --require-reviewed
python3 tools/summarize_effectiveness_benchmark.py --benchmark tmp/benchmark/benchmark.json
```

For an isolated Codex execution with completion-event token and duration
capture:

```sh
python3 tools/run_codex_effectiveness_benchmark.py --benchmark /tmp/benchmark/benchmark.json
```

The executor leaves `review.status` pending. A different operator or process
must inspect target diffs and apply the same acceptance criteria to every mode
before `--require-reviewed` comparisons are valid.

Reviewed compact historical results may be promoted under `results/` without
committing complete target snapshots or raw model logs. Validate those records
with `python3 tools/check_captured_effectiveness_results.py`.

Use `benchmark-plan-template.json` for the input shape and
`effectiveness-run-report-template.json` for captured reports. Keep real
repository facts and generated workspaces outside this source directory.
