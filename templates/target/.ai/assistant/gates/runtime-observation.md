# Runtime Observation Gate

This gate passes only when:

- the target policy is resolved and the observation window is complete;
- every relevant event has a stable ID, count, classification, disposition,
  and evidence reference;
- no forbidden event was observed;
- no event is unknown or unresolved;
- every `supported` claim has all required events and no observed contradiction;
- recurrence candidates have an explicit incident-lineage disposition;
- post-result adapter validation passed against the resulting revision and the
  evidence is fresh.

Otherwise report `partial`, `blocked`, or `unverified`. A passing structural
validator proves record consistency, not runtime truth or classification
correctness.
