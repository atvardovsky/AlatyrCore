# What Is AlatyrCore?

AlatyrCore is a vendor-neutral project guardian for software teams and AI
coding agents. It is designed to keep the knowledge needed to understand and
change a project with the project itself.

> This document is a human-oriented explanation. Canonical framework rules
> remain owned by the referenced framework documents and
> [rule registry](../../framework/rule-registry.md).

## Capability Status

- **Implemented framework contracts:** ownership separation, source-of-truth
  routing, architecture-state separation, conversational operation routing,
  context profiles, validation evidence, and thin assistant bridges.
- **Target-dependent behavior:** useful project explanations and safe change
  guidance require a correctly adapted target repository with current facts,
  owners, validation, and supported assistant surfaces.
- **Evidence-limited outcomes:** faster onboarding, lower rework, and lower AI
  cost are intended benefits that require broader validation in real teams.

The authoritative limits on these claims are in
[framework guarantees and limits](../../framework/guarantees.md).

## The Project Guardian

A coding agent acts on a request. A project guardian preserves the context in
which that request should be understood.

For an installed project, AlatyrCore connects an assistant to project-owned
records such as:

- canonical sources of truth and their decision owners
- architectural areas, patterns, constraints, and decision states
- business, data, security, runtime, and public-contract boundaries
- project-specific validation and manual review
- known gaps, contradictions, and residual risks
- supported assistant behavior and local limitations

AlatyrCore supplies the portable process and record shapes. It does not supply
the target project's business rules, architecture facts, commands, or security
policy. That separation is owned by the
[project adapter contract](../../framework/project-adapter-contract.md).

## Why Project Memory Belongs In The Repository

An assistant session is temporary. A vendor-specific memory feature may be
unavailable to another agent, another team, or a future project owner.
Repository-owned knowledge can instead be:

- reviewed with the code and documentation it governs
- attributed to a project owner or decision authority
- versioned, compared, and migrated
- reused by different compatible assistants
- marked missing, stale, contradicted, or unverified
- transferred with the project when people or tools change

This memory is not one giant narrative. The
[source-of-truth registry](../../framework/source-of-truth-registry.md) maps
fact types to canonical owners and derived surfaces. The
[context router](../../framework/context-router.md) helps an assistant load
only the part relevant to the current task.

When an investigation produces an expensive reusable conclusion, the assistant
may propose it for review. A project decision owner accepts, narrows, rejects,
or defers the candidate. Accepted facts stay in canonical project sources;
compact route shards only help later developers and assistants find and
reverify those owners. See
[project knowledge promotion and delivery](../../framework/project-knowledge.md).

## Agent And Guardian Are Different Roles

The AI agent is an interaction and execution surface. It can answer a
question, inspect files, prepare a plan, edit approved surfaces, and report
evidence.

The project guardian is the repository-owned continuity layer that tells a
compatible agent:

- where project truth is owned
- which decisions are accepted rather than merely observed
- which boundaries and approvals apply
- which validation is expected
- what remains unknown

AlatyrCore is therefore not a hosted agent, daemon, or universal command. Its
conversational interface is an assistant response pattern backed by an
installed adapter, as defined by
[operation help](../../framework/operation-help.md).

## Value For Project Roles

### Developers

AlatyrCore can help a developer find the right source before changing code,
understand local constraints, and identify the validation expected for the
change.

### Maintainers

It is designed to keep ownership, known gaps, assistant instructions, and
validation evidence discoverable when the repository or team evolves.

### Architects

It distinguishes observed implementation from proposed, accepted, preferred,
restricted, deprecated, contradicted, and unknown architecture. The canonical
state model belongs to
[architecture knowledge](../../framework/architecture-knowledge.md).

### Teams

It can provide different compatible AI assistants with the same canonical
project entry points while preserving assistant-specific limitations. The
contract for those differences is the
[bridge capability matrix](../../framework/bridge-capability-matrix.md).

## Canonical Sources Still Decide

AlatyrCore does not turn every adapter file into a new source of truth. The
adapter should route to existing project owners and record how derived
surfaces synchronize. If an owner is missing or two sources conflict, the
assistant should report the gap instead of choosing the nearest or newest file.

Project decision owners retain authority. AlatyrCore continues recorded
intent; it does not create that authority or make an old decision permanently
correct.
