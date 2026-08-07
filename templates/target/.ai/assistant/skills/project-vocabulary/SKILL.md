# Project Vocabulary Skill

Status: `{PROPOSED_ACCEPTED_DEPRECATED_CONTRADICTED_OR_UNKNOWN}`
Canonical catalog: `.ai/project/vocabulary/catalog.json`
Canonical records: `.ai/project/vocabulary/terms.json`
Portable rule: `.ai/framework/project-vocabulary.md`

Use this skill only after the target has adapted it and enabled the
`project-vocabulary` module.

## Activation

- The request asks about a project term, alias, acronym, glossary, vocabulary,
  or terminology consistency.
- A changed fact introduces, renames, deprecates, or changes a project concept.
- Allowed actions permit the requested lookup, proposal, or synchronization.

## Process

1. Load the compact catalog and resolve canonical, alias, or acronym matches.
2. Filter candidates by domain and usage scope; do not silently select between
   multiple accepted meanings.
3. Load only selected full term records and their named canonical sources.
4. Preserve `observed`, `proposed`, `accepted`, `deprecated`, `contradicted`,
   and `unknown` states in answers and changes.
5. Load data-dictionary links only when selected terms require them.
6. Propose missing or revised records from bounded evidence. Do not accept them.
7. Route accepted terminology changes through logical integrity review and
   target approval when required.
8. Report selected IDs, meanings, states, owners, sources, ambiguity,
   validation, skipped checks, and residual risk.

## Prohibited

- Do not activate this placeholder as an accepted project skill.
- Do not infer accepted meaning from usage frequency.
- Do not invent definitions, owners, sources, links, or acceptance.
- Do not replace canonical schema, API, business, architecture, security,
  code, or operational facts with vocabulary records.
- Do not load the full vocabulary for one bounded lookup.
