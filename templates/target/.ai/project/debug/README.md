# Alatyr Debug Evidence

This directory stores optional, non-canonical observability evidence for
explicitly selected Alatyr-assisted tasks in `{PROJECT_NAME}`.

Owner: `{DEBUG_EVIDENCE_OWNER}`
Storage mode: `{REPOSITORY_INTERNAL_BRANCH_IGNORED_LOCAL_OR_APPROVED_EXTERNAL}`
Visibility: `{DEBUG_EVIDENCE_VISIBILITY}`
Retention policy: `{DEBUG_EVIDENCE_RETENTION_POLICY}`
Redaction policy: `{DEBUG_EVIDENCE_REDACTION_POLICY}`
External patch policy: `{EXCLUDE_FROM_EXTERNAL_PATCH_OR_TARGET_APPROVED_INCLUSION}`

Debug records answer how Alatyr and human supervision contributed to a task.
They do not own architecture, business rules, code contracts, approvals, or
validation facts. Route accepted findings to their canonical project owner and
link that owner or durable engineering-evidence record from the debug record.

Debug Mode is inactive unless the user explicitly enables it for the current
task or session. Activation expires when that logical scope completes, changes,
is abandoned, or is explicitly disabled.

Use `index.json` for compact cross-task lookup. Load only the selected record
under `records/` when detailed evidence is needed. Never store raw
conversations, chain-of-thought, prompts, credentials, secrets, unrelated
personal data, complete diffs, or verbose logs here.
