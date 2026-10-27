# AlatyrCore

**Your project should remember why it was built this way.**

AlatyrCore is a vendor-neutral project guardian for software teams and AI
coding agents. It helps teams keep project knowledge, architectural decisions,
and development guidance in their repository, rather than relying on a
person's memory or an assistant's chat history.

It connects that knowledge to compatible AI agents, helping them find relevant
context, respect project boundaries, and keep supporting documentation aligned
with changes. You keep using your chosen assistant; the project keeps its
knowledge.

- **Project memory:** preserve reviewed decisions and the reasons behind them.
- **Architectural continuity:** distinguish accepted intent from what the code
  currently does.
- **Project discussion:** ask questions and compare changes using recorded
  project sources.
- **Connected change:** coordinate code, tests, documentation, and validation
  around the same change.

**Status: alpha.** Read the [current limitations](#current-maturity-and-limitations)
before adopting it.

## Start Here

- **Install in an existing project:** follow the [installation guide](INSTALL.md)
  and give your assistant the
  [installation request template](installer/assistant-request-template.md).
- **Explore before installing:** read [What is AlatyrCore?](docs/human/what-is-alatyr.md)
  or follow the [documentation walkthrough](docs/human/quick-demo.md).
- **Check your assistant:** see [supported surfaces and limitations](docs/assistant-compatibility.md).
- **Work on AlatyrCore itself:** start with [Contributing](#contributing).

To begin without authorizing changes, open your target project in a compatible
assistant and ask:

```text
Inspect this repository and propose the smallest useful AlatyrCore installation
from https://github.com/atvardovsky/AlatyrCore. Explain what would change, what
facts are missing, and which approvals are needed. Do not edit, commit, or push.
```

This starts an inspection and plan, not a completed installation. Continue with
the [installation guide](INSTALL.md) before approving changes.

## Why Project Memory Belongs In The Repository

A project can outlast its developers, its AI tools, and the conversations that
shaped it. Without recorded decisions, the next person or agent must
reconstruct why a boundary exists, who owns a business rule, or which checks
matter before changing it.

Repository-owned knowledge can be reviewed alongside code, versioned with the
project, and shared across compatible assistants. That does not mean copying
every conversation into a memory folder. Important facts stay in their
existing project sources; the Alatyr adapter records where to find them and
what remains missing, stale, or contradictory.

For example, a rule against direct database writes is more useful when an
agent can also find its owner, reason, affected subsystem, and required tests.

### Why Not Just `AGENTS.md`?

`AGENTS.md` is a useful starting point. Alatyr connects that entry point to
project-owned sources, accepted decisions,
freshness checks, change boundaries, and validation. The instruction file
does not need to become one large, duplicated manual.

Read the [project guardian concept](docs/human/project-guardian-concept.md) for
the longer explanation.

## How It Works

The individual ideas are familiar: document decisions, provide relevant
context, review changes, and validate results. AlatyrCore's focus is connecting
them into a continuous project-owned workflow:

**Understand -> discuss -> authorize -> implement -> synchronize knowledge -> validate**

A compatible assistant uses the project's installed adapter to find the
sources relevant to the task. It checks which decisions are accepted, which
facts come from observed implementation, and where evidence is missing. The
assistant can then discuss options or perform work authorized for the current
task.

For business changes, the assistant must distinguish approved requirements from
its own inferences. A repair retains the original reported case, so passing
tests or a healthy adapter cannot by themselves mean the user's problem is fixed.

For uncertain causes, [evidence-guided analysis](framework/task-decomposition.md#evidence-guided-analysis)
connects hypotheses to predictions, small discriminating checks and their result
artifacts. Conclusions can be revised without losing unresolved duties. Optional
[knowledge queries](framework/project-knowledge.md#explicit-planner-queries)
bring selected project guidance into the task, not the entire archive. These
mechanisms support disciplined investigation; they do not prove better reasoning
or grant permission to act.

When code or tests change, the assistant must review the effect on project
knowledge: update affected sources, explain why no update is needed, or report
blocked or unverified work. A useful discovery can be proposed for review by a
project decision owner and preserved in its accepted source for later tasks.

These parts reinforce one another. Stored knowledge helps the next task only
if it is current and discoverable; validation helps only if its coverage is
clear; a completed implementation is not the same as finalized evidence or
published changes.

Responsibility stays explicit:

- **The project owns its knowledge and rules.** The adapter points to existing
  sources rather than creating a competing description of the project.
- **The agent investigates and performs authorized work.** Alatyr is not an
  autonomous coding agent or a hosted service.
- **Project decision owners retain authority.** An assistant's observation or
  proposal does not become accepted architecture by itself.

The canonical details are in the
[project adapter contract](framework/project-adapter-contract.md),
[source-of-truth registry](framework/source-of-truth-registry.md),
[context router](framework/context-router.md),
[project knowledge workflow](framework/project-knowledge.md), and
[support-information sync rules](framework/support-information.md).

## Discuss The Project Before Changing It

You can use Alatyr to understand a project before deciding whether to change
it. Ask your compatible assistant questions such as:

- Why is this module designed this way?
- Where is the source of truth for this business rule?
- Is this behavior observed, proposed, or accepted?
- Would this change conflict with our architecture?
- Which tests and project documents would need review?

A discussion or recommendation does not authorize edits. The assistant should
cite project sources, separate facts from assumptions, and name missing or
contradictory evidence.

The following conversations are illustrative. Angle-bracketed sources are
examples of target-project evidence, not paths or business facts in AlatyrCore.

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
This may affect payment state, idempotency, failure handling, observability,
and related tests.

Before implementation, I need to inspect:
- <relevant source>
- <relevant contract>
- <relevant validation>
```

The installed adapter must resolve real answers from the target repository.
If the sources are absent, the assistant should report that gap instead of
inventing an explanation. See
[architecture discussion](framework/architecture-knowledge.md) and
[logical integrity review](framework/logical-integrity.md).

## Who It Is For

AlatyrCore is designed for:

- maintainers of long-lived projects with important architecture and
  compatibility decisions;
- teams using different AI coding assistants on the same codebase;
- architects and platform teams who need project guidance to survive handoffs;
- developers who need to understand an unfamiliar project before changing it.

It is most useful when the project can provide decision owners, current
sources, and meaningful validation. A small prototype may need only a compact
instruction file; installing every Alatyr capability is not the goal.

For practical examples, read the [team use cases](docs/human/team-use-cases.md)
and [team collaboration workflow](docs/human/team-collaboration-workflow.md).

## Agent-Driven Installation

Installation is repository-aware adaptation performed by an AI assistant.
Give the assistant this repository and access to the target project, then use
the [installation request template](installer/assistant-request-template.md).

The assistant inspects the target, proposes an installation plan, preserves
existing instructions, and asks for approval before protected changes. It
derives project facts from target evidence instead of treating generic
templates as accepted architecture.

The result is a project-specific adapter: the files that connect Alatyr's
portable rules to your project's sources, owners, checks, and supported
assistants. Missing facts remain explicit gaps.

The main support files live under `.ai/`: portable framework guidance,
project-owned references, and assistant workflows. Short instruction entry
points connect supported assistants to those files without replacing existing
project instructions. See the [repository layout](docs/repository-layout.md)
for the source and target structures.

Optional scaffolding can create placeholder structure. It cannot inspect
project truth, resolve those gaps, grant approval, or complete installation.

### Start With The Smallest Profile

Enable only the capabilities the project needs and can maintain. Optional
modules cover areas such as architecture knowledge, vocabulary, code-reference
documentation, test-first development, diagrams, team coordination, and
adapted AI infrastructure.

For recurring defects, an optional repair review helps distinguish a test that
ran from one that exercised the intended scenario. A faithful failing test can
guide a repair; component success or a faster benchmark does not establish that
the original incident is fixed. See [repair evidence](framework/test-first-development.md#incident-repair-review).

Task-specific routing is designed to avoid loading the complete support
library for routine work. Optional phase-specific working sets preserve required
owners and checks while selecting additional evidence within budget. Contract
routing separates complete graph checks from
the selected area evidence an agent needs; compact views do not replace the
project's canonical sources or approval boundaries. When workers are useful and the selected assistant
has verified support, independent read-only investigations can be delegated
with bounded context. The coordinating assistant still owns decisions, edits,
integration, and final validation. Delegation can increase total token use.

See the [installation guide](INSTALL.md),
[module profile](framework/module-profile.md), and
[large-task explanation](docs/human/what-is-alatyr.md#how-large-tasks-stay-manageable).

## After Installation

Keep using your supported assistant in natural language:

```text
Alatyr
Alatyr status
Explain this project to a new developer.
Review the architectural impact of this change.
Create or repair the project blueprint.
Update Alatyr from the selected framework source.
```

These are chat requests, not universal shell commands. Clear requests can
route to the relevant workflow; ambiguous or protected work needs clarification
or a preview and the required approval.

Inspecting, editing, committing, pushing, and live external actions have
separate authorization boundaries. A previous request to commit or push does
not authorize publication of a different task.

An update request includes assessing the selected framework source, adapting
the target, refreshing supporting indexes, and final validation. The assistant
reports acceptance or the exact blocker and next action; an assessment alone
is not a completed upgrade.

Working in several local sessions? Local session presence lets participating
assistants see each other's reported tasks and maintain short entries while
working. New accepted installations enable it by default; coordination becomes
active when multiple independent sessions report work. Existing opt-outs are
preserved. Linked worktrees share the registry, and each session removes its
own entry when finished. It is not a scheduler or an exclusive work lock.
See [session presence](framework/session-continuity.md#concurrent-session-presence).

The assistant-facing details, including validation coverage and the
transactional support finalizer, remain in [AI_ASSISTANTS.md](AI_ASSISTANTS.md)
and the [source tooling reference](tools/README.md). Installed request routing
is defined by [installed operations](framework/installed-operations.md) and
[operation help](framework/operation-help.md).

## Current Maturity And Limitations

The source [VERSION](VERSION) currently records `0.1.0-alpha.109`. Implemented assets
include framework contracts, target templates, assistant-driven installation
guidance, source checks, conformance fixtures, optional scaffolding, and an
optional installed-adapter validator.

Important limits:

- **Instructions are not enforcement.** Alatyr cannot guarantee that every
  assistant loads or follows every rule, or that a proposed change is correct.
- **Project facts need project authority.** Automated checks do not establish
  correct architecture or business behavior by themselves. Missing and
  conflicting sources still require investigation and decisions.
- **Assistant support needs evidence.** Bridge files and static checks do not
  prove identical behavior across clients. Each target must record what it
  has actually verified.
- **Performance benefits are not established broadly.** Lower onboarding
  effort, rework, supervision, and AI cost remain intended outcomes requiring
  wider field validation. Context estimates are not measured token savings,
  and caching benefits depend on the exact provider and client.
- **There is no complete runnable demonstration target here.** The
  [quick demo](docs/human/quick-demo.md) is a documentation-only walkthrough.
- **Optional modules create maintenance obligations.** Start small rather than
  treating more support files as evidence of better results.

The [evidence status](conformance/evidence-status.json) distinguishes
current-contract real-run coverage from prepared, stale, and historical
evidence. The full claim boundaries, including delegation and provider limits,
remain in [framework guarantees and limits](framework/guarantees.md).

## Documentation

Choose the detail you need:

- **Understand the concept:** [What is AlatyrCore?](docs/human/what-is-alatyr.md)
  and the [project guardian explanation](docs/human/project-guardian-concept.md).
- **Walk through a task:** [documentation walkthrough](docs/human/quick-demo.md).
- **Use it with a team:** [use cases](docs/human/team-use-cases.md) and
  [collaboration workflow](docs/human/team-collaboration-workflow.md).
- **Resolve common questions:** [FAQ](docs/human/faq.md).
- **Install or update:** [installation guide](INSTALL.md).
- **Check assistant support:** [compatibility guide](docs/assistant-compatibility.md).
- **Explore implementation:** [repository layout](docs/repository-layout.md),
  [source architecture](docs/source-architecture.md), and
  [tooling reference](tools/README.md).
- **Review contracts and evidence:** [framework index](framework/README.md),
  [task evidence validation](docs/task-evidence-validation.md),
  [release process](docs/release-process.md), and [changelog](CHANGELOG.md).

Human guides explain the product. Canonical policy remains owned by the
referenced framework documents and [rule registry](framework/rule-registry.md),
not by this README.

## For AI Assistants

Start with [AI_ASSISTANTS.md](AI_ASSISTANTS.md). It routes source maintenance,
installation, and installed-project work to the appropriate instructions and
canonical owners. This README is the human-facing overview, not an additional
operating contract.

<!--
Machine-checked assistant rule references are intentionally kept out of the
rendered human guide. Installation routing starts at installer/context-router.json
and framework/file-inventory.json.
Read only selected or changed canonical framework owners. Derived rules include
ALATYR-ADAPTER-001,
ALATYR-APPROVAL-001,
ALATYR-SAFETY-001, ALATYR-SAFETY-002, ALATYR-INTEGRITY-001,
ALATYR-DECOMPOSITION-001, ALATYR-EVIDENCE-001, ALATYR-OPERATION-001.
-->

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), and the
[framework maintenance guide](docs/framework-maintenance.md) before making
changes. Use the documented source checks; those commands validate AlatyrCore,
not every target project's runtime.

Security reports follow [SECURITY.md](SECURITY.md). Do not put credentials,
private project facts, or exploit details in public issues.
Use [pseudonymized case summaries](docs/external-case-pseudonyms.md) for external
project reviews; keep real identities and raw captures outside this repository.

For usage questions, start with the [FAQ](docs/human/faq.md). Report reproducible
non-sensitive problems in [GitHub issues](https://github.com/atvardovsky/AlatyrCore/issues),
including the Alatyr version, assistant, expected behavior, and sanitized evidence.

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
