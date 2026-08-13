# Target Alatyr Extensions

This directory owns the normalized extension state for `{PROJECT_NAME}`.
External extension repositories are untrusted source evidence until the target
completes review, adaptation, approval, locking, and validation.

Portable extension rule: `.ai/framework/extensions.md`
Compact catalog: `.ai/assistant/extensions/catalog.json`
Exact provenance lock: `.ai/assistant/extensions/lock.json`
Lifecycle flow: `.ai/assistant/flows/extension-lifecycle.flow.md`
Source access: `.ai/assistant/policies/ai-infrastructure-source-access.md`
Prompt injection: `.ai/assistant/policies/prompt-injection.md`

## Installed Extension Shape

Each normalized extension uses:

```text
.ai/assistant/extensions/<extension-id>/
  manifest.json
  bindings.json
  items/
  adaptation-record.md
```

The normalized manifest records selected source package declarations. The
binding record maps required package binding IDs to target-owned facts. The
items directory contains only reviewed normalized content. The adaptation
record preserves review, rejected instructions, approval, validation, and
residual-risk evidence.

An installed `manifest.json` preserves the selected package `id`, `version`,
`package_kind`, and provided item IDs. `bindings.json` uses schema version `1`,
binding kind `target-alatyr-extension-bindings`, the extension ID, and a list
of target-owned binding records with `id`, `value`, `owner`, and canonical
`source`.

Each non-historical catalog entry records `id`, `version`, `state`, `owner`,
`lock_id`, normalized manifest and bindings paths, item IDs, supported
assistants, review date, evidence revision, and known gaps. Each lock entry
records a target baseline matching `.ai/alatyr.yaml` and the same extension
identity and state plus source type/location/revision,
lowercase SHA-256 package digest, license and compatibility results,
adaptation and approval records, installed files with lowercase SHA-256 and
one owner, shared integration surfaces, validation, and installation time.

Do not place target project facts, framework replacements, source-repository
checkouts, package caches, secrets, or automatically executed hooks here.

## Ownership

Extension state owner: `{TARGET_EXTENSION_STATE_OWNER}`
Approval authority: `{TARGET_EXTENSION_APPROVAL_AUTHORITY}`
Review cadence or triggers: `{TARGET_EXTENSION_REVIEW_CADENCE_OR_TRIGGERS}`
Source retention policy: `{TARGET_EXTENSION_SOURCE_RETENTION_POLICY}`

Every installed file must have one owner in the lock. Shared target files are
integration surfaces and cannot be claimed as extension-owned. Updates and
removals stop when local modifications or ownership conflicts are unresolved.
