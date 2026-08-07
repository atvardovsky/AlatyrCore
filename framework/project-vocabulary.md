---
alatyr_doc:
  id: framework.project-vocabulary
  type: framework-rule-owner
  owns_rules:
    - ALATYR-VOCABULARY-001
  depends_on:
    - ALATYR-CONTEXT-001
    - ALATYR-SOURCE-001
    - ALATYR-INTEGRITY-001
    - ALATYR-ADAPTER-001
  applies_to:
    - docs-local
    - code-local
    - business-change
    - architecture-change
    - data-change
---
# Project Vocabulary

This document defines the portable contract for project-owned terminology,
aliases, acronyms, ambiguity, and links to canonical data definitions.

Concrete terms, definitions, domains, owners, sources, aliases, acronyms, data
entities, fields, and naming restrictions belong to the target project contour.
Alatyr Core owns only the state, lookup, proposal, synchronization, context,
and evidence process.

## Purpose

An enabled project-vocabulary module should help a target project:

- explain project language consistently to developers and assistants
- distinguish accepted meanings from observed usage and unresolved ambiguity
- resolve aliases and acronyms to stable term IDs
- connect business, product, architecture, operational, and technical language
  without merging their canonical owners
- link terms to data dictionaries, schemas, APIs, and code symbols without
  copying those facts into a glossary
- identify conflicting or discouraged synonyms during discussion, planning,
  documentation, implementation, and review
- propose missing terms from bounded evidence while keeping acceptance with
  target decision owners

The module is not a general dictionary and should not inventory every word,
identifier, class, field, or abbreviation in a repository.

## Vocabulary Boundaries

Keep these responsibilities distinct:

- The project glossary explains the accepted meaning and use of business,
  product, architecture, operational, and technical terms.
- The acronym registry resolves project-specific abbreviations and expansions.
- A data dictionary, schema, API specification, or model owner defines entities,
  fields, types, units, constraints, and relationships.
- Code owns declarations and implementation facts assigned to it by the target
  source-of-truth registry.
- Vocabulary records may link to those owners but must not replace them.

When a term has different accepted meanings in different domains, use separate
stable term IDs with explicit domain scopes. Do not force one global definition.
When ownership or meaning is disputed, record the contradiction instead of
selecting the most frequent wording.

## Term States

Every vocabulary term must use one of these states:

- `observed`: usage exists in target evidence, but no target owner has accepted
  the definition
- `proposed`: an evidence-backed definition or normalization awaits review
- `accepted`: the target decision owner has accepted the scoped meaning
- `deprecated`: the term remains discoverable but should migrate to a named
  replacement when one exists
- `contradicted`: evidence or owners disagree about the meaning or usage
- `unknown`: evidence, scope, or ownership is insufficient

Only an `accepted` term may direct terminology normalization or be presented as
the project's authoritative meaning. Other states must be stated in answers.

## Record Contract

Each full term record should contain:

- stable term ID, canonical term, normalized lookup key, and term kind
- state, domain scopes, usage scopes, audience, and sensitivity
- concise definition and explicit non-meanings where ambiguity is likely
- aliases, acronym expansions, discouraged synonyms, and replacement term ID
- owner, decision authority, canonical sources, selected evidence, and last
  verified repository revision
- related term IDs and data-dictionary, schema, API, or code references
- examples only when their assumptions are supported by target evidence
- validation, known contradictions, and unresolved gaps

Term kinds may include domain term, product term, architecture term,
operational term, technical term, acronym, or another target-defined kind.
Kinds classify records; they do not establish source-of-truth precedence.

## Compact Catalog And Lookup

Keep a compact machine-readable catalog separate from full definitions. The
catalog maps normalized canonical terms, aliases, and acronyms to stable term
IDs and scoped record locations.

For a vocabulary request:

1. Normalize the requested text according to target-recorded rules.
2. Load the compact catalog, not every full term record.
3. Match canonical terms, then exact aliases or acronyms, then scoped
   candidates.
4. Prefer an accepted candidate whose domain and usage scope match the request.
5. If multiple accepted candidates remain, present the scoped meanings and ask
   for the smallest clarification needed.
6. Load only selected full records and their named canonical sources.
7. Report state, owner, source revision, ambiguity, and unresolved gaps.

Fuzzy or semantic search may suggest candidates, but it must not silently
select an authoritative definition. Search infrastructure is target-specific
and optional.

## Proposal And Acceptance

The assistant may prepare a proposed term from bounded target evidence such as
canonical docs, approved decisions, schemas, APIs, code, tests, recurring
review findings, and project discussions that the target permits as evidence.

A proposal should include:

- candidate canonical term, aliases, kind, domains, and usage scope
- proposed definition and non-meanings
- observed conflicting meanings and deprecated alternatives
- canonical owner, decision authority, and source links
- related terms and data-dictionary links
- sampled evidence and rejected interpretations
- expected companion updates, validation, approval needs, and residual risk

Do not mark a proposal accepted merely because it appears often in code or
discussion. Acceptance must follow target ownership and approval policy.

## Data Dictionary Links

Vocabulary records may link to data entities, fields, events, API concepts,
units, or enumerations through stable references. Each link should name:

- term ID
- referenced fact type and canonical owner
- entity, field, event, API, or schema identifier
- relationship such as `represents`, `measured-by`, `stored-as`, `emitted-as`,
  `not-equivalent-to`, or another target-defined relation
- direction, evidence, validation, and last verified revision

The link is routing evidence. It does not make the vocabulary registry the
owner of schema, type, validation, retention, or runtime behavior.

## Synchronization And Integrity

Review affected vocabulary when a change:

- introduces or renames a business, product, architecture, operational, or
  technical concept
- changes the accepted meaning, scope, lifecycle, or owner of a term
- adds or changes an acronym, alias, prohibited synonym, or replacement
- changes a linked data entity, field, event, API, unit, or schema concept
- creates terminology differences across code, documentation, diagrams,
  prompts, skills, gates, tests, or user-facing text

Logical integrity review should name changed term IDs and verify canonical
sources, aliases, related terms, data links, derived surfaces, validation, and
residual ambiguity. A local wording change that does not alter accepted meaning
may skip vocabulary edits with a recorded reason.

## Assistant Skill Boundary

A target may adapt a project-vocabulary skill for lookup, proposal, review, and
terminology checks. The skill must use the compact catalog first, load bounded
records, preserve states, and route accepted changes to canonical owners.

The skill is an execution aid. It must not own definitions, acceptance,
normalization policy, source precedence, or target facts. A placeholder skill
must not be presented as an enabled target capability.

## Context Economy

Keep vocabulary detail outside routine bootstrap. Route explicit vocabulary
requests through a compact intent descriptor and catalog. For ordinary tasks,
load vocabulary only when the request or changed fact uses an ambiguous,
deprecated, contradicted, unknown, or materially changed project term.

Do not load the full glossary for onboarding, architecture, code, or
documentation tasks. Load selected term records and linked canonical owners.

## Evidence

Vocabulary work should report:

- mode, requested text, selected term IDs, match reason, domain, and state
- definition source, owner, decision authority, and evidence revision
- aliases, acronyms, ambiguity, non-meanings, and replacements
- related terms and selected data-dictionary links
- proposed or changed records and affected companion surfaces
- validation, approval or acceptance state, skipped checks, and residual risk

## Rejection Criteria

Reject or revise vocabulary work that:

- treats observed frequency as accepted project meaning
- invents a definition, owner, source, relation, or acceptance state
- collapses distinct domain meanings into one global definition
- copies schema, API, business-rule, or architecture ownership into a glossary
- normalizes source or documentation from proposed, contradicted, or unknown
  terms without target acceptance
- stores secrets, personal data, or sensitive raw discussion in term evidence
- loads the complete vocabulary for an unrelated or bounded task
- claims that structural validation proves semantic correctness
