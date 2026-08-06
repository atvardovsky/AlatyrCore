# Documentation Sync Flow

## Purpose

Keep target code comments, generated reference documentation, project docs,
diagrams, prompts, gates, skills, bridge files, and assistant workflows
synchronized after relevant changes. When the optional `code-documentation`
module is enabled, select project-area comment styles and generators from
accepted target profiles rather than applying one convention repository-wide.

## Routing Modes

- `inventory`: identify documentation areas, profiles, owners, generators,
  outputs, and gaps without changing files
- `propose`: inspect a bounded source set and prepare an evidence-backed
  comment-style and generator profile for target acceptance
- `review`: inspect an existing profile, comments, generated output, freshness,
  ambiguity, and direct-edit drift
- `document`: add or update structured comments under one accepted profile
- `synchronize`: update derived documentation and companion surfaces after a
  changed fact
- `generate`: run the selected target generator and validate its output policy

Route clear requests automatically. The user does not need to name a mode.

## Allowed Actions

- `read-only`: inventory, explain, compare, or propose; do not edit source,
  profile, configuration, generated output, CI, or publication surfaces
- `docs-only`: update project-owned documentation or proposed profile records;
  do not mass-edit source comments or mark a profile accepted
- `code-and-tests`: update source comments and run accepted local generation or
  validation within the selected profile; do not install dependencies, change
  CI, or publish externally
- `full-with-approval`: perform specifically approved dependency, CI,
  publication, permission, broad migration, or accepted-profile changes

## Steps

1. Classify the request mode, changed facts, allowed actions, source scope, and
   project area.
2. Apply the Semantic Change Decision Gate from
   `.ai/assistant/gates/checklist.md` and
   `.ai/framework/logical-integrity.md`.
3. Resolve changed fact IDs and canonical owners. When the optional
   `consistency-map` module is enabled, follow applicable `documents`,
   `visualizes`, `generates`, `verifies`, and dependent-contract edges.
4. If code comments or generated reference documentation are in scope, check
   that `code-documentation` is enabled and load
   `.ai/project/documentation/catalog.json` plus
   `.ai/project/documentation/profiles.json`.
5. Select accepted profile candidates by path/source-set, language, framework,
   specificity, and explicit priority. Stop automatic generation on an equal
   conflict. If no accepted profile applies, route to `propose` under
   `read-only`.
6. For `propose`, inspect existing comments, compilers, linters, generators,
   documentation sites, scripts, CI, IDE support, canonical specifications,
   source owners, recurring findings, and maintenance constraints. Prefer an
   existing convention; otherwise compare language-appropriate options using
   common criteria.
7. Record proposed syntax and project-area content separately. Frontend,
   backend, shared-library, and infrastructure profiles may require different
   semantic sections even when they share a language.
8. Before changing comments, confirm that the selected profile is accepted and
   unambiguous. Apply its required symbol set, semantic content, avoid rules,
   uncertainty policy, and source-of-truth boundary.
9. Never edit a configured generated output directly. Run the target-recorded
   generator only when allowed actions permit it.
10. Enforce the selected output policy:
    - `ci-artifact`: generation succeeds without requiring committed output
    - `committed-generated`: regeneration leaves no unexplained generated diff
    - `local-only`: output remains local under target retention policy
    - `external-publish`: target approval and publication boundary are present
    - `unresolved`: do not claim generation readiness
11. Update other companion docs, tests, diagrams, prompts, gates, skills,
    bridge files, or checker rules when selected relationships require them.
12. Run target comment lint, generation, link, example, build, or manual review
    recorded by the selected profile.
13. Report selected and skipped relationships, selected profile and state,
    comments changed, symbols skipped, generated output, direct-edit result,
    validation, skipped checks, approvals, and residual risk.

## Rejection Criteria

Reject or revise work that:

- imposes one style on unrelated source areas without target evidence
- selects a generator before checking existing project tooling
- uses a proposed, unknown, deprecated, contradicted, or ambiguous profile for
  broad source edits
- edits generated output directly
- invents accepted business, architecture, security, data, API, or operational
  intent from implementation comments
- adds comments that only repeat code syntax, identifiers, or types
- installs dependencies, changes CI, publishes, or broadens permissions without
  required approval
- claims semantic correctness because documentation generation succeeded

## Target Sources

- `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- `{TARGET_PUBLIC_DOCS}`
- `{TARGET_BLUEPRINT_OR_EQUIVALENT}`
- `{TARGET_TEST_STRATEGY}`
- `{TARGET_DIAGRAM_POLICY}`
- `.ai/project/documentation/catalog.json` and
  `.ai/project/documentation/profiles.json` when `code-documentation` is enabled
- `.ai/project/consistency-map.json` when the optional module is enabled
