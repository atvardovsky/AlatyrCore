# Diagram Presentation

Use this template to present a diagram during an assistant discussion.

## Identity

- Diagram ID: `{STABLE_DIAGRAM_ID}`
- Draft revision: `{POSITIVE_INTEGER}`
- Supersedes or parent revision: `{REVISION_ID_OR_NONE}`
- Created or updated: `{ISO_8601_TIMESTAMP}`
- Decision reference: `{DECISION_ID_OR_NONE}`
- Diagram title: `{DIAGRAM_TITLE}`
- Purpose and scope: `{DIAGRAM_PURPOSE_AND_SCOPE}`
- Diagram type: `{CONTEXT_CONTAINER_COMPONENT_SEQUENCE_STATE_DATA_OR_OTHER}`
- Status: `{DRAFT_ACCEPTED_SOURCE_OR_DERIVED_VIEW}`
- Current assistant surface: `{ASSISTANT_SURFACE_ID}`

## Evidence

- Fact owners: `{FACT_IDS_AND_CANONICAL_OWNERS_OR_MISSING}`
- Repository revision: `{REVISION_REQUIRED_FOR_ACCEPTED_OR_DERIVED_OTHERWISE_UNKNOWN}`
- Source revision or content hash: `{REQUIRED_FOR_ACCEPTED_OR_DERIVED_OTHERWISE_NOT_AVAILABLE}`
- Assumptions: `{ASSUMPTIONS_OR_NONE}`
- Unresolved facts: `{UNRESOLVED_FACTS_OR_NONE}`
- Intentionally omitted detail: `{OMITTED_DETAIL_OR_NONE}`

## Presentation

- Presentation mode: `{NATIVE_INLINE_RENDERED_ARTIFACT_OR_TEXT_FALLBACK}`
- Capability evidence: `{CURRENT_ASSISTANT_CAPABILITY_ENTRY_VERSION_TIME_AND_EVIDENCE}`
- Editable source format: `{SOURCE_FORMAT_OR_NONE}`
- Editable source path: `{SOURCE_PATH_OR_INLINE_ONLY}`
- Rendered artifact: `{ARTIFACT_PATH_ATTACHMENT_UNSUPPORTED_OR_NONE}`

Inline or artifact presentation:

`{INLINE_PRESENTATION_ARTIFACT_LINK_OR_NOT_SUPPORTED}`

Readable text fallback:

```text
{READABLE_TEXT_DIAGRAM_OR_ACCESSIBLE_EQUIVALENT_REASON}
```

Editable source when useful:

```text
{EDITABLE_SOURCE_OR_SOURCE_PATH_REFERENCE}
```

## Security And Artifact Policy

- Data classification: `{PUBLIC_INTERNAL_CONFIDENTIAL_RESTRICTED_OR_TARGET_EQUIVALENT}`
- Redactions applied: `{REDACTIONS_OR_NONE}`
- External renderer or network action: `{NONE_REQUESTED_BLOCKED_OR_HANDOFF}`
- Approval evidence: `{APPROVAL_ID_OR_NOT_REQUIRED}`
- Artifact storage: `{TARGET_PATH_ATTACHMENT_OR_NONE}`
- Retention and deletion: `{TARGET_POLICY_OR_NOT_APPLICABLE}`
- Sharing boundary: `{TARGET_ALLOWED_AUDIENCE_OR_NOT_APPLICABLE}`

## Integrity

- Explains current facts, compares alternatives, or proposes change:
  `{CURRENT_ALTERNATIVES_OR_PROPOSED_CHANGE}`
- Accepted fact change detected: `{YES_NO_OR_UNRESOLVED}`
- Required handoff: `{NONE_DECISION_DOCUMENTATION_SYNC_OR_PRODUCT_CHANGE}`
- Validation or manual review: `{VALIDATION_RESULT_OR_NOT_RUN}`
- Stale-view risk: `{RISK_AND_REFRESH_TRIGGER}`
- Next action: `{CONTINUE_REVISE_PERSIST_ACCEPT_HANDOFF_OR_STOP}`

The rendered or inline view is not project source of truth unless the target
registry explicitly names it as an accepted owner.

An `accepted-source` or `derived-view` without repository revision and source
revision or content hash is invalid and must remain `draft`.
