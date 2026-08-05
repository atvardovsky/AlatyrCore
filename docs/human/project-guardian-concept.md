# The Project Guardian Concept

AlatyrCore separates durable project intent from the AI assistants that
interact with it.

> This document is a human-oriented explanation. Canonical framework rules
> remain owned by the referenced framework documents and
> [rule registry](../../framework/rule-registry.md).

## Conceptual Model

```text
Architectural intent
        |
        v
Project-owned sources of truth
        |
        v
Alatyr project adapter
        |
        v
Interchangeable AI assistants
        |
        v
Developers and engineering workflows
```

This is an implemented conceptual contract, not a claim that every target
repository already has complete or correct project knowledge. Installation
must adapt the model from target evidence.

## Architectural Intent

Architectural intent includes accepted decisions, quality drivers, ownership,
constraints, preferred or restricted patterns, and explicit exceptions. Code
can provide evidence about the current implementation, but code alone does not
prove that an implementation is intended or accepted.

The canonical architecture state and discussion model belongs to
[architecture knowledge](../../framework/architecture-knowledge.md).

## Project-Owned Sources Of Truth

Each fact type may have a different owner. An API specification, data schema,
decision record, runtime configuration, security policy, validation command,
and public explanation do not need one universal precedence order.

The target project's registry should identify the canonical owner, derived
surfaces, synchronization direction, validation, conflict resolver, and known
gaps. See the
[source-of-truth registry](../../framework/source-of-truth-registry.md).

## The Alatyr Project Adapter

The adapter binds portable AlatyrCore rules to one repository. It records the
target's contours, owners, sources, context routes, operations, validation,
assistant bridges, enabled modules, and unresolved gaps.

The adapter does not replace the project sources it points to. It is a routing
and operating layer whose requirements are owned by the
[project adapter contract](../../framework/project-adapter-contract.md).

## Interchangeable AI Assistants

Compatible assistants can use the same project-owned entry points, but their
loading behavior, permission model, skill support, and presentation capability
may differ. Thin bridges and target capability records make those differences
explicit without moving project truth into a vendor-specific file.

See the
[bridge capability matrix](../../framework/bridge-capability-matrix.md) for
the canonical compatibility model. Source checks can verify bridge structure;
they do not prove that every external client behaves identically.

## Developers And Engineering Workflows

Developers can use natural-language questions and tasks. A clear request can
route directly to a project operation, while an ambiguous request receives a
small set of relevant choices. This is a conversational use of repository
instructions, not a universal Alatyr service or shell command.

The canonical interaction model belongs to
[operation help](../../framework/operation-help.md). Task-specific context is
owned by [context profiles](../../framework/context-profiles.md) and the
[context router](../../framework/context-router.md).

## Authority Is Preserved

AlatyrCore is intended to continue the recorded intent of project decision
owners. It does not replace architects, maintainers, security owners, product
owners, or programmers who hold approval authority.

An assistant may explain an accepted decision, identify a contradiction, or
prepare a proposal. It must not silently convert an observed implementation or
new recommendation into accepted architecture. Protected decisions still
follow project ownership, approval, and validation.

## Intent Can Change

Project memory should preserve continuity, not freeze the past. Decisions can
be superseded, patterns can become deprecated, and constraints can change.
When they do, the project should update the canonical owner and synchronize
affected implementation, tests, docs, diagrams, gates, and adapter records.

Framework and adapter versioning expectations are defined in
[lifecycle guidance](../../framework/lifecycle.md). Semantic change evidence
remains subject to the limits in
[framework guarantees and limits](../../framework/guarantees.md).

