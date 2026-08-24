# Project Knowledge Delivery

This directory contains the compact derived routing surface that helps later
developers and assistants find reviewed knowledge in `{PROJECT_NAME}`.
Canonical project facts remain owned by the sources referenced from route
entries. Promotion and routing records do not replace those owners.

Index: `.ai/project/knowledge/index.json`

Route shards: `.ai/project/knowledge/routes/`

Promotion records: `.ai/project/knowledge/promotions/`

Owner: `{TARGET_PROJECT_KNOWLEDGE_OWNER}`

Review policy: `{TARGET_PROJECT_KNOWLEDGE_REVIEW_POLICY}`

Retention policy: `{TARGET_PROJECT_KNOWLEDGE_RETENTION_POLICY}`

Redaction policy: `{TARGET_PROJECT_KNOWLEDGE_REDACTION_POLICY}`

Only accepted and current route entries may be supplied as project
constraints. Revalidation-required entries are warnings. Contradicted entries
must route to the registered decision owner. Proposed, observed, unresolved,
historical, and superseded entries remain outside routine task packets.

Do not store raw chats, chain-of-thought, secrets, credentials, personal data,
undisclosed vulnerabilities, complete diffs, or copied third-party material.

Canonical rule: `.ai/framework/project-knowledge.md`
