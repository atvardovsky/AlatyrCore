# Runtime Observation Records

Store concrete compact observation records here when the target policy permits
repository storage. Add only records selected for the current change to the
parent `index.json`. Raw logs remain outside normal context and follow the
target retention and redaction policy. Bind each record to an immutable full
Git commit ID. Later changes are limited to files in this evidence directory;
any product or other support-surface change makes the observation stale.
