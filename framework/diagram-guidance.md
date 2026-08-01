---
alatyr_doc:
  id: framework.diagram-guidance
  type: framework-rule-owner
  owns_rules:
    - ALATYR-DIAGRAM-001
  depends_on:
    - ALATYR-SOURCE-001
    - ALATYR-INTEGRITY-001
    - ALATYR-OPERATION-001
    - ALATYR-BRIDGE-001
    - ALATYR-SAFETY-001
  applies_to:
    - docs-local
    - code-local
    - business-change
    - architecture-change
    - data-change
    - security-sensitive
---
# AI Framework Diagram Guidance

This file defines portable diagram reasoning for projects that use diagrams as
AI-readable and human-readable architecture artifacts.

The framework does not choose a universal diagram tool. The project adapter
must define source format, visual format, render commands, ownership, and drift
checks.

It also defines how an assistant can present a diagram during a discussion.
The target adapter records the presentation modes each supported assistant can
actually use. Native rendering, repository-hosted visual artifacts, and local
preview links are target or client capabilities, not portable framework
guarantees.

## When Diagrams Help

Use diagrams when a change affects:

- system context, actors, or external boundaries
- containers, modules, layers, or dependency direction
- object, DTO, message, or port relationships
- data model, persistence, keys, indexes, or ownership
- runtime sequence, async flow, retries, failures, or audit path
- state machines or lifecycle transitions
- deployment, operations, scaling, observability, or rate limits
- verification architecture, gates, approvals, or assistant workflow

Do not add diagrams for trivial facts that are clearer as text.

## Source And Visual Split

A healthy adapter defines:

- editable source diagrams for assistants and code review
- visual artifacts for humans
- generation or manual-render policy
- drift check or explicit manual review
- ownership split between project diagrams and assistant-process diagrams

Generated visual files should not be edited as the only source of truth unless
the adapter explicitly defines them as source.

## Discussion Diagram Contract

When a programmer asks to see, sketch, compare, or revise a diagram during a
discussion, the assistant should select the `diagram-discussion` operation when
the target diagrams module is available.

A discussion diagram must report:

- stable diagram ID, draft revision, and prior revision or parent when revised
- purpose, scope, and diagram type
- `draft`, `accepted-source`, or `derived-view` status
- fact owners and repository revision used
- assumptions, unresolved facts, and intentionally omitted detail
- editable source format and source path when persisted
- presentation mode used and the fallback that remains available
- rendered artifact path or attachment when one was created
- validation, manual review, and stale-view risk

Discussion diagrams are `draft` by default. A rendered or inline view does not
become an accepted architecture, data, business, or runtime fact merely because
it appeared in chat. Promotion into project source of truth requires the normal
owner, approval, allowed-action, logical-integrity, and validation rules.

Use the smallest supported presentation mode in this order:

1. Native inline rendering when the current assistant surface is recorded as
   supporting the selected source syntax.
2. A rendered visual artifact or attachment produced by target-owned tooling
   when the operation permits file generation and the artifact can be linked or
   attached in the current client.
3. A readable text diagram plus the editable source block or source path.

The third mode is the portable fallback. Do not claim that a client rendered a
diagram when only source text was returned. If no mode can preserve the needed
meaning, explain the limitation and provide a focused textual model instead.

For a read-only discussion, keep the diagram in the response and do not create
repository files. Under `docs-only`, persist only diagram source and allowed
derived visual artifacts. Code, runtime configuration, accepted project facts,
or assistant infrastructure require a separately permitted operation.

When a discussion revises a diagram, retain the diagram ID, increment the
draft revision, name the superseded or parent revision, and identify whether
the new view replaces the prior draft, compares alternatives, or proposes a
project fact change. An `accepted-source` or `derived-view` must bind to its
repository revision and source revision or content hash. If that evidence is
unavailable, keep the result `draft` and report the gap.

## Security, Privacy, And External Rendering

Before presenting or persisting a diagram:

- classify its data as public, internal, confidential, restricted, or the
  target-equivalent class
- redact secrets, credentials, personal data, private endpoints, sensitive
  identifiers, and target-prohibited operational details
- treat external renderers, hosted preview services, network tools, and remote
  attachments as live external actions governed by target security, source
  access, privacy, and approval policy
- do not send diagram source or project facts to an external renderer without
  recorded permission, sufficient operation allowed actions, and approval when
  required
- make repository artifacts inherit target storage, sharing, retention, and
  deletion policy

Keep review separate from execution. `read-only` and `docs-only` diagram
discussion never invokes a network renderer; `docs-only` may use target-owned
local rendering. A requested external action must hand off to an operation
that permits it and pass policy and approval gates. When classification or
redaction is unresolved, use a bounded local text fallback or stop.

## Target Presentation Policy

An enabled diagrams module should record:

- canonical diagram source formats and owning paths
- supported discussion source syntaxes
- per-assistant native inline rendering capability
- visual render command or manual-render process
- generated artifact paths and whether assistants can link or attach them
- required text fallback
- validation or manual readability review
- source revision, content hash, or other stale-view evidence
- data classification, redaction, external-renderer, artifact storage,
  retention, and sharing policy

Unknown client rendering support must be recorded as unknown and routed to the
portable text fallback. Installation and update work must not infer support
from another assistant, repository, or client version.

## Readability Rules

Diagrams should:

- have a clear scope and title
- avoid mixing unrelated architecture levels
- use stable names from the project glossary or data dictionary
- show direction of dependencies, data flow, or state transition where relevant
- include keys, indexes, states, retries, or external boundaries when they are
  part of the contract
- remain readable in the target visual tool
- prefer multiple focused diagrams over one dense diagram

## Sync Rules

When diagram-relevant facts change:

- update the owning project or assistant-process diagram source
- update or regenerate the visual artifact according to the adapter policy
- update public diagram indexes when the diagram set changes
- explain why no diagram update was needed when facts are unchanged

## Rejection Criteria

Reject diagram work that:

- contradicts code, docs, tests, gates, or source-of-truth architecture
- uses a visual artifact as source while ignoring the adapter-defined source
- hides a behavior or architecture change inside diagram-only edits
- invents tables, flows, states, APIs, or actors not present in accepted docs
- produces unreadable, overlapping, or ambiguous diagrams
- copies source project diagram tools into another project as framework core
- claims native or artifact rendering without bridge capability evidence
- exposes secrets, personal data, private endpoints, or restricted detail
- invokes an external renderer without target policy and required approval
- promotes an accepted or derived view without repository and source revision
  evidence
- presents a discussion draft as accepted project truth
- writes files during a read-only diagram discussion
- returns source syntax alone while claiming the user received a rendered view
