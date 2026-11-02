# Documentation Sync Flow

Keep project support synchronized with changed facts, using coherent indexed
topics under
`.ai/framework/support-information.md#topic-layout-and-legacy-refactoring`.
Never impose one convention repository-wide.

## Routing Modes

- `inventory`: locate areas, canonical owners, profiles, generators and gaps
- `propose`: recommend evidence-backed comment/generator profiles
- `review`: check profiles, comments, output, freshness and ambiguity
- `document`: update comments under an accepted profile
- `synchronize`: update required companion surfaces
- `generate`: run the accepted generator within its output policy
- `refactor-proposal`: assess legacy support and propose a bounded migration
- `refactor`: apply the specifically approved migration

Route clear requests automatically; users need not name modes.

## Allowed Actions

- `read-only`: inspect, explain or propose; no file, CI or publication changes
- `docs-only`: edit authorized project docs or proposed profiles; no mass source
  edits or profile acceptance
- `code-and-tests`: edit authorized comments and run accepted local generators;
  no dependency installation, CI change or publication
- `full-with-approval`: only specifically approved protected changes

These modes never supply approval. Generic update/sync authorization does not
authorize legacy restructuring or accepted-profile changes.

## Steps

1. Classify mode, changed facts, current authorization, scope and project area.
   Apply the Semantic Change Decision Gate in
   `.ai/assistant/gates/checklist.md` and `.ai/framework/logical-integrity.md`.
2. Resolve canonical owners and dependencies. Follow applicable `documents`,
   `visualizes`, `generates`, `verifies` and dependent-contract edges when
   `consistency-map` is enabled; otherwise review companion surfaces manually.
3. For legacy refactoring, follow the owning topic-layout contract: bind the
   proposal to sources, review semantic boundaries, pilot, obtain explicit
   current-scope approval, preserve authority/conflicts/provenance, update
   references and indexes, verify and retain rollback. Assessment never applies.
4. For comments/generated references, require enabled `code-documentation`;
   select from `.ai/project/documentation/catalog.json` and `profiles.json`
   by source-set/path, language, framework, specificity and priority. Stop on
   equal conflicts; missing accepted profiles route to read-only `propose`.
5. Inspect existing comments, compilers, linters, generators, sites, scripts,
   CI, IDE support, specifications, owners, recurring findings and maintenance
   constraints. Prefer existing conventions; compare language-appropriate
   alternatives before proposing syntax and semantic content separately.
   Frontend, backend, shared-library, and infrastructure profiles may differ.
6. Edit comments only under an accepted unambiguous profile, retaining required
   symbols/sections, content focus, avoid rules, uncertainty and source-of-truth
   boundaries. Do not repeat syntax/types or infer accepted intent from code.
7. Never edit a configured generated output directly. Run only authorized
   target-recorded generators. Enforce `ci-artifact` success,
   `committed-generated` freshness without unexplained diff, `local-only`
   retention, or separately approved `external-publish`; `unresolved` blocks
   generation readiness.
8. Synchronize required docs, tests, diagrams, prompts, gates, skills, bridges
   and checker rules. Apply `.ai/assistant/gates/contract-artifacts.md` for affected contracts
   and `.ai/assistant/gates/visual-validation.md` for rendered/UI/accessibility surfaces.
9. Run recorded target lint, generation, links, examples, builds, visual checks
   or manual review. Report selected/skipped relationships, profile/state,
   changed/skipped symbols, output/direct-edit findings, artifact/visual
   results, validation/skips, approvals, Project Contour Sync Decision and risk.
   Generation success does not prove semantic correctness.

## Target Sources

- `{TARGET_PROJECT_SOURCE_OF_TRUTH}`, `{TARGET_PUBLIC_DOCS}`
- `{TARGET_BLUEPRINT_OR_EQUIVALENT}`, `{TARGET_TEST_STRATEGY}`
- `{TARGET_DIAGRAM_POLICY}`
- Selected enabled documentation profiles and consistency map only
