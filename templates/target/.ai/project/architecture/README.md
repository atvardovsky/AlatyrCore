# Project Architecture Knowledge

Use this project-contour index to explain `{PROJECT_NAME}` architecture and
route assistants to canonical target evidence without loading every
architecture document.

Replace placeholders from target evidence before enabling the
`architecture-knowledge` module.

Machine-readable catalog: `.ai/project/architecture/catalog.json`
Source-of-truth registry: `.ai/project/source-of-truth-registry.md`

## Ownership And Evidence

Architecture owner: `{TARGET_ARCHITECTURE_OWNER}`
Decision authority: `{TARGET_ARCHITECTURE_DECISION_AUTHORITY}`
Canonical architecture sources: `{TARGET_ARCHITECTURE_SOURCES}`
Decision-record sources: `{TARGET_ARCHITECTURE_DECISION_SOURCES}`
Diagram sources: `{TARGET_ARCHITECTURE_DIAGRAM_SOURCES_OR_NONE}`
Validation or fitness checks: `{TARGET_ARCHITECTURE_VALIDATION_OR_REVIEW}`
Last reviewed: `{ISO_DATE_OR_UNKNOWN_WITH_REASON}`
Evidence revision: `{TARGET_REVISION_OR_UNKNOWN_WITH_REASON}`

## Status Meanings

- `observed`: repository evidence exists, but intended use is not confirmed.
- `proposed`: under discussion and not accepted project architecture.
- `accepted`: approved and recorded by the target architecture owner.
- `preferred`: accepted for new work in a named scope.
- `restricted`: allowed only in recorded scopes or circumstances.
- `deprecated`: retained for compatibility and not for new work.
- `contradicted`: intended architecture and repository evidence disagree.
- `unknown`: evidence is missing or conflicting.

Implementation frequency, age, or recency does not make a pattern accepted.

## Architecture Areas

Area: `{ARCHITECTURE_AREA_ID}`
Name: `{ARCHITECTURE_AREA_NAME}`
Status: `{OBSERVED_PROPOSED_ACCEPTED_CONTRADICTED_OR_UNKNOWN}`
Owner: `{ARCHITECTURE_AREA_OWNER}`
Canonical detail: `{TARGET_ARCHITECTURE_AREA_DOC_OR_NONE}`
Pattern IDs: `{ARCHITECTURE_PATTERN_IDS_OR_NONE}`
Evidence: `{TARGET_AREA_EVIDENCE_OR_GAP}`

## Architecture Patterns And Items

Pattern ID: `{ARCHITECTURE_PATTERN_ID}`
Name: `{ARCHITECTURE_PATTERN_NAME}`
Kind: `{STYLE_BOUNDARY_INTEGRATION_DATA_SECURITY_RUNTIME_OPERATIONAL_OR_OTHER}`
Status: `{OBSERVED_PROPOSED_ACCEPTED_PREFERRED_RESTRICTED_DEPRECATED_CONTRADICTED_OR_UNKNOWN}`
Scope: `{TARGET_PATTERN_SCOPE}`
Problem: `{TARGET_PROBLEM_THE_PATTERN_ADDRESSES}`
Decision owner: `{TARGET_PATTERN_DECISION_OWNER}`
Canonical detail: `{TARGET_PATTERN_DOC_OR_DECISION_RECORD}`
Evidence: `{TARGET_PATTERN_EVIDENCE_OR_GAP}`
Validation: `{TARGET_PATTERN_VALIDATION_OR_REVIEW}`
Last verified revision: `{TARGET_REVISION_OR_UNKNOWN_WITH_REASON}`

## Known Gaps And Contradictions

- `{ARCHITECTURE_KNOWLEDGE_GAP_OR_CONTRADICTION}`

## Maintenance Triggers

Review this index and the catalog after accepted architecture decisions, new
project areas or dependencies, changed data or trust boundaries, repeated
undocumented pattern use, recurring architecture review findings, pattern
deprecation, moved owners, or contradictions between intended architecture and
repository evidence.

Supporting documentation is project truth only when the target registry names
it as canonical. Otherwise it is a routed explanation or draft derived from
the listed owners.
