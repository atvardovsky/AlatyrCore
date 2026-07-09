# AI Framework Skill And Assistant Infrastructure Adaptation

This file defines how Alatyr Core treats assistant skills, prompts, and
third-party assistant infrastructure.

Skill and AI infrastructure adaptation is portable framework guidance.
Concrete skill files, prompts, assistant-native formats, tools, commands,
permissions, and validation belong to the project adapter.

## Purpose

AI infrastructure can make recurring assistant work more reliable, but it can
also duplicate policy, bypass gates, broaden tool access, or import assumptions
from another repository.

Alatyr Core treats skills, prompts, wrappers, assistant-native rules, command
prompts, memories, MCP/tool configuration, checker manifests, and similar
assistant infrastructure as adapter-owned unless the item is purely portable
framework text. Imported items must be inventoried, reviewed, and normalized
before becoming canonical target instructions.

## AI Infrastructure Items

AI infrastructure items include:

- skills and assistant-native skill folders
- prompts, prompt templates, command prompts, and chat templates
- bridge files, wrappers, rules, memories, and assistant-specific instruction
  files
- flows, gates, checklists, operation templates, and checker manifests
- MCP, tool, connector, model, permission, or automation configuration
- generated assistant artifacts, inventory reports, and adapter audit reports

The target adapter may define additional item types.

## Source Inventory

Before adding or importing AI infrastructure, inspect what already exists in
the target repository. Record:

- item type
- path or external reference
- owner: framework, project, repository adapter, bridge, generated artifact,
  external assistant infrastructure, or unknown
- source/provenance and source type
- supported assistant surfaces
- files, tools, commands, services, models, or permissions it expects
- overlap with existing flows, gates, prompts, skills, bridge files, or checker
  rules
- safety, dependency, live-service, destructive-operation, credential, privacy,
  and validation surfaces
- recommended action: keep, adapt, add, replace, remove, or leave unresolved

Inventory-only work must not import or normalize external infrastructure.

## Source Records

For any new or changed AI infrastructure item, record:

- source or provenance
- source type: local path, Git URL, HTTPS URL, assistant-native skill
  reference, pasted content, package/plugin reference, or unknown
- item type: skill, prompt, wrapper, bridge, rule, memory, MCP/tool config,
  checker, flow, gate, template, or other target-defined item
- intended task and non-goals
- supported assistant surfaces
- files, tools, commands, services, or permissions it expects
- output format and final evidence expectations
- security, privacy, live-service, destructive-operation, and dependency
  surfaces
- target adapter rules it must follow

If provenance or expected permissions are unclear, treat that as unresolved
context.

## Adaptation Request Alias

A target adapter may support a shorthand request such as:

```text
alatyr-adaptation <source>
alatyr-add-ai <source>
alatyr-ai-inventory
```

These are assistant request aliases, not portable executable commands.
`alatyr-ai-inventory` asks the assistant to inspect existing AI
infrastructure. `alatyr-adaptation <source>` and `alatyr-add-ai <source>` ask
the assistant to route the source through adaptation. The source may identify a
local file or directory, a Git URL, an HTTPS URL, an assistant-native skill or
prompt reference, pasted content, a package/plugin reference, or another
adapter-defined source form.

Before reading remote content or importing anything into canonical target
files, the assistant must check the target adapter's network, dependency,
provenance, and approval rules. If those rules are missing, the assistant may
only describe the required review or ask for approval; it must not claim the
skill is trusted, compatible, or installed.

## Adaptation Process

Before integrating an item into canonical target files:

1. Inspect the target adapter and framework rules that govern the task.
2. Inventory existing target AI infrastructure or use a current inventory
   result.
3. Parse the requested source, source type, item type, intended task, target
   assistant surfaces, and whether the request is review-only or canonical
   integration.
4. Classify the item as portable framework guidance, project fact, repository
   adapter workflow, bridge wrapper, generated artifact, or external assistant
   infrastructure.
5. Compare the item against target context, approval, validation, safety, and
   documentation-sync rules.
6. Remove or rewrite assumptions copied from another project.
7. Normalize file paths, source-of-truth references, validation, and final
   evidence to target adapter facts.
8. Restrict live, destructive, spend-affecting, credential, dependency, or
   permission behavior unless the target adapter explicitly allows it and
   approval is present.
9. Keep assistant-specific wrappers short and point them to canonical target
   files.
10. Add or update target validation and manual review expectations when the
    item changes recurring work.
11. Record approvals, skipped checks, and residual risk.

## Approval Triggers

Explicit programmer approval is required before:

- importing third-party assistant infrastructure into canonical target files
- broadening tool access, permissions, live-service access, or destructive
  capabilities
- weakening gates, approval rules, validation, documentation-sync, redaction,
  or final evidence
- adding production dependencies or external services
- changing accepted architecture, business behavior, security behavior, or
  privacy handling

Planning, review, and isolated scratch evaluation may proceed when they do not
modify canonical target files or protected behavior.

## Wrapper And Bridge Rules

Assistant-native wrappers may exist for tools such as Codex, Claude, Gemini,
GitHub Copilot, Cursor, Devin, Cascade, or Windsurf.

Wrappers should:

- remain short
- name the canonical target files to read
- avoid duplicating full framework, project, or adapter policy
- avoid becoming a divergent source of truth
- state assistant-specific constraints only when the target adapter owns them

The target adapter decides which wrappers are supported.

## Evidence Format

AI infrastructure adaptation evidence should include:

```text
Source: <origin or unknown>
Source type: <local path/Git URL/HTTPS URL/native reference/pasted/unknown>
Item type: <skill/prompt/wrapper/bridge/rule/MCP/tool/checker/flow/gate/template/other>
Purpose: <task the item supports>
Inventory result: <existing item, conflict, duplicate, or missing owner>
Classification: <framework/project/adapter/bridge/external>
Conflicts found: <policy or target-fact conflicts>
Normalization: <target files or rules changed>
Safety review: <live/destructive/secrets/dependency/permission surface>
Validation: <target checks or manual review>
Approvals: <used or not required>
Residual risk: <unresolved provenance, compatibility, or validation>
```

## Rejection Criteria

Reject or revise skill changes that:

- import third-party instructions without provenance or approval when required
- duplicate full framework or project policy inside wrappers
- add AI infrastructure without first checking what already exists
- copy another project's commands, business facts, security rules, diagrams, or
  validation as target facts
- grant broader tool, live-service, destructive, dependency, credential, or
  permission access without explicit approval
- weaken existing gates, validation, approval triggers, or evidence
  requirements
- claim compatibility with an assistant surface without target evidence
