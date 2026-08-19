---
alatyr_doc:
  id: framework.bridge-capability-matrix
  type: framework-rule-owner
  owns_rules:
    - ALATYR-BRIDGE-001
  depends_on:
    - ALATYR-ADAPTER-001
  applies_to:
    - ai-infrastructure
    - framework-upgrade
---
# Bridge Capability Matrix

A bridge capability matrix records how each supported assistant surface loads
instructions and what limitations apply.

Thin bridge files are still required, but thinness alone does not prove
equivalent behavior across assistants. The matrix makes differences explicit.

## Matrix Contract

For each supported assistant, record:

- assistant surface ID and display label
- bridge file path
- auto-load behavior
- instruction priority or known precedence
- supported Markdown, prompt, rule, or skill surfaces
- AI infrastructure router and item-ID support
- tool permission model
- whether operation help aliases are routed
- whether the single `Alatyr` entry and read-only status/doctor aliases route
  through the compact index and canonical catalog
- whether automatic routing and risk-gated pre-change preview reach the same
  canonical flow on every supported surface
- whether AI infrastructure inventory, recommendation, and adaptation aliases
  are routed
- whether enabled team status, task, conflict, handoff, decision, review, and
  merge-check requests route through the canonical catalog and lazy team
  overlay
- whether enabled code-documentation aliases route through the canonical
  operation index, documentation intent, selected target profile, and shared
  flow regardless of assistant-native skill support
- whether enabled project-vocabulary aliases route through the canonical
  operation index, vocabulary intent, compact catalog, selected term records,
  and shared flow regardless of assistant-native skill support
- whether test-first configuration and enabled execution aliases route through
  the canonical operation index, intent, target policy, selected flow, and
  shared gate regardless of assistant-native skill support
- whether extension list, inspection, installation, update, disablement,
  removal, and review aliases route through the canonical operation index,
  selected catalog/lock entry, lifecycle flow, and shared gate
- the selected path in the compact generated assistant-capability index
- whether diagram discussion routes through the canonical operation index
- supported native inline diagram syntaxes and artifact presentation mode;
  portable ASCII remains required without client capability evidence
- client version, verification time, and evidence for capability freshness
- whether selected AI infrastructure items route through canonical target
  permissions, gates, validation, and output contracts
- known limitations
- conformance check or manual review

The target adapter owns exact assistant behavior. The framework only requires
the behavior to be discoverable and kept consistent with canonical target
files.

The human bridge matrix owns explanatory precedence and limitation notes.
`.ai/assistant/assistant-capabilities.json` is its compact runtime projection
for selecting one assistant surface without loading the whole matrix. It maps
surface IDs to separate target-owned records under
`.ai/assistant/assistant-capabilities/`. Each record must use constrained
values, retain client version, verification, expiry or review-trigger
freshness evidence, and be checked against the surface list and matrix
references. Derive the index from those records; do not maintain duplicate
capability claims in the index.

## Baseline Template Surfaces

The target bridge capability matrix template should include baseline entries
for the assistant surfaces tracked by the source conformance surface list:

- generic
- agents
- codex
- claude
- gemini
- github-copilot
- cursor
- devin-cascade
- windsurf

Targets may mark a surface unsupported or not applicable, but a missing row
should be treated as a bridge capability gap when that assistant is expected
to work.

## Conformance Expectations

Each bridge should:

- preserve the compact bootstrap directly: load `AGENTS.md` exactly once
  (host-preloaded when supported), then load the manifest, compact project map,
  and context router
- point to the canonical root entry point
- point to the compact operation index, canonical catalog, compact help, and
  operation routing
- route `Alatyr`, `Alatyr status`, and `Alatyr doctor` without presenting them
  as executable shell commands
- route `alatyr-ai-inventory`, `alatyr-suggest-ai`, `alatyr-improve-ai`,
  `alatyr-adaptation`, and `alatyr-add-ai` when those aliases are supported by
  the target
- route selected AI infrastructure work through the canonical target router
  instead of choosing item content from a bridge
- route current-actor aliases and enabled team operations through the
  canonical catalog and `.ai/assistant/team/context-overlay.json`, and apply
  the active-work preflight before state-changing operations instead of
  embedding team or identity policy
- route enabled code-documentation requests through the canonical operation
  index and intent descriptor; assistant-native wrappers point to the shared
  target profile and do not duplicate comment policy
- route enabled project-vocabulary requests through the canonical operation
  index and intent descriptor; assistant-native wrappers point to the shared
  target records and do not duplicate term definitions
- route test-first configuration while the module is disabled and route
  execution only when enabled, without duplicating target triggers, commands,
  isolation, or exceptions in bridge files
- route extension lifecycle requests through the canonical target catalog,
  lock, intent, and flow; never let a bridge fetch, trust, activate, update, or
  remove an extension independently
- route enabled `Alatyr diagram` and equivalent requests through the compact
  operation index, diagram discussion flow, presentation template, and only
  the selected assistant-capability record
- provide the same bounded pure-ASCII baseline on every supported surface,
  with native or artifact output only as a capability-checked supplement
- avoid duplicating full framework, project, or adapter policy
- avoid becoming a source of truth for project facts
- state assistant-specific limitations only when target evidence supports
  them

If an assistant surface cannot auto-load a bridge, record the manual loading
step or unsupported status.

Source conformance may prepare the same fixture prompt for every supported
surface and verify bridge discovery deterministically. This proves source
contract coverage only. Actual assistant runs should capture the selected
capability record, loaded paths or sections, context measurement kind,
presentation result, fallback, repository changes, and residual risk. Hidden
client context must remain `unknown` unless the client exposes evidence.

## Upgrade Use

During framework update or adapter recheck:

1. Read the matrix.
2. Check every listed bridge file still exists.
3. Check each bridge points to the same canonical entry points.
4. Check the compact operation index still derives exactly from the catalog.
5. Check operation aliases still route to the canonical flows.
6. Check diagram presentation claims, enums, client version, verification
   time, expiry or review triggers, and evidence against current surface
   capability; retain the ASCII baseline for unknown, stale, or unsupported
   rich rendering.
7. Report bridge-specific limitations and residual risk.
