# AI Assistant Entry Point

All assistants should treat `AGENTS.md` as the canonical instruction file for
working on Alatyr Core.

If you are installing Alatyr Core into a target project:

1. Read `README.md`.
2. Read `INSTALL.md`.
3. Read all files under `framework/`, including logical integrity,
   blueprint-driven change, and skill adaptation guidance.
4. Read `installer/assistant-installation.flow.md`.
5. Read `installer/readiness-checklist.md`.
6. Read `installer/installation-plan-template.md`.
7. Inspect the target repository before writing files.
8. Create an installation plan.
9. Rewrite target adapter facts from target evidence.
10. Use `templates/target` only as placeholders.
11. Do not invent target validation commands.
12. Report unresolved checks and residual risk.

Assistant-specific target bridge files should be short pointers to target
canonical files. Do not duplicate full Alatyr Core policy into bridge files.
