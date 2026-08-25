# Frequently Asked Questions

> This document is a human-oriented explanation. Canonical framework rules
> remain owned by the referenced framework documents and
> [rule registry](../../framework/rule-registry.md).

## Is AlatyrCore Another Coding Agent?

No. AlatyrCore is a repository-owned framework and project adapter. Compatible
AI coding agents use it as an interaction and execution surface. The canonical
separation is defined by the
[project adapter contract](../../framework/project-adapter-contract.md).

## Does It Replace Architects?

No. It preserves and routes recorded architectural intent, evidence, owners,
and decision states. Architects and other project decision owners retain
authority. An assistant must not convert observed implementation or a proposal
into accepted architecture without target decision evidence. See
[architecture knowledge](../../framework/architecture-knowledge.md).

## Does It Automatically Infer Architecture From Code?

No. Code can provide evidence for an `observed` architecture item. Accepted,
preferred, restricted, or deprecated states require project-owned decision
evidence. Contradictions and unknowns should remain explicit.

## Does Every Developer Need To Understand The Internal Framework?

No. Developers are intended to interact through normal questions and tasks.
Maintainers who install, update, or govern the adapter need a deeper
understanding of ownership, modules, approvals, and validation. The
conversational routing model is defined by
[operation help](../../framework/operation-help.md).

## Why Is Installation Performed By An AI Assistant?

A universal installer cannot know a target repository's business facts,
architecture owners, commands, tests, security policy, assistant bridges, or
approval boundaries. The assistant inspects the target, prepares a plan, and
adapts placeholders from repository evidence. Optional scaffolding can create
structure, but it does not complete installation. See
[INSTALL.md](../../INSTALL.md).

## Can It Be Used In Private Repositories?

The framework design does not require a public repository or an Alatyr-hosted
service. A private project can use it when the team permits the selected AI
assistant and tools to access the repository under its own security, privacy,
network, and credential policies. AlatyrCore does not override those policies.

## Does It Require A Specific AI Vendor?

No. The framework is vendor-neutral and target adapters can support multiple
assistant surfaces. Actual loading behavior and capabilities differ by client
and must be recorded rather than assumed. See the
[bridge capability matrix](../../framework/bridge-capability-matrix.md).

## Does It Guarantee That AI-Generated Changes Are Correct?

No. AlatyrCore defines process commitments and deterministic structural checks
where possible. It cannot guarantee correct missing facts, flawless assistant
reasoning, complete impact analysis, or successful target validation. See
[framework guarantees and limits](../../framework/guarantees.md).

## How Is Project Knowledge Kept Current?

The target adapter should identify owners, review cadence or triggers, source
of truth, validation, known gaps, and framework baseline. Reusable conclusions
remain historical until a target decision owner reviews their promotion.
Accepted facts are updated in canonical project sources; bounded derived route
shards help later assistants find and reverify those sources. This maintenance
is controlled and checked, not automatic semantic inference. See the
[project adapter contract](../../framework/project-adapter-contract.md) and
[project-knowledge rule](../../framework/project-knowledge.md).

## What Happens When Project Documentation Contradicts The Code?

The assistant should identify the fact type, consult its source-of-truth owner,
mark the contradiction, re-derive relevant invariants, and report the conflict
resolver, validation, and residual risk. It should not assume that either the
newest file or the implementation is automatically correct. See the
[source-of-truth registry](../../framework/source-of-truth-registry.md).

## Is The Project Production-Ready?

The source [VERSION](../../VERSION) currently records `0.1.0-alpha.30`.
AlatyrCore has implemented framework contracts, target templates, source
checks, conformance fixtures, optional scaffolding, and an optional structural
target validator. It should not be
presented as a turnkey production service or as proof that a target adapter is
correct. Real adoption requires repository-specific adaptation, ownership,
approval, validation, and operational review.

## What Is Currently Experimental?

The following areas are implemented or prepared at the source-contract level
but remain evidence-limited in real-world use:

- assistant behavior across client versions and instruction-loading models
- broad multi-model and multi-project runtime conformance
- measured onboarding, rework, quality, and cost effects
- long-term maintenance of large target adapters and optional modules
- a complete runnable public demonstration target

Source checks and prepared conformance artifacts must not be presented as
proof of product-market value or equivalent external assistant behavior.
