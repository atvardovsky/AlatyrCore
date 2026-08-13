# Alatyr Extension Package Template

This directory is an authoring example for a declarative Alatyr extension
repository. It is not an installed target extension and is not loaded as
AlatyrCore framework policy.

Copy and adapt `alatyr-extension.json` in an extension repository. Replace all
placeholders, add the declared files below `items/`, and validate the local
checkout with:

```sh
python3 /path/to/AlatyrCore/tools/alatyr.py inspect-extension --package .
python3 /path/to/AlatyrCore/tools/alatyr.py inspect-extension --package . --target /path/to/installed-target
```

The validator performs read-only structural and digest checks. With `--target`,
it also compares framework, adapter schema, template, and required-rule
compatibility with the target's installed manifest and rule registry. It does
not execute extension instructions or prove that the package is trustworthy,
licensed correctly, useful, or semantically compatible with that project.

Canonical rules are owned by `framework/extensions.md` and
`framework/prompt-injection.md`.
