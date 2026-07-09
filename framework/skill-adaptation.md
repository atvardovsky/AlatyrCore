# AI Framework Skill Adaptation

This file defines how Alatyr Core treats assistant skills, prompts, and
third-party assistant infrastructure.

Skill adaptation is portable framework guidance. Concrete skill files,
assistant-native formats, tools, commands, permissions, and validation belong
to the project adapter.

## Purpose

Skills can make recurring assistant work more reliable, but they can also
duplicate policy, bypass gates, broaden tool access, or import assumptions from
another repository.

Alatyr Core treats a skill as adapter-owned unless it is purely portable
framework text. Imported skills must be reviewed and normalized before becoming
canonical target instructions.

## Skill Sources

For any new or changed skill, record:

- source or provenance
- intended task and non-goals
- supported assistant surfaces
- files, tools, commands, services, or permissions it expects
- output format and final evidence expectations
- security, privacy, live-service, destructive-operation, and dependency
  surfaces
- target adapter rules it must follow

If provenance or expected permissions are unclear, treat that as unresolved
context.

## Adaptation Process

Before integrating a skill into canonical target files:

1. Inspect the target adapter and framework rules that govern the task.
2. Classify the skill as portable framework guidance, project fact, repository
   adapter workflow, bridge wrapper, or external assistant infrastructure.
3. Compare the skill against target context, approval, validation, safety, and
   documentation-sync rules.
4. Remove or rewrite assumptions copied from another project.
5. Normalize file paths, source-of-truth references, validation, and final
   evidence to target adapter facts.
6. Restrict live, destructive, spend-affecting, credential, dependency, or
   permission behavior unless the target adapter explicitly allows it and
   approval is present.
7. Keep assistant-specific wrappers short and point them to canonical target
   files.
8. Add or update target validation and manual review expectations when the
   skill changes recurring work.
9. Record approvals, skipped checks, and residual risk.

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

## Wrapper Rules

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

Skill adaptation evidence should include:

```text
Skill source: <origin or unknown>
Purpose: <task the skill supports>
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
- copy another project's commands, business facts, security rules, diagrams, or
  validation as target facts
- grant broader tool, live-service, destructive, dependency, credential, or
  permission access without explicit approval
- weaken existing gates, validation, approval triggers, or evidence
  requirements
- claim compatibility with an assistant surface without target evidence
