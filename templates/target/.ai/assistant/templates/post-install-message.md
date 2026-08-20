# Post-Install Assistant Chat Message

Use this template for the assistant's chat response after Alatyr Core is
installed in `{PROJECT_NAME}`.

Replace placeholders with target facts before sending the message.

```text
Alatyr Core is installed for `{PROJECT_NAME}`.

Entry points:
- `AGENTS.md`
- `AI_ASSISTANTS.md`
- `.ai/alatyr.yaml`
- `.ai/README.md`
- `.ai/assistant/templates/installation-note.md`
- `.ai/assistant/help.md`
- `.ai/assistant/help-reference.md`
- `.ai/assistant/operation-index.json`
- `.ai/assistant/operation-catalog.json`
- `.ai/assistant/context-router.json`
- `.ai/assistant/bootstrap-index.json`
- `.ai/assistant/gates/index.json`
- `.ai/assistant/context-profiles.md`
- `.ai/assistant/module-profile.md`
- `.ai/project/source-of-truth-registry.md`
- `.ai/project/consistency-map.json` when the optional module is enabled
- `.ai/project/architecture/README.md` and `.ai/project/architecture/catalog.json` when architecture knowledge is enabled
- `.ai/project/documentation/catalog.json` and `.ai/project/documentation/profiles.json` when code documentation is enabled
- `.ai/project/vocabulary/catalog.json`, `.ai/project/vocabulary/terms.json`, and `.ai/project/vocabulary/data-dictionary-links.json` when project vocabulary is enabled
- `.ai/project/testing/test-first-policy.json` when test-first development is enabled
- `.ai/project/team-policy.json`, `.ai/assistant/team/active-work-index.json`, and `.ai/assistant/team/work-registry.json` when team collaboration is enabled
- `.ai/assistant/maturity-profile.md`
- `.ai/assistant/bridge-capability-matrix.md`
- `.ai/assistant/assistant-capabilities.json`
- `.ai/assistant/ai-infrastructure-router.json` when AI infrastructure is enabled
- `.ai/assistant/extensions/catalog.json` and `.ai/assistant/extensions/lock.json` when extensions are enabled
- `.ai/assistant/change-packages/index.json` when change packages are enabled

Future assistant bootstrap:
- Do not rely on this chat message alone.
- Treat `AGENTS.md` as preloaded; start from `.ai/assistant/bootstrap-index.json`.
- Repair a stale generated index from its named manifest, project-map, and router sources; otherwise load profiles, module state, registries, blueprint, gate fragments, and the installation note only when routing or unclear adapter state requires them.
- Send `Alatyr` for compact actions or `Alatyr status` for a read-only adapter health check.
- If the installation itself is unclear, run `recheck-after-installation` before editing files.

Installed operation help:
- Send `Alatyr` to see adapter state and up to three relevant operations.
- Send `Alatyr status` or `Alatyr doctor` for read-only health evidence.
- Clear development requests route automatically; operation IDs are optional.
- Risky or cross-boundary changes show a pre-change preview before edits.
- Use `.ai/assistant/templates/operation-request.md` for structured requests.
- When team collaboration is enabled, use `Alatyr set actor <actor>`, `Alatyr who am I`, `Alatyr team status`, `Alatyr start`, `Alatyr claim`, `Alatyr conflicts`, `Alatyr checkpoint`, `Alatyr handoff`, `Alatyr decision`, `Alatyr review`, `Alatyr merge check`, or `Alatyr release`. Actor selection is local attribution, not authentication or authority.
- When architecture knowledge is enabled, use `Alatyr architecture` to inventory, explain, discuss, compare, review, or document project architecture and patterns.

Available next actions:
- `create-project-blueprint`: create or repair project source-of-truth docs from target evidence.
- `recheck-after-installation`: verify the installed adapter and report gaps.
- `product-change`: run blueprint-driven change from intent through validation and evidence.
- `logical-integrity-review`: check consistency across code, docs, tests, diagrams, prompts, skills, gates, and bridges.
- `architecture-assistance`: discuss project architecture and patterns from a compact evidence-backed catalog; observed or proposed items are not accepted architecture.
- `documentation-sync`: propose project-area comment styles, document selected
  symbols, or generate derived reference documentation through one accepted
  frontend, backend, shared, or infrastructure profile when the optional
  module is enabled.
- `project-vocabulary`: explain project terms, resolve aliases or acronyms,
  propose glossary entries, or check terminology through scoped target-owned
  records when the optional module is enabled.
- `test-first-configuration`: use `Alatyr enable test-first` to assess and
  configure project-adapted triggers, commands, isolation, exceptions, and
  evidence. Use `Alatyr test first` for an enabled policy; suggestions remain
  non-blocking unless the accepted target trigger is required.
- `diagram-discussion`: show, compare, or revise a diagram using `Alatyr
  diagram`; the adapter uses compact current-surface evidence, stable draft
  lineage, security/privacy policy, and a portable ASCII view. Accepted/derived
  views require project-owner and source-revision evidence.
- `large-task`: coordinate cross-boundary or resumable work with bounded workstreams, checkpoints, and final convergence.
- Change packages activate automatically for coherent material outcomes,
  semantic multi-surface approval, audit, or publishable provenance when the
  optional module is enabled; ordinary local tasks do not create one.
- `team-identity`, `team-status`, and related team operations: select ignored local attribution, coordinate target-owned actors and conflict-safe task records, run active-work preflight, and preserve revision-bound handoff, decision, review, and merge evidence when enabled.
- `ai-infrastructure-inventory`: check existing AI instructions, prompts, skills, wrappers, bridges, rules, MCP/tool configs, gates, and checkers. Alias: `alatyr-ai-inventory`.
- `ai-infrastructure-recommendation`: suggest new items or improvements to existing items from bounded project evidence in read-only mode. Aliases: `alatyr-suggest-ai <scope>`, `alatyr-improve-ai <item-id>`.
- `skill-adaptation`: adapt or add skills, prompts, wrappers, bridges, rules, MCP/tool configs, gates, checkers, or third-party assistant infrastructure. Aliases: `alatyr-adaptation <source>`, `alatyr-add-ai <source>`.
- `extension-management`: list, inspect, plan, install, update, disable, remove, or review declarative extension packages. Aliases: `Alatyr extensions`, `Alatyr inspect extension <source>`, `Alatyr add extension <source>`, `Alatyr update extension <id>`, `Alatyr disable extension <id>`, `Alatyr remove extension <id>`, `Alatyr review extension <id>`.
- `Alatyr suggest extensions <scope>` routes to read-only AI infrastructure recommendation and does not fetch or install source.
- AI infrastructure operations select a route and item ID before loading item-specific context.
- Use `continue large task <packet-path-or-operation-id>` to resume a target-approved operation packet without reloading completed workstream context.

Validation run:
`{VALIDATION_RUN_OR_UNRESOLVED}`

Known adapter gaps:
`{KNOWN_GAPS_OR_NONE}`

Suggested first request:
Alatyr status
```
