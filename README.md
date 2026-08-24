# AlatyrCore

**Your project should remember why it was built this way.**

AlatyrCore is a vendor-neutral project guardian for software teams and AI
coding agents. It keeps project knowledge, architectural intent, decision
boundaries, and validation guidance with the repository so they can survive
changes in people, tools, agents, and time.

- Persistent project memory owned by the project
- Architectural continuity without treating code as the whole design record
- Conversational project reference for developers and maintainers
- Onboarding support designed to reduce project discovery time
- Safer AI-assisted change through project-specific boundaries and validation
- Interchangeable assistant support without vendor-owned project memory

Other systems add AI to a project. AlatyrCore gives the project memory, a
voice, and continuity.

## What AlatyrCore Is

AlatyrCore is not another coding agent. It is a repository-owned framework and
project adapter that gives compatible AI assistants a shared way to discover
what the project knows, distinguish evidence from decisions, route questions,
and prepare changes with the right context, approvals, validation, and final
evidence.

The project remains the owner. AI assistants are replaceable interaction and
execution surfaces over project-owned sources of truth. The same project
memory can support onboarding, daily reference, architecture discussion,
implementation planning, validation, review, and knowledge transfer.

The canonical boundaries for this model are the
[project adapter contract](framework/project-adapter-contract.md),
[source-of-truth registry](framework/source-of-truth-registry.md), and
[framework guarantees and limits](framework/guarantees.md).

## The Problem It Solves

Project knowledge is usually fragmented across code, architecture decisions,
runbooks, tests, CI, diagrams, review history, and the memories of individual
people. AI coding agents can produce useful local changes, but they do not
automatically preserve the intent and constraints distributed across those
surfaces.

AlatyrCore gives supported assistants the same project-owned starting point.
It routes a request to the smallest relevant context, identifies fact owners,
separates observed implementation from accepted intent, and requires
validation and residual-risk evidence before consistency is claimed.

This is the practical distinction:

- **The AI agent performs the work.** It reads, explains, plans, edits, and
  validates within its available capabilities.
- **The installed Alatyr adapter supplies project continuity.** It records
  where truth is owned, which decisions are accepted, which boundaries apply,
  and what remains unknown.
- **People retain authority.** AlatyrCore preserves recorded decisions and
  approval boundaries; it does not replace project owners or make stale
  decisions permanently correct.

## See It In Action

The following conversations are illustrative. Angle-bracketed sources describe
target-project evidence; they are not paths or facts from this repository.

```text
Developer:
Why can the billing module not write directly to the order database?

Alatyr:
The accepted ownership rule assigns order lifecycle state to the Order Service.
Direct writes are restricted because they bypass validation and event
publication.

Sources:
- <canonical architecture source>
- <relevant ownership or decision record>
```

```text
Developer:
Add retry handling to payment processing.

Alatyr:
This change may affect the payment state invariant, idempotency contract,
failure classification, observability requirements, and related tests.

Before implementation, I need to inspect:
- <relevant source>
- <relevant contract>
- <relevant validation>
```

AlatyrCore does not contain those example business rules. An installed project
adapter must resolve answers from the target repository or report that the
required fact is missing. The current
[quick demo](docs/human/quick-demo.md) is a documentation-only walkthrough;
this repository does not yet include a complete runnable demonstration target.

## Discuss The Project Before Changing It

You do not need an implementation-ready request to use an installed Alatyr
adapter. You can discuss the project with the agent before deciding whether or
how to change it.

For example, you can ask the agent to:

- explain an existing business rule, workflow, architecture area, or pattern
- check whether a proposed change conflicts with accepted project boundaries
- compare design or architecture options against the same project constraints
- identify affected facts, owners, contracts, tests, diagrams, and risks
- challenge assumptions and name missing or contradictory evidence
- refine a broad idea into a bounded proposal and implementation plan
- review a proposed solution without editing the repository

```text
Developer:
We are considering separating reporting from order processing. Before changing
code, help me check whether that fits the current architecture and compare the
reasonable options.

Alatyr:
I will treat this as a read-only architecture discussion. First I will inspect
the accepted boundaries, current implementation evidence, data ownership,
runtime dependencies, and relevant quality constraints.

I will return:
- what is observed versus accepted
- viable options compared against the same criteria
- likely impact and validation needs
- assumptions, contradictions, and missing evidence
- a proposed recommendation, without changing project files
```

During discussion, the agent should cite target-project evidence and keep
`observed`, `proposed`, and `accepted` states separate. A recommendation does
not become accepted architecture, authorize protected work, or change files by
itself. When the project owner accepts a direction, the discussion can continue
into a blueprint-driven change, logical integrity review, implementation, and
validation.

Canonical guidance is in
[architecture knowledge and discussion](framework/architecture-knowledge.md)
and [logical integrity review](framework/logical-integrity.md).

## Start Here

Choose the path that matches what you are doing:

- **Understand the idea:** read
  [What is AlatyrCore?](docs/human/what-is-alatyr.md).
- **Evaluate the workflow:** follow the
  [quick demonstration](docs/human/quick-demo.md) and review the
  [current limitations](#current-maturity-and-limitations).
- **Install it in a project:** give this repository and the target repository
  to a capable AI coding assistant, then use the
  [installation request template](installer/assistant-request-template.md).
- **Guide an AI assistant:** start at
  [AI_ASSISTANTS.md](AI_ASSISTANTS.md).
- **Contribute to AlatyrCore:** read [AGENTS.md](AGENTS.md) and the
  [framework maintenance guide](docs/framework-maintenance.md).

Installation is assistant-driven because the adapter must be derived from the
target repository, not copied as generic project facts. The assistant inspects
the target, prepares an installation plan, preserves existing instructions,
and asks for approval before protected changes.

## Who It Is For

- Developers who need a reliable explanation of an unfamiliar project before
  making a change
- Maintainers who need project decisions, validation, and known gaps to remain
  discoverable
- Architects who want intended architecture distinguished from implementation
  that merely happens to exist
- Teams using one or more AI coding assistants for onboarding, daily work,
  review, and knowledge transfer
- Platform and developer-experience teams that need repository-owned AI
  operating boundaries rather than vendor-specific memory

The intended outcomes require validation in real projects. AlatyrCore does not
claim to eliminate onboarding time, prevent every AI mistake, or make project
facts correct by itself.

## How It Works

1. The target repository identifies canonical project sources, owners,
   architecture states, validation, and known gaps.
2. A repository-aware project adapter connects those facts to portable
   AlatyrCore rules and supported assistant surfaces.
3. A generated, hash-bound bootstrap index and compact router select the
   smallest task, gate fragments, and project-area context for a question or
   change.
4. The assistant explains the project or follows the matching workflow,
   including approvals for protected changes.
5. Deterministic checks validate structural contracts where possible; human
   and assistant reasoning still decide semantic correctness.
6. Before a material task ends, a proportional evidence gate preserves the
   compact invariant, root cause, solution rationale, regression intent,
   validation, and exact repository binding when that knowledge would
   otherwise disappear with the session. Small self-explanatory changes may
   skip it with a specific reason.

Optional modules can add architecture knowledge, project vocabulary, generated
code-reference documentation, test-first development, team coordination,
large-task orchestration, capability-gated worker delegation with project-
owned roles and provider-specific thin bindings, diagrams, and adapted AI
infrastructure. A passive dependency-knowledge module can also bind
framework or library documentation to exact installed package artifacts while
keeping one active project adapter and project-owned deviations. Optional
modules are enabled only when the target project needs and can maintain them.
Workspace modes can additionally separate application, framework, library,
skeleton, dependency, or workspace perspectives. The assistant proposes modes
from repository evidence after installation, while users decide which modes
are accepted. Each actual mode keeps bounded support in its own project-owned
directory; optional root support holds only facts shared across modes.

For selected tasks, the optional [Debug Mode](framework/debug-mode.md) can
record normalized, non-canonical evidence about what Alatyr found
independently, where human supervision changed the investigation, which
validation expanded, and how the task concluded. Its versioned event model
separates actor, causality, intervention, and contribution so a task request or
validation request is not misreported as a correction. Finalization closes the
durable-evidence decision, evaluates reusable materiality, distinguishes exact
from partial reproduction evidence, preserves repository-binding lineage, and
opens continued work in a new linked record rather than rewriting completed
evidence. Debug Mode is explicitly enabled per task or session, does not store
raw conversations or private reasoning, and does not grant permission to edit
code, commit, publish, or perform protected actions.

### Core Differentiators

1. **Project memory belongs to the project.** Knowledge is recorded in
   repository-owned sources rather than entrusted to one agent session or
   vendor.
2. **The framework adapts to the target repository.** AlatyrCore supplies the
   process; each project supplies its own facts, commands, policies, and
   validation.
3. **The assistant performs repository-aware installation.** It inspects the
   target, prepares a plan, and rewrites adapter placeholders from target
   evidence.
4. **Architecture is not inferred solely from code.** Observed implementation,
   proposals, accepted decisions, restrictions, deprecations, contradictions,
   and unknowns remain distinct.
5. **Project knowledge is versioned with the repository.** Sources, adapter
   metadata, decisions, and gaps can evolve through normal repository review.
6. **Humans interact through natural language.** `Alatyr` and related phrases
   are assistant request shortcuts backed by target files, not a universal
   daemon or shell command.
7. **Checks complement reasoning.** Source and optional target validators can
   detect structural drift, but they do not prove business truth or replace
   logical integrity review.

## Agent-Driven Installation

AlatyrCore is installed through assistant reasoning, not blind application of
a universal installer. The assistant reads this repository, inspects the
target repository, creates an installation plan, and adapts only the framework
and project-adapter surfaces the target can support. Existing instructions and
protected changes remain subject to approval.

Start with the [installation guide](INSTALL.md). The assistant uses
`installer/context-router.json` to select the current installation stage and
`framework/file-inventory.json` for deterministic copy and hash comparison.
Read only selected or changed canonical framework owners; unchanged framework
files do not need to be loaded as prose.

Optional scaffolding can create placeholder structure, but it does not inspect
the target, resolve project facts, approve changes, or complete installation.
It can scaffold an explicit dependency-closed capability set instead of
copying every optional target surface.

To our knowledge, AlatyrCore is among the first publicly documented AI
engineering frameworks whose primary installation model is repository-aware
adaptation performed by an AI assistant rather than blind application of a
universal installer.

## After Installation

Developers continue using their supported assistant in natural language:

```text
Alatyr
Alatyr status
Explain this project to a new developer.
Where is the source of truth for payment state?
Review the architectural impact of this change.
Create or repair the project blueprint.
Recheck Alatyr after the framework update.
```

`Alatyr` is a conversational entry request, not a shell command. A healthy
adapter reports its current evidence status and relevant next actions. Clear,
low-risk requests route automatically; ambiguous or protected work receives a
bounded preview and any required approval before changes.

Action authorization is tied to the newest request and current logical task.
Returning to an issue, backlog item, report, or discussion is read-only unless
the same request clearly asks for implementation. Implementation does not
authorize commit or push, and commit does not authorize push. AlatyrCore keeps
these phases separate from allowed file scope, protected-change approval, and
tool access.

The full installed-operation and assistant workflow is documented in
[AI_ASSISTANTS.md](AI_ASSISTANTS.md),
[installed operations](framework/installed-operations.md), and
[operation help](framework/operation-help.md).

## Start With The Smallest Profile

Do not install every optional capability by default. Establish the required
core profile first, then enable optional modules only when the target needs and
can maintain them. The source scaffolder exposes `core`, `standard`, and `full`
support profiles, repeatable `--enable-module` capability selection, and
dependency-closed `core`, `standard`, and `complete` framework packs.

The [module profile](framework/module-profile.md) defines required and optional
capabilities. The [context router](framework/context-router.md) keeps routine
tasks from loading the complete framework or project corpus.

## Current Maturity And Limitations

The source [VERSION](VERSION) currently records `0.1.0-alpha.26`. Implemented
repository assets include portable framework contracts, target templates,
assistant-driven installation guidance, source consistency checks, conformance
fixtures, optional scaffolding, and an optional installed-adapter structural
validator.

Important limits:

- There is no complete runnable demonstration target in this repository.
- AlatyrCore is not a hosted service, universal runtime, autonomous coding
  agent, or portable shell command.
- Source checks prove selected repository structures and references, not the
  correctness of target business facts or architecture.
- Generated bootstrap, gate, upgrade-impact, and validator routes reduce
  repeated structural work; they do not replace assistant logical reasoning.
- Static bridge and prompt checks do not prove that every external assistant
  client auto-loads or follows instructions identically.
- Onboarding, quality, rework, and cost benefits require broader validation in
  real teams and projects.
- The generated [evidence status](conformance/evidence-status.json) records
  which assistant surfaces and effectiveness claims have current-contract
  real-run support; same-version stale, historical, or prepared evidence is not
  promoted to current proof.
- Optional modules are useful only when a target provides owners, evidence,
  maintenance, and validation.

The authoritative claim boundaries are documented in
[framework guarantees and limits](framework/guarantees.md).

## Documentation

Human-oriented guides:

- [What is AlatyrCore?](docs/human/what-is-alatyr.md)
- [The project guardian concept](docs/human/project-guardian-concept.md)
- [Quick demonstration](docs/human/quick-demo.md)
- [Team use cases](docs/human/team-use-cases.md)
- [Team collaboration workflow](docs/human/team-collaboration-workflow.md)
- [Frequently asked questions](docs/human/faq.md)

Technical entry points:

- [AI assistant guide](AI_ASSISTANTS.md)
- [Installation guide](INSTALL.md)
- [Framework index](framework/README.md)
- [Repository layout](docs/repository-layout.md)
- [Source tooling reference](tools/README.md)
- [Assistant compatibility](docs/assistant-compatibility.md)
- [Passive dependency knowledge](framework/dependency-knowledge.md)
- [User-owned workspace modes](framework/workspace-modes.md)
- [Durable engineering evidence](framework/engineering-evidence.md)

Human guides explain the product; they do not own framework policy. Canonical
rules remain in the referenced framework documents and
[rule registry](framework/rule-registry.md).

## For AI Assistants

`AI_ASSISTANTS.md` is the dedicated assistant-facing description and route.
For installation, treat `AGENTS.md` as host-preloaded context, read
`installer/context-router.json`, and load only the selected stage's sources.
Use `framework/file-inventory.json` for unchanged-file comparison and read only
selected or changed canonical framework owners.

Apply canonical rule references rather than copying policy text into bridge
files: `ALATYR-ADAPTER-001`, `ALATYR-APPROVAL-001`, `ALATYR-AUTHORIZATION-001`, `ALATYR-SAFETY-001`,
`ALATYR-SAFETY-002`, `ALATYR-INTEGRITY-001`, `ALATYR-EVIDENCE-001`,
`ALATYR-ENGINEERING-EVIDENCE-001`, and `ALATYR-OPERATION-001`. Load
`ALATYR-DEPENDENCY-001` only when the optional
dependency-knowledge module or a dependency operation is selected.
Load `ALATYR-MODE-001` only when workspace modes are enabled, mode selection is
ambiguous, or a mode lifecycle operation is requested.

## Contributing

Before changing AlatyrCore, read [CONTRIBUTING.md](CONTRIBUTING.md),
[AGENTS.md](AGENTS.md), and the
[framework maintenance guide](docs/framework-maintenance.md). Keep portable
framework rules, installation material, target templates, and explanatory docs
separate. Source-repository commands and checker details are owned by the
[tooling reference](tools/README.md), not by the portable framework.

Security reports follow [SECURITY.md](SECURITY.md). Do not place credentials,
private target-project facts, or exploit details in public issues.

## License

AlatyrCore is licensed under the Apache License, Version 2.0.
See [`LICENSE`](LICENSE) for the complete terms.

Unless a file explicitly states otherwise, the license covers this
repository's framework documents, source tools, templates, schemas, and public
documentation. It does not change the ownership or licensing of target-project
source code, architecture, business rules, project-specific documentation, or
project-specific adapter content generated during installation. Those remain
subject to the target repository's ownership and licensing rules.

The Apache License 2.0 covers the AlatyrCore source, framework documents,
templates, and tools. It does not grant rights to use the AlatyrCore name or
visual identity to imply that a derived product is an official AlatyrCore
release.
