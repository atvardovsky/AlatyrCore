# Alatyr Core Installation Readiness Checklist

Use this checklist before installing Alatyr Core into a target repository.

This is an assistant reasoning aid. It is not a script and does not approve
changes.

## 1. Target Repository Profile

- Target repository path:
- New install or upgrade:
- Primary language/framework:
- Package/build files:
- Existing docs:
- Existing tests:
- Existing CI:
- Known validation commands:
- Existing test tools, fixtures, helpers, and isolation rules:
- Existing source-of-truth/context map:
- Existing blueprint or equivalent source-of-truth docs:
- Existing installed-operation, operation-help, operation-routing,
  blueprint-creation, adapter-recheck, or chat-message process:
- Existing risk or approval policy:
- Existing security, privacy, live-service, destructive-operation, dependency,
  and credential/log-redaction policies:
- Existing diagram sources, visual artifacts, render/manual-review process, and
  drift checks:
- Existing assistant instruction files:
- Existing skills, prompts, third-party assistant infrastructure, provenance
  notes, and wrappers:
- Supported assistants needed:

## 2. Existing AI Surface

Check whether the target already has:

- `AGENTS.md` or `agents.md`
- `AI_ASSISTANTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `.github/copilot-instructions.md`
- `.github/instructions`
- `.github/prompts`
- `.cursor/rules` or `.cursorrules`
- `.cursor/skills`
- `.claude/skills`
- `.devin/rules`
- `.windsurf/rules` or `.windsurfrules`
- `.ai`
- `.agents/skills`

Do not overwrite existing target instructions without explicit approval.

## 3. Core Versus Adapter

Classify every proposed file:

- Framework core:
- Project adapter:
- Project fact:
- Assistant bridge/wrapper:
- Skill/prompt/third-party assistant infrastructure:
- Generated/visual artifact:
- Existing target-owned file:
- Do not copy:

Framework core may be structurally copied or adapted from `framework/`.
Project adapter files must be rewritten from target facts.

Commands, scripts, generated-file tools, checker paths, hooks, test tools,
fixture helpers, folder names, CI jobs, security policies, live-service
allowlists, dependency scanners, diagram formats/tools, generated visual paths,
framework version strings, lifecycle notes, adapter owner names, skill sources,
assistant-native formats, tool permissions, and third-party assistant
infrastructure are target adapter details, not framework core.

## 4. Required Target Contours

The target installation must define or adapt:

- framework contour: what portable AI operating rules own
- project contour: what target product/code/business facts own
- repository adapter contour: what local assistant operating rules and
  validation own

Reject installation plans that keep framework rules, project facts, and
adapter details mixed without a clear split.

## 5. Target Project Adapter Inputs

Collect target-specific facts before writing project docs:

- product purpose
- architecture/module facts
- use cases or main workflows
- blueprint-driven change or equivalent product-change workflow
- business/domain rules
- data model
- runtime flows
- test strategy
- existing test levels, folders, fixtures, fakes, and isolation rules
- validation commands and manual checks
- context/source-of-truth owners and generated artifacts
- risk classes and approval triggers
- security, privacy, live-service, destructive-operation, dependency, and
  credential/log-redaction rules
- deployment/operations facts
- diagram needs, source format, visual format, render/manual-review policy, and
  drift checks
- skills, prompts, wrappers, third-party assistant infrastructure, provenance,
  output formats, permissions, and safety rules
- adapter maturity gaps and lifecycle expectations
- installed-operation request, blueprint-creation, adapter-recheck, and
  framework-update review expectations
- operation help, routing, and post-install/update assistant chat-message
  expectations

## 6. Assistant Compatibility

Choose only bridge files that the target needs:

- Generic assistant entry point
- Codex / AGENTS-aware tools
- Claude
- Gemini
- GitHub Copilot
- Cursor
- Devin/Cascade
- Windsurf legacy

Bridge files must stay short and point to canonical target files.
Assistant-specific skill wrappers must also point to canonical target rules
instead of duplicating full policy.

## 7. Approval And Risk

Approval is required before:

- overwriting existing AI instructions
- changing target project architecture
- weakening target gates
- changing accepted business behavior
- adding production dependencies
- importing third-party assistant infrastructure into canonical target files
- broadening assistant tool permissions, live-service access, destructive
  capabilities, or credential handling
- enabling live, destructive, spend-affecting, or data-loss side effects

## 8. Validation Plan

List commands or manual checks:

- target package/build validation:
- target tests:
- target test structure advice:
- target test isolation rules:
- static analysis:
- docs/diagram checks:
- installed-operation or adapter-recheck review:
- operation-help or routing review:
- skill/provenance/safety review:
- AI consistency checks, if installed:
- source commands intentionally not copied:
- source test tools/fixtures/CI jobs intentionally not copied:
- source security policies, diagram tooling, lifecycle notes, and adapter owner
  facts intentionally not copied:
- skipped gates and reason:

## 9. Final Evidence

Final evidence must say:

- framework core installed/adapted
- target adapter rewritten
- contours created or updated
- bridge files added or checked
- installed-operation, operation-help, operation-routing, blueprint-creation,
  adapter-recheck, or post-install/update chat-message templates added or
  skipped
- skills, prompts, wrappers, or third-party assistant infrastructure adapted or
  skipped
- existing target instructions preserved or approved for overwrite
- commands or manual checks run
- skipped checks and residual risk
