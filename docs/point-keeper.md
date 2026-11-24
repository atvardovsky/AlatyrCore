# Point Keeper

A read-only projection for point-oriented worker streams. It answers one
question for every supportive agent and deploy step: **which point is this, what
state is it in, and may this role act on it now?**

It does not introduce a second task registry. It reads the target's existing
team task records and change-package index.

## Sources

- `.ai/assistant/team/tasks/*.json` — one point per target team task record
- `.ai/assistant/team/active-work-index.json` — worker claims
- `.ai/assistant/change-packages/index.json` — deploy sets and package state
- `review_evidence_refs`, `reviewed_head_revision`, `validation_state`,
  `blockers`, `related_task_ids` inside each point record
- current deploy revision, passed explicitly or read from `git rev-parse HEAD`

A point belongs to a deploy set when the deploy-set ID appears in the point's
`related_task_ids`. The deploy set itself should exist as a change package.

## Roles

| Role | Scoped view | Typical action |
|---|---|---|
| `coordinator` | all points, counts, attention list, package state | assign, review, freeze, integrate, deploy |
| `explorer` | one point, read-only | inspect |
| `reviewer` | one `in_review` point and its evidence requirements | review |
| `implementer` | one `pending`/`in_progress` point and write scope | modify |
| `test-runner` | one point, read-only code | test |
| `documentation-worker` | one point and docs scope | modify docs |
| `fast-focused-worker` | one bounded point | scoped work |
| `deploy` | one frozen point or an eligible deploy set | deploy |

Workers receive one point, not the global pending/frozen list. The coordinator
and deploy agent receive the global view.

## Commands

```sh
python3 tools/alatyr.py point-keeper --target . status --current-revision SHA
python3 tools/alatyr.py point-keeper --target . check --point P-17 --role reviewer
python3 tools/alatyr.py point-keeper --target . preflight --deploy-set D-20261120-A --current-revision SHA
```

`status` exits 1 when no point records are available. `check` exits 1 when the
requested point is missing or invalid. `preflight` exits 1 when any member is
not deployable.

## Point State

Normalized states:

- `pending` — proposed, ready, todo, backlog
- `in_progress` — implementing, active, started
- `in_review` — review, reviewing, awaiting review
- `done` — done, complete, frozen, reviewed
- `blocked` — failed, needs check
- `cancelled` — cancelled, superseded, archived

A point is **frozen** only when it is `done`, its review is `reviewed` or
`not-required`, and required review evidence is present. A point with
`review_state=in-review` or missing evidence is not frozen.

## Deploy Preflight

A deploy set is ready only when every member:

- is `done` and frozen
- has `reviewed` review state, or review is `not-required`
- has at least one review evidence reference when review is required
- has `validation_state` in `passed`, `current`, `not-required`, or `ok`
- has no blockers
- has a `reviewed_head_revision` that matches the deploy revision
- is not blocked, cancelled, or superseded

The deploy package must exist and be `complete` or `validated`. An unknown,
empty, blocked, or implementing deploy set is blocked.

A frozen point whose reviewed revision differs from the deploy revision is
`frozen-drift`; it cannot deploy. Create a successor point, review it, and
freeze the successor.

## Failure Behavior

| Condition | Result |
|---|---|
| tasks directory missing | `unavailable` |
| malformed point record | reported and preflight blocked |
| duplicate point ID | reported and preflight blocked |
| more than 4,096 task records | inventory incomplete; role lookup and deploy preflight blocked |
| malformed or duplicate package entries | package index unavailable; deploy preflight blocked |
| review evidence missing | `review-evidence-missing` |
| validation not current | `validation:<state>` |
| deploy revision unknown | `revision-unknown` |
| unknown deploy set | `deploy-set-unknown` |
| blocked package | `deploy-package-blocked` |
| frozen revision mismatch | `frozen-drift` |

The keeper carries no authority. It never grants, freezes, reviews, approves, or
deploys. State changes remain with the coordinator and the target's review and
approval contracts.

## OpenCode Integration

No daemon is required:

- `session.context` injects the coordinator or worker view when a blocker exists.
- `session.create` injects the scoped worker view into the worker prompt.
- `tool.execute.before` can block frozen writes or deploy/publish actions.
- `session.compaction` advances the read-ledger epoch.
- the deploy script calls `preflight` as its final gate.

External support agents receive the same scoped JSON packet plus the
`keeper_digest`; the orchestrator rejects a result without a matching digest and
observed state.
