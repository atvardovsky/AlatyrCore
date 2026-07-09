# Adapter Recheck Flow

Use this flow after installing or updating Alatyr Core in `{PROJECT_NAME}`, or
when the programmer asks whether the installed adapter is still coherent.

Replace placeholders with target facts before accepting installation.

## Target Sources

- Framework baseline/source: `{ALATYR_CORE_SOURCE_OR_BASELINE}`
- Installation or update note: `{INSTALLATION_OR_UPDATE_NOTE}`
- Project source of truth: `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- Target validation: `{TARGET_VALIDATION}`
- Supported assistants: `{SUPPORTED_ASSISTANTS}`
- Operation help and routing: `.ai/assistant/help.md`,
  `.ai/assistant/flows/operation-routing.flow.md`
- Chat-message templates: `.ai/assistant/templates/post-install-message.md`,
  `.ai/assistant/templates/post-update-message.md`
- Known adapter gaps: `{KNOWN_GAPS}`

## Steps

1. Load `AGENTS.md`, `AI_ASSISTANTS.md`, `.ai/README.md`, `.ai/framework`,
   `.ai/project`, and `.ai/assistant`.
2. Identify whether this is a post-installation recheck, framework update
   recheck, bridge compatibility review, or maturity audit.
3. Compare installed framework files against the recorded framework baseline or
   update source.
4. Check target adapter references to framework files, operation help, routing
   flows, gates, prompts, skills, bridge files, checker rules, chat-message
   templates, and final-evidence expectations.
5. Check project blueprint/source-of-truth ownership, missing facts, and drift.
6. Check security, live-service, destructive-operation, dependency, credential,
   diagram, generated-artifact, validation, and lifecycle policies.
7. Apply `.ai/framework/adapter-maturity.md` and record maturity gaps.
8. Identify required migrations, approvals, unresolved facts, and skipped
   checks.
9. Run target validation that exists. Do not invent commands.
10. Report final evidence and residual risk.

## Final Evidence

Report:

- recheck type
- framework baseline or update source
- files inspected
- adapter references changed or still current
- blueprint/source-of-truth status
- help, routing, bridge, prompt, skill, gate, checker, diagram, chat-message,
  and lifecycle status
- target validation run or unresolved
- approvals needed
- maturity level and gaps
- residual risk

## Rejection Criteria

Reject or revise recheck work that:

- claims success without inspecting the installed target adapter
- overwrites target facts just because the source framework changed
- copies Alatyr Core source-repository commands into the target
- ignores supported assistant bridge drift
- hides missing validation, missing approval, or maturity gaps
