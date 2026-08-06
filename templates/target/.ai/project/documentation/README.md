# Project Code Documentation

Use this project-contour index to route code-comment and generated-reference
work for `{PROJECT_NAME}` without imposing one style on every source area.

Replace placeholders from target evidence before enabling the
`code-documentation` module.

Machine-readable catalog: `.ai/project/documentation/catalog.json`
Documentation profiles: `.ai/project/documentation/profiles.json`
Source-of-truth registry: `.ai/project/source-of-truth-registry.md`

## Ownership

Documentation owner: `{TARGET_CODE_DOCUMENTATION_OWNER}`
Profile decision authority: `{TARGET_DOCUMENTATION_PROFILE_DECISION_AUTHORITY}`
Generation and publication owner: `{TARGET_DOCUMENTATION_GENERATION_OWNER}`
Last reviewed: `{ISO_DATE_OR_UNKNOWN_WITH_REASON}`
Evidence revision: `{TARGET_REVISION_OR_UNKNOWN_WITH_REASON}`

## Profile States

- `proposed`: evidence-backed recommendation awaiting target acceptance.
- `accepted`: approved target convention that may guide comment generation.
- `deprecated`: retained for existing scope while migration is planned.
- `contradicted`: repository evidence and the recorded profile disagree.
- `unknown`: ownership or evidence is insufficient.

Only accepted, unambiguous profiles may direct routine source-comment changes.

## Source-Of-Truth Boundary

Code declarations and structured comments own only the target fact types named
in the source-of-truth registry. Generated reference documentation is derived
and must not be edited directly. API specifications, business blueprints,
architecture decisions, security policy, and operational sources remain
canonical where the registry assigns them ownership.

## Documentation Areas

Area ID: `{DOCUMENTATION_AREA_ID}`
Name: `{DOCUMENTATION_AREA_NAME}`
Owner: `{DOCUMENTATION_AREA_OWNER}`
Source scope: `{DOCUMENTATION_AREA_SOURCE_SCOPE}`
Profile IDs: `{DOCUMENTATION_AREA_PROFILE_IDS}`
Audience: `{DOCUMENTATION_AREA_AUDIENCE}`
Public boundary: `{DOCUMENTATION_AREA_PUBLIC_BOUNDARY}`
Generated output: `{DOCUMENTATION_AREA_OUTPUT_OR_NONE}`
Status: `{MISSING_PARTIAL_USABLE_STALE_CONTRADICTED_OR_UNKNOWN}`
Evidence: `{DOCUMENTATION_AREA_EVIDENCE_OR_GAP}`

## Maintenance Triggers

Review the selected profile after public contract, responsibility, invariant,
failure, side-effect, authorization, transaction, concurrency, data-lifecycle,
accessibility, deprecation, compatibility, generator, publication, or ownership
changes. Local refactors may skip documentation changes when final evidence
explains why no documented fact changed.

This index routes to target owners. It does not replace canonical project facts
or make generated output authoritative.
