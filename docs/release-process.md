# Release Process

This is the maintainer process for releasing the AlatyrCore source
repository. It is not an installed target adapter requirement.

Target repositories use their own release, validation, approval, and migration
processes. AlatyrCore releases provide source framework evidence that target
adapters can use during `recheck-after-framework-update`.

## Version Files

AlatyrCore tracks three source versions:

- `VERSION`: framework version.
- `ADAPTER_SCHEMA_VERSION`: installed-adapter schema version.
- `TEMPLATE_VERSION`: target template version.

`VERSION` uses SemVer-like syntax:

```text
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
```

`ADAPTER_SCHEMA_VERSION` and `TEMPLATE_VERSION` are positive integers. Increase
them only when installed adapter manifests or target templates need migration
attention.

## Changelog

`CHANGELOG.md` keeps an `Unreleased` section.

Before a release:

- move accepted changes from `Unreleased` into a versioned section
- name added, changed, deprecated, removed, fixed, and security-relevant items
  when applicable
- call out added, changed, removed, or deprecated rule IDs
- call out framework version, adapter schema version, and template version
  changes
- call out required target migration actions and optional target actions
- leave a new empty `Unreleased` section for future work

During active development, `Unreleased` may contain pending entries.

## Migration Evidence

For releases that affect installed adapters, prepare migration evidence from:

- `framework/rule-registry.json`
- `framework/rule-ownership.md`
- framework file-list or content-hash comparison
- target template changes
- adapter schema or template version changes
- bridge capability changes
- prompt-injection, approval, operation, context-profile, or module-profile
  contract changes

Use `docs/release-migration-report-template.md` as the source report shape.
It is separate from the installed target adapter migration-note template.

Use `tools/report_migration_diff.py` to generate source migration evidence
when comparing two framework baselines. The report is evidence only; it does
not update target repositories. It should include adapter contract impact,
affected rule categories, affected task profiles, affected canonical sources,
and migration action hints.

Store the reviewed report for a tagged version at
`docs/releases/<VERSION>-migration.md`. The report must name the compared
source baseline, all three version values, required target actions, validation,
and residual risks. Generated output is a starting point; replace temporary
paths and unresolved version labels before accepting it as release evidence.

## Pre-Release Checklist

Before tagging a source release:

- update `VERSION` when the framework version changes
- update `ADAPTER_SCHEMA_VERSION` when installed adapter schema changes
- update `TEMPLATE_VERSION` when target template contracts change
- update `CHANGELOG.md`
- add `docs/releases/<VERSION>-migration.md`
- update `framework/rule-registry.md` and `framework/rule-registry.json` when
  rule IDs, rule summaries, owners, dependencies, or enforcement levels change
- update `framework/rule-ownership.md` when category owners change
- update target templates and conformance fixtures when installable surfaces
  change
- run source-repository checks listed in `docs/framework-maintenance.md`
- run `tools/check_release_migration_template.py`
- run `tools/check_migration_diff_report.py`
- run `tools/check_versioning.py`
- review `git diff --check`

## Tagging

Use source repository tags that match the framework version:

```text
v<VERSION>
```

Do not tag a release that has unresolved source-repository consistency
failures. If a release intentionally ships unresolved target-adapter migration
work, record it in the changelog and migration evidence.

## Target Adapter Update Message

After a target project consumes a new AlatyrCore release, the installed adapter
should route future work through its post-update message and
`recheck-after-framework-update` operation. The target adapter decides local
validation, approval, and migration application.
