# Team Use Cases

AlatyrCore is designed to support project continuity across developers,
maintainers, architects, teams, and compatible AI assistants. The use cases
below describe intended outcomes. They are not measured promises.

> This document is a human-oriented explanation. Canonical framework rules
> remain owned by the referenced framework documents and
> [rule registry](../../framework/rule-registry.md).

## Onboarding

An adapted project guardian can help a new developer find the project contour,
major architecture areas, canonical fact owners, validation entry points, and
known gaps without requiring them to begin with the full framework corpus.

This is designed to reduce discovery friction, but onboarding improvement
requires validation in real teams. Context selection is owned by
[context profiles](../../framework/context-profiles.md).

## Daily Project Reference

Developers can ask where a rule is owned, why a boundary exists, which command
or review validates a concern, and what remains unknown. The assistant should
answer from target evidence and cite the owner rather than relying on session
memory.

The conversational behavior is defined by
[operation help](../../framework/operation-help.md), while fact ownership is
defined by the target adaptation of the
[source-of-truth registry](../../framework/source-of-truth-registry.md).

## Architecture Explanation

AlatyrCore can help explain selected architecture areas, patterns, constraints,
and decision status. It is intended to make the distinction between current
implementation and intended architecture visible during discussion.

Architecture explanation still depends on target-owned evidence and decision
authority. See
[architecture knowledge](../../framework/architecture-knowledge.md).

## Change-Impact Analysis

Before implementation, the project adapter can help an assistant identify
changed facts, owners, invariants, affected areas, approval triggers,
validation, and documentation or diagram synchronization. This can help reduce
isolated fixes that overlook a related contract.

It does not guarantee a complete impact set. The process commitments and
non-guarantees are documented in
[framework guarantees and limits](../../framework/guarantees.md).

## Review Preparation

An assistant can prepare a review summary that names semantic changes,
canonical owners, validation evidence, skipped checks, contradictions, and
residual risk. This is intended to make review evidence easier to inspect; it
does not replace reviewer judgment or approval authority.

## Knowledge Preservation When People Leave

Repository-owned project knowledge can help preserve decisions, ownership,
constraints, and unresolved gaps when a maintainer or architect leaves the
team. The value depends on owners keeping those records current and resolving
conflicts instead of treating documentation as automatically true.

Adapter ownership and review requirements belong to the
[project adapter contract](../../framework/project-adapter-contract.md).

For expensive non-obvious discoveries, a separate
[project-knowledge lifecycle](../../framework/project-knowledge.md) lets an
assistant propose a reusable conclusion and lets a target decision owner
accept, narrow, reject, or defer it. Accepted facts remain in canonical project
sources; compact routing is designed to reduce repeated orientation for later
related work without preloading the full memory corpus.

## Coordination Between AI Assistants

Thin assistant bridges can point different compatible AI tools to the same
project-owned adapter. This is intended to reduce vendor-specific drift while
still recording client-specific loading, permissions, presentation, and known
limitations.

Source checks can validate bridge structure, but equivalent runtime behavior
requires external evidence. See the
[bridge capability matrix](../../framework/bridge-capability-matrix.md).

Project-knowledge conformance additionally checks that supported surfaces are
given the same canonical authority, protected boundaries, required validation,
and unresolved decisions. It does not require identical implementation
strategies or claim equivalent client behavior without captured runs.

When the optional team module is enabled, compatible assistants can also use
the same actor policy, compact active-work projection, conflict-safe task
records, checkpoints, handoffs, decisions, and revision-bound review evidence.
Current-user selection remains ignored local attribution and does not grant
authentication or authority. See the
[team collaboration workflow](team-collaboration-workflow.md).

## Detecting Contradictions

When implementation and intended architecture disagree, AlatyrCore requires
the difference to be marked as contradicted or unresolved rather than silently
selecting one source. The target source-of-truth owner and conflict resolver
decide what should change.

This can help surface drift. It cannot determine the correct business or
architecture decision without target evidence and authority.

## Evidence Boundary

These use cases are supported by implemented framework contracts and target
templates. Their practical effect on onboarding time, rework, delivery speed,
quality, and cost remains dependent on target adaptation and requires
validation in real teams.
