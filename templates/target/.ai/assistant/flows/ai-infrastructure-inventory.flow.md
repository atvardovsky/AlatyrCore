# AI Infrastructure Inventory Flow

Use this flow in `{PROJECT_NAME}` when the programmer asks what AI assistant
infrastructure already exists, asks what can be added, or uses an alias such as
`alatyr-ai-inventory`.

Replace placeholders with target facts before accepting installation.

## Base Target Sources

- Compact bootstrap, with `AGENTS.md` treated as preloaded
- Framework routing guidance: `.ai/framework/ai-infrastructure-routing.md`
- AI infrastructure router: `.ai/assistant/ai-infrastructure-router.json`
- Target assistant contour: `.ai/assistant/contour.md`
- Target gates: `.ai/assistant/gates/checklist.md`
- Inventory report template:
  `.ai/assistant/templates/ai-infrastructure-inventory.md`
- Target validation: `{TARGET_VALIDATION}`

## Conditional Sources

- Operation help: `.ai/framework/operation-help.md` only for ambiguous routing
- Framework adaptation guidance: `.ai/framework/skill-adaptation.md` only when
  handing off to adaptation
- AI infrastructure source-access policy:
  `.ai/assistant/policies/ai-infrastructure-source-access.md` only when an
  external source is inspected
- Prompt-injection policy: `.ai/assistant/policies/prompt-injection.md` only
  when an external source is inspected
- Target AI infrastructure source/access policy:
  `{TARGET_AI_INFRASTRUCTURE_SOURCE_ACCESS_POLICY}` only when source access is
  in scope

## Items To Inspect

- assistant entry points and bridge files
- flows, gates, checklists, templates, prompts, and skills under `.ai`
- assistant-native rules, prompts, commands, memories, and skill folders
- MCP, tool, connector, model, or permission configuration
- checker manifests, consistency scripts, hooks, generated assistant artifacts,
  and adapter reports
- provenance, source/access, approval, safety, and lifecycle notes
- source hash, commit, version, license, and prompt-injection notes when known

## Steps

1. Load the compact adapter bootstrap, then
   `.ai/assistant/ai-infrastructure-router.json` and declared item paths.
2. Inspect router-declared locations and known assistant surfaces for
   `{SUPPORTED_ASSISTANTS}` before broader directory search.
3. Read source-access or prompt-injection policy only when inventory touches an
   external, remote, package/plugin, pasted, or unknown source.
4. Classify each found item as framework, project, repository adapter, bridge,
   generated artifact, external assistant infrastructure, or unknown.
5. Record item ID, router status, type, path or reference, owner,
   source/provenance, license or
   unknown-license status, source hash or commit when known, permission
   surface, supported assistants, and validation or manual review status.
6. Identify overlaps, duplicate policy, stale bridge files, unsafe permissions,
   missing provenance, and missing adapter facts.
7. Report which items are routable, blocked, stale, need adaptation, need approval, need
   removal, or should stay unresolved.
8. Record reusable inventory evidence with
   `.ai/assistant/templates/ai-infrastructure-inventory.md` when the target
   adapter wants durable inventory records.
9. If the programmer asks to add an item, route to
   `.ai/assistant/flows/skill-adaptation.flow.md` with the inventory result as
   context.
10. Do not import or normalize external infrastructure during inventory-only
   work.

## Final Evidence

Report:

- surfaces inspected
- router status, selected route, and item IDs
- items found
- classification and owner for each item
- provenance and source/access status
- source hash or commit and license status when known
- prompt-injection risk notes
- permission, live-service, destructive-operation, dependency, or credential
  surface
- conflicts, duplicates, or stale items
- recommended add/adapt/remove/skip actions
- validation or manual checks run
- approvals needed
- residual risk

## Rejection Criteria

Reject or revise inventory work that:

- treats bridge files or generated artifacts as canonical without checking
  their owner
- imports an external item during inventory-only work
- claims compatibility without inspecting the target adapter
- hides missing provenance, permissions, approval, or validation
- copies source-project facts into target assistant infrastructure
