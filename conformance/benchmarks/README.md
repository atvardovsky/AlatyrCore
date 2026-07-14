# Effectiveness Benchmarks

These contracts support paired comparisons of the same task under `none`,
`minimal`, and `full` adapter modes.

Each task supplies three repository snapshots. Their project files must match;
only paths covered by `adapter_surface_patterns` may differ. Preparation copies
each snapshot into an isolated run workspace so one run cannot mutate another.

The source tooling prepares prompts and report paths. It does not run an
assistant, decide that an adapter mode is mature, or prove that Alatyr is
cheaper. A reviewer must evaluate the same acceptance criteria for every mode.
Token and monetary comparisons are shown only when every paired report uses a
comparable measurement source and currency; otherwise they remain unknown or
non-computable.

```sh
python3 tools/prepare_effectiveness_benchmark.py --plan benchmark.json --output tmp/benchmark
python3 tools/check_effectiveness_benchmark.py --benchmark tmp/benchmark/benchmark.json
python3 tools/check_effectiveness_benchmark.py --benchmark tmp/benchmark/benchmark.json --require-reports --require-reviewed
python3 tools/summarize_effectiveness_benchmark.py --benchmark tmp/benchmark/benchmark.json
```

Use `benchmark-plan-template.json` for the input shape and
`effectiveness-run-report-template.json` for captured reports. Keep real
repository facts and generated workspaces outside this source directory.
