# Adapter Recheck Flow

Use this flow after installing or updating Alatyr Core in `{PROJECT_NAME}`, or
when the programmer asks whether the installed adapter is still coherent.

Replace placeholders with target facts before accepting installation.

## Target Sources

- Framework baseline/source: `{ALATYR_CORE_SOURCE_OR_BASELINE}`
- Adapter manifest: `.ai/alatyr.yaml`
- Installation or update note: `{INSTALLATION_OR_UPDATE_NOTE}`
- Project source of truth: `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- Source-of-truth registry: `.ai/project/source-of-truth-registry.md`
- Consistency map: `.ai/project/consistency-map.json`
- Context router: `.ai/assistant/context-router.json`
- Context profiles: `.ai/assistant/context-profiles.md`
- Module profile: `.ai/assistant/module-profile.md`
- Maturity profile: `.ai/assistant/maturity-profile.md`
- Bridge capability matrix: `.ai/assistant/bridge-capability-matrix.md`
- Target validation: `{TARGET_VALIDATION}`
- Supported assistants: `{SUPPORTED_ASSISTANTS}`
- Operation help and routing: `.ai/assistant/help.md`,
  `.ai/assistant/flows/operation-routing.flow.md`
- AI infrastructure inventory:
  `.ai/assistant/flows/ai-infrastructure-inventory.flow.md`
- AI infrastructure recommendation:
  `.ai/assistant/flows/ai-infrastructure-recommendation.flow.md`,
  `.ai/assistant/templates/ai-infrastructure-recommendation.md`
- Development pattern evidence:
  `.ai/project/development-evidence.json`,
  `.ai/assistant/flows/development-evidence-capture.flow.md`
- AI infrastructure router, recommendation, and adaptation record:
  `.ai/assistant/ai-infrastructure-router.json`,
  `.ai/assistant/templates/ai-infrastructure-adaptation-record.md`
- Chat-message templates: `.ai/assistant/templates/post-install-message.md`,
  `.ai/assistant/templates/post-update-message.md`
- Migration note template: `.ai/assistant/templates/migration-note.md`
- Effectiveness report template:
  `.ai/assistant/templates/effectiveness-report.md`
- Large-task flow and packet: `.ai/assistant/flows/large-task-orchestration.flow.md`,
  `.ai/assistant/templates/large-task-operation-packet.md`
- Known adapter gaps: `{KNOWN_GAPS}`

## Steps

1. Treat `AGENTS.md` as preloaded, load the compact bootstrap, and select the
   `framework-upgrade` profile plus only affected adapter areas. Do not load
   all `.ai/project` or `.ai/assistant` files before identifying the recheck
   scope.
2. Identify whether this is a post-installation recheck, framework update
   recheck, bridge compatibility review, or maturity audit.
3. Prepare or review migration assessment evidence before target changes.
   Compare rule registries, installed and next framework files, framework
   version, adapter schema version, template version, and current structural
   validator findings.
4. Use affected canonical sources, rule categories, task profiles, template
   surfaces, bridge capabilities, and local deviations from that assessment to
   select additional context. Do not load the full framework corpus by default.
5. Compare installed framework files against the recorded framework baseline or
   update source.
6. Compare framework version, adapter schema version, template version, module
   states, known gaps, local deviations, and owner facts in `.ai/alatyr.yaml`.
7. Check required core and optional module state in
   `.ai/assistant/module-profile.md`.
8. Check target adapter references to framework files, operation help, routing
   flows, AI infrastructure inventory, recommendation and item router, gates,
   prompts, skills, recommendation/adaptation records, bridge files,
   checker rules, large-task flow and packet, chat-message templates, and
   final-evidence expectations.
9. Check adapter drift hazards: hard-coded local machine paths in `.ai/*`,
   root assistant entry points, bridge files, templates, and policies; stale
   statements about whether local Alatyr or adapter checkers exist; duplicate
   required-context references inside context profiles or router entries;
   missing `.ai/assistant/context-router.json` references where bootstrap
   routing is described; unresolved owner placeholders that are not recorded as
   known gaps; and target-local adapter checker evidence that no longer matches
   repository files.
10. Check project blueprint/source-of-truth ownership, registry entries,
   consistency-map nodes and edges when enabled, missing facts, stale
   relationships, and drift.
11. Check security, live-service, destructive-operation, dependency, credential,
   diagram, generated-artifact, validation, and lifecycle policies.
12. Check task-specific maturity using `.ai/assistant/maturity-profile.md` when
   it exists.
13. Check bridge behavior using `.ai/assistant/bridge-capability-matrix.md`.
14. Identify required migrations, approvals, unresolved facts, and skipped
   checks.
15. Use `.ai/assistant/templates/migration-note.md` when a framework update
    requires target migration evidence.
16. Use `.ai/assistant/templates/effectiveness-report.md` only when comparing
    adapter effectiveness across comparable tasks or adapter states.
17. Run target validation that exists. Do not invent commands.
18. Classify final evidence as `current-state`, `historical-record`, or `mixed`.
    Current files prove current structure only; name dated operation, approval,
    validation, or migration records before making historical claims.
19. Report final evidence and residual risk.

## Final Evidence

Report:

- recheck type
- framework baseline or update source
- migration assessment and affected canonical sources selected from it
- candidate context intentionally omitted with reasons
- framework version, adapter schema version, and template version
- files inspected
- evidence basis, observation time, and repository revision when available
- historical records used and historical claims that remain unverifiable
- adapter references changed or still current
- adapter drift checks result, including local path leakage, stale checker
  statements, duplicate profile references, context-router references, owner
  placeholders, and target-local checker evidence
- blueprint/source-of-truth registry status
- consistency-map relationship coverage and staleness status
- context router and context profile status
- module profile status
- help, routing, AI infrastructure inventory/recommendation, bridge, prompt,
  skill, gate, checker, item router, recommendation/adaptation records,
  large-task orchestration, diagram, chat-message, and lifecycle status
- development-pattern index schema, owner, retention/privacy policy, evidence
  references, and target-only optimization boundary
- bridge capability matrix status
- target validation run or unresolved
- approvals needed
- task-specific maturity level and gaps
- migration note created or not needed
- residual risk

## Rejection Criteria

Reject or revise recheck work that:

- claims success without inspecting the installed target adapter
- overwrites target facts just because the source framework changed
- copies Alatyr Core source-repository commands into the target
- ignores supported assistant bridge drift
- hides missing validation, missing approval, or maturity gaps
