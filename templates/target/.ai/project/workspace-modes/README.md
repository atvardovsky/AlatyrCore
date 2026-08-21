# Project Workspace Modes

This directory contains user-owned development modes for `{PROJECT_NAME}`.
Canonical rules are in `.ai/framework/workspace-modes.md`.

- `catalog.json` is the compact workspace and mode index.
- `root/` contains optional support shared by selected modes.
- `modes/<mode-id>/` contains one `mode.json` and one human `README.md` for
  every actual mode.
- `modes/_template/` is an authoring template and is never an active mode.

Each catalog mode entry contains `id`, `title`, `state`, `mode_kind`, `path`,
`summary`, and `evidence_revision`. The path must be
`.ai/project/workspace-modes/modes/<mode-id>/mode.json` and agree with the
descriptor identity, kind, and state.

Modes select context and explain workspace/artifact relationships. They do not
grant write scope, approval, permissions, authority, or permission to bypass
validation. Keep detailed project facts in their canonical project sources and
link to them from mode records.
