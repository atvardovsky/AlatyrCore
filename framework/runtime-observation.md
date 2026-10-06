# Runtime Observation

This optional module applies `ALATYR-EVIDENCE-001`, `ALATYR-INTEGRITY-001`,
and `ALATYR-PACKAGE-001` to changes whose acceptance depends on runtime
behavior. It does not make Alatyr a monitoring system and does not define
project commands, log formats, event meanings, or production access.

## Target-Owned Policy

The target adapter owns stable event IDs, evidence sources, bounded collection
commands, observation windows, redaction, retention, and approval requirements.
Raw logs remain lazy evidence. The normal context artifact is a compact record
containing counts, classifications, samples, and references to retained source
evidence.

The target runtime-observation index is the bounded selector for current
records. `required_for_current_change: true` with no selected record is a
blocking acceptance failure. Validators inspect selected current records, not
the historical records directory. Each index entry binds its operation ID,
target-relative record path, and SHA-256. Concrete record paths are explicit
changed-scope triggers. The record uses an immutable full Git commit ID rather
than a branch, tag, short hash, or `HEAD`. Any later committed, staged,
unstaged, or untracked non-evidence change makes the runtime evidence stale;
only files below the runtime-observation evidence directory may follow it.

## Claim-to-Event Contract

Each runtime-dependent completion claim names:

- events required to support it;
- events that contradict it;
- the completed observation window and repository revision;
- unresolved or unclassified events;
- limitations on what the evidence proves.

A claim is not `supported` when its required events are absent, a contradicting
event is observed, the window is incomplete, or any relevant event remains
unclassified or unresolved. Structural validation of the record does not prove
that the target classified an event correctly.

## Recurrence Signal

A fresh runtime contradiction, a failed required gate, an explicit predecessor,
or repeated changed-fact identity is a recurrence candidate. The assistant must
review incident lineage before another isolated repair. The signal does not
infer business causality; it prevents silent loss of known continuity.

## Post-Result Acceptance

After code, commit, deployment, restart, or another result that can change the
observed revision or runtime state, acceptance evidence must be rerun or marked
stale. Pre-result evidence may justify the action but cannot prove the resulting
state. A record requests current-run adapter validation; it never self-certifies
that validation already passed. Publication and live actions still require
current-scope authorization.

## Cost Boundary

Load the compact record first. Open raw evidence only for a failed obligation,
an unknown event, a contradiction, a disputed classification, or an explicit
review request. Sampling must never replace counts needed by the selected
claim.
