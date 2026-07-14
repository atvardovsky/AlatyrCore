# Codex Docs-Local Effectiveness Benchmark

This benchmark ran the same wording-only README change in three isolated
snapshots: no adapter, core/minimal adapter, and full adapter. Source commit:
`061987108d8e7ecd15625953d7c41683ee7fe497`.

All three modes passed all four acceptance criteria with no rework, invented
commands, validation errors, missed companion updates, or unresolved
consistency gaps. A separate orchestrator review verified the exact README
change and unchanged `package.json` and `src/App.txt` hashes.

Measured outcomes relative to no adapter:

- minimal: 0.4% more total tokens and 24.7% less elapsed time
- full: 67.0% more total tokens and 11.0% more elapsed time

Monetary cost was not computed because no comparable billing export was
available. This one low-risk task does not support a broad claim that Alatyr is
cheaper. It does support using the smallest adequate profile and avoiding the
full adapter context for simple documentation work.

Raw JSONL logs and complete mode workspaces remain ignored local evidence and
are not committed. The reports, execution summary, review hashes, and generated
summary preserve the reviewed comparison.
