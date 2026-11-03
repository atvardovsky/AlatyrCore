# Core-Only Repair And Finalization

Use this conditional walkthrough for registered non-small work in an accepted
core installation. It is not an installer or an additional policy layer.
Canonical owners: [authorization](../framework/action-authorization.md),
[task analysis](../framework/task-decomposition.md),
[incident review](../framework/test-first-development.md#incident-repair-review),
and [evidence retention](../framework/engineering-evidence.md).

All target paths and IDs below are illustrative. Replace them with inspected
target facts. Run source commands from a compatible AlatyrCore checkout;
`/path/to/project` is the target. Python 3.10+ with documented tool dependencies
is required. On Windows, use `py -3` and native paths instead of `python3`.

## 1. Establish Scope And Preserve The Failure

Record the current user request, allowed actions, target branch/base, canonical
owners, original case and affected validation before editing. Existing explicit
repair authorization need not be requested again for the same scope. Commit,
push and external actions remain separate. A record cannot create permission.

Keep failed observations immutable. Retain source/test copies as inert artifacts,
such as `evidence/repair/test_case.py.snapshot`, after checking the target's
actual discovery configuration. Do not add executable test copies or narrow the
prescribed test command to conceal their collection. Keep secrets/private
reasoning out of retained evidence.

## 2. Publish A Current Model

Adapt `.ai/assistant/templates/problem-model.json` into an ignored authoring
draft. Bind actual task/operation IDs, owners, changed facts, original-case
obligations, required reviews and incident lineage. Use ordinary obligation IDs
for generic repair review. The reserved `repair-evidence-review` ID requires a
valid explicitly enabled optional test policy; core installation alone does
not adopt it.

For a new task, prepare a registration draft matching
`schemas/alatyr-active-task-index.schema.json` from the source checkout, with
state `active`, no completion claim and the same task/operation/class/family.
Keep the existing active index valid; do not insert an incomplete header to
bootstrap publication. `--registration` adds the new header transactionally.

```sh
python3 tools/alatyr.py publish-task --target /path/to/project --task-id REPAIR-1 --draft .ai/.runtime/drafts/repair.json --registration .ai/.runtime/drafts/registration.json
```

Review the no-write plan; add `--write` only within current modification scope.
For an existing active task omit `--registration` unless reviewed header changes
are needed. Republish after evidence changes; the helper derives model/projection
hashes and preserves peers and captured duties. A handoff revision additionally
requires an explicit renewed `--retention-review`.

## 3. Repair, Validate And Retain Closure

Run the real product regression and prescribed affected validation after all
relevant evidence packaging. Record exact commands, outcomes and limitations.
Passing structural evidence does not execute a command or prove causality.
Update owning project knowledge alongside the implementation.

Resolve each predecessor through its retained model/closure. Do not delete an
unclosed predecessor, reset an original case or waive a failed gate merely to
make the current task pass. Use the selected read-only view to locate blockers:

```sh
python3 tools/alatyr.py doctor --target /path/to/project --current-task REPAIR-1 --json
```

This source command supports JSON. The installed delegate supports
`doctor --current-task REPAIR-1` with text output, not `--json`. Verify the exact
entry point and arguments; help or a valid core installation alone does not
establish an optional context-planning route. Planning additionally requires a
resolved profile's `operation_candidates`, router `operation_routing`, and its
operation index/catalog. Do not enable capabilities implicitly to satisfy a
benchmark protocol.

Adapt `.ai/assistant/templates/task-closure.json`, retain its task/operation,
changed-fact and lineage bindings, and register the closed task with exact
closure/model hashes. Keep implementation, finalization and publication states
separate. A reviewed selected-file snapshot can bind local uncommitted results;
it must cover every claimed implementation surface and canonical owner, and
exclude its own closure and active index. It is not commit/publication evidence.

After explicit retention/privacy review, freeze witnesses with:

```sh
python3 tools/alatyr.py archive-task-evidence --target /path/to/project --task-id REPAIR-1 --retention-review request:retention-reviewed
```

Review the plan, then add `--write` under the same authorized retention scope.
The helper preserves original hashes; it does not sanitize content or accept work.

## 4. Converge And Request Strict Acceptance

Select a real approval record covering the current diff and permitted surfaces.
Use the actual task class. Core-only installations need no change package when
that optional module is not enabled; enabled modules keep their own duties.

```sh
python3 tools/alatyr.py finalize-support --target /path/to/project --write --require-current-change --diff-ref BASE-REVISION --approval-record /path/to/project/.ai/assistant/approvals/repair.json --task-id REPAIR-1 --task-class standard-task --require-task-acceptance
```

This refreshes generated support transactionally and runs full canonical
validation. It neither approves the diff nor invents missing task evidence.
For inspect-only verification omit `--write`. Confirm full acceptance scope,
current-change approval enforcement and explicit selected-task acceptance;
`task_acceptance.state: not-requested` is not closure. Preserve failed reports
and report blocked/provisional results honestly.

## Mistaken Reserved-ID Capture

New incompatible captures fail before publication. An older captured requirement
cannot be silently renamed, removed, reset or bypassed with a successor. Inspect
its original model, policy baseline and user decisions, preserve the evidence,
and report the task blocked. A target owner may explicitly adopt a valid repair
policy and provide the required evidence; generic repair authorization does not
authorize that policy change. No automatic waiver or force-reset is provided.

Select the task with the complete source doctor command in section 3, replacing
`REPAIR-1` with its registered task ID.
`repair_preflight.state: captured-requirement-needs-review` identifies a current
obligation/policy mismatch, not proof that historical capture was mistaken.
Follow its owner-review guidance; retain the model, header and failed reports.
An absent, unreadable, invalid or deferred current policy is not authority to
remove a genuine historical requirement. A core incident without a captured
requirement can continue with generic obligations; optional-policy adoption is
not a prerequisite.

## Executable Coverage

`tests/test_core_repair_workflow.py` exercises a synthetic core installation,
real failed/repaired input, public publication/finalization/validation commands,
retained witnesses and current-change approval scope without enabling optional
review. Exact source JSON and installed-delegate text invocations are exercised;
the unsupported delegate JSON flag is a negative protocol control. A separate
configured context fixture must exercise the exact planning route before a
trial is frozen. A stale result must block. Fixture approvals are synthetic test data,
not reusable user grants. These checks do not establish real-world cognitive,
latency, token-cost or domain-correctness improvements.
