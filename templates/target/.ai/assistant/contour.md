# Repository AI Adapter Contour

This contour describes how assistants operate in `{PROJECT_NAME}`.

Replace placeholders with target facts before accepting installation.

## Owns

- assistant workflows under `.ai/assistant/flows`
- gates under `.ai/assistant/gates`
- prompts, skills, bridge files, and assistant-specific wrappers
- AI infrastructure inventory, source access, provenance, adaptation,
  output-format, safety, and wrapper rules
- target validation commands or manual checks
- blueprint-driven change or equivalent target product-change workflow
- installed-operation request, blueprint-creation, adapter-recheck, and
  framework-update review flows
- operation help, operation-routing, and post-install/update assistant chat
  message templates
- documentation-sync rules
- final evidence requirements
- target adapter maturity and lifecycle notes

## Does Not Own

- portable Alatyr Core framework rules
- target product/business facts
- target blueprint or equivalent source-of-truth content
- generated visual artifacts unless the target adapter says they are source

## Relationship To Framework Core

`.ai/framework` defines portable Alatyr Core rules. This adapter applies those
rules to `{PROJECT_NAME}` using target facts and validation.
