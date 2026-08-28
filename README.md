# AlatyrCore

**Your project should remember why it was built this way.**

AlatyrCore is a vendor-neutral project guardian for software teams and AI
coding agents. It makes project-specific development rules, recorded
architectural intent, and reviewed engineering knowledge properties of the
repository rather than of one developer or AI agent. These rules, records,
boundaries, and validation expectations remain available as people, tools,
agents, and time change.

- Project-owned development rules for human and AI engineering
- Recorded architectural intent and reviewed engineering knowledge
- Bounded task-specific delivery of applicable rules and context
- Target-designated authority and approval boundaries
- Project-specific validation and evidence expectations
- Continuity across developers, compatible agents, tools, and sessions

AlatyrCore lets the project own the rules, knowledge, and recorded intent that
guide compatible assistants.

**One project. Shared rules, recorded intent, and reviewed knowledge. Many human
and AI executors.**

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

## The Project Development Model

Collectively, a target's canonical sources and installed Alatyr adapter
represent its project development model: the applicable development rules,
recorded intent, reviewed knowledge, authority boundaries, validation, and
known gaps that shape engineering work.

This is a human-facing description of a distributed model, not a new source of
truth or an active Alatyr runtime. Architecture decisions, policies, CI,
configuration, tests, and other project facts remain owned by their registered
canonical sources. The adapter connects compatible assistants to those owners
and reports missing or contradictory parts instead of pretending the model is
complete.

## The Problem It Solves

Project knowledge is usually fragmented across code, architecture decisions,
runbooks, tests, CI, diagrams, review history, and the memories of individual
people. AI coding agents can produce useful local changes, but they do not
automatically preserve the intent and constraints distributed across those
surfaces.

Each new developer, session, or assistant can therefore repeat the same
repository archaeology: locating authority, reconstructing architecture,
rechecking dependency behavior, and asking maintainers to explain constraints
the project has already established. AlatyrCore is designed to reduce that
repeated reconstruction without replacing source inspection or freshness
checks.

Executors must otherwise also infer how the project expects changes to be made:
which boundaries are intentional, which compatibility commitments matter,
which solution classes are restricted, what validation is required, and when a
decision by a target-designated owner is necessary. Repeating that inference
across people, sessions, and tools creates development-guidance drift even when
everyone starts from the same repository. AlatyrCore makes those expectations
explicit and routable where the target has recorded them; it does not
automatically detect or repair every semantic disagreement.

AlatyrCore gives supported assistants the same project-owned starting point.
It routes a request to a bounded task-relevant context packet, identifies fact
owners, separates observed implementation from accepted intent, and requires
validation and residual-risk evidence before consistency is claimed.

This is the practical distinction:

- **The AI agent performs the work.** It reads, explains, investigates, and
  proposes a solution. When the current request authorizes implementation, it
  edits and validates within accepted project boundaries and its available
  capabilities.
- **The installed Alatyr adapter supplies project continuity.** It records
  where truth is owned, which decisions are accepted, which boundaries apply,
  and what remains unknown.
- **Target-designated decision owners retain authority.** AlatyrCore preserves
  recorded decisions and approval boundaries; it does not grant every
  contributor the same authority, replace project owners, or make stale
  decisions permanently correct.

## Project-Owned Development Rules

An installed adapter can route not only project facts, but also accepted rules
for how particular changes should be made. Depending on the target, these may
include:

- public API compatibility and release policy
- subsystem ownership and permitted dependency directions
- validation required for specific change classes
- protected architecture decisions and approval triggers
- security, data, runtime, or generated-artifact boundaries
- accepted restrictions on solution classes rejected by project decision owners

The rule remains owned by its canonical project source. AlatyrCore does not
invent target policy from common practice, source-code statistics, or agent
consensus, and the adapter must not duplicate a rule merely to make it easier to
route.

```text
target decision
        -> accepted development rule
        -> canonical project owner
        -> bounded task-specific guidance
        -> authorized agent execution
        -> project validation
```

The adapter records whether guidance came from a reviewed engineering
discovery or directly from a target-authorized decision owner. Narrower rules
and exceptions remain scope- and authority-bound, while missing coverage is
reported as a known gap or unknown rather than hidden behind a completeness
score.

## From Engineering Discovery To Project Knowledge

AlatyrCore separates historical engineering evidence from accepted project
knowledge. An assistant may identify an expensive, reusable conclusion, but it
cannot promote that conclusion into project truth by itself.

```text
engineering discovery
        -> reusable knowledge proposal
        -> target decision-owner review
        -> accepted canonical project source
        -> bounded routing to later related work
```

The reviewer may accept, narrow, reject, or defer the proposal. Only accepted,
current knowledge can become a candidate constraint, and a later executor must
still read the canonical owner before relying on it for a material decision.
Stale knowledge becomes a revalidation warning; contradictory knowledge blocks
a definitive conclusion until the target owner resolves it.

The adapter reports whether this capability is merely enabled with an empty
index, populated with reviewed routes, or supported by observed later-task
reuse evidence. An empty index is a valid starting point, but it is not evidence
that project knowledge reduced rediscovery.

The intended product criterion is straightforward: help a new developer or
compatible AI agent begin from reviewed project knowledge and spend less effort
reconstructing already-known context. That is a measurable goal, not a claim
that current evidence proves the benefit for every project or assistant.

Canonical behavior is defined by
[Project Development Model guidance and knowledge delivery](framework/project-knowledge.md).

## What AlatyrCore Is Not

AlatyrCore is not a coding agent, hosted intelligence service, daemon, or
universal shell command. It does not replace architects or target decision
owners, automatically infer accepted intent from code, or turn assistant
conclusions into project truth.

It also does not copy the repository or raw conversations into one large memory
store. Its adapter routes bounded project-owned sources and reviewed derived
records. Structural checks can detect contract drift, but they cannot guarantee
semantic correctness or that every assistant client loaded and followed the
same instructions.

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

## Why Not Just `AGENTS.md`?

An `AGENTS.md` file is a useful assistant entry surface, and AlatyrCore supports
it. A single instruction file can point an agent in the right direction, but it
does not by itself provide AlatyrCore's project-level contracts for:

- canonical ownership, authority, and provenance
- accepted, observed, proposed, stale, contradicted, and historical states
- task-specific context and project-knowledge routing
- freshness, revalidation, conflict, and supersession handling
- approval, validation, and final-evidence boundaries
- reviewed promotion of reusable engineering discoveries

In an installed adapter, `AGENTS.md` remains a compact bridge into those
project-owned contracts. It is not required to duplicate the complete policy or
project-memory model.

For example, `AGENTS.md` may tell an assistant not to break public APIs in patch
releases. The project sources behind an Alatyr route can additionally identify
where that rule is owned, which branches and versions it covers, why it exists,
which exceptions require approval, what validation demonstrates compliance,
and whether its owner has changed since the rule was reviewed.

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

- Engineering teams using AI agents for production changes that must remain
  consistent with project-specific rules and validation
- Maintainers responsible for architecture, backward compatibility, release
  policy, and known gaps
- Architects and senior engineers whose recorded decisions need to scale across
  developers and compatible AI agents
- Teams using interchangeable AI coding tools or multiple AI vendors
- Platform and developer-experience teams that need repository-owned AI
  operating boundaries rather than vendor-specific memory
- Developers who need a reliable explanation of an unfamiliar project before
  making a change

The intended outcomes require validation in real projects. AlatyrCore does not
claim to eliminate onboarding time, prevent every AI mistake, or make project
facts correct by itself.

The intended outcome is not zero human involvement. It is to concentrate human
attention on new architecture, compatibility, risk, exception, and authority
decisions while compatible agents perform authorized investigation,
implementation, and validation. A correction that establishes a reusable
project decision should be reviewed into its canonical owner so later work does
not require the same explanation. Actual supervision savings remain an
evidence-limited outcome.

## How It Works

Conceptually:

1. The project records applicable development rules and accepted intent in
   canonical sources.
2. The installed adapter routes a bounded relevant subset of rules, knowledge,
   boundaries, and validation to the current task.
3. The agent performs the authorized engineering work within that context.
4. Target decision owners review matters requiring project authority or
   judgment.
5. Reusable discoveries and corrections can be reviewed back into canonical
   project knowledge.

The framework implements that model through these repository surfaces:

1. The target repository identifies canonical project sources, owners,
   architecture states, validation, and known gaps.
2. A repository-aware project adapter connects those facts to portable
   AlatyrCore rules and supported assistant surfaces.
3. A generated, hash-bound bootstrap index and compact router select the
   bounded task profile, gate fragments, and project-area context for a
   question or change. Recursive contour indexes then expose only matching
   branches instead of whole support directories.
4. A small versioned semantic codebook resolves repeated framework concepts
   once per context packet. Compact terms retain complete definitions and
   canonical-owner fallback; they never replace project facts or policy.
5. The assistant explains the project or follows the matching workflow,
   including approvals for protected changes.
6. Deterministic checks validate structural contracts where possible; human
   and assistant reasoning still decide semantic correctness.
7. Before a material task ends, a proportional evidence gate preserves the
   compact invariant, root cause, solution rationale, regression intent,
   validation, and exact repository binding when that knowledge would
   otherwise disappear with the session. Small self-explanatory changes may
   skip it with a specific reason.
8. A separate project-knowledge gate lets target decision owners accept,
   narrow, reject, or defer reusable conclusions. Accepted facts remain in
   canonical project sources; compact, freshness-checked route shards help a
   later assistant find those owners without loading the full project memory.

The checked static surface registry covers generic and AGENTS-aware clients,
Codex, JetBrains Junie, Cline, Kiro, Zed Agent, OpenCode, Claude, Gemini,
GitHub Copilot, Cursor, Devin/Cascade, Windsurf, and legacy Roo Code. This means
AlatyrCore supplies a bridge and evidence contract, not that every client has
been observed following it. Each installed project records the exact client,
instruction precedence, skills, permissions, diagrams, and delegation before
claiming runtime support. See [assistant compatibility](docs/assistant-compatibility.md).

The recursive indexes behave like site navigation: each root links to smaller
sections, sections may link to deeper sections, and selecting a parent does not
load every child. Entries carry stable identities, selectors, word estimates,
and content digests. For non-trivial or expanded work, a deterministic context
packet records the chosen index chain, content identities, resolved semantic
definitions, budget, and fallback state. These records prove routing identity,
not that a model understood or followed the content.

A target-owned support policy classifies the adapter and assistant entry
surfaces, while a canonical cross-platform support state records which of them
changed. For projects that enable a consistency map, changed paths and fact IDs
select only relevant relationship shards and concrete companion surfaces.
Hashes and graph routes reduce repeated scanning; people and assistants still
derive the invariant, decide whether a newly observed relationship is valid,
and approve the coherent repair set. See
[support information](framework/support-information.md).

Optional modules can add architecture knowledge, project vocabulary, generated
code-reference documentation, test-first development, team coordination,
large-task orchestration, capability-gated worker delegation with project-
owned roles and provider-specific thin bindings, diagrams, and adapted AI
infrastructure. A passive dependency-knowledge module can also bind
framework or library documentation to exact installed package artifacts while
keeping one active project adapter and project-owned deviations. Optional
support generation can coordinate target-declared deterministic derivatives,
assistant proposals, and owner-maintained artifacts without turning generated
output into a new source of truth. Optional
modules are enabled only when the target project needs and can maintain them.
Workspace modes can additionally separate application, framework, library,
skeleton, dependency, or workspace perspectives. The assistant proposes modes
from repository evidence after installation, while users decide which modes
are accepted. Each actual mode keeps bounded support in its own project-owned
directory; optional root support holds only facts shared across modes.

For selected tasks, the optional [Debug Mode](framework/debug-mode.md) can
record normalized, non-canonical evidence about what the active executor found,
which behavior came from deterministic Alatyr routing or checks, where human
supervision changed the investigation, which validation expanded, and how the
task concluded. Its versioned event model separates actor role, identity,
runtime provenance, causality, correction disposition, and contribution so a task request or
validation request is not misreported as a correction. Finalization closes the
durable-evidence decision, evaluates reusable materiality, distinguishes exact
from partial reproduction evidence, distinguishes phase completion from a full
analysis-to-validation lifecycle, closes reusable knowledge candidates through
reviewable dispositions, preserves reciprocal durable-evidence and repository-
binding lineage, and opens continued work in a new linked record rather than
rewriting completed evidence. Debug Mode is explicitly enabled per task or session, does not store
raw conversations or private reasoning, and does not grant permission to edit
code, commit, publish, or perform protected actions.

### Core Differentiators

1. **The project owns its development guidance.** Development rules, recorded
   intent, reviewed knowledge, authority boundaries, and validation expectations
   remain in project-owned canonical sources.
2. **Applicable rules travel with task context.** Bounded routing selects the
   relevant project model without loading every policy or retained knowledge
   item.
3. **Owners retain authority while agents retain engineering freedom.** Target
   decision owners govern accepted truth, exceptions, and protected risk;
   compatible agents perform authorized engineering work within those
   boundaries and their available capabilities.
4. **Important corrections can become reusable knowledge.** Human-reviewed
   conclusions can update canonical owners and reach later related work without
   turning raw conversations into authority.
5. **The guidance survives changes in compatible executors.** Project-owned
   sources do not depend on one assistant session or vendor, while bridge
   capabilities and limitations remain explicit.
6. **Architecture is not inferred solely from code.** Observed implementation,
   proposals, accepted decisions, restrictions, deprecations, contradictions,
   and unknowns remain distinct.
7. **Validation and evidence are part of the guidance.** Structural checks and
   project validation complement semantic reasoning without claiming business
   truth.
8. **The framework adapts to the target repository.** AlatyrCore supplies the
   portable process; each project supplies its own facts, commands, policies,
   validation, and unresolved gaps.
9. **The assistant performs repository-aware installation.** It inspects the
   target, prepares a plan, and rewrites adapter placeholders from target
   evidence.
10. **Humans interact through natural language.** `Alatyr` and related phrases
   are assistant request shortcuts backed by target files, not a universal
   daemon or shell command.

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

The source [VERSION](VERSION) currently records `0.1.0-alpha.34`. Implemented
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
- Provider-neutral conformance contracts can prepare, import, collect, and
  validate evidence across supported surfaces, but only captured reviewed runs
  prove actual provider behavior.
- Context receipts separate planned and resolved source estimates from observed
  host/provider telemetry; estimates are not presented as actual token savings.
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
- [Project knowledge promotion and delivery](framework/project-knowledge.md)
- [Target adapter contract compatibility](docs/target-adapter-contract-compatibility.md)

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
`ALATYR-ENGINEERING-EVIDENCE-001`, `ALATYR-KNOWLEDGE-001`, and
`ALATYR-OPERATION-001`. Load
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
