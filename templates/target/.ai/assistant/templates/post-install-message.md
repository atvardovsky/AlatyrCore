# Post-Install Assistant Chat Message

Use this template for the assistant's chat response after Alatyr Core is
installed in `{PROJECT_NAME}`.

Replace placeholders with target facts before sending the message.

Delivery evidence is separate from this template. Record `sent`, `skipped`, or
`blocked`, together with the delivery mechanism, reason, and observation time.
The presence of this file never proves that a chat message reached a user.

```text
Alatyr Core is installed for `{PROJECT_NAME}`.

Installation state: `{SCAFFOLDED_STAGED_ACCEPTED_DEGRADED_OR_INVALID}`
Adapter health: `{READY_ATTENTION_BLOCKED_OR_UNVERIFIED}`
Acceptance eligible: `{YES_OR_NO_WITH_REASON}`

`scaffolded`, `staged`, and `degraded` installations are not `ready`.
Only `accepted` installation state with current strict validation can be
reported as `ready`.

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
- `.ai/assistant/policies/action-authorization.json`
- `.ai/assistant/context-router.json`
- `.ai/assistant/bootstrap-index.json`
- `.ai/framework/context-index.json`, `.ai/project/context-index.json`, and
  `.ai/assistant/context-index.json`
- `.ai/project/support-policy.json` and final `.ai/support-state.json`
- `.ai/framework/semantics/index.json`
- `.ai/assistant/gates/index.json`
- `.ai/assistant/context-profiles.md`
- `.ai/assistant/module-profile.md`
- `.ai/project/source-of-truth-registry.md`
- `.ai/project/engineering-evidence/index.json` and its target storage policy
- `.ai/project/knowledge/index.json`, reviewed promotions, compact route shards,
  and `.ai/assistant/context/project-knowledge-routing.json`
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/debug/index.json"]} -->
- `.ai/project/debug/index.json` and its non-canonical storage/privacy policy
  when optional Debug Mode is enabled
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/consistency-map.json"]} -->
- `.ai/project/consistency-map.json` when the optional module is enabled
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/architecture/catalog.json"]} -->
- `.ai/project/architecture/README.md` and `.ai/project/architecture/catalog.json` when architecture knowledge is enabled
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/documentation/catalog.json"]} -->
- `.ai/project/documentation/catalog.json` and `.ai/project/documentation/profiles.json` when code documentation is enabled
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/vocabulary/catalog.json"]} -->
- `.ai/project/vocabulary/catalog.json`, `.ai/project/vocabulary/terms.json`, and `.ai/project/vocabulary/data-dictionary-links.json` when project vocabulary is enabled
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/testing/test-first-policy.json"]} -->
- `.ai/project/testing/test-first-policy.json` when test-first development is enabled
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/team-policy.json"]} -->
- `.ai/project/team-policy.json`, `.ai/assistant/team/active-work-index.json`, and `.ai/assistant/team/work-registry.json` when team collaboration is enabled
<!-- /alatyr:scaffold-fragment -->
- `.ai/assistant/maturity-profile.md`
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/bridge-capability-matrix.md"]} -->
- `.ai/assistant/bridge-capability-matrix.md`
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/assistant-capabilities.json"]} -->
- `.ai/assistant/assistant-capabilities.json`
- For the selected assistant surface, resolve its provider/model cache mode,
  exposed controls, telemetry, and freshness from the indexed capability
  record. Keep stable semantic context before task-specific context, but use
  bounded routing normally when caching is unsupported or unknown. Do not
  treat cached input as removed from the model context window.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/delegation-policy.json",".ai/assistant/workers/role-catalog.json",".ai/assistant/prompts/worker-orchestration.md"]} -->
- `.ai/assistant/delegation-policy.json`, `.ai/assistant/workers/role-catalog.json`, and `.ai/assistant/prompts/worker-orchestration.md` when subagent delegation is enabled
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/ai-infrastructure-router.json"]} -->
- `.ai/assistant/ai-infrastructure-router.json` when AI infrastructure is enabled
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/extensions/catalog.json",".ai/assistant/extensions/lock.json"]} -->
- `.ai/assistant/extensions/catalog.json` and `.ai/assistant/extensions/lock.json` when extensions are enabled
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/dependencies/policy.json"]} -->
- `.ai/project/dependencies/policy.json`, `catalog.json`, `knowledge-lock.json`, and `deviations.json` when dependency knowledge is enabled
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/workspace-modes/catalog.json"]} -->
- `.ai/project/workspace-modes/catalog.json`, optional root context, and one subdirectory per actual mode when workspace modes are enabled
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/change-packages/index.json"]} -->
- `.ai/assistant/change-packages/index.json` when change packages are enabled
<!-- /alatyr:scaffold-fragment -->

Future assistant bootstrap:
- Do not rely on this chat message alone.
- Treat `AGENTS.md` as preloaded; start from
  `.ai/assistant/bootstrap-index.json`, then
  `.ai/assistant/entry-packet.json`.
- Use the bootstrap's resolved core semantic definitions once. Follow only
  task-selected branches from the three contour context indexes; a parent
  index does not authorize loading every child.
- Repair stale recursive indexes and then the bootstrap from their named
  sources; otherwise load profiles, module state, registries, blueprint, gate
  fragments, and the installation note only when routing or unclear adapter
  state requires them. Fall back to canonical owner prose when a compact term
  cannot be resolved exactly.
- Rebuild the entry packet, optional consistency/generation indexes, and
  recursive context indexes before refreshing support state. Use support
  differences to select context; do not infer semantic correctness from
  matching hashes.
- Send `Alatyr` for compact actions or `Alatyr status` for a read-only adapter health check.
- If the installation itself is unclear, run `recheck-after-installation` before editing files.
- Re-evaluate the newest request at every action-phase boundary. A completed
  task's edit, commit, or push authorization does not carry into a new issue,
  backlog item, discussion, report, or subject switch.

Installed operation help:
- Send `Alatyr` to see adapter state and up to three relevant operations.
- Send `Alatyr status` or `Alatyr doctor` for read-only health evidence.
- Clear development requests route automatically; operation IDs are optional.
- Issue/backlog returns, status requests, discussion, analysis, plans, reports,
  and ambiguous continuation are read-only until the current request explicitly
  authorizes implementation. Implementation intent does not authorize commit
  or push, and commit intent does not authorize push.
- Risky or cross-boundary changes show a pre-change preview before edits.
- Use `.ai/assistant/templates/operation-request.md` for structured requests.
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/team-policy.json"]} -->
- When team collaboration is enabled, use `Alatyr set actor <actor>`, `Alatyr who am I`, `Alatyr team status`, `Alatyr start`, `Alatyr claim`, `Alatyr conflicts`, `Alatyr checkpoint`, `Alatyr handoff`, `Alatyr decision`, `Alatyr review`, `Alatyr merge check`, or `Alatyr release`. Actor selection is local attribution, not authentication or authority.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/architecture/catalog.json"]} -->
- When architecture knowledge is enabled, use `Alatyr architecture` to inventory, explain, discuss, compare, review, or document project architecture and patterns.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/workspace-modes/catalog.json"]} -->
- Review installation mode suggestions separately. Installation approval does
  not accept a suggested mode. Use `Alatyr suggest modes`, then `Alatyr accept
  mode <id>` only for a mode the user chooses.
<!-- /alatyr:scaffold-fragment -->

Available next actions:
- `create-project-blueprint`: create or repair project source-of-truth docs from target evidence.
- `project-knowledge`: explain, route, review, promote, reject, defer, record
  registered decision-owner guidance or an explicit exception, supersede, or
  revalidate reusable project guidance without treating historical evidence as
  current authority.
- `recheck-after-installation`: verify the installed adapter and report gaps.
- `product-change`: run blueprint-driven change from intent through validation and evidence.
- `logical-integrity-review`: check consistency across code, docs, tests, diagrams, prompts, skills, gates, and bridges.
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/flows/architecture-assistance.flow.md"]} -->
- `architecture-assistance`: discuss project architecture and patterns from a compact evidence-backed catalog; observed or proposed items are not accepted architecture.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/documentation/catalog.json"]} -->
- `documentation-sync`: propose project-area comment styles, document selected
  symbols, or generate derived reference documentation through one accepted
  frontend, backend, shared, or infrastructure profile when the optional
  module is enabled.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/flows/project-vocabulary.flow.md"]} -->
- `project-vocabulary`: explain project terms, resolve aliases or acronyms,
  propose glossary entries, or check terminology through scoped target-owned
  records when the optional module is enabled.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/testing/test-first-policy.json"]} -->
- `test-first-configuration`: use `Alatyr enable test-first` to assess and
  configure project-adapted triggers, commands, isolation, exceptions, and
  evidence. Use `Alatyr test first` for an enabled policy; suggestions remain
  non-blocking unless the accepted target trigger is required.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/flows/diagram-discussion.flow.md"]} -->
- `diagram-discussion`: show, compare, or revise a diagram using `Alatyr
  diagram`; the adapter uses compact current-surface evidence, stable draft
  lineage, security/privacy policy, and a portable ASCII view. Accepted/derived
  views require project-owner and source-revision evidence.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/flows/large-task-orchestration.flow.md"]} -->
- `large-task`: coordinate cross-boundary or resumable work with bounded workstreams, checkpoints, and final convergence.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/delegation-policy.json"]} -->
- `subagent-delegation`: when enabled, let the primary assistant propose or
  dispatch bounded worker tasks through project-owned roles and the selected
  current assistant capability. Unsupported clients continue sequentially;
  native worker support and model choice are never inferred.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/change-packages/index.json"]} -->
- Change packages activate automatically for coherent material outcomes,
  semantic multi-surface approval, audit, or publishable provenance when the
  optional module is enabled; ordinary local tasks do not create one.
<!-- /alatyr:scaffold-fragment -->
- `engineering-evidence`: use `Alatyr evidence`, `Alatyr capture evidence`, or
  `Alatyr explain decision <evidence-id>`. Material tasks preserve compact
  reusable conclusions when triggered; small self-explanatory tasks may skip
  with a specific reason. Raw assistant reasoning is never retained.
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/flows/debug-mode.flow.md"]} -->
- `debug-mode`: when enabled, use `Enable Alatyr Debug Mode for this task`,
  `Alatyr debug status`, `Alatyr debug checkpoint`, `Alatyr debug summary`,
  `Disable Alatyr Debug Mode`, or `Alatyr compare debug`. The module starts
  inactive; each task/session needs explicit activation, and no engineering,
  commit, push, publication, or live-action permission is granted.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/team-policy.json"]} -->
- `team-identity`, `team-status`, and related team operations: select ignored local attribution, coordinate target-owned actors and conflict-safe task records, run active-work preflight, and preserve revision-bound handoff, decision, review, and merge evidence when enabled.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/ai-infrastructure-router.json"]} -->
- `ai-infrastructure-inventory`: check existing AI instructions, prompts, skills, wrappers, bridges, rules, MCP/tool configs, gates, and checkers. Alias: `alatyr-ai-inventory`.
- `ai-infrastructure-recommendation`: suggest new items or improvements to existing items from bounded project evidence in read-only mode. Aliases: `alatyr-suggest-ai <scope>`, `alatyr-improve-ai <item-id>`.
- `skill-adaptation`: adapt or add skills, prompts, wrappers, bridges, rules, MCP/tool configs, gates, checkers, or third-party assistant infrastructure. Aliases: `alatyr-adaptation <source>`, `alatyr-add-ai <source>`.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/extensions/catalog.json"]} -->
- `extension-management`: list, inspect, plan, install, update, disable, remove, or review declarative extension packages. Aliases: `Alatyr extensions`, `Alatyr inspect extension <source>`, `Alatyr add extension <source>`, `Alatyr update extension <id>`, `Alatyr disable extension <id>`, `Alatyr remove extension <id>`, `Alatyr review extension <id>`.
- `Alatyr suggest extensions <scope>` routes to read-only AI infrastructure recommendation and does not fetch or install source.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/dependencies/policy.json"]} -->
- `dependency-knowledge`: report, discover, inspect, plan, synchronize, explain, or assess passive dependency knowledge. Aliases: `Alatyr dependencies`, `Alatyr sync dependencies`, `Alatyr explain dependency <package>`, `Alatyr dependency impact <package-or-change>`. It does not run package managers, update packages, or activate nested adapters.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/project/workspace-modes/catalog.json"]} -->
- `workspace-mode`: list, suggest, inspect, select, define, accept, update,
  disable, deprecate, remove, or review user-owned workspace modes. Aliases:
  `Alatyr modes`, `Alatyr suggest modes`, `Alatyr mode <id>`, `Alatyr define
  mode`, and `Alatyr accept mode <id>`. A mode selects context only.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/ai-infrastructure-router.json"]} -->
- AI infrastructure operations select a route and item ID before loading item-specific context.
<!-- /alatyr:scaffold-fragment -->
<!-- alatyr:scaffold-fragment {"requires_paths":[".ai/assistant/flows/large-task-orchestration.flow.md"]} -->
- Use `continue large task <packet-path-or-operation-id>` to resume a target-approved operation packet without reloading completed workstream context.
<!-- /alatyr:scaffold-fragment -->

Validation run:
`{VALIDATION_RUN_OR_UNRESOLVED}`

Known adapter gaps:
`{KNOWN_GAPS_OR_NONE}`

Delivery status: `{SENT_SKIPPED_OR_BLOCKED}`
Delivery mechanism: `{CHAT_SURFACE_OR_UNAVAILABLE}`
Delivery reason: `{WHY_SENT_SKIPPED_OR_BLOCKED}`
Delivery observed at: `{DELIVERY_TIMESTAMP_OR_NOT_OBSERVED}`

Suggested first request:
Alatyr status
```
