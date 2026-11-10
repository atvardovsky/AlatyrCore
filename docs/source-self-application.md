# Source Self-Application

Scope: AlatyrCore source repository only. This is an operational adapter for
maintaining AlatyrCore, not an installation mechanism or a second portable policy.
Canonical rules remain with the [rule registry](../framework/rule-registry.json).

## Small Work

Classify first using the existing source router and minimum-work planner. A small,
settled change keeps its source-linked request brief inline, selected owners and
focused checks. It needs no registered task, runtime projection or extra bootstrap.
Reclassify if scope, uncertainty or protected effects expand.

## Material Work

For non-trivial implementation, audits, recurring repairs or release work:

1. Run `python3 tools/alatyr.py source-adoption status`. If necessary, preview
   `source-adoption reconcile`, then explicitly add `--write`. This initializes
   only ignored task/policy projections, never a full self-installation.
2. Keep a current [problem model](../framework/task-decomposition.md) and
   [request brief](../framework/task-state-delivery.md), using their canonical target
   templates and schemas. Publish the model through `publish-task
   --target . --source-contour`; authoring drafts and per-request evidence remain
   ignored. Do not change the template to record source-project facts.
3. Deliver `lifecycle-checkpoint --target . --source-contour checkpoint --event
   request` with a JSON session identity on stdin. Retain its new request ID in the
   brief. Capture a source-contour context baseline containing the task index,
   selected model/projection/strategy, brief, lifecycle policy, source control
   inputs and any selected approval/history artifacts. `selected_task()` and the
   bind diagnostic identify missing inputs; do not capture the entire corpus.
4. Bind via the same lifecycle command's `bind` action, with `--session-id`,
   `--request-id`, `--task-id`, `--baseline` and `--request-brief`. For state-changing
   work, also supply `--diff-ref` and explicit `--approval-record` bindings. The
   source lane resolves the base revision and retains exact record hashes.
5. Before a state-changing phase and before completion, review the declared action
   through the bound procedural checkpoint. Inspect, modify, commit and publish
   remain separate authorizations. Compare the actual Git change set against
   canonical approval scope; an empty declared path list cannot hide extra files.
6. Reconcile changed selected inputs at phase boundaries and after compaction.
   A new request resets scope; a rebind or resume cannot silently enlarge its
   existing approval bindings. End the lifecycle session when the work ends.

Use the existing [delivery-efficiency controls](../framework/test-delivery-efficiency.md)
for costly validation, recurrent retries or material multi-step execution. Keep
history and progress receipts in the canonical brief/model flow; never start a
parallel retry ledger. A successful test run is supporting evidence, not proof
that the original outcomes or companion updates are complete. Retain the
request's remaining outcomes and contradictions until resolved or explicitly
handed off. Full source acceptance remains cold, not a reused focused result.

Runtime commands are procedural aids. They do not intercept every tool, authenticate
human approval, prevent an assistant from ignoring instructions, or grant acceptance.
Source runtime files are ignored and are not durable team knowledge.

Source authoring uses `publish-task --source-contour` and focused source checks;
converge projections with `refresh-source` before cold acceptance. Installed-target
`finalize-support` is not a source self-installation route. For substantial
primary-controlled parallel work, follow the conditional
[source worker strategy](source-worker-strategy.md#activation) and
[workflow efficiency reference](workflow-efficiency.md). Keep workers inspect-only
and the source-check scheduler unchanged; no helper grants authority or adoption.

## Knowledge And Decisions

`tools/source_knowledge.json` is a bounded index of source-owned architecture,
terminology and incident lessons. `source-adoption knowledge --query <term>`
returns matching owners and headings, not a replacement explanation. Load only
the owner needed for the current decision. Observed, proposed, accepted and
contradicted states must remain distinct. Promote reusable findings into the
existing maintainer/architecture owners; do not leave them only in ignored tasks.

## Evidence Boundaries

`tools/source_adoption.json` classifies every optional capability as a source
equivalent, conditional, or conformance-only. This describes applicability, not
proof that an agent used it. Source status distinguishes projection freshness
from exercise evidence. Test fixtures prove contract behavior, not real provider
interception, team adoption or product effectiveness.

Measure retrieval I/O, delivered context, worker overhead, latency and provider
billing separately using existing run artifacts. Missing provider/client usage
stays unknown. Do not derive billing savings from fewer bytes or test totals.

## Assistant Entry Points

The root `AGENTS.md` is the canonical source entry. `source-adoption bridge
--surface <id>` previews a short source-only bridge using the existing assistant
surface catalog. `--write` is permitted only for ignored, untracked paths and
never overwrites different existing instructions. It installs no native hooks,
plugins or global client configuration. Catalog support levels and client-loading
limitations still apply. Select the bridge explicitly; no client detection guesses.

## Maintenance

Preview projection changes before writing. Existing task indexes are preserved;
modified managed projections require explicit reconciliation with
`--approve-policy-update`. Local edits that do not match the prior managed hash
are rejected, not overwritten. Re-evaluate source applicability after capability,
source workflow or architecture changes. Source-only controls do not change the
portable framework, adapter schema or target template contracts.
