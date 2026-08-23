# Debug Records

Store one normalized JSON record per explicitly enabled Debug Mode task or
session. Keep records non-canonical, compact, target-owned, and consistent with
the parent directory's privacy, retention, visibility, and external-patch
policy.

Do not create records by copying raw conversations or private reasoning.

New records use schema version 3. Events continue to separate attribution
dimensions:

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

Schema-version-3 records also keep completed lifecycle timestamps immutable,
open related continuation work in a new linked record, type every supporting
evidence event, evaluate the full materiality set, prove canonical preservation
before skipping, and classify validation fidelity.

Schema-version-1 and version-2 records remain migration-limited evidence. Do
not infer or rewrite historical attribution, materiality, claim fidelity, or
continuation lineage. New completed records close the durable Engineering
Evidence decision and use a final repository binding with lineage.
