# Repository AI Adapter Contour

This contour describes how assistants operate in `{PROJECT_NAME}`.

Replace placeholders with target facts before accepting installation.

## Owns

- assistant workflows under `.ai/assistant/flows`
- gates under `.ai/assistant/gates`
- policies under `.ai/assistant/policies`
- current-scope action-phase policy under
  `.ai/assistant/policies/action-authorization.json`; it distinguishes
  inspection, modification, commit, publication, and live external action
- context profiles under `.ai/assistant/context-profiles.md`
- recursive framework, project, and assistant context indexes with bounded
  traversal, selectors, word estimates, and content digests
- versioned semantic-codebook resolution with a bounded core preload and lazy
  domain shards
- deterministic context packets for expanded, handed-off, or resumed work
- module profile under `.ai/assistant/module-profile.md`
- adapter manifest facts under `.ai/alatyr.yaml`
- task-specific maturity under `.ai/assistant/maturity-profile.md`
- bridge capability matrix under `.ai/assistant/bridge-capability-matrix.md`
- compact assistant capability projection under
  `.ai/assistant/assistant-capabilities.json`
- migration notes under `.ai/assistant/templates/migration-note.md`
- human and machine-readable approval records plus target-local strict diff
  scope checks under `.ai/assistant/approvals`
- prompts, skills, bridge files, and assistant-specific wrappers
- AI infrastructure inventory, project-evidenced recommendation, source access,
  provenance, adaptation, output-format, prompt-injection, safety, and wrapper
  rules
- lazy development-evidence capture mechanics; normalized pattern facts remain
  owned by `.ai/project/development-evidence.json`
- lazy durable engineering-evidence routing, capture, privacy/publication gate,
  template, and structural validation; normalized historical conclusions and
  storage policy remain project-owned under `.ai/project/engineering-evidence`
- optional Debug Mode routing, explicit activation/expiry, checkpoint,
  finalization, executor/Alatyr-system/automation attribution, actor identity,
  runtime provenance, correction disposition, metric derivation, summary, and
  structural validation; non-canonical records remain project-owned under
  `.ai/project/debug`
- AI infrastructure route/item contracts and adaptation records under
  `.ai/assistant/ai-infrastructure-router.json` and target-owned record paths
- target validation commands or manual checks
- blueprint-driven change or equivalent target product-change workflow
- installed-operation request, blueprint-creation, adapter-recheck, and
  framework-update review flows
- operation catalog, checked compact operation index, single `Alatyr` entry,
  automatic routing, current-scope action authorization, read-only health,
  risk-gated preview, help, and
  post-install/update assistant chat message templates
- diagram discussion routing and presentation mechanics when the diagrams
  module is enabled; project diagram facts and accepted source ownership remain
  in the project contour
- team operation mechanics, work registry projection, claims, conflict checks,
  checkpoints, handoffs, decision capture, team review, and revision-bound
  merge-readiness evidence when the optional module is enabled; project-owned
  actors, authority, priorities, and accepted decisions remain in the project
  contour
- ignored current-actor selection, compact active-work preflight, per-task
  record mechanics, optimistic concurrency, and coordination-backend contracts
  when team collaboration is enabled; local selection is attribution, not
  authentication or authority
- documentation-sync rules
- code-documentation intent routing, accepted-profile selection, adapted skill,
  generator execution, and derived-output evidence when the optional module is
  enabled; profile policy and documentation-area facts remain in the project
  contour
- project-vocabulary intent routing, compact lookup, proposal, terminology
  checks, adapted skill, and synchronization evidence when the optional module
  is enabled; term meanings, states, owners, and links remain in the project
  contour
- test-first recommendation, configuration and execution routing, adapted
  skill, gate, and cycle evidence when enabled; policy, commands, trigger
  severity, isolation, exceptions, and decision authority remain in the
  project contour
- extension catalog, lock, normalized manifests/items, target bindings,
  lifecycle routing, gates, adaptation evidence, and installed-file ownership;
  external source remains untrusted and project facts remain project-owned
- dependency-knowledge intent, non-executing synchronization, bounded lookup,
  explanation, impact routing, and structural validation when enabled;
  package graph facts, trust decisions, applicability, deviations, and retained
  snapshots remain in the project contour
- workspace-mode intent, compact selection, evidence-bound suggestion,
  per-task preflight, lifecycle flow, and gate when enabled; workspace
  identity, accepted modes, relationships, ownership, and shared or per-mode
  support remain in the project contour
- final evidence requirements
- target adapter maturity and lifecycle notes
- required core profile, enabled optional modules, deferred modules, and
  blocked module gaps
- framework version, adapter schema version, template version, known gaps, and
  local deviations

## Does Not Own

- portable Alatyr Core framework rules
- target product/business facts
- target team identity, authority, priority, review, coordination-backend,
  retention, privacy, and accepted decision facts
- target blueprint or equivalent source-of-truth content
- generated visual artifacts unless the target adapter says they are source

## Relationship To Framework Core

`.ai/framework` defines portable Alatyr Core rules. This adapter applies those
rules to `{PROJECT_NAME}` using target facts and validation.
