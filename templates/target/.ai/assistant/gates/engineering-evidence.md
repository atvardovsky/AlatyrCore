# Durable Engineering Evidence Gate

Canonical owner: `ALATYR-ENGINEERING-EVIDENCE-001`.

Before completing a material semantic, architectural, or non-obvious repair,
ask whether reusable engineering knowledge would be lost after this session.

Capture when evidence shows an undocumented invariant, material rejected
hypothesis, non-obvious side effect, cross-area impact, invariant-driven broad
regression matrix, compatibility or architecture decision, reviewer
correction, or another reusable conclusion that is expensive to reconstruct.

Small self-explanatory changes may skip capture with a short fact-specific
reason. Do not activate a change package solely because this gate captures a
lightweight record.

For capture, require a task reference, repository result binding, invariant,
root cause, solution rationale, material alternatives when applicable,
regression rationale, validation, residual uncertainty, canonical-owner links,
and target storage policy. Store normalized conclusions only, never raw chat,
chain-of-thought, secrets, personal data, or unrelated session history.

Final evidence must report `durable_engineering_evidence` as `captured`,
`skipped`, or `blocked`, plus the record ID/path or a specific reason.
