---
alatyr_doc:
  id: framework.project-adapter-contract
  type: framework-rule-owner
  owns_rules:
    - ALATYR-ADAPTER-001
  depends_on: []
  applies_to:
    - framework-upgrade
    - ai-infrastructure
---
# Alatyr Core Project Adapter Contract

A project adapter binds the portable AI framework to one concrete repository.
It preserves the boundary between portable framework rules, project-owned
facts, and repository-local assistant behavior.

## Contract Boundary

`ALATYR-ADAPTER-001` owns the adapter's structural interface. It does not own
the detailed behavior of every capability that an adapter can carry. Those
semantics remain with the rule owner named by
[`framework/rule-registry.json`](rule-registry.json) and with the selected
capability definition in [`framework/capabilities.json`](capabilities.json).

The adapter rule is foundational, so its metadata intentionally has no rule
dependencies. Downstream rule owners may compose `ALATYR-ADAPTER-001`; adding
all downstream rules as adapter dependencies would reverse that relationship
and create cycles.

The deterministic structural inputs are:

- `framework/rule-registry.json` for rule IDs and source owners
- `framework/capabilities.json` for capability files, dependencies, checks,
  and target surfaces
- `framework/framework-packs.json` for dependency-closed portable file sets
- the target manifest and module profile for the target's selected state

Installation plans, readiness views, help, and validation reports are derived
projections of those owners plus target evidence. They must not become
independent copies of downstream policy.

## Adapter Must Provide

Every project using this framework must define these structural bindings:

- **Identity and lifecycle:** framework version, adapter schema version,
  template version, selected support profile, installed framework pack,
  installation state, baseline revision, known gaps, and local deviations.
- **Ownership:** responsible project owner, technical owner, backup or
  escalation route, review triggers, and file ownership where the repository
  supports it.
- **Contour separation:** explicit project, portable-framework, and
  repository-adapter contours, including which contour owns each kind of fact.
- **Project evidence entry points:** project source-of-truth owners, validation
  entry points, generated-artifact boundaries, and missing-evidence escalation.
- **Installed framework projection:** a dependency-closed selected pack whose
  installed rule registry, ownership map, file inventory, and framework files
  agree with the source projection.
- **Capability state:** required core state plus enabled, deferred, disabled,
  not-applicable, and blocked optional capabilities with reasons. Enabled
  capabilities must satisfy the catalog's dependency and required-surface
  closure.
- **Assistant routing:** bounded context selection, supported assistant entry
  points, bridge pointers, operation routing, recursive framework, project,
  and assistant context indexes, semantic-codebook binding, resolved packet
  evidence, local action boundaries, and per-surface provider context-caching
  evidence. Assistant surface and model provider are separate facts. Cache
  delivery must retain bounded-routing fallback and must not claim to reduce
  context-window occupancy.
- **Support-information state:** target-owned collection/classification policy,
  canonical cross-platform digests, changed-surface evidence, and bounded
  impact routing with unresolved relationship candidates kept non-authoritative.
- **Local execution bindings:** project-specific validation, approval,
  authorization, safety, output-evidence, and checker status. Missing local
  automation must be reported as a gap rather than represented as available.
- **Acceptance evidence:** an explicit staged or accepted result showing that
  installed files, selected capability state, target facts, local checks, and
  unresolved placeholders were evaluated at the target revision.

The exact contents of a selected capability are defined by its canonical rule
owner and catalog entry. Required Project Development Model guidance remains a
derived envelope over registered canonical project owners; it is not a new
fact store. Optional architecture knowledge, project
vocabulary, test-first development, extensions, dependency knowledge,
workspace modes, diagrams, team collaboration, delegation, Debug Mode, and AI
infrastructure each keep their detailed policy outside this structural
contract.

Optional support generation also remains outside this structural contract. Its
registry may coordinate existing generators, but it cannot become the owner of
the facts or generation policies that those artifacts project.

## Capability Composition

For every selected capability, the adapter must:

1. Resolve its dependency closure from `framework/capabilities.json`.
2. Install the owning rule through the selected framework pack.
3. Bind required target surfaces to evidence from the target repository.
4. Preserve the canonical owner as the semantic authority.
5. Validate the capability with its declared deterministic checks or record
   the target-owned manual-review gap.
6. Project only the compact status and references needed by aggregate
   installation, readiness, help, and lifecycle views.

A capability that is not selected does not become an adapter requirement merely
because its rule exists in AlatyrCore. A capability reported as enabled must not
retain deferred, unavailable, or unresolved live-state claims.

## Adapter May Provide

An adapter may add target-owned checks, reports, records, wrappers, generated
artifacts, hooks, external integrations, or public explanations when required
by selected capabilities or local engineering needs. Their ownership,
retention, permissions, and validation remain target decisions.

These are adapter details. They are not portable framework core and must not be
promoted into this contract as universal project facts.

## Adapter Must Not

The adapter must not:

- merge framework, project, and repository-adapter facts into one owner
- present target-specific business logic, commands, tools, or policies as
  portable framework requirements
- declare a capability enabled without its dependency, owner, required-file,
  and validation closure
- copy detailed downstream policy into aggregate adapter surfaces instead of
  referencing its canonical rule owner
- represent staged, unresolved, or unchecked content as an accepted adapter
- let assistant bridges or generated summaries become divergent sources of
  truth
- let recursive indexes, semantic terms, or context packets become canonical
  fact owners, redefine target vocabulary, or hide unresolved policy
- weaken a selected rule owner's approval, authorization, safety, integrity,
  or validation contract through adapter-local wording
- advertise operations or assistant behavior that the target cannot route and
  validate

## Source And Installed Owner Identities

AlatyrCore source owners use repository paths such as
`framework/context-profiles.md`. Their installed projections use target paths
such as `.ai/framework/context-profiles.md`. Generated ownership documentation
must show both identities explicitly; an installed `.ai/...` path is not a
source-repository canonical path.

Project facts and repository-local assistant behavior are not projections of
framework owners. They remain target-owned under surfaces such as `.ai/project`
and `.ai/assistant`.

## Typical Target Adapter

In a target repository, the adapter usually includes:

- `AGENTS.md` and `AI_ASSISTANTS.md`
- `.ai/alatyr.yaml` or equivalent adapter manifest
- `.ai/framework` containing the selected portable framework pack
- `.ai/project` containing project-owned facts, canonical-owner references,
  and derived Project Development Model guidance routes
- `.ai/assistant` containing repository-local routing, gates, and operations
- optional project-selected skills and assistant-native wrappers
- local consistency checks, validation commands, or manual-review rules owned
  by that repository

Those files apply Alatyr Core to one project. Target-owned surfaces must be
rewritten from target evidence rather than copied from another project.
