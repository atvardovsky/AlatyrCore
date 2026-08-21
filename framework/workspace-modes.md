---
alatyr_doc:
  id: framework.workspace-modes
  type: framework-rule-owner
  owns_rules:
    - ALATYR-MODE-001
  depends_on:
    - ALATYR-CONTEXT-001
    - ALATYR-SOURCE-001
    - ALATYR-RISK-001
    - ALATYR-APPROVAL-001
    - ALATYR-MODULE-001
    - ALATYR-EVIDENCE-001
  applies_to:
    - code-local
    - architecture-change
    - ai-infrastructure
    - framework-upgrade
---
# Workspace Modes

This document defines optional user-owned development modes for repositories
whose root, framework, application, skeleton, library, workspace-member, or
dependency roles cannot be represented safely by one undifferentiated project
context.

A mode selects context and explains the relationship between the current
workspace and the subject of work. It does not grant approval, write scope,
permissions, authority, tool access, or permission to weaken validation.

## Three Independent Facts

Never collapse these facts into one inferred label:

- workspace identity: the selected repository or explicit workspace scope
- artifact relationship: how another package, skeleton, member, or copied
  source relates to that workspace
- task mode: the user-approved operating perspective for the current task

The same framework can be `workspace-root` in its own repository, a passive
`dependency` in an application, or a `scaffold-origin` whose copied files are
now target-owned. A task profile such as `code-local` describes risk and
context needs; it does not determine this relationship.

## Ownership And Activation

The target project owns its workspace identity, accepted modes, default mode,
shared root context, and artifact relationships. An assistant may propose
modes from observed evidence but must not accept, enable, rename, or delete a
mode without a clear user decision under target change policy.

Only the adapter for the selected workspace scope is active. A mode cannot
activate nested adapters. Relationship values are:

- `workspace-root`: the selected root and its active adapter
- `workspace-member`: an explicitly declared member scope
- `dependency`: package-manager-resolved passive upstream content
- `scaffold-origin`: generation provenance and migration guidance only
- `vendored-source`: copied source maintained under explicit target policy

Adapter roles are `active`, `passive`, or `provenance-only`. Ownership is
recorded separately as `target`, `upstream`, or `mixed` with named evidence.

## Target Structure

When enabled, the target maintains:

- `.ai/project/workspace-modes/catalog.json` as the compact workspace,
  selection, and mode index
- `.ai/project/workspace-modes/root/context.json` as optional shared context
  routing
- `.ai/project/workspace-modes/root/README.md` as human-oriented shared
  rationale and canonical-source links
- `.ai/project/workspace-modes/modes/<mode-id>/mode.json` as one accepted,
  proposed, disabled, deprecated, or blocked mode descriptor
- `.ai/project/workspace-modes/modes/<mode-id>/README.md` as that mode's
  human-oriented explanation and source links

Every actual mode has its own directory. The source `_template` directory is
an authoring surface only and must never appear in the active catalog.

Each compact catalog entry records `id`, `title`, `state`, `mode_kind`, `path`,
`summary`, and `evidence_revision`. Its `path` is exactly
`.ai/project/workspace-modes/modes/<mode-id>/mode.json`; state, kind, and
identity must agree with that descriptor.

Human explanations and mode descriptors route to canonical project sources;
they do not become a second owner for architecture, behavior, security,
dependency, or business facts.

## Shared Root Context

Root support is optional. It is appropriate for compact facts that genuinely
apply to every selected mode, such as repository purpose, root ownership,
workspace map, global terminology entry point, or universal safety boundary.

The root descriptor records required and conditional target-relative context
paths. Keep it disabled or empty when no shared context is needed. Do not place
full blueprints, every policy, every command, or every mode's supporting files
in root context merely for convenience.

When enabled, root context is loaded after mode selection and only under the
descriptor's conditions. It is not routine bootstrap content.

## Mode Descriptor

Each `mode.json` records:

- stable mode ID, title, lifecycle state, owner, decision authority, and review
  evidence
- one mode kind: `application-development`, `framework-development`,
  `library-development`, `skeleton-development`, `dependency-integration`,
  `dependency-contribution`, `skeleton-migration`, `workspace-coordination`,
  or `custom`
- selected workspace scope and bounded include/exclude surfaces
- positive and negative selection signals
- explicit artifact relationships with role, adapter activation, ownership,
  and evidence
- root-context behavior plus required and conditional supporting context
- relevant source-of-truth IDs, validation entry-point IDs, known gaps, and
  mode-specific constraints

Paths select context or describe scope; they do not authorize writes. Mode
constraints may narrow actions, but they cannot broaden the operation's
allowed actions, approval, safety, source-of-truth, or gate policy.

## Installation Suggestions

During installation, the assistant should inspect repository purpose, Git and
workspace boundaries, package-manager manifests and locks, framework markers,
scaffolding provenance, existing instructions, build/test topology, and named
owners. It may then propose zero or more modes.

Each suggestion must provide:

- proposed ID, title, kind, purpose, and workspace scope
- observed evidence and confidence
- relationships and ownership transfer assumptions
- proposed shared and mode-specific context
- when to use and when not to use the mode
- overlap, ambiguity, maintenance cost, and validation
- files that acceptance would create or change

Suggestions remain `proposed`. Do not infer user acceptance from installation
approval, package presence, directory names, or a high confidence score. A
simple repository may need no mode module; record that conclusion instead of
creating ceremonial modes.

Re-suggest mode changes after repository restructuring, workspace changes,
new package/skeleton roles, repeated routing ambiguity, or framework update
that changes this contract. Preserve accepted target modes until the user
reviews a proposed migration.

## Selection Procedure

For each routed task when the module is enabled:

1. Read the compact catalog after bootstrap. Do not load every mode directory.
2. Prefer an explicit mode named by the user for the current task.
3. Otherwise compare accepted mode signals with current workspace, task
   subject, artifact relationship, paths, and operation evidence.
4. Automatically select only one accepted mode when the match is unambiguous
   and target policy permits automatic selection.
5. Use an accepted default only when its stated conditions apply; a default is
   not a fallback for contradictory evidence.
6. Ask the user when multiple modes match, no accepted mode can represent the
   requested relationship, or workspace identity conflicts with the request.
7. Load the selected descriptor, permitted root context, and only the named
   supporting context. Then compose the ordinary task profile, intent, area,
   gate, and task-scale overlays.
8. Show a compact preflight before changes: workspace, mode, task profile,
   subject relationships, active/passive adapter roles, ownership, context,
   candidate surfaces, and ambiguity result.
9. Record the selected mode in operation or task evidence. Selection is
   per-task unless target policy explicitly permits a local default hint.

Do not persist silent session state as canonical project configuration. A
local preference is a hint and must not override an explicit task request or
current contradictory evidence.

## Mode Changes

`list`, `status`, `suggest`, `inspect`, and selection preview are read-only.
Creating, accepting, updating, disabling, deprecating, or removing a mode is
an adapter/project-knowledge change and requires a preview plus the user
decision required by target policy.

Mode changes that alter accepted architecture, ownership, security policy,
dependencies, production behavior, permissions, or validation use the normal
protected operation and approval path. Deleting a mode must preserve or
relocate evidence referenced by active tasks, decisions, or migrations.

## Ambiguity And Failure

Stop before state-changing work when:

- selected workspace root or active adapter is unclear
- a request names a framework/application relationship contradicted by target
  evidence
- multiple accepted modes match with materially different ownership or scope
- an accepted mode descriptor is missing, stale, unresolved, or references
  context outside the target
- a mode would activate a dependency or scaffold adapter
- a selected mode attempts to broaden allowed actions or bypass a gate

The safe fallback is read-only explanation from known root evidence with the
mode reported as unresolved. Do not guess a mode and continue changing files.

## Cost And Validation

Keep the catalog compact. Load one mode descriptor, shared root context only
when enabled, and selected support paths. Measure the added file and context
cost before claiming that modes improve speed or cost.

Deterministic checks should validate unique IDs, directory/path agreement,
accepted-mode completeness, catalog/descriptor state agreement, relationship
enums, one active root relationship, target-relative context, known source and
validation references when registries permit it, and absence of `_template`
from active records. They cannot prove that a suggested mode is strategically
correct or that an assistant followed the selected mode.

## Final Evidence

Report:

- workspace identity and selected scope
- explicit, automatic, default, or unresolved selection basis
- selected mode ID, kind, lifecycle state, and evidence revision
- artifact relationships, adapter roles, and ownership
- root and mode context loaded, skipped, and expanded
- composed task profile, intent, area, gate, and task-scale overlays
- mode constraints and confirmation that they did not grant permission
- suggestion or mode-definition changes and user decision evidence
- validation, skipped checks, ambiguity, context cost, and residual risk
