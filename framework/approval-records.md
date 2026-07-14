---
alatyr_doc:
  id: framework.approval-records
  type: framework-rule-owner
  owns_rules:
    - ALATYR-APPROVAL-001
  depends_on:
    - ALATYR-RISK-001
  applies_to:
    - business-change
    - architecture-change
    - data-change
    - security-sensitive
    - ai-infrastructure
    - framework-upgrade
---
# Approval Records

Approval records bind protected changes to a specific plan, scope, and
evidence trail.

They are required when a target adapter needs durable evidence for an approval,
when approval scope covers multiple files or protected categories, or when a
plan may be reused after review.

## When To Use

Use an approval record for:

- architecture changes
- accepted business behavior changes
- destructive, live-service, data-loss, spend-affecting, or production actions
- new production dependencies or external services
- permission, credential, authentication, authorization, privacy, or security
  changes
- importing third-party assistant infrastructure into canonical target files
- overwriting existing AI instructions
- weakening tests, gates, approval rules, validation, or final evidence

Simple chat approval can be enough only when the target adapter explicitly
allows it and the protected change is narrow, immediate, and unambiguous.

## Minimum Record

An approval record should include:

- approval ID
- operation ID
- plan version
- plan hash or content hash when available
- approved plan file or recorded reason when a file is unavailable
- approved diff base when approval is bound to a repository comparison
- patch hash when an exact proposed diff is approved and deterministic hashing
  is practical
- allowed protected changes
- allowed files or surfaces
- excluded files or surfaces, including an explicit `none` when applicable
- excluded actions
- approval source or message reference
- approved by
- approved at
- repository revision at approval when available
- whether reuse is allowed
- scope invalidation rule
- evidence of whether the final patch still matches the approved scope
- use result, result evidence, validation, and residual risk

If the plan changes after approval, the assistant must treat the approval as
stale for any changed protected scope.

An approval record is `historical-record` evidence. Keep allowed and excluded
files in explicit list fields so a checker can compare them with an actual
diff. A path mentioned only in narrative text does not place it inside the
approved scope.

For deterministic enforcement, use a machine-readable approval record with a
schema version, record kind, approved diff base, target-relative allowed and
excluded path lists, invalidation rule, and approval identity. Markdown may
remain the human explanation surface, but it must not be the only source used
for a strict `changed paths subset of approved scope` check.

Strict scope validation should:

- use only approval records explicitly selected for the operation, not every
  historical record in the approval directory
- verify that each selected record is bound to the requested Git diff base
- include committed, staged, unstaged, renamed, deleted, and untracked paths
- fail when any changed path is outside the union of allowed scopes
- fail when any changed path matches an excluded scope
- report unavailable Git or record evidence instead of treating it as a pass

The strict comparison covers the complete operation diff, including code,
tests, docs, diagrams, adapter files, and approval evidence. Protected-change
classification decides whether approval is required; once a scoped approval is
used, companion files do not silently fall outside that scope.

## Repository Storage

Installed adapters should reserve a target-owned approval directory, commonly:

```text
.ai/assistant/approvals/
```

Approval records are target adapter evidence, not portable framework core.
The target may choose whether committed records are allowed, redacted, or
stored outside the repository.

## Hash Guidance

When a deterministic hash is practical, hash the approved plan text or proposed
patch. If hashing is not practical, record the exact plan version and the
reason hash evidence is unavailable.

When an installed adapter uses a validator, it may verify the recorded plan
hash against an approved plan file and the patch hash against the current diff.
If either hash cannot be verified, final evidence should say why rather than
claiming cryptographic approval binding.

Approved plan file references used for hash verification should be
target-relative paths. Do not point approval records at arbitrary absolute
local paths.

Do not include secrets in approval records or hash inputs that must remain
private.

Patch hashes and path-scope validation are different controls. A scope check
does not prove content approval, and a patch hash that omits untracked content
does not prove the complete working tree. Report which control was actually
verified.

## Final Evidence

When an approval record was used, final evidence should name:

- approval ID
- protected categories covered
- files or surfaces changed under approval
- whether the implementation stayed within scope
- whether the approval remained valid after plan, patch, or scope changes
- validation run or skipped
- result or evidence reference
- residual risk
