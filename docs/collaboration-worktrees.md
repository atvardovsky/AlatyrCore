# Worktree Collaboration Helpers

These optional source tools support the canonical
[continuity rule](../framework/session-continuity.md). They do not install,
upgrade, authorize, lock or deploy a project. Commands below are illustrative;
replace target paths, IDs and observation values with reviewed target evidence.
Use `python` on Windows with a supported Python environment.

## Start A Worktree

```sh
python3 tools/alatyr.py worktree-preflight --target /path/to/target-repo --framework-source . --task-id TASK_ID --require-ready
```

This bounded check reads declared versions, installation state and registered
active-model bindings, not the full adapter or project test suite. Exit 0 means
prerequisites are available for context review, not acceptance. With
`--require-ready`, unresolved prerequisites return 1; invalid input returns 2.

Source selection precedence is explicit `--framework-source`, `ALATYR_CORE`,
worktree `.ai/local/framework-source`, then an explicitly configured
`alatyr/framework-source` file below `git rev-parse --git-common-dir`. A relative
common locator resolves from its containing `alatyr` directory. Invalid selected
configuration fails closed. Keep all workstation locators uncommitted. This
shares a tooling location only, not an active nested adapter or compatibility
decision. Separate clones need their own configuration.

## Retain And Recover Active Evidence

```sh
python3 tools/alatyr.py publish-task --target /path/to/target-repo --task-id TASK_ID --draft .ai/.runtime/drafts/task.json --retention-review REVIEW_REFERENCE
python3 tools/alatyr.py restore-task --target /path/to/target-repo --task-id TASK_ID
```

Preview first; add `--write` only with current authorization. Publication retains
reviewed model/projection bytes under `.ai/assistant/task-evidence/<task-id>/<sha>/`
and binds `analysis_handoff` in the active header. Every updated handoff needs a
new explicit retention review. This does not automatically detect secrets; do
not retain raw chat, private reasoning or unsafe payloads.

Commit the reviewed handoff and header together using separate current-scope
commit/push authorization. A linked worktree then has the same evidence.
Digest-bound analysis artifacts must also be retainable and committed with the
handoff. Ignored probe inputs/results block retention: explicitly move reviewed
evidence to durable target-owned paths and revise bindings first. The helper
does not copy, sanitize or rewrite these artifacts automatically.
`restore-task` restores only the registered bytes to ignored runtime paths;
changed digests, wrong identities and conflicting postimages fail. Missing
unretained evidence must be recovered from its actual origin or handled through
an explicit successor decision, never invented. A selected task needs runtime
rehydration and renewed authorization/freshness review. Foreign active witnesses
retain current schema and source checks; closed historical exemptions do not
apply. Full validation remains mandatory where the target requires it.

## Acknowledged Publication Handoff

`cooperation-preflight` optionally reads two target-relative JSON files:
`--handoff` and `--handoff-current`. Store them in target-authorized ignored
storage; they are observations, not executable instructions or approval grants.
The handoff shape is:

```json
{
  "schema_version": 1,
  "intent": {
    "resource_id": "deployment/staging",
    "publisher_uid": "11111111-1111-4111-8111-111111111111",
    "approval_ref": "approval:current-task-publication",
    "candidate_revision": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "origin_id": "origin:target-repository",
    "expected_previous_pin": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "expected_pin_generation": "generation-2"
  },
  "acknowledgement": {
    "publisher_uid": "11111111-1111-4111-8111-111111111111",
    "intent_sha256": "RECOMPUTE_FROM_EXACT_INTENT",
    "recorded_at": "2026-10-30T11:59:00Z",
    "evidence_ref": "handoff:publisher-acknowledgement"
  },
  "availability": {
    "candidate_revision": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "origin_id": "origin:target-repository",
    "state": "available",
    "observed_at": "2026-10-30T11:59:00Z",
    "evidence_ref": "origin-observation:exact-candidate"
  }
}
```

The sample is not current evidence. `intent_sha256` is SHA-256 of ASCII JSON with
sorted keys and compact separators, as owned by
[`intent_digest()`](../tools/collaboration_observations.py). The acknowledgement
must name the nominated session and unchanged intent. UID consistency is not
authentication. All seven intent fields are required, with full immutable Git
IDs for candidate and predecessor. An unknown/absent pin is unresolved in this
pre-activation protocol; do not fabricate a predecessor or generation.

The independent current-input file contains `intent` with those same seven
bindings, `max_age_seconds` in 1..86400, and `pin` with `revision`, `generation`,
`observed_at` and `evidence_ref`. Reobserve from the intended target, not by
copying a saved receipt. Stale/future/naive timestamps, unknown availability,
different origin/candidate/publisher/approval/resource/pin or changed generation
remain unresolved. Matching local trees do not prove availability at the origin.

```sh
python3 tools/alatyr.py cooperation-preflight --target /path/to/target-repo --scope resource:deployment --handoff .ai/local/publication-handoff.json --handoff-current .ai/local/publication-current.json --require-clear
```

`reported-consistent` means only supplied bindings agree at inspection time.
No fetch, push or deployment occurs; no live availability or activation order is
verified. Reobserve immediately before separately authorized publication, use
target conditional pin updates where supported, and preserve presence conflicts
and uncertainties. A preflight cannot prevent a race or detect an unobserved ABA
change when the target supplies no generation token.

## Optional Build Capacity

Pass `--capacity .ai/local/build-capacity.json` to the same preflight. Schema 1
contains explicit `max_age_seconds`, 1..64 `domains` and 1..64 `builds`:

- Domain: `domain_id`, available `headroom_bytes`, available `cpu_slots`,
  `observed_at`, `evidence_ref`. Headroom is after existing consumption and any
  target reserve, not total installed memory.
- Build: unique `instance_id`, `domain_id`, `process_tree_peak_bytes`,
  `cpu_slots`, `basis: process-tree-peak-estimate`, `observed_at`, `evidence_ref`.
  Distinct instances of the same command count separately.

Quantities are bounded integers; demands are positive, headroom can be zero.
Aggregate only within the same domain. Missing placement, unknown/stale estimates,
heap-only targets and excess memory/CPU remain unresolved. `estimated-fit` is
not an OOM guarantee, reservation or substitute for coordination. Optional inputs
are not read when unselected; there is no polling or scheduler.

## Focused Assistance

`plan-test-resources` and command-selected cooperation preflight include
`selected_test_context`: canonical policy, configuration paths, prerequisites,
effects, environment and proof boundary. Verify the target's positive-case
fixture/authentication/feature settings; this brief does not execute or authorize
tests. See [testing guidance](../framework/testing-guidance.md).

At non-trivial completion, `suggest-knowledge --task-id TASK_ID --limit 3`
selects existing recurrence proposals by canonical owner and reports omissions.
The owner still reviews freshness, meaning and promotion. An empty knowledge
index is valid. See [project knowledge](../framework/project-knowledge.md).

`doctor --json` retains all findings and adds artifact-specific `repair_plan`
prerequisites for unavailable task bindings, with exact task/path/digest and a
recovery action. Historical attention is listed separately. These views do not
waive findings, infer domain causality or make full validation cheaper.
