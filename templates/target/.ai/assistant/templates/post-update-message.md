# Post-Update Assistant Chat Message

Use this template for the assistant's chat response after Alatyr Core is
updated in `{PROJECT_NAME}`.

Replace placeholders with target facts before sending the message.

Delivery evidence is separate from this template. Record `sent`, `skipped`, or
`blocked`, together with the delivery mechanism, reason, and observation time.
The presence of this file never proves that a chat message reached a user.

```text
Alatyr Core has been updated for `{PROJECT_NAME}`.

Framework baseline:
`{ALATYR_CORE_SOURCE_OR_BASELINE}`

Framework version/schema:
`{ALATYR_CORE_VERSION}`, adapter schema `{ALATYR_ADAPTER_SCHEMA_VERSION}`, template `{ALATYR_TEMPLATE_VERSION}`

Updated adapter surfaces:
`{UPDATED_ADAPTER_SURFACES}`

Future assistant bootstrap:
- Do not rely on this chat message alone.
- Treat `AGENTS.md` as preloaded; start from
  `.ai/assistant/bootstrap-index.json`, then
  `.ai/assistant/entry-packet.json`.
- Verify or rebuild the entry packet plus recursive framework, project, and
  assistant context indexes from this branch's installed files, then repair the
  bootstrap from `.ai/alatyr.yaml`, `.ai/README.md`,
  `.ai/assistant/context-router.json`, and `.ai/framework/semantics/index.json`
  when stale.
- Preserve target-owned support classifications, accepted relationships,
  candidates, and generator bindings. Rebuild optional reverse/generation
  indexes, then generate `.ai/support-state.json` last.
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/assistant-capabilities.json"]} -->
- Preserve selected assistant/provider capability evidence. Recheck provider
  cache mode, exposed client controls and telemetry, and freshness before
  using or reporting caching; otherwise retain bounded-routing fallback.
<!-- /alatyr:scaffold-fragment -->
- Use the resolved core semantic definitions once, follow only selected index
  branches, and load canonical owner prose for unresolved or conflicting terms.
  Report stale entries, omitted live references, and fallback events.
- Send `Alatyr` for compact actions or `Alatyr status` for a read-only adapter health check.
- If migration impact is unclear, run `recheck-after-framework-update` before editing files.
- Re-evaluate `.ai/assistant/policies/action-authorization.json` at every
  action-phase boundary. Never reuse edit, commit, push, or live-action intent
  from a completed or superseded scope.

Recommended follow-up:
Use the installed Alatyr adapter in this repository.
Operation type: recheck-after-framework-update
Goal: compare the installed adapter against the updated Alatyr Core baseline and report required migrations.
Non-goals: do not change project behavior without approval.
Allowed actions: read-only

Migration assessment:
`{MIGRATION_ASSESSMENT_PATH_OR_MANUAL_REVIEW}`

Upgrade impact router:
`{UPGRADE_IMPACT_JSON_PATH_OR_MANUAL_REVIEW}`

Load only canonical sources and target surfaces selected by the migration
assessment. Record candidate context intentionally omitted.

Operation help:
- Send `Alatyr` for compact relevant operations; use `Alatyr status` or
  `Alatyr doctor` for read-only health evidence.
- Exact IDs and aliases route through `.ai/assistant/operation-index.json`;
  bounded natural-language requests route automatically and operation IDs are
  optional. Load the full catalog only for ambiguity or repair.
- Issue/backlog returns, status requests, discussion, analysis, plans, reports,
  and ambiguous continuation remain read-only. Require current-scope intent for
  modification, commit, publication, and live external action separately; a
  clear request may authorize multiple named phases together.
- Risky or cross-boundary changes show a pre-change preview before edits.
- Use `.ai/assistant/help.md`, `.ai/assistant/help-reference.md`, and `.ai/assistant/templates/operation-request.md` for structured requests.
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/flows/large-task-orchestration.flow.md"]} -->
- Use `large-task` only for cross-boundary or resumable work, and resume an existing packet when one is named.
<!-- /alatyr:scaffold-fragment -->
- Use `Alatyr what do we know <subject>` for bounded accepted/current project
  knowledge, `Alatyr remember this` for a review proposal, and `Alatyr
  revalidate knowledge <id>` after freshness triggers. Historical evidence is
  not promoted during update.
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/change-packages/index.json"]} -->
- Recheck change-package records, semantic approval fields, provenance grades,
  and validator support when the optional module or schema changed. Preserve
  historical target records.
<!-- /alatyr:scaffold-fragment -->
- Preserve durable engineering-evidence IDs and records. Recheck compact index
  synchronization, contract/template versions, task/revision binding state,
  Git object type/ancestry, prior-binding lineage, canonical-owner links, privacy,
  external-patch policy, and record access; never replace existing records
  with source placeholders.
- Preserve project-knowledge promotion IDs and dispositions, canonical owner
  bindings/digests, candidate origins, guidance kinds, direct decision-owner
  authority, exception precedence, coverage states, route shards,
  contradiction and supersession lineage, and retention policy. Revalidate
  accepted facts against canonical owners and rebuild derived routes when
  needed; do not promote historical evidence or source placeholders during
  update.
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/debug/index.json"]} -->
- Preserve Debug Mode IDs, records, active-scope evidence, normalized events,
  timing, metrics, and publication policy when the module is enabled. Recheck
  versioned actor/causality/intervention/contribution attribution, structured
  architectural impacts, direction-change hypothesis/replacement chains,
  lifecycle timestamp bounds, immutable completion and continuation lineage,
  typed evidence-event roles, materiality evaluation, canonical skip
  preservation, claim-validation fidelity, durable Engineering Evidence
  decisions/references, binding lineage, completed-record comparison,
  dependency closure, schema, lazy route, operation, validator, and activation
  expiry. Preserve schema-version-1 and version-2 records as migration-limited
  evidence; do not reactivate or append to a closed scope or include debug
  files in a clean external patch. Use schema version 3 only for new records;
  do not silently invent historical attribution or materiality.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/documentation/catalog.json"]} -->
- When code documentation is enabled, preserve target profiles and recheck
  source-set matching, accepted state, canonical owners, generator/output
  policy, adapted skill, and validation before generation.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/vocabulary/catalog.json"]} -->
- When project vocabulary is enabled, preserve term IDs, definitions, states,
  aliases, acronyms, owners, canonical sources, and data links; recheck lookup,
  ambiguity, normalization, adapted skill, and validation before use.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/testing/test-first-policy.json"]} -->
- When test-first development is enabled, preserve target policy ownership,
  triggers, modes, commands, isolation, exceptions, adapted skill, and
  historical evidence; recheck recommendation and RED/GREEN routing before use.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/extensions/catalog.json"]} -->
- When extensions are enabled, preserve catalog/lock entries, immutable source
  provenance, target bindings, permissions, approvals, file ownership, local
  deviations, and lifecycle history; recheck compatibility and drift without
  automatically updating, activating, or removing any extension.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/dependencies/policy.json"]} -->
- When dependency knowledge is enabled, preserve target policy, reviewed
  package instances, independent semantic state, deviations, retention
  decisions, and permitted snapshots; recheck export API, artifact identity,
  fingerprints, routing, and drift without running package managers,
  activating nested adapters, or presenting stale claims as current.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/workspace-modes/catalog.json"]} -->
- When workspace modes are enabled, preserve user-accepted mode IDs,
  per-mode directories, shared root context, relationships, ownership, and
  decision evidence. Recheck them against the revised contract and present
  migrations as proposals; never accept, replace, or activate a mode solely
  because Alatyr was updated.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/team-policy.json"]} -->
- When team collaboration is enabled, recheck the structured policy, ignored
  identity boundary, active index, registry/task schemas, backend contract,
  optimistic concurrency, active task IDs, claims, handoffs, decisions,
  external references, stale overlaps, and revision-bound reviews before
  changing active records. Migrate schema-1 arrays atomically when applicable.
- Use `Alatyr set actor <actor>` for local attribution, `Alatyr who am I` to
  inspect it, `Alatyr team status` for coordination evidence, and the specific
  team aliases for task, conflict, handoff, decision, review, or merge work.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/delegation-policy.json"]} -->
- When subagent delegation is enabled, preserve the target policy, role
  catalog/prompts, execution plans, packet/result evidence, privacy, and
  retry/conflict rules. Recheck each surface's exact client/runtime, native
  definition format and paths, invocation mode, tools, isolation, background/
  nested behavior, role/model bindings, and freshness. Remove or migrate stale
  thin native bindings only from target evidence; never infer support from the
  updated framework templates.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/ai-infrastructure-router.json"]} -->
- Recheck AI infrastructure router entries and adaptation records when skills, prompts, gates, tools, or bridge contracts changed.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/flows/diagram-discussion.flow.md",".ai/assistant/assistant-capabilities.json"]} -->
- Recheck `diagram-discussion`, stable diagram lineage, security/privacy and
  external-renderer policy, and each selected compact assistant capability's
  enums, client version, verification time, and evidence when diagram or
  bridge contracts changed.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/architecture/catalog.json"]} -->
- Recheck the architecture catalog owner, decision authority, item states,
  selected evidence paths, validation, and evidence revision when
  `architecture-knowledge` or project architecture contracts changed. Use
  `Alatyr architecture` for a bounded inventory, explanation, comparison, or
  review.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/ai-infrastructure-router.json"]} -->
- Use `alatyr-suggest-ai <scope>` or `alatyr-improve-ai <item-id>` for a read-only recommendation when project needs or existing item outcomes changed.
<!-- /alatyr:scaffold-fragment -->

Validation run:
`{VALIDATION_RUN_OR_UNRESOLVED}`

Validation phase and branch/revision:
`{ACCEPTANCE_OR_MIGRATION_STAGING_AND_TARGET_BRANCH_REVISION}`

Acceptance status:
`{ACCEPTED_OR_STAGED_WITH_ACTIVE_PLACEHOLDERS_AND_REQUIRED_STRICT_RERUN}`

Adapter health:
`{READY_ATTENTION_BLOCKED_OR_UNVERIFIED_WITH_REASON}`

Do not describe the update as complete when validation used migration staging,
active adapter placeholders remain, enabled manifest modules disagree with the
module profile, or evidence belongs to another branch or revision.

Do not report adapter health as `ready` unless installation state is
`accepted` and current strict acceptance validation passed for this branch and
revision.

Known adapter gaps or migrations:
`{KNOWN_GAPS_OR_MIGRATIONS}`

Migration note:
`.ai/assistant/templates/migration-note.md` or `{MIGRATION_NOTE_RESULT}`

Delivery status: `{SENT_SKIPPED_OR_BLOCKED}`
Delivery mechanism: `{CHAT_SURFACE_OR_UNAVAILABLE}`
Delivery reason: `{WHY_SENT_SKIPPED_OR_BLOCKED}`
Delivery observed at: `{DELIVERY_TIMESTAMP_OR_NOT_OBSERVED}`
```
