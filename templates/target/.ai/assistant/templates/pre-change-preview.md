# Alatyr Pre-Change Preview

Use this bounded artifact before edits when operation routing identifies a
semantic or protected change, cross-boundary scope, external or destructive
effect, or unclear allowed-action surface.

The preview is not approval. Refresh it when changed facts, risk, expected
surfaces, allowed actions, or approval scope changes materially.

## Preview

- Operation ID: `{OPERATION_ID}`
- Goal: `{GOAL}`
- Selected context profile and overlays: `{PROFILE_AND_OVERLAYS}`
- Changed facts or suspected facts: `{CHANGED_FACT_IDS_AND_SUMMARIES}`
- Canonical owners: `{SOURCE_OF_TRUTH_OWNERS}`
- Affected contours, project areas, and external surfaces:
  `{AFFECTED_SURFACES}`
- Risk classes: `{RISK_CLASSES}`
- Preview trigger: `{SEMANTIC_PROTECTED_CROSS_BOUNDARY_EXTERNAL_OR_UNCLEAR_SCOPE}`
- Expected files or bounded surface patterns: `{EXPECTED_CHANGE_SCOPE}`
- Allowed actions: `{ALLOWED_ACTIONS}`
- Approval needs and selected records: `{APPROVAL_NEEDS_AND_RECORDS}`
- Planned validation: `{VALIDATION_OR_MANUAL_REVIEW}`
- Unresolved questions: `{UNRESOLVED_QUESTIONS_OR_NONE}`
- Evidence basis: `{FILES_RECORDS_AND_REVISION}`
- Decision: `{PROCEED_ASK_OR_BLOCKED}`

## Skip Evidence

For routine read-only or local non-semantic work, do not create a full preview.
Record only:

```text
Pre-change preview: skipped
Reason: <no semantic or protected effect, no boundary crossing, and allowed
scope is clear>
```
