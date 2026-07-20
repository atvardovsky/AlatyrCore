# Repository AI Adapter Contour

This contour describes how assistants operate in `{PROJECT_NAME}`.

Replace placeholders with target facts before accepting installation.

## Owns

- assistant workflows under `.ai/assistant/flows`
- gates under `.ai/assistant/gates`
- policies under `.ai/assistant/policies`
- context profiles under `.ai/assistant/context-profiles.md`
- module profile under `.ai/assistant/module-profile.md`
- adapter manifest facts under `.ai/alatyr.yaml`
- task-specific maturity under `.ai/assistant/maturity-profile.md`
- bridge capability matrix under `.ai/assistant/bridge-capability-matrix.md`
- migration notes under `.ai/assistant/templates/migration-note.md`
- human and machine-readable approval records plus target-local strict diff
  scope checks under `.ai/assistant/approvals`
- prompts, skills, bridge files, and assistant-specific wrappers
- AI infrastructure inventory, project-evidenced recommendation, source access,
  provenance, adaptation, output-format, prompt-injection, safety, and wrapper
  rules
- lazy development-evidence capture mechanics; normalized pattern facts remain
  owned by `.ai/project/development-evidence.json`
- AI infrastructure route/item contracts and adaptation records under
  `.ai/assistant/ai-infrastructure-router.json` and target-owned record paths
- target validation commands or manual checks
- blueprint-driven change or equivalent target product-change workflow
- installed-operation request, blueprint-creation, adapter-recheck, and
  framework-update review flows
- operation catalog, single `Alatyr` entry, automatic routing, read-only
  health, risk-gated preview, help, and post-install/update assistant chat
  message templates
- documentation-sync rules
- final evidence requirements
- target adapter maturity and lifecycle notes
- required core profile, enabled optional modules, deferred modules, and
  blocked module gaps
- framework version, adapter schema version, template version, known gaps, and
  local deviations

## Does Not Own

- portable Alatyr Core framework rules
- target product/business facts
- target blueprint or equivalent source-of-truth content
- generated visual artifacts unless the target adapter says they are source

## Relationship To Framework Core

`.ai/framework` defines portable Alatyr Core rules. This adapter applies those
rules to `{PROJECT_NAME}` using target facts and validation.
