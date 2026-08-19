# AI Assistant Entry Point

All assistants should treat `AGENTS.md` as the canonical instruction file for
working on Alatyr Core.

Rule references for installation routing: `ALATYR-CONTEXT-001`,
`ALATYR-ADAPTER-001`, `ALATYR-APPROVAL-001`, `ALATYR-SAFETY-001`,
`ALATYR-SAFETY-002`, `ALATYR-OPERATION-001`,
`ALATYR-ARCHITECTURE-001`, `ALATYR-VOCABULARY-001`,
`ALATYR-TDD-001`, `ALATYR-EXTENSION-001`, `ALATYR-DIAGRAM-001`, and
`ALATYR-EVIDENCE-001`.
When the optional team module is selected, also apply `ALATYR-TEAM-001`.

If you are installing Alatyr Core into a target project:

1. Treat `AGENTS.md` as host-preloaded context.
2. Read `installer/context-router.json` and select the current stage.
3. Inspect the target repository before writing files.
4. Load only stage-required canonical owners and selected target templates.
5. Create and review an installation plan before protected changes.
6. Use `framework/file-inventory.json` for deterministic file and hash
   comparison without loading unchanged framework prose.
7. Rewrite target adapter facts from target evidence.
8. Use `templates/target` only as placeholders.
9. Do not invent target validation commands.
10. Report unresolved checks and residual risk.

Assistant-specific target bridge files should be short pointers to target
canonical files. Do not duplicate full Alatyr Core policy into bridge files.
