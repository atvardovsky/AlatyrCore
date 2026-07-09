# Alatyr Core Framework Contour

This contour defines the reusable AI assistant framework core.

The framework contour is not a target project. It is also not a specific
assistant vendor configuration. It defines the rules that make AI work normally
on a project when a project adapter supplies project facts and local
validation.

## Owns

Framework core owns:

- context-loading contract
- project/framework/adapter ownership separation
- context discovery, missing-context, and source-of-truth decision pattern
- change-risk classification and protected approval trigger pattern
- security, safety, live-service, and destructive-operation reasoning pattern
- diagram reasoning and source/visual synchronization pattern
- architecture discussion and approval pattern
- semantic change decision pattern
- logical integrity review pattern
- blueprint-driven product-change workflow pattern
- documentation-sync pattern
- stack-aware testing analysis pattern
- gate categories and final evidence pattern
- skill, prompt, wrapper, and third-party assistant infrastructure adaptation
  pattern
- supported-assistant bridge pattern
- installed-adapter operation, blueprint creation, and recheck pattern
- operation help and ambiguous-request routing pattern
- project-adapter contract
- framework installation and portability rules
- improvement-advice trigger pattern
- adapter maturity and framework lifecycle/upgrade pattern

## Does Not Own

Framework core must not own:

- project business behavior
- project architecture facts
- project runtime flows, data structures, database relations, or diagrams
- project-specific commands, scripts, hooks, CI jobs, generated-file tools, or
  checker paths
- project-specific skill triggers or rejection criteria
- project-specific skill sources, assistant-native formats, tool permissions,
  or third-party assistant infrastructure
- concrete test tools, commands, fixtures, CI jobs, or folder names from one
  project
- credentials, environment assumptions, or production deployment choices
- project-specific security policy, live-service allowlists, dependency
  scanners, incident procedures, or destructive-command policies
- project-specific diagram source formats, visual formats, render commands, or
  generated-file drift tooling
- project-specific framework version strings, release process, or adapter
  owner names
- project-specific post-install request cadence, report owners, or adapter
  maintenance schedule
- project-specific operation names, help wording, local command aliases, or
  chat-completion message text

## Adjacent Contours In A Target Repository

- `.ai/project`: target product/project facts.
- `.ai/assistant`: target repository AI adapter that applies Alatyr Core to
  the target project.
- `.agents`, `.claude`, `.cursor`, `.github`, and bridge files: adapter or
  assistant-specific wrappers around framework/project instructions.

## Repository Adapter

A repository adapter supplies local project context, supported-assistant
bridges, local validation, and final-evidence expectations. It can use the
framework, but it is not framework core.

## Drift Rule

When a framework rule changes, update:

- `.ai/framework/*`
- repository adapter references under `.ai/assistant`
- supported assistant wrappers when their instructions change
- public docs and indexes that explain the framework
- deterministic consistency assertions when the rule is machine-checkable

When a target project fact changes, update the target `.ai/project` and
repository adapter, not Alatyr Core framework core.
