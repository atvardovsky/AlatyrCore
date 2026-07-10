# AI Framework Operation Help

This file defines the portable help and routing pattern for installed Alatyr
Core adapters.

Operation help is not a CLI command, daemon, runtime service, or universal
agent. It is an assistant response pattern backed by target adapter files.
When a programmer asks for "Alatyr help", asks for available Alatyr actions, or
gives a request the assistant cannot classify safely, the assistant must show
the available operation choices instead of guessing.

Concrete operation names, local validation, supported assistants, and final
evidence formats belong to the target repository adapter.

## Goals

Operation help exists to:

- make installed Alatyr usage discoverable after installation or update
- route unclear requests to the right target flow
- prevent assistants from treating vague requests as permission to edit files
- distinguish assistant requests from nonexistent universal commands
- expose missing target adapter facts before work starts

## Help Trigger

Show operation help when:

- the user asks for Alatyr help, commands, actions, or what Alatyr can do
- the requested operation type is missing or ambiguous
- multiple flows could apply and choosing wrong may change project facts
- required target context is missing before the assistant can classify risk
- the assistant cannot tell whether the request is framework, project,
  repository adapter, bridge, generated artifact, or skill/prompt work

Showing help does not require approval because it does not change repository
facts.

## Operation Menu Shape

A target adapter help file should list each supported operation with:

- operation name
- short description
- when to use it
- matching target flow
- minimum input needed from the programmer
- allowed-action modes and context profile when useful
- approval triggers or safety notes
- expected final evidence

Typical operation categories include:

- help or operation routing
- project blueprint creation or repair
- adapter recheck after installation
- adapter recheck after framework update
- framework upgrade impact review
- target source-of-truth drift review
- blueprint-driven product change
- logical integrity review
- AI infrastructure inventory
- skill, prompt, wrapper, or third-party assistant infrastructure adaptation
- documentation, diagram, gate, or bridge synchronization
- adapter maturity review

The target adapter may narrow, rename, or add operations when it records the
local meaning and matching flow.

When a target uses a module profile, operation help should list only operations
whose required module is enabled or required. Deferred, disabled,
not-applicable, or blocked modules should appear as gaps or unavailable
options, not as ready actions.

Target adapters may also define operation type aliases. These aliases can map
natural-language requests such as "Alatyr help", "update Alatyr", "check
integrity", or target-language equivalents to canonical operation names.
Aliases must be documented as assistant request syntax, not portable
executable commands.

For AI infrastructure, aliases may include `alatyr-ai-inventory`, which routes
to an inventory flow, or `alatyr-adaptation <source>` and
`alatyr-add-ai <source>`, which route to adaptation. The `<source>` may be a
local path, Git URL, HTTPS URL, assistant-native skill or prompt reference,
pasted content, package/plugin reference, or other adapter-defined source.
Target help should state near these aliases that they are chat/request
shortcuts, not shell commands.

## Routing Rules

When routing a request:

1. Read the target assistant entry point, adapter manifest, area map, and
   context profiles.
2. Read the target operation help file when it exists.
3. Classify the request by contour, task profile, and changed fact.
4. Normalize documented operation aliases before selecting a flow.
5. Choose the matching flow only when the operation is clear enough to proceed
   safely.
6. If the operation is unclear, show the operation menu with short
   descriptions and ask for the smallest missing decision.
7. If the user asks for commands, explain that Alatyr is used through assistant
   requests over Markdown adapter files unless the target adapter defines local
   commands.
8. If the request asks what already exists, route to AI infrastructure
   inventory and do not import anything during inventory-only work.
9. If the request supplies an external source, check target provenance,
   network, dependency, prompt-injection, and approval rules before fetching or
   importing it.
10. Do not edit repository files while only presenting help or resolving
   operation ambiguity.

## Evidence Format

Operation routing should be reportable as:

```text
Requested action: <user request>
Matched operation: <operation or unresolved>
Matching flow: <target flow or missing adapter fact>
Reason: <why this operation was selected>
Missing input: <facts needed before work can proceed>
Next safe action: <help shown, question asked, or flow started>
```

The target adapter may require a stricter format.

## Rejection Criteria

Reject or revise operation routing that:

- invents a universal `alatyr` command
- starts edits from an ambiguous request without selecting a flow
- hides missing target context behind a confident operation choice
- treats bridge files or generated files as the source of operation truth
- omits approval needs for protected operations
- lists operations that the target adapter cannot support or explain
