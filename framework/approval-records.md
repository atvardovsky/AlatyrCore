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
- allowed protected changes
- allowed files or surfaces
- excluded actions
- approval source or message reference
- approved by
- approved at
- whether reuse is allowed
- scope invalidation rule
- evidence of whether the final patch still matches the approved scope
- use result, result evidence, validation, and residual risk

If the plan changes after approval, the assistant must treat the approval as
stale for any changed protected scope.

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

Do not include secrets in approval records or hash inputs that must remain
private.

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
