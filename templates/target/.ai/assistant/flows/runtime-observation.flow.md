# Runtime Observation Flow

Use this flow only when `runtime-observation` is enabled and acceptance depends
on runtime behavior.

1. Confirm current authorization for read-only observation and obtain separate
   approval before live mutation, restart, deployment, or publication.
2. Load the target runtime-observation policy and select stable event IDs before
   reading raw logs.
3. Bind the observation to the operation, repository revision, source, and a
   complete bounded window.
4. Record counts for every relevant event. Classify unknown events explicitly;
   never omit them because they are inconvenient or noisy.
5. Bind each completion claim to required and contradicting event IDs.
6. Treat failed gates, predecessors, repeated fact identities, and fresh runtime
   contradictions as recurrence candidates. Review incident lineage before an
   isolated repair.
7. After a result-changing action, rerun adapter validation and observation as
   needed against the resulting revision. Mark older evidence stale.
8. Load raw evidence only for contradictions, unknowns, failures, disputes, or
   explicit review.

Do not infer success from process health, one successful sample, absence of an
exception, or a structurally valid evidence record.
