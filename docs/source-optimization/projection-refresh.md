## Projection Refresh

`python3 tools/alatyr.py refresh-source` calculates a plan in an isolated copy.
The source graph orders existing renderers and checks their fixed-point output
before showing the changed paths. Stabilization is bounded; a cycle, renderer
failure, unowned output, or concurrent source change blocks application.

`--check` reports drift without source writes. `--write` applies only changed,
uniquely owned outputs after rechecking source revision and content. Existing
unchanged files retain their modification times. An interrupted apply is not
accepted; inspect the partial result before rerunning. This is not a filesystem
transaction or a replacement for the documented source checks.

Golden cost baselines, migrations, and release evidence remain separately
reviewed. They are intentionally not accepted by the refresh graph.

The support stage preserves recorded bytes when its canonical freshness check
passes, including historical generation revisions. A commit alone is not drift.
Managed content, policy, and stable provenance changes still trigger refresh;
every stage must pass its final check before a plan is accepted.
