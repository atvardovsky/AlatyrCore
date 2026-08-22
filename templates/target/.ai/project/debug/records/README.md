# Debug Records

Store one normalized JSON record per explicitly enabled Debug Mode task or
session. Keep records non-canonical, compact, target-owned, and consistent with
the parent directory's privacy, retention, visibility, and external-patch
policy.

Do not create records by copying raw conversations or private reasoning.

New events use this structured classification shape in addition to the other
required event fields:

```json
{
  "architectural_supervision": false,
  "architectural_impacts": [],
  "decision_effect": "none",
  "hypothesis_outcome": "not-applicable"
}
```

Use only architectural-impact and decision-effect values allowed by the
installed Debug session schema. Older events may omit the two structured
fields and remain migration-limited evidence. Do not infer historical values
without evidence.
