# Session Continuity Gate

Before state-changing work resumes after a context boundary, verify:

- the continuity packet is structurally valid and its digest matches
- current repository, branch, revision, changed-path, and approval evidence
  matches the packet or every difference was explicitly reconciled
- referenced rule IDs and canonical owners remain available
- the active-projection digest and its bound problem-model digest still match;
  routine recovery loaded the projection rather than full model history
- affected obligations were reopened after any strategy, assumption, or
  evidence change
- the newest user instruction re-establishes the current logical scope and
  required action phase
- publish and live-external authority were not restored from the packet
- risk and protected-change approval were reevaluated after material drift
- only changed or uncertain context was reloaded
- focused validation proves the next action is safe

Failure keeps the task inspect-only. Report the mismatched evidence, context
loaded for repair, and smallest next confirmation or action needed.
