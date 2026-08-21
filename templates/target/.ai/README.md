# AI Area Map

This directory is split by ownership.

For routine routing, treat root `AGENTS.md` as preloaded and read only
`.ai/assistant/bootstrap-index.json`. That file is a generated, hash-bound
projection of this project map, `.ai/alatyr.yaml`, and
`.ai/assistant/context-router.json`; load those canonical sources when the
projection is stale, routing is ambiguous, or adapter repair is required. Load
the blueprint, registries, contours, module profile, and human context profiles
only when the selected task profile, task-scale overlay, or project-area
overlay requires them.

## Framework Area

`.ai/framework` contains Alatyr Core portable framework rules.

Framework files must not contain `{PROJECT_NAME}` business facts, target
commands, target security policy, target diagram tooling, or target lifecycle
facts, or target skill infrastructure.

## Project Area

`.ai/project` contains target product facts:

- product purpose
- architecture facts
- optional architecture knowledge index and compact catalog for selected
  patterns, areas, states, owners, evidence revisions, and documentation routes
- optional code-documentation index, compact catalog, and source-set profiles
  for selected comment styles, generators, outputs, owners, and evidence
- optional project-vocabulary catalog, scoped terms, and canonical data links
- optional project-owned test-first policy with bounded recommendation,
  explicit enablement, target commands, and RED/GREEN/refactor evidence
- optional declarative external extensions with compact catalog, immutable
  source and installed-file lock, target bindings, permissions, and lifecycle
- optional passive dependency knowledge with exact resolved-artifact binding,
  target-owned trust/freshness/authority/applicability state, deviations,
  retention, bounded synchronization, lazy explanation, and impact routing
- optional user-owned workspace modes with an explicit active root, artifact
  relationships, one directory per actual mode, and optional shared root
  support outside routine bootstrap
- blueprint or equivalent source-of-truth facts
- source-of-truth registry entries
- optional machine-readable consistency relationships for bounded impact
  traversal
- use cases or workflows
- business/domain rules
- data model
- runtime flows
- project terminology and decisions
- compact durable engineering evidence for material task invariants, root
  causes, solution rationale, regression intent, validation, and repository
  binding; these historical records link to but do not replace canonical owners
- optional non-canonical Debug Mode evidence for measuring Alatyr contribution
  and human supervision in explicitly selected task/session scopes

Replace this section with the actual target project map.

## Repository Adapter Area

`.ai/assistant` contains local assistant operating rules:

- a compact generated bootstrap index that does not own project facts or rules
- context profiles for task-specific context loading
- module profile for required core and optional Alatyr capabilities
- compact workspace-mode routing and per-mode support when application,
  framework, library, skeleton, dependency, or workspace perspectives differ
- task-specific maturity profile
- bridge matrix and indexed per-assistant capability evidence
- portable ASCII diagram layout and readability rules
- flows
- architecture-assistance flow and pattern/area/result record templates when
  the project architecture-knowledge module is enabled
- code-documentation intent, profile-review template, adapted skill, and
  generated-reference flow when the project code-documentation module is
  enabled
- vocabulary route, review template, flow, and skill when enabled
- gates
- a compact gate index and phase-specific gate fragments; the complete
  checklist remains lazy for audits and repair
- prompts
- skills
- skill adaptation and provenance rules
- prompt-injection rules for imported AI infrastructure
- human and machine-readable approval records, diff-base binding, and strict
  changed-path scope enforcement
- current-scope action authorization separating inspection, repository edits,
  commits, publication, and live external effects
- bridge-file policy
- validation evidence expectations
- documentation-sync rules
- installed-operation requests and adapter rechecks
- optional large-task operation packets, bounded workstreams, checkpoints,
  and resume evidence under a target-owned storage policy
- optional change packages for coherent material outcomes, semantic approval
  scope, companion decisions, implementation corrections, and before-to-after
  repository provenance
- lazy durable engineering-evidence capture and validation that preserves
  normalized conclusions without raw chat or assistant reasoning traces
- optional task-local Debug Mode activation, normalized event capture,
  evidence-based supervision metrics, clean-upstream projection, and compact
  summaries without making debug records project authority
- migration notes for framework updates
- operation help, operation routing, and post-install/update assistant chat
  messages
- canonical operation catalog, checked compact alias index, single `Alatyr`
  entry point, read-only adapter health, and risk-gated pre-change preview
- AI infrastructure inventory, project-evidenced recommendation, source access,
  adaptation, and compatibility review
- AI infrastructure router entries for selecting target skills, prompts,
  gates, checkers, tools/MCP configs, bridges, wrappers, permissions,
  validation, and output contracts
- durable AI infrastructure adaptation records for imported or materially
  changed items

Target commands and manual checks belong here or in linked target docs. They
are not framework core.

## Adapter Manifest

`.ai/alatyr.yaml` records target-owned installation metadata such as framework
version, adapter schema version, template version, selected support profile,
installed framework pack and projected inventory,
supported assistants, source-of-truth files, module state, validation entry
points, known gaps, and local deviations.
