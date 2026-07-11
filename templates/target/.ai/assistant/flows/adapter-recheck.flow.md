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
- Chat-message templates: `.ai/assistant/templates/post-install-message.md`,
  `.ai/assistant/templates/post-update-message.md`
- Migration note template: `.ai/assistant/templates/migration-note.md`
- Effectiveness report template:
  `.ai/assistant/templates/effectiveness-report.md`
- Known adapter gaps: `{KNOWN_GAPS}`

## Steps

1. Load `AGENTS.md`, `AI_ASSISTANTS.md`, `.ai/alatyr.yaml`, `.ai/README.md`,
   `.ai/assistant/context-router.json`,
   `.ai/assistant/context-profiles.md`, `.ai/project`, and `.ai/assistant`.
2. Identify whether this is a post-installation recheck, framework update
   recheck, bridge compatibility review, or maturity audit.
3. Compare installed framework files against the recorded framework baseline or
   update source.
4. Compare framework version, adapter schema version, template version, module
   states, known gaps, local deviations, and owner facts in `.ai/alatyr.yaml`.
5. Check required core and optional module state in
   `.ai/assistant/module-profile.md`.
6. Check target adapter references to framework files, operation help, routing
   flows, AI infrastructure inventory, gates, prompts, skills, bridge files,
   checker rules, chat-message templates, and final-evidence expectations.
7. Check project blueprint/source-of-truth ownership, registry entries,
   missing facts, and drift.
8. Check security, live-service, destructive-operation, dependency, credential,
   diagram, generated-artifact, validation, and lifecycle policies.
9. Check task-specific maturity using `.ai/assistant/maturity-profile.md` when
   it exists.
10. Check bridge behavior using `.ai/assistant/bridge-capability-matrix.md`.
11. Identify required migrations, approvals, unresolved facts, and skipped
   checks.
12. Use `.ai/assistant/templates/migration-note.md` when a framework update
    requires target migration evidence.
13. Use `.ai/assistant/templates/effectiveness-report.md` only when comparing
    adapter effectiveness across comparable tasks or adapter states.
14. Run target validation that exists. Do not invent commands.
15. Report final evidence and residual risk.

## Final Evidence

Report:

- recheck type
- framework baseline or update source
- framework version, adapter schema version, and template version
- files inspected
- adapter references changed or still current
- blueprint/source-of-truth registry status
- context router and context profile status
- module profile status
- help, routing, AI infrastructure inventory, bridge, prompt, skill, gate,
  checker, diagram, chat-message, and lifecycle status
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
