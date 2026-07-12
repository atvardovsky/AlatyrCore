# Approval Record

Replace placeholders with `{PROJECT_NAME}` approval evidence before using this
record.

Approval ID: `{APPROVAL_ID}`
Operation ID: `{OPERATION_ID}`
Operation type: `{OPERATION_TYPE}`
Plan version: `{PLAN_VERSION}`
Plan hash: `{PLAN_HASH_OR_NOT_AVAILABLE_WITH_REASON}`
Approved plan file: `{APPROVED_PLAN_FILE_OR_NOT_AVAILABLE_WITH_REASON}`
Patch hash: `{PATCH_HASH_OR_NOT_AVAILABLE_WITH_REASON}`
Requested by: `{REQUESTED_BY}`
Approved by: `{APPROVED_BY}`
Approved at: `{APPROVED_AT}`
Approval source/message: `{APPROVAL_SOURCE_OR_MESSAGE_REFERENCE}`
Expires at or reuse policy: `{EXPIRATION_OR_REUSE_POLICY}`
Scope invalidation rule: `{APPROVAL_INVALIDATION_RULE}`

## Approved Scope

Allowed protected changes:

- `{ALLOWED_PROTECTED_CHANGE}`

Allowed files or surfaces:

- `{ALLOWED_FILE_OR_SURFACE}`

Excluded actions:

- `{EXCLUDED_ACTION}`

Allowed actions mode: `{READ_ONLY_DOCS_ONLY_ADAPTER_ONLY_CODE_AND_TESTS_OR_FULL_WITH_APPROVAL}`

## Plan Evidence

Approved plan summary:

```text
{APPROVED_PLAN_SUMMARY}
```

Approved validation or manual review:

- `{APPROVED_VALIDATION_OR_REVIEW}`

## Use Result

Used by operation/change: `{TASK_OPERATION_OR_CHANGE_REFERENCE}`
Patch changed after approval: `{YES_NO_AND_REASON}`
Implementation stayed within approved scope: `{YES_NO_AND_REASON}`
Validation run: `{VALIDATION_RUN_OR_SKIPPED_WITH_REASON}`
Result/evidence: `{RESULT_OR_EVIDENCE_REFERENCE}`
Residual risk: `{RESIDUAL_RISK}`
