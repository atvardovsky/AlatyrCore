# Post-Update Assistant Chat Message

Use this template for the assistant's chat response after Alatyr Core is
updated in `{PROJECT_NAME}`.

Replace placeholders with target facts before sending the message.

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
- Treat `AGENTS.md` as preloaded; start from `.ai/assistant/bootstrap-index.json`.
- Repair a stale generated index from `.ai/alatyr.yaml`, `.ai/README.md`, and `.ai/assistant/context-router.json`; otherwise load profiles, module state, registries, blueprint, gate fragments, and the installation note only when routing or unclear adapter state requires them.
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
- Use `large-task` only for cross-boundary or resumable work, and resume an existing packet when one is named.
- Recheck change-package records, semantic approval fields, provenance grades,
  and validator support when the optional module or schema changed. Preserve
  historical target records.
- Preserve durable engineering-evidence IDs and records. Recheck compact index
  synchronization, task/revision binding, canonical-owner links, privacy,
  external-patch policy, and record access; never replace existing records
  with source placeholders.
- Preserve Debug Mode IDs, records, active-scope evidence, normalized events,
  timing, metrics, and publication policy when the module is enabled. Recheck
  structured architectural impacts, direction-change hypothesis/replacement
  chains, exact durable Engineering Evidence references, completed-record
  comparison, dependency closure, schema, lazy route, operation, validator,
  and activation expiry. Preserve older unstructured events as migration-
  limited evidence; do not reactivate a closed scope or include debug files in
  a clean external patch.
- When code documentation is enabled, preserve target profiles and recheck
  source-set matching, accepted state, canonical owners, generator/output
  policy, adapted skill, and validation before generation.
- When project vocabulary is enabled, preserve term IDs, definitions, states,
  aliases, acronyms, owners, canonical sources, and data links; recheck lookup,
  ambiguity, normalization, adapted skill, and validation before use.
- When test-first development is enabled, preserve target policy ownership,
  triggers, modes, commands, isolation, exceptions, adapted skill, and
  historical evidence; recheck recommendation and RED/GREEN routing before use.
- When extensions are enabled, preserve catalog/lock entries, immutable source
  provenance, target bindings, permissions, approvals, file ownership, local
  deviations, and lifecycle history; recheck compatibility and drift without
  automatically updating, activating, or removing any extension.
- When dependency knowledge is enabled, preserve target policy, reviewed
  package instances, independent semantic state, deviations, retention
  decisions, and permitted snapshots; recheck export API, artifact identity,
  fingerprints, routing, and drift without running package managers,
  activating nested adapters, or presenting stale claims as current.
- When workspace modes are enabled, preserve user-accepted mode IDs,
  per-mode directories, shared root context, relationships, ownership, and
  decision evidence. Recheck them against the revised contract and present
  migrations as proposals; never accept, replace, or activate a mode solely
  because Alatyr was updated.
- When team collaboration is enabled, recheck the structured policy, ignored
  identity boundary, active index, registry/task schemas, backend contract,
  optimistic concurrency, active task IDs, claims, handoffs, decisions,
  external references, stale overlaps, and revision-bound reviews before
  changing active records. Migrate schema-1 arrays atomically when applicable.
- Use `Alatyr set actor <actor>` for local attribution, `Alatyr who am I` to
  inspect it, `Alatyr team status` for coordination evidence, and the specific
  team aliases for task, conflict, handoff, decision, review, or merge work.
- When subagent delegation is enabled, preserve the target policy, role
  catalog/prompts, execution plans, packet/result evidence, privacy, and
  retry/conflict rules. Recheck each surface's exact client/runtime, native
  definition format and paths, invocation mode, tools, isolation, background/
  nested behavior, role/model bindings, and freshness. Remove or migrate stale
  thin native bindings only from target evidence; never infer support from the
  updated framework templates.
- Recheck AI infrastructure router entries and adaptation records when skills, prompts, gates, tools, or bridge contracts changed.
- Recheck `diagram-discussion`, stable diagram lineage, security/privacy and
  external-renderer policy, and each selected compact assistant capability's
  enums, client version, verification time, and evidence when diagram or
  bridge contracts changed.
- Recheck the architecture catalog owner, decision authority, item states,
  selected evidence paths, validation, and evidence revision when
  `architecture-knowledge` or project architecture contracts changed. Use
  `Alatyr architecture` for a bounded inventory, explanation, comparison, or
  review.
- Use `alatyr-suggest-ai <scope>` or `alatyr-improve-ai <item-id>` for a read-only recommendation when project needs or existing item outcomes changed.

Validation run:
`{VALIDATION_RUN_OR_UNRESOLVED}`

Validation phase and branch/revision:
`{ACCEPTANCE_OR_MIGRATION_STAGING_AND_TARGET_BRANCH_REVISION}`

Acceptance status:
`{ACCEPTED_OR_STAGED_WITH_ACTIVE_PLACEHOLDERS_AND_REQUIRED_STRICT_RERUN}`

Do not describe the update as complete when validation used migration staging,
active adapter placeholders remain, enabled manifest modules disagree with the
module profile, or evidence belongs to another branch or revision.

Known adapter gaps or migrations:
`{KNOWN_GAPS_OR_MIGRATIONS}`

Migration note:
`.ai/assistant/templates/migration-note.md` or `{MIGRATION_NOTE_RESULT}`
```
