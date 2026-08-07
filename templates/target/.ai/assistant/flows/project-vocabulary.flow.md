# Project Vocabulary Flow

## Purpose

Explain, propose, review, and synchronize project terminology without turning
observed usage into accepted meaning or replacing canonical business, data,
architecture, API, code, security, or operational owners.

## Routing Modes

- `lookup`: resolve a term, alias, or acronym and explain its scoped meaning
- `inventory`: report vocabulary ownership, states, ambiguities, and gaps
- `propose`: prepare an evidence-backed new term or revision for review
- `review`: inspect term state, sources, aliases, conflicts, links, and freshness
- `synchronize`: update accepted terminology and required derived surfaces
- `terminology-check`: detect ambiguous, deprecated, contradicted, unknown, or
  inconsistent terms in a bounded change or document

Infer the mode from a clear request. The user does not need to name it.

## Allowed Actions

- `read-only`: lookup, inventory, proposal preview, review, or terminology check
- `docs-only`: create or update proposed vocabulary records and derived project
  explanations; do not accept semantic definitions or rewrite canonical owners
- `full-with-approval`: perform specifically approved acceptance, deprecation,
  semantic normalization, broad replacement, or protected companion changes

## Steps

1. Classify mode, requested text or scope, allowed actions, and likely domain.
2. Confirm that `project-vocabulary` is enabled; otherwise report the missing
   module or route to a read-only installation recommendation.
3. Load `.ai/project/vocabulary/catalog.json` and normalize the request using
   its target-recorded policy.
4. Match canonical terms, exact aliases, or acronyms before considering fuzzy
   candidates. Filter by domain and usage scope.
5. If multiple accepted meanings remain, present their scopes and ask only the
   smallest clarification needed. Do not silently choose one.
6. Load selected records from `.ai/project/vocabulary/terms.json` and only their
   named canonical sources.
7. Load `.ai/project/vocabulary/data-dictionary-links.json` only when selected
   terms reference entities, fields, events, APIs, units, enums, or schemas.
8. Preserve term state in every answer. Only `accepted` may be described as the
   authoritative scoped project meaning.
9. For `propose`, record candidate meaning, non-meanings, aliases, domains,
   owner, decision authority, sources, evidence, related terms, data links,
   rejected interpretations, approval needs, and residual risk.
10. For `synchronize`, classify changed term IDs and apply logical integrity
    review to canonical owners, aliases, related terms, data links, code,
    documentation, diagrams, tests, prompts, skills, gates, and user-facing
    text selected by target relationships.
11. Do not mark observed or proposed records accepted without target authority
    and required approval. Do not let vocabulary edits silently change schema,
    API, business, architecture, security, or runtime facts.
12. Run target-recorded vocabulary, link, documentation, code, schema, API, or
    manual validation applicable to the selected terms.
13. Report selected term IDs, match reasons, states, sources, owners, ambiguity,
    changed surfaces, validation, approvals, skipped checks, and residual risk.

## Rejection Criteria

Reject or revise work that:

- infers accepted meaning from frequency in code or discussion
- invents definitions, owners, sources, links, or acceptance
- collapses domain-specific meanings into one global definition
- makes the glossary canonical for schema, API, business, architecture,
  security, code, or operational facts owned elsewhere
- rewrites source from a proposed, contradicted, or unknown term
- loads every vocabulary record for a bounded lookup. Do not load the full
  vocabulary for one term
- claims structural checks prove semantic truth

## Target Sources

- `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- `{TARGET_GLOSSARY_OR_TERMINOLOGY_SOURCES_OR_NONE}`
- `{TARGET_DATA_DICTIONARY_SCHEMA_API_OR_MODEL_SOURCES}`
- `{TARGET_VOCABULARY_VALIDATION_OR_MANUAL_REVIEW}`
