# Durable Engineering Evidence

This directory is the compact historical engineering-evidence surface for
`{PROJECT_NAME}`. Canonical project facts remain owned by the project sources
referenced from each record.

Index: `.ai/project/engineering-evidence/index.json`

Records: `.ai/project/engineering-evidence/records/`

Owner: `{TARGET_ENGINEERING_EVIDENCE_OWNER}`

Storage mode: `{REPOSITORY_INTERNAL_BRANCH_IGNORED_LOCAL_OR_APPROVED_EXTERNAL}`

External patch policy: `{EXCLUDE_FROM_EXTERNAL_PATCH_OR_TARGET_APPROVED_INCLUSION}`

Retention policy: `{TARGET_ENGINEERING_EVIDENCE_RETENTION_POLICY}`

Redaction policy: `{TARGET_ENGINEERING_EVIDENCE_REDACTION_POLICY}`

Ignored local storage is not durable team memory unless an approved retained
store also preserves the record. Do not store raw chats, chain-of-thought,
secrets, credentials, personal data, unrelated session history, complete
diffs, or verbose validation logs.

Canonical rule: `.ai/framework/engineering-evidence.md`

New schema-version-3 records list related Debug session IDs when Debug Mode was
active. Each link is reciprocal and shares a task or issue reference. Leave the
list empty when Debug Mode was not active; do not add inferred links to schema-
version-1 or version-2 historical records. Schema-version-3 records require the
schema-version-4 index.
