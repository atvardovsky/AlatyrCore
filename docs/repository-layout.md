# Repository Layout

Alatyr Core is split by ownership.

## `framework/`

Portable framework core.

These files describe reusable assistant operating rules. They must not contain
target project business facts, local commands, test folders, security policy,
diagram tooling, or lifecycle facts from one project.

An assistant normally adapts these files into a target repository under
`.ai/framework`.

## `installer/`

Assistant-readable installation process.

These files tell an assistant how to inspect a target repository, prepare an
installation plan, classify files by contour, request approval when needed, and
report final evidence.

## `templates/target/`

Starter files for a target project.

These files are intentionally incomplete. They contain placeholders and
instructions. The installing assistant must rewrite them from target facts
before claiming installation is complete.

## `docs/`

Maintainer-facing explanation of Alatyr Core itself.

Docs should explain how to work on this source repository without turning
source repository details into framework requirements.

## Root Files

- `README.md`: main assistant and maintainer entry point.
- `AGENTS.md`: canonical instructions for assistants working on Alatyr Core.
- `AI_ASSISTANTS.md`: generic assistant entry point.
- `INSTALL.md`: human-readable installation guide.
- `CHANGELOG.md`: framework lifecycle notes.

## Ownership Rule

If a fact describes how assistants should generally work, it may belong in
`framework/`.

If a fact describes how to install Alatyr Core into a target project, it may
belong in `installer/`.

If a fact describes an example target file shape, it may belong in
`templates/target/`, but it must remain placeholder-based.

If a fact describes one real project, it does not belong in Alatyr Core.

