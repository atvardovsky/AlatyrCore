# Workflow Efficiency Tools

Source-maintainer interface reference. Canonical rules remain in
[delivery efficiency](../framework/test-delivery-efficiency.md) and
[delegation](../framework/subagent-delegation.md#dispatch-and-convergence).
These helpers complement agent reasoning; neither is a scheduler or permission
source. Small tasks add no runtime record or bootstrap requirement.

## Early Finalization Checks

```sh
python3 tools/alatyr.py finalize-support --target /path/to/repo --preflight --task-id TASK_ID --task-class standard-task --diff-ref BASE --require-task-acceptance
```

The installed delegate accepts the same finalization options. Use the actual
class and immutable comparison base. Explicit approval bindings can be supplied
with repeatable `--approval-record`. This diagnostic mode is mutually exclusive
with `--write`; it writes no projections, locks or task records.

The helper reuses canonical header schemas, pure model contracts, selected model/closure digests,
header correspondence, closure and publication-receipt shapes, and explicit
approval shape/hash checks. It does not repeat expensive result snapshots,
architecture reviews, model-to-runtime/source verification or unrelated task history.
Its JSON always has `acceptance_eligible: false`. It does not establish
full approval-versus-diff coverage, current human authorization, archive
acceptance or projection convergence. Full canonical validation remains required.

Write mode performs these selected checks before acquiring the support writer
lock and rechecks their inputs under that lock before mutation. Generated drift
is still repaired by the canonical renderer sequence. Full validation and
conflict-preserving rollback remain in place; final transaction-owned outputs
are rechecked before success. The lock coordinates cooperating writers only;
it is not filesystem-wide atomic compare-and-swap against arbitrary editors.

Keep support convergence, pre-publication checks and final task acceptance
separate. A task that requires publication cannot claim that outcome early.
Do not remove acceptance flags from an unchanged final-completion request to
obtain a passing result. Resolve contradictory target gate order with its owner.

## Parallel Admission

The optional `cooperation-preflight --admission admission.json` input is a
temporary, bounded projection of an existing primary-owned plan, not a second
task registry. Keep stable IDs and statuses synchronized with that plan; its
digest proves byte identity, not semantic correspondence or approved acceptance.

Exact schema-1 shape, with a single illustrative task:

```json
{
  "schema_version": 1,
  "plan": {"path": "task-plan.md", "sha256": "<actual lowercase SHA-256>"},
  "capacity": 2,
  "max_parallel": 2,
  "accepted_ids": [],
  "retry_ids": [],
  "tasks": [
    {"id": "part-a", "requires": [], "state": "READY", "slots": 1,
     "resources": [], "write_scope": []}
  ]
}
```

- Input and referenced plan each fit 64 KiB; 1..64 tasks, capacities/slots
  are integers 1..64, and ID/reference/path lists are bounded to 64 entries.
- States are the existing `PLANNED`, `READY`, `RUNNING`, `REVIEW_REQUIRED`,
  `DONE`, `FAILED`, `CANCELLED`, `BLOCKED`. Planned work is held until the primary
  marks it ready. Only declared primary-accepted `DONE` IDs settle
  dependencies; their entire prerequisite closure must also be accepted.
- `retry_ids` selects only failed tasks for reviewed retry, never extra retry
  allowance. Pending primary reviews retain write/resource claims and consume
  parallel/review capacity, but not running CPU slots.
- `resources` uses the canonical test-resource shape (kind, id, namespace,
  access, isolation). `write_scope` contains literal normalized target-relative
  paths, with enclosing paths conservatively covering descendants, `.` covering
  the repository, and case-folded overlap protecting case-insensitive hosts.
  Resolve filesystem aliases before actual writes. Empty lists
  explicitly declare none; null means unknown and blocks unsafe admission.
- The input order is primary-owned priority. Proposals account for active work
  and previously selected candidates. Oversized or locally blocked tasks do not
  block unrelated compatible work. Active conflicts require reconciliation.

Pass `--scope`, current session identity and any applicable registered test
command IDs as usual. Selected/active resource presence scopes are added by the
helper, with the existing combined eight-scope ceiling; narrow the proposal if
necessary, never omit a resource. Peer conflict or uncertainty clears proposals and retains
hold reasons. Reported resource identities must be reconciled with the same
plan; omission is not evidence of isolation. The report reserves nothing.

Reconsider only at meaningful completion, review, resource-release or dependency
events. Recheck bindings before actual dispatch. Primary chooses capacity from
remaining policy/context budgets, verified native limits, host CPU/RAM, nested
test workers, active peer work and review throughput. Reserve capacity if
backfill would starve a critical task. Missing capacity evidence is not spare
capacity; target/native dispatch remains outside this helper.

## Qualification And Migration

Preserve target-owned test timing, manual review, approval and concurrency.
Upgrade helper/flow pointers without automatically enabling modules, hooks,
workers, expensive tests or retries. Existing model/history schemas are unchanged;
no migration rewrites old evidence into accepted current results.

Compare equivalent workloads for outcomes, companion completeness, escaped
defects, rework, worker preparation/review, wait and end-to-end time. Keep I/O,
context, CPU, latency and billing separate. Fast diagnostics and synthetic
parallel plans do not prove real-agent speedup or provider savings.
