# AI Assistant Entry Point

All assistants should treat `AGENTS.md` as the canonical instruction file for
working on Alatyr Core.

Rule references for installation routing: `ALATYR-CONTEXT-001`,
`ALATYR-ADAPTER-001`, `ALATYR-APPROVAL-001`, `ALATYR-SAFETY-001`,
`ALATYR-SAFETY-002`, and `ALATYR-EVIDENCE-001`.

If you are installing Alatyr Core into a target project:

1. Read `README.md`.
2. Read `INSTALL.md`.
3. Read `AGENTS.md`, `framework/README.md`,
   `framework/context-profiles.md`, `framework/project-adapter-contract.md`,
   `framework/portability.md`, `framework/module-profile.md`,
   `framework/rule-ownership.md`, `framework/rule-registry.md`, and
   `framework/rule-registry.json`.
4. Read `installer/assistant-installation.flow.md`.
5. Read `installer/readiness-checklist.md`.
6. Read `installer/installation-plan-template.md`.
7. Inspect the target repository before writing files.
8. Create an installation plan.
9. Read each framework file before copying or adapting it into target
   `.ai/framework`; full-core installs read the full framework corpus at that
   stage.
10. Rewrite target adapter facts from target evidence.
11. Use `templates/target` only as placeholders.
12. Do not invent target validation commands.
13. Report unresolved checks and residual risk.

Assistant-specific target bridge files should be short pointers to target
canonical files. Do not duplicate full Alatyr Core policy into bridge files.
