# AI Framework Installed Operations

This file defines how to use an installed Alatyr Core adapter after the initial
installation.

Installed operations are requests to an assistant working inside a target
repository that already has Alatyr Core files and adapter facts. They include
creating or repairing project blueprints, rechecking adapter maturity after a
framework update, reviewing drift, inventorying or adapting AI infrastructure,
or running a guided product-change workflow.

Concrete project facts, validation commands, reports, prompts, and update
cadence belong to the target repository adapter.

## Operation Types

An installed adapter should support these operation categories:

- operation help or routing when the request is unclear
- project blueprint creation or repair
- adapter recheck after Alatyr Core installation or upgrade
- framework upgrade impact review
- target source-of-truth drift review
- blueprint-driven product change
- logical integrity review
- AI infrastructure inventory for existing skills, prompts, wrappers, bridge
  files, rules, MCP/tool configs, gates, checkers, and prompts
- skill, prompt, wrapper, or third-party assistant infrastructure adaptation
- documentation, diagram, gate, or bridge synchronization
- adapter maturity review

The target adapter may define narrower or stricter operations.

## Request Contract

A post-install request should state:

- target repository path
- operation type
- goal and non-goals
- known changed facts or framework update source
- AI infrastructure source when the operation is adaptation or add, including
  local path, Git URL, HTTPS URL, assistant-native reference, pasted content,
  package/plugin reference, or unknown source type
- target source-of-truth docs to inspect
- validation commands or manual checks known to the target
- approval constraints
- expected final evidence

If a request says "ask Alatyr" or similar, interpret that as "ask an assistant
to use the installed Alatyr Core adapter in this repository." Do not assume a
runtime service, CLI, agent daemon, or universal command exists.

If the requested operation is unclear, route the request through the target
operation help file and show the operation menu before changing files.

If the request uses an alias such as `alatyr-ai-inventory`, interpret it as an
AI infrastructure inventory request. If it uses `alatyr-adaptation <source>` or
`alatyr-add-ai <source>`, interpret it as the skill-adaptation operation with
`<source>` as untrusted input until the target adapter's provenance, network,
dependency, and approval rules have been checked.

## Required Flow

For installed operations:

1. Read the target assistant entry point and adapter context.
2. Identify whether the request is framework-core, target-project, repository
   adapter, bridge, generated-artifact, or skill/prompt work.
3. Use operation help and operation routing when the request is ambiguous.
4. Apply logical integrity review before claiming consistency.
5. Use blueprint-driven change when accepted project facts may change.
6. Use skill adaptation when prompts, skills, wrappers, or third-party
   assistant infrastructure change.
7. Use AI infrastructure inventory before adding, importing, replacing, or
   removing assistant infrastructure.
8. Use adapter maturity review when the request is broad, post-install, or
   post-upgrade.
9. Run target validation that exists, or record unresolved checks.
10. Report changed facts, files inspected, files changed, approvals, validation,
   skipped checks, and residual risk.

## Blueprint Creation

Blueprint creation is a target-project operation. The assistant may draft or
repair blueprint-equivalent docs only from target evidence:

- README and public docs
- architecture, design, use-case, business-rule, data, and runtime-flow docs
- code structure and package/build files
- tests, fixtures, and CI
- diagrams and generated artifacts
- security, live-service, destructive-operation, and dependency policy
- existing prompts, skills, gates, bridge files, and checker rules

Missing facts must stay marked as missing. The assistant must not invent
business rules, architecture, security policy, validation commands, diagrams,
or lifecycle notes.

## Adapter Recheck

After installation or framework upgrade, an assistant should recheck:

- mandatory framework files and target adapter references
- operation help, operation-routing flow, and post-install/update chat-message
  templates
- source-of-truth and blueprint ownership
- logical integrity and blueprint-driven change flows
- gates, prompts, skills, bridge files, checker rules, and final evidence
- AI infrastructure inventory, source access, provenance, and compatibility
  status
- security, live-service, destructive-operation, and dependency boundaries
- diagram and generated-artifact policy
- validation commands or manual checks
- adapter maturity gaps, local deviations, and lifecycle notes

If a framework update adds requirements, the assistant should identify whether
the target adapter needs migration, approval, new placeholders, or manual
follow-up.

## Rejection Criteria

Reject or revise installed-operation work that:

- treats Alatyr Core as a universal executable command or service
- guesses an operation instead of showing help when the request is ambiguous
- updates target blueprints from guesses instead of target evidence
- copies source-repository facts into target project docs
- overwrites existing target instructions without approval
- claims adapter recheck success without inspecting the installed target
  adapter
- claims validation without target commands or manual-review evidence
- hides missing project facts, approvals, or residual risk
