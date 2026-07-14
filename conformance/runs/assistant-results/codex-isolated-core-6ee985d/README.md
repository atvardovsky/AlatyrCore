# Codex Isolated Core-Profile Conformance

This run used four fresh Codex CLI `0.144.4` processes against source commit
`6ee985df3e6e65507cda175944b2b3ea4be630ae`. Each process used its fixture
target as the working root, disabled user configuration, used an ephemeral
session, and received a staged `core` placeholder adapter.

The staged adapter is not an accepted installation and target validation is
not claimed. It exists to test target bridge discovery, compact bootstrap,
context routing, gap preservation, and report behavior without loading the
AlatyrCore source installation corpus.

All four reports passed the actual-report validator. Total recorded CLI usage:

- input tokens: `2,401,253`
- cached input tokens: `2,239,232`
- output tokens: `23,112`
- reasoning output tokens: `1,667`
- elapsed fixture time: `634.782` seconds

The backend fixture loaded 15 target files and approximately 5,423 unique
words. Compared with the source-bootstrap backend baseline, that is a 79.6%
reduction in observed loaded words and a 41.5% reduction in cumulative CLI
input tokens. Cumulative input includes repeated and cached context across
tool turns; it is not equivalent to unique prompt tokens or monetary cost.

Raw JSONL event logs were retained only in the ignored local run workspace and
are not committed. `evidence/execution-summary.json` preserves per-fixture thread IDs,
durations, exit codes, exact CLI usage totals, and report presence.
