# Project Vocabulary

Use this project-contour index to explain and maintain the terminology of
`{PROJECT_NAME}` without turning observed wording into accepted project truth.

Replace placeholders from target evidence before enabling the
`project-vocabulary` module.

Compact catalog: `.ai/project/vocabulary/catalog.json`
Full term records: `.ai/project/vocabulary/terms.json`
Data dictionary links: `.ai/project/vocabulary/data-dictionary-links.json`
Source-of-truth registry: `.ai/project/source-of-truth-registry.md`

## Ownership

Vocabulary owner: `{TARGET_VOCABULARY_OWNER}`
Term decision authority: `{TARGET_TERM_DECISION_AUTHORITY}`
Data dictionary owner or registry: `{TARGET_DATA_DICTIONARY_OWNER_OR_REGISTRY}`
Last reviewed: `{ISO_DATE_OR_UNKNOWN_WITH_REASON}`
Evidence revision: `{TARGET_REVISION_OR_UNKNOWN_WITH_REASON}`

## Term States

- `observed`: target usage exists, but the meaning is not accepted.
- `proposed`: an evidence-backed definition awaits review.
- `accepted`: the scoped meaning is accepted by the target owner.
- `deprecated`: the term remains discoverable but has a preferred replacement.
- `contradicted`: evidence or owners disagree about meaning or use.
- `unknown`: evidence, scope, or ownership is insufficient.

Only accepted terms may direct terminology normalization. Answers about any
other state must name the state and uncertainty.

## Vocabulary Boundaries

The glossary explains scoped project meaning. Acronym records resolve
project-specific abbreviations. Schemas, APIs, data dictionaries, code,
business blueprints, architecture decisions, and operational sources retain
the fact ownership assigned by the source-of-truth registry.

Vocabulary records link to those owners; they do not replace them.

## Lookup Behavior

Resolve canonical terms, aliases, and acronyms through the compact catalog.
Load only matching full records and named canonical sources. When multiple
accepted domain meanings match, present them and ask for bounded clarification.

## Maintenance Triggers

Review vocabulary after accepted concept, naming, ownership, acronym, alias,
data entity, field, event, API, unit, schema, documentation, diagram, prompt,
skill, gate, test, or user-facing terminology changes.

This document is a project-contour routing index. It does not make Alatyr or
the vocabulary registry the owner of target business or technical facts.
