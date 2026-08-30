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
- explicit advertised, selected, supported, verified, and freshness state
- product lifecycle and source-support status
- exact client/runtime variant, selected instruction entry path, competing
  sources, rule-toggle/configuration state, observed auto-load, precedence
  evidence, and freshness review triggers
- skill discovery paths, selected source, activation mode, and evidence
- auto-load behavior
- instruction priority or known precedence
- supported Markdown, prompt, rule, or skill surfaces
- AI infrastructure router and item-ID support
- tool permission model
- evidence that client permissions or auto-approval restrict execution but do
  not grant Alatyr modify, commit, publish, or live-external authorization
- whether operation help aliases are routed
- whether the single `Alatyr` entry and read-only status/doctor aliases route
  through the compact index and canonical catalog
- whether automatic routing and risk-gated pre-change preview reach the same
  canonical flow on every supported surface
- whether current-scope inspect, modify, commit, publish, and live-external
  authorization routes through the same canonical policy on every supported
  surface
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
- whether optional subagent delegation routes through the target policy,
  worker orchestration prompt, role catalog, delegated-execution overlay,
  task/packet/result templates, and primary convergence
- whether the surface uses native workers, an approved external dispatcher,
  suggestion-only handoff, or no delegation
- which target AI-infrastructure item owns an external dispatcher, including
  its permissions, approval, provenance, privacy, and failure behavior
- exact client/runtime; whether the selected backend supports explicit or
  automatic delegation, project worker definitions and their target paths,
  tool restrictions, write isolation, background or nested execution, model
  override, parallel dispatch, and actual-model evidence
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
`.ai/assistant/assistant-capabilities/`. The compact index must record the
selected-surface evidence model and treat the per-surface records as
authoritative. Each record must use capability schema 3 and constrained
values. It records the explicit surface state, instruction loading, skill
routing, tool-permission separation, diagrams, and delegation with client
version, verification, expiry, or review-trigger freshness evidence. The
source template generator also projects bridge-path ownership from the
canonical source surface registry so an installed validator can distinguish
unsupported bridges without hard-coded vendor mappings. Derive the index from
those sources; do not manually maintain duplicate capability claims or bridge
ownership.

Surface state has four separate meanings that must not collapse into one
claim:

- `advertised_by_surface`: the vendor or client appears in the target support
  set.
- `selected_for_target`: the target adapter is currently using that surface.
- `overall`: the target's current support judgment for that surface.
- `evidence_state` and `verified_for_target`: whether the judgment is backed
  by current target evidence.

Unknown, stale, expired, or unverified evidence is not support evidence. It
should route to recheck or manual review before an assistant relies on native
skills, workers, diagrams, permissions, or auto-loaded instructions.

Neutral project entry points remain active validation surfaces regardless of
assistant selection. A vendor-specific bridge may be treated as inactive only
when every owning surface is represented, explicitly unsupported, and
unselected. Missing, malformed, partial, or unknown ownership and capability
evidence remains active fail-safe.

## Baseline Template Surfaces

The target bridge capability matrix template should include baseline entries
for the assistant surfaces tracked by the source conformance surface list:

- generic
- agents
- codex
- junie
- cline
- roo-code (legacy compatibility for the archived client)
- kiro
- zed-agent
- opencode
- claude
- gemini
- github-copilot
- cursor
- devin-cascade
- windsurf

Targets may mark a surface unsupported or not applicable, but a missing row
should be treated as a bridge capability gap when that assistant is expected
to work.

Named source admission means AlatyrCore has a checked static bridge and target
evidence contract. It does not prove a vendor client loaded or followed the
instructions. Keep runtime capabilities unknown until an exact-client run
records instruction precedence, configuration/toggle state, permissions,
skills, delegation, diagram presentation, and post-install/update delivery.

Use root `AGENTS.md` for Junie, Cline, Kiro, and OpenCode unless target evidence
requires a reviewed native adaptation. Preserve `.junie/AGENTS.md`, Junie
custom-guideline settings, Cline rule directories/toggles, Kiro steering and
custom-agent resources, and OpenCode V1/V2 differences during inspection. Use
the generated `.rules` thin bridge for Zed Agent because it is the first
compatible project instruction path. Keep `.roo/rules/alatyr-core.md` only as
a legacy bridge; Roo Code was archived and shut down on 2026-05-15, so do not
claim maintained or current runtime support.

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
- route state-changing phases through the target action-authorization policy;
  bridge or client tool permission must not grant commit, publish, or live
  action authority
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
- route enabled subagent delegation through the target policy and selected
  capability record; native, external, and suggestion-only routes use the same
  worker orchestration, role, task, packet, result, and convergence contracts,
  while unsupported surfaces continue locally without pretending a dispatch
  or model override occurred
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
- bind a selected target assistant to a capability record whose instruction
  route is not contradicted by its bridge, runtime variant, or precedence

If an assistant surface cannot auto-load a bridge, record the manual loading
step or unsupported status.

Source conformance may prepare the same fixture prompt for every supported
surface and verify bridge discovery deterministically. This proves source
contract coverage only. Actual assistant runs should capture the selected
capability record, loaded paths or sections, context measurement kind,
presentation result, fallback, repository changes, and residual risk. Hidden
client context must remain `unknown` unless the client exposes evidence.

Conformance execution uses one provider-neutral lifecycle: `prepare`,
`invoke-or-manual-import`, `collect`, and `validate`. A native provider adapter
may implement invocation when the current runtime supports it. Other surfaces
remain manual or unverified until reviewed reports are imported. Static
fixtures, prepared matrices, manual imports, and capability declarations must
never be represented as observed vendor execution.

## Upgrade Use

During framework update or adapter recheck:

1. Read the matrix.
2. Check every listed bridge file still exists.
3. Check each bridge points to the same canonical entry points.
4. Check the compact operation index still derives exactly from the catalog.
5. Check operation aliases still route to the canonical flows.
6. Recheck instruction entry path, runtime variant, competing sources, client
   toggles/configuration, observed auto-load, skills, and permissions. A new
   surface remains runtime-unverified until target evidence is captured.
7. Check diagram presentation claims, enums, client version, verification
   time, expiry or review triggers, and evidence against current surface
   capability; retain the ASCII baseline for unknown, stale, or unsupported
   rich rendering.
8. When delegation is enabled, recheck the exact client/runtime, role bindings,
   native worker-definition format and paths, permissions, isolation,
   background/nested behavior, and fallback. Remove stale generated native
   definitions when support is no longer accepted; never infer replacement
   paths from another assistant.
9. Report bridge-specific limitations and residual risk.
