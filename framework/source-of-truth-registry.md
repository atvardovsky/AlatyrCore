---
alatyr_doc:
  id: framework.source-of-truth-registry
  type: framework-rule-owner
  owns_rules:
    - ALATYR-SOURCE-001
  depends_on:
    - ALATYR-ADAPTER-001
  applies_to:
    - docs-local
    - code-local
    - business-change
    - architecture-change
    - data-change
---
# Source Of Truth Registry

A source-of-truth registry maps fact types to canonical owners and derived
surfaces.

It prevents assistants from choosing owners by convenience, file proximity, or
recency when project evidence conflicts.

## Purpose

The registry should answer:

- which file or surface owns a fact type
- which files are derived from that owner
- which direction synchronization should flow
- which validation or manual review confirms consistency
- who decides when two canonical-looking sources disagree

Do not define one global precedence order for all facts. API contracts,
database schemas, ADRs, tests, public docs, runtime config, and assistant
policy can each have different owners.

## Registry Entry Contract

Each entry should define:

- fact type
- canonical owner
- derived surfaces
- sync direction
- validation or manual review
- conflict resolver
- approval trigger when changing the canonical owner
- final evidence expected after a change

If a target does not know the owner for a fact type, mark it as missing instead
of inferring ownership from the nearest file.

## Common Fact Types

Target adapters may include fact types such as:

- product behavior
- business rule
- public API contract
- internal service contract
- architecture decision
- data model
- migration
- runtime configuration
- security policy
- validation command
- diagram source
- generated documentation
- assistant operation
- skill, prompt, wrapper, or bridge behavior
- approval rule

The target adapter decides the actual names and owners.

## Baseline Template Entries

The target registry template should include baseline entries for fact types
that commonly create drift when left ownerless:

- product behavior
- business rule
- architecture decision
- data model
- validation command
- security policy
- assistant operation
- AI infrastructure item

Each baseline entry may remain placeholder-based during installation planning,
but before an adapter claims maturity the owner should be resolved from target
evidence or explicitly marked missing.

## Conflict Handling

When sources disagree:

1. Identify the fact type.
2. Read the registry entry for that fact type.
3. Name the canonical owner and derived surfaces.
4. If the owner is missing or ambiguous, report the missing adapter fact.
5. Repair the smallest coherent set of derived surfaces.
6. Record validation, skipped checks, and residual risk.

If the registry itself is wrong or stale, treat that as an adapter change. Do
not silently repair product facts by changing the registry unless approval is
present when required.
