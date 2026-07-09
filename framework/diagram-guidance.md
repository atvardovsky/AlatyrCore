# AI Framework Diagram Guidance

This file defines portable diagram reasoning for projects that use diagrams as
AI-readable and human-readable architecture artifacts.

The framework does not choose a universal diagram tool. The project adapter
must define source format, visual format, render commands, ownership, and drift
checks.

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

