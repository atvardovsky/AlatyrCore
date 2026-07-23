# Migration Diff

Migration diff is the process for comparing two Alatyr framework baselines and
turning the difference into target adapter actions.

It is not an automatic upgrade mechanism. It is evidence used by an assistant
and programmer before applying protected target changes.

## Inputs

- previous framework version
- next framework version
- previous adapter schema version
- next adapter schema version
- previous template version
- next template version
- changed rule IDs
- changed framework file hashes or file list
- added or removed framework files
- changed target template surfaces
- local deviations in the installed adapter
- adapter schema, template, rule registry, rule owner, framework-file, and
  target-template impact

## Output Contract

A migration diff should report:

- added rules
- changed rules
- removed or deprecated rules
- required target actions
- optional target actions
- affected target surfaces
- affected rule categories
- affected task profiles
- affected canonical framework sources
- migration action hints
- bridge capability impact
- enabled optional-module impact, including stateful record schemas and lazy
  routing surfaces
- approval requirements
- validation or manual review
- residual risk

Target adapters may store the result in a migration note.

## Migration-First Context Routing

Generate or review migration evidence before loading broad upgrade context.
Start with lifecycle guidance, this migration contract, the installed rule
registry and manifest, the adapter recheck flow, and existing migration or
installation notes. Then use the report's changed rule IDs, categories, task
profiles, canonical sources, framework files, target template surfaces, and
local deviations to select additional files.

Record selected and intentionally omitted canonical sources in the context
receipt. A migration report that identifies no impact does not prove target
compatibility; structural and target validation still apply.

## Safety Rules

Do not apply target changes directly from a diff.

If the diff affects protected categories, existing AI instructions, imported
assistant infrastructure, bridge loading behavior, validation gates, approval
rules, or source-of-truth ownership, require explicit approval before changing
target files.

If an enabled module contains target state, such as the team work registry,
the migration assessment must distinguish source template changes from target
records. Preserve current IDs and evidence, plan schema conversion from a copy,
and never apply the source placeholder as an update.

## Source-Repository Tooling

The AlatyrCore source repository includes `tools/report_migration_diff.py`,
which compares two `framework/rule-registry.json` files and emits a Markdown
report. When given `--from-framework-dir`, it also compares framework file
names and content hashes against the next framework directory. When given
`--from-template-dir`, it compares target template surface names and content
hashes against the next target template directory. The report also summarizes
affected rule categories, task profiles, canonical sources, adapter contract
impact, and migration action hints. The report is evidence only; it must not
overwrite target adapter files without approval.

`tools/validate_target_adapter.py` can consume a reviewed migration report via
`--migration-diff <report.md>` while checking an installed adapter. That check
does not apply an upgrade; it only reports whether framework drift has
rule/category/action evidence attached to the recheck.

`tools/plan_target_upgrade.py` composes the migration report and structural
validator into an assessment directory before target changes. The
cross-platform `tools/alatyr.py assess-upgrade` entry point exposes the same
source helper on Linux, macOS, and Windows. These helpers write evidence only;
they are not the installation mechanism and do not apply an upgrade.
