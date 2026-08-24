# Contributing To AlatyrCore

Start with [AGENTS.md](AGENTS.md) for repository bootstrap and authorization
rules, then use the smallest source context profile that matches the change.
The detailed maintenance and validation contract is in
[docs/framework-maintenance.md](docs/framework-maintenance.md).

## Change Boundaries

- Keep portable framework rules under `framework/` free of target-project
  business facts and local commands.
- Keep installer guidance, target templates, maintainer documentation, schemas,
  and source tooling in their existing ownership contours.
- Treat discussion, modification, commit, publication, and live external
  actions as separate current-scope authorization phases.
- Update generated surfaces only through their owning renderer and review the
  resulting diff.
- Record version and migration impact when framework, adapter-schema, template,
  or shipped schema contracts change.

## Validation

Run the focused checks owned by the changed surfaces, followed by:

```sh
python3 tools/check_all.py --profile full
git diff --check
```

The supported source-tooling runtime and pinned CI dependency set are recorded
in `tools/runtime-compatibility.json` and `constraints-ci.txt`. External
assistant conformance and effectiveness benchmarks incur real model usage and
must not be represented as executed unless captured evidence exists.

## Review Evidence

Describe changed facts, affected owners, validation, generated outputs,
remaining limitations, and version impact. Passing deterministic checks proves
the checked structural contracts; it does not prove target-project semantics,
assistant interpretation, or broad cost improvement.
