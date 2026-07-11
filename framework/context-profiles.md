---
alatyr_doc:
  id: framework.context-profiles
  type: framework-rule-owner
  owns_rules:
    - ALATYR-CONTEXT-001
  depends_on:
    - ALATYR-ADAPTER-001
  applies_to:
    - all
---
# Context Profiles

Context profiles limit the required reading set for an Alatyr task.

They preserve the minimum sufficient context rule: start from bootstrap files,
choose the closest task profile, read that profile's required sources, and
expand only when boundaries or conflicts require it.

When an installed adapter includes a machine-readable context router, it must
use the same canonical profile names and stay aligned with this Markdown
contract. The router is an optimization for cheaper startup, not a replacement
for the human-readable profile rationale or logical integrity review.

## Canonical Profiles

Use these profile names unless a target adapter deliberately renames them:

- `docs-local`
- `code-local`
- `business-change`
- `architecture-change`
- `data-change`
- `security-sensitive`
- `ai-infrastructure`
- `framework-upgrade`

Target adapters may add local profiles, but they should not remove the
canonical names unless the target documents the replacement.

## Profile Contract

Each target profile should define:

- use when
- required context
- optional context triggers
- approval gates
- validation or manual review
- expected final evidence

The profile should list concrete target paths after installation. Placeholder
paths are acceptable only before the adapter is accepted.

## Bootstrap Context

Every installed adapter should keep a small bootstrap set:

- target root assistant entry point
- `.ai/alatyr.yaml`
- `.ai/README.md`
- `.ai/assistant/context-router.json` when present
- `.ai/assistant/context-profiles.md`
- `.ai/assistant/module-profile.md`
- project contour
- assistant contour
- task-owned source of truth when known

Framework documents, flows, gates, and policies should be loaded through the
selected task profile instead of being mandatory for every task.

## Expansion Rules

Expand context when:

- a semantic or logical fact changes
- source-of-truth evidence conflicts
- a change crosses architecture, business, data, security, lifecycle, or
  assistant-infrastructure boundaries
- approval scope is unclear
- validation evidence contradicts the proposed change
- a bridge, prompt, skill, checker, or gate may be affected

If the profile is ambiguous, use the smallest likely profile, report the
assumption, and ask only for the missing decision that blocks safe routing.
