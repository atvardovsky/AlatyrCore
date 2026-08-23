# Debug Records

Store one normalized JSON record per explicitly enabled Debug Mode task or
session. Keep records non-canonical, compact, target-owned, and consistent with
the parent directory's privacy, retention, visibility, and external-patch
policy.

Do not create records by copying raw conversations or private reasoning.

New records use schema version 2. New events separate attribution dimensions:

```json
{
  "actor": "alatyr",
  "causal_class": "independent-within-scope",
  "intervention_kind": "not-applicable",
  "contribution_kind": "finding",
  "architectural_supervision": false,
  "architectural_impacts": [],
  "decision_effect": "none",
  "hypothesis_outcome": "not-applicable"
}
```

The initial user task request stays in activation metadata. Add a human or
external intervention event only for a specific direction, expansion,
constraint, correction, or validation request. Use only values allowed by the
installed Debug session schema.

Schema-version-1 records remain migration-limited evidence. Do not infer or
rewrite historical attribution. New completed records close the durable
Engineering Evidence decision and use a final repository binding with
lineage.
