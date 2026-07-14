# Scaffolding

Scaffolding is an optional helper step that can create placeholder directories
and files before an assistant performs the real installation work.

Scaffolding is not installation. It does not inspect target facts, choose
project source-of-truth owners, approve overwrites, fill placeholders, or
claim the adapter is usable.

## Allowed Scaffolder Behavior

A safe scaffolder may:

- create missing directories
- copy placeholder target templates
- copy portable framework documents and `framework/rule-registry.json` into
  `.ai/framework`
- create an empty or placeholder manifest
- run in dry-run mode
- refuse to overwrite existing files by default
- report skipped files and protected surfaces

## Forbidden Scaffolder Behavior

A scaffolder must not:

- fill project facts from guesses
- overwrite existing target instructions without explicit approval
- change product code, tests, runtime config, CI, secrets, or dependencies
- import third-party AI infrastructure into canonical target files
- claim installation is complete
- replace target repository inspection, readiness review, installation plan,
  approval gates, logical integrity review, or final evidence

## Source Repository Helper

The AlatyrCore source repository may include helper scripts for maintainers,
such as `tools/scaffold_target_structure.py`.

Those helpers validate or scaffold source templates. They are not portable
framework requirements and must not be copied into target repositories as
required validation or installation commands.

Source conformance helpers may materialize temporary fixture repositories to
check scaffolder behavior. Such checks validate source templates and helper
behavior only; they are not assistant installation tests and do not prove a
target adapter is complete.

Source helpers should be platform-neutral when practical. The canonical
scaffolder is Python standard-library code and may provide thin launch wrappers
for Windows shells. Wrapper files must delegate to the canonical helper and
must not duplicate installation logic.

A source scaffolder may expose bounded support profiles when their contents are
deterministic and machine-checked:

- `core`: required adapter, routing, ownership, integrity, evidence, and
  manifest-referenced support surfaces
- `standard`: core plus common blueprint, recheck, help, and lifecycle
  operation surfaces
- `full`: all target templates, optional modules, and assistant bridges

The selected scaffold profile limits placeholder files only. It does not
enable modules, choose supported assistants, resolve target facts, or prove
installation maturity. Keep the complete portable framework copy available so
the target can enable modules later without changing the framework baseline.

## Final Evidence

If scaffolding was used, installation evidence should report:

- helper name and mode
- selected scaffold profile
- target path
- files created
- files skipped because they already existed
- whether any overwrite approval was used
- remaining placeholders
- confirmation that target facts still need assistant and human review
