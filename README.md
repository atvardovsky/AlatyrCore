# Alatyr Core

Alatyr Core is a Markdown-first AI assistant framework for software
repositories.

It gives an assistant a portable way to work on a project without guessing:
load the right context, separate framework rules from project facts, classify
risk, request approval for protected changes, keep documentation synchronized,
and report evidence.

Alatyr Core is not tied to PHP, Symfony, Node, Python, Go, Java, a database,
or a specific assistant vendor.

## Why This Exists

AI agents are good at producing local code changes, but weak at preserving
system-wide consistency unless the repository gives them a process. Alatyr Core
turns AI-assisted work into a controlled change pipeline: context discovery,
risk classification, logical integrity review, blueprint-driven update,
validation, and final evidence.

## If You Are An AI Assistant

If a programmer gives you this repository and asks you to install Alatyr Core
into another project, do this:

1. Read this `README.md`, `AGENTS.md`, `INSTALL.md`, `framework/README.md`,
   `framework/contour.md`, `framework/guarantees.md`,
   `framework/project-adapter-contract.md`, `framework/portability.md`,
   `framework/context-discovery.md`, `framework/change-risk-model.md`,
   `framework/logical-integrity.md`,
   `framework/blueprint-driven-change.md`,
   `framework/security-safety-guidance.md`,
   `framework/diagram-guidance.md`, `framework/testing-guidance.md`,
   `framework/skill-adaptation.md`, `framework/adapter-maturity.md`,
   `framework/lifecycle.md`, `framework/installed-operations.md`,
   `framework/operation-help.md`, `installer/assistant-installation.flow.md`,
   `installer/readiness-checklist.md`, and
   `installer/installation-plan-template.md`.
2. Inspect the target repository before creating files.
3. Identify existing AI instructions, project docs, tests, commands, CI,
   diagrams, security policy, generated files, and assistant bridge files.
4. Create an installation plan from
   `installer/installation-plan-template.md`.
5. Separate portable framework core from target project adapter facts.
6. Copy or adapt `framework/*.md` into the target repository's
   `.ai/framework`.
7. Rewrite target adapter files from the target repository, using
   `templates/target` only as placeholders.
8. Do not copy Alatyr Core source-repository commands, tool assumptions,
   target facts from another project, security policies, diagram tooling, or
   lifecycle notes as framework core.
9. Ask for explicit programmer approval before overwriting existing target AI
   instructions, changing target architecture or business behavior, weakening
   gates, adding dependencies, or enabling live/destructive side effects.
10. Run only target validation that exists in the target repository. If a check
    is unknown or unavailable, report it as unresolved instead of inventing a
    command.

For details, use [INSTALL.md](INSTALL.md). For a copyable installation prompt,
use
[installer/assistant-request-template.md](installer/assistant-request-template.md).
For post-install work in a target repository that already has Alatyr Core, use
[installer/installed-operation-request-template.md](installer/installed-operation-request-template.md).

## Repository Layout

- `framework/`: portable Alatyr Core framework documents. These are the core
  files an assistant adapts into a target `.ai/framework` directory.
- `installer/`: assistant-readable installation flow, readiness checklist,
  installation plan template, assistant request template, and installed
  operation request template.
- `templates/target/`: starter files for a target repository adapter. These
  files contain placeholders and must be rewritten from target facts.
- `docs/`: public explanation for maintainers and assistant compatibility.
- `tools/`: source-repository maintenance checks for Alatyr Core itself.
- `AGENTS.md`: canonical instructions for assistants working on Alatyr Core
  itself.
- `AI_ASSISTANTS.md`: generic assistant entry point.

## Self-Application Notes

Alatyr Core can be used to review this source repository, but generated target
adapter output from that exercise is scratch material.

Use ignored local paths such as `tmp/` or root-local assistant adapter paths
when drafting self-installation plans, trial `.ai` trees, or bridge files.
Promote reusable findings by editing the canonical source files under
`framework/`, `installer/`, `templates/target/`, `docs/`, or the root docs
instead of committing generated self-installation output.

For Alatyr Core source-repository maintenance, run
`python3 tools/check_framework_consistency.py` when available. This helper is
not a portable validation requirement for target projects.

## What Alatyr Core Provides

- framework/project/repository-adapter contour separation
- context discovery and source-of-truth decisions
- semantic change decision
- first-class logical integrity review
- blueprint-driven product-change workflow
- change-risk classification and approval triggers
- documentation-sync and final-evidence patterns
- stack-aware testing guidance without hard-coded commands
- security/safety reasoning without hard-coded policies
- diagram guidance without hard-coded diagram tooling
- AI infrastructure inventory and third-party skill/assistant-infrastructure
  adaptation guidance
- adapter maturity and lifecycle guidance
- installed-adapter operation and recheck guidance
- operation help and routing guidance for unclear requests
- bridge-file pattern for modern assistants

## What Alatyr Core Does Not Provide

- project business rules
- project architecture facts
- local commands, scripts, package managers, CI jobs, hooks, or test tools
- project-specific security policy, live-service allowlists, dependency
  scanners, diagram formats, render commands, or lifecycle notes
- a universal installer script

All of those belong to the target project or its repository adapter.

## Installation Summary

Alatyr Core is installed by an assistant, not by a script.

The assistant reads this repository, inspects the target repository, writes an
installation plan, and then creates or updates target files according to the
plan. Fresh installs can usually proceed after the plan when the programmer has
asked for installation and no protected target files or behaviors are changed.
Overwrites and protected changes require explicit programmer approval.

## After Installation

After Alatyr Core is installed in a target repository, programmers can ask an
assistant to use the installed adapter for follow-up operations: creating or
repairing project blueprints, rechecking the adapter after a framework update,
reviewing drift, running blueprint-driven product changes, or adapting skills
and prompts.

Use
[installer/installed-operation-request-template.md](installer/installed-operation-request-template.md)
for a copyable post-install request. This is still assistant reasoning over
Markdown files, not a universal Alatyr command or runtime service. The request
can bound the assistant with `Allowed actions`, such as `read-only`,
`docs-only`, `adapter-only`, `code-and-tests`, or `full-with-approval`.

If the intended operation is unclear, ask for "Alatyr help". A complete target
adapter should answer with the local operation menu, short descriptions,
matching flows, required input, and approval or validation notes before making
changes.

For skills, prompts, wrappers, bridge files, rules, MCP/tool configs, gates,
checkers, or other AI infrastructure, a target adapter may define request
aliases such as `alatyr-ai-inventory`, `alatyr-adaptation <source>`, or
`alatyr-add-ai <source>`. These aliases are chat/request shortcuts, not shell
commands. Sources can be local paths, Git URLs, HTTPS URLs, assistant-native
references, packages/plugins, or pasted content, but existing infrastructure,
provenance, permissions, safety, and approval are reviewed before anything
becomes canonical.

## Suggested Target Shape

A mature target installation usually has:

- `AGENTS.md`
- `AI_ASSISTANTS.md`
- `.ai/README.md`
- `.ai/framework/*.md`
- `.ai/project/contour.md`
- `.ai/project/context` or equivalent project source-of-truth docs
- `.ai/assistant/contour.md`
- `.ai/assistant/help.md`
- `.ai/assistant/flows`
- `.ai/assistant/gates/checklist.md`
- `.ai/assistant/policies/ai-infrastructure-source-access.md` when AI
  infrastructure can be inventoried or adapted
- `.ai/assistant/templates/operation-request.md`
- `.ai/assistant/templates/post-install-message.md`
- `.ai/assistant/templates/post-update-message.md`
- optional skills, prompts, bridge files, diagrams, and consistency checks

The target adapter decides actual validation commands and supported assistant
bridges.
