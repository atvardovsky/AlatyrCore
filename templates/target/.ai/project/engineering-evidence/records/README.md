# Engineering Evidence Records

Store compact validated record files here when the target policy selects
repository storage. Load only the record selected by the index for the current
task; do not load this directory as a corpus.

Do not store raw chats, private reasoning, prompts, secrets, credentials,
personal data, unrelated session history, complete diffs, or verbose logs.

Create new records with schema version 2. Mark repository bindings provisional
while work is in progress and final only when the object IDs and ancestry are
reproducible. Preserve replaced bindings in `prior_bindings`. Keep
schema-version-1 records unchanged as legacy evidence unless a human-reviewed
migration has enough evidence to populate the new fields.
