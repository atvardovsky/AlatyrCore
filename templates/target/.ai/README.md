# AI Area Map

This directory is split by ownership.

For routine routing, treat root `AGENTS.md` as preloaded and read only this
file, `.ai/alatyr.yaml`, and `.ai/assistant/context-router.json`. Load the
blueprint, registries, contours, module profile, and human context profiles
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
- blueprint or equivalent source-of-truth facts
- source-of-truth registry entries
- optional machine-readable consistency relationships for bounded impact
  traversal
- use cases or workflows
- business/domain rules
- data model
- runtime flows
- project terminology and decisions

Replace this section with the actual target project map.

## Repository Adapter Area

`.ai/assistant` contains local assistant operating rules:

- context profiles for task-specific context loading
- module profile for required core and optional Alatyr capabilities
- task-specific maturity profile
- bridge matrix and indexed per-assistant capability evidence
- portable ASCII diagram layout and readability rules
- flows
- architecture-assistance flow and pattern/area/result record templates when
  the project architecture-knowledge module is enabled
- code-documentation intent, profile-review template, adapted skill, and
  generated-reference flow when the project code-documentation module is
  enabled
- gates
- prompts
- skills
- skill adaptation and provenance rules
- prompt-injection rules for imported AI infrastructure
- human and machine-readable approval records, diff-base binding, and strict
  changed-path scope enforcement
- bridge-file policy
- validation evidence expectations
- documentation-sync rules
- installed-operation requests and adapter rechecks
- optional large-task operation packets, bounded workstreams, checkpoints,
  and resume evidence under a target-owned storage policy
- optional change packages for coherent material outcomes, semantic approval
  scope, companion decisions, implementation corrections, and before-to-after
  repository provenance
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
supported assistants, source-of-truth files, module state, validation entry
points, known gaps, and local deviations.
