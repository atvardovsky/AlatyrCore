# Debug Records

Store one normalized JSON record per explicitly enabled Debug Mode task or
session. Keep records non-canonical, compact, target-owned, and consistent with
the parent directory's privacy, retention, visibility, and external-patch
policy.

Do not create records by copying raw conversations or private reasoning.

New records use schema version 4. Events separate role, target-local identity,
provenance, causality, and correction classification:

```json
{
  "actor_role": "executor",
  "actor_identity": {
    "actor_id": "{TARGET_LOCAL_ACTOR_ID}",
    "identity_kind": "pseudonymous"
  },
  "actor_provenance": {
    "evidence_kind": "declared",
    "provider": "{AI_PROVIDER_OR_NULL}",
    "product": "{ASSISTANT_PRODUCT_OR_NULL}",
    "model": "{MODEL_OR_NULL}",
    "runtime": "{RUNTIME_OR_NULL}",
    "evidence": ["{PROVENANCE_EVIDENCE_REFERENCE}"]
  },
  "causal_class": "independent-within-scope",
  "intervention_kind": "not-applicable",
  "correction_disposition": "not-applicable",
  "related_guidance_ids": [],
  "correction_evidence": [],
  "contribution_kind": "finding",
  "architectural_supervision": false,
  "architectural_impacts": [],
  "decision_effect": "none",
  "hypothesis_outcome": "not-applicable"
}
```

The initial user task request stays in activation metadata. Add a human or
external intervention event only for a specific direction, expansion,
constraint, correction, or validation request. Give each such intervention one
of these dispositions: `new-guidance-candidate`,
`known-guidance-routing-failure`, `known-guidance-compliance-failure`,
`task-local`, `scope-change`, or `validation-request`. Include compact evidence;
known-guidance failures also name the related guidance IDs. Use only values
allowed by the installed Debug session schema.

Schema-version-4 records also keep completed lifecycle timestamps immutable,
open related continuation work in a new linked record, type every supporting
evidence event, evaluate the full materiality set, prove canonical preservation
before skipping, and classify validation fidelity.

Schema versions 1 through 3 remain migration-limited evidence with their
original attribution semantics. Versions 2 and 3 keep legacy `actor` values and
`alatyr_independent_*` metric names, which do not distinguish the executor from
Alatyr system behavior. Do not infer, rewrite, or reinterpret historical
attribution, materiality, claim fidelity, or continuation lineage. New
completed records close the durable Engineering Evidence decision and use a
final repository binding with lineage.
