# Installed Alatyr Operation Request Template

Use this prompt when a target repository already has Alatyr Core installed and
you want an assistant to use that installed adapter.

```text
Use the installed Alatyr Core adapter in the target repository.

Target repository path:
<path-or-repo-url-to-target-project>

Operation type:
<help/create-project-blueprint/recheck-after-installation/recheck-after-framework-update/product-change/logical-integrity-review/skill-adaptation/drift-review/documentation-sync/adapter-maturity-review/other>

Goal:
<what the assistant should accomplish>

Non-goals:
<what must not be changed>

Known context:
<changed facts, framework update source, existing docs, or suspected drift>

Constraints:
- Read the target `AGENTS.md`, `AI_ASSISTANTS.md`, `.ai/README.md`,
  `.ai/framework`, `.ai/project`, and `.ai/assistant` files before changing
  anything.
- If the operation is unclear, read `.ai/assistant/help.md`, show the
  operation choices with descriptions, and ask for the smallest missing
  decision before editing files.
- Use target source-of-truth docs and target evidence only.
- For blueprint creation or repair, keep missing target facts marked as
  missing instead of inventing business rules, architecture, security policy,
  validation commands, diagrams, or lifecycle notes.
- For a framework update or adapter recheck, compare installed framework files,
  target adapter references, bridge files, gates, prompts, skills, lifecycle
  notes, and validation expectations.
- Ask for explicit approval before changing architecture, accepted business
  behavior, security/live-service behavior, destructive behavior, production
  dependencies, gates, approvals, or existing AI instructions.
- Run only target validation that exists; report unresolved checks.
- Report final evidence: files inspected, changed facts, files changed,
  approvals, validation, skipped checks, adapter gaps, and residual risk.
```

This template does not define a universal command. It gives an assistant a
portable request shape for operating an installed Alatyr Core adapter.
