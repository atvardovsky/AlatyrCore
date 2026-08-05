# AlatyrCore Quick Demonstration

This repository does not currently include a complete runnable demonstration
target. The walkthrough below is documentation-only and uses files that exist
in the AlatyrCore source repository. It does not pretend that placeholder
templates contain real project facts.

> This document is a human-oriented explanation. Canonical framework rules
> remain owned by the referenced framework documents and
> [rule registry](../../framework/rule-registry.md).

## What This Demonstrates

The walkthrough shows how an installed target adapter is intended to route
project questions. It demonstrates source contracts and request shapes, not a
measured onboarding result or a live Alatyr service.

## 1. Inspect The Actual Source Templates

These paths exist in this repository:

- [Target architecture index template](../../templates/target/.ai/project/architecture/README.md)
- [Target architecture catalog template](../../templates/target/.ai/project/architecture/catalog.json)
- [Target source-of-truth registry template](../../templates/target/.ai/project/source-of-truth-registry.md)
- [Architecture assistance flow](../../templates/target/.ai/assistant/flows/architecture-assistance.flow.md)
- [Installed operation request template](../../templates/target/.ai/assistant/templates/operation-request.md)

The placeholders show which project facts an installing assistant must resolve.
They are not accepted facts about AlatyrCore or another target repository.

## 2. See The Available Source Tool Entry Point

From the AlatyrCore source checkout, this existing command lists maintainer
tools:

```sh
python3 tools/alatyr.py --help
```

This command does not launch a conversational runtime. It exposes optional
source-repository tooling such as structural checks and scaffolding support.

The architecture source contract can be checked with:

```sh
python3 tools/check_architecture_knowledge.py
```

That check validates framework and template structure. It cannot prove the
architecture of a target project.

## 3. Ask A Project-Level Question

After AlatyrCore has been adapted into a real target repository, ask:

```text
Explain this project to a new developer.
```

The assistant should route to the target's project overview, contours,
architecture index, and selected canonical sources. It should cite what it
used and mark missing or conflicting facts instead of filling gaps from
assumption.

## 4. Explore Architecture

Ask the following questions one at a time:

```text
What are the main architectural areas?
```

```text
Where is the source of truth for <selected concept>?
```

```text
Is this implementation observed, proposed, or accepted?
```

Expected behavior:

- start from the compact target architecture catalog
- load only selected area, pattern, decision, and evidence records
- keep observed implementation separate from accepted intent
- cite the target owner or report that it is missing

This behavior is defined by
[architecture knowledge](../../framework/architecture-knowledge.md) and the
[source-of-truth registry](../../framework/source-of-truth-registry.md).

## 5. Prepare A Change

Ask:

```text
Which constraints apply to this proposed change?
```

```text
What validation would be required?
```

The assistant should identify the proposed changed facts, canonical owners,
relevant invariants, approval needs, validation, companion documentation, and
residual risk. It should not edit files if the request is read-only or the
required scope is ambiguous.

Operation routing is defined by
[operation help](../../framework/operation-help.md). Process-claim limits are
defined by
[framework guarantees and limits](../../framework/guarantees.md).

## 6. Understand The Evidence Boundary

A useful target answer should distinguish:

- what the repository currently demonstrates
- what a decision owner accepted
- what the assistant proposes
- what is contradicted or unknown
- which validation ran, was skipped, or remains unavailable

Without a completed target adapter, this repository can demonstrate only the
framework contracts and placeholder shapes. A future runnable demonstration
target would be needed for an end-to-end public product demo.

