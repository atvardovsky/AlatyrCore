# Installing Alatyr Core With An Assistant

Alatyr Core is installed by assistant reasoning, not by an installer script.

The assistant receives this repository, reads the framework and installer
documents, inspects the target repository, writes an installation plan, and
then adapts the framework into the target.

## Source Files To Read

Read these Alatyr Core files before planning an installation:

- `README.md`
- `AGENTS.md`
- `AI_ASSISTANTS.md`
- `framework/README.md`
- `framework/contour.md`
- `framework/guarantees.md`
- `framework/project-adapter-contract.md`
- `framework/portability.md`
- `framework/context-discovery.md`
- `framework/change-risk-model.md`
- `framework/logical-integrity.md`
- `framework/blueprint-driven-change.md`
- `framework/security-safety-guidance.md`
- `framework/diagram-guidance.md`
- `framework/testing-guidance.md`
- `framework/skill-adaptation.md`
- `framework/adapter-maturity.md`
- `framework/lifecycle.md`
- `framework/installed-operations.md`
- `framework/operation-help.md`
- `installer/assistant-installation.flow.md`
- `installer/readiness-checklist.md`
- `installer/installation-plan-template.md`
- `templates/target`

## Target Repository Inspection

Before creating files in the target repository, inspect:

- existing AI instruction files
- README and public docs
- architecture or design docs
- package/build files
- test folders and test conventions
- CI files and validation commands
- security, live-service, credential, and destructive-operation policies
- diagram sources, visual artifacts, and generated files
- skills, prompts, third-party assistant infrastructure, and provenance notes
- existing assistant bridge files, prompts, skills, gates, checker rules,
  source-access policies, operation help, routing, or chat-completion message
  templates

If a target fact is missing, mark it as missing. Do not invent it.

## Planning Rule

Prepare an installation plan using
`installer/installation-plan-template.md`.

The plan must identify:

- target repository profile
- supported assistants
- files to create, adapt, preserve, or skip
- framework core versus target adapter decisions
- target validation plan
- approvals needed
- unresolved facts and residual risk

## Approval Rule

Explicit programmer approval is required before:

- overwriting existing target AI instructions
- changing target project architecture
- changing accepted business behavior
- weakening existing target gates or approval rules
- adding production dependencies or external services
- enabling live, destructive, or spend-affecting side effects
- integrating third-party assistant infrastructure into canonical target files

Preferred approval format:

```text
APPROVE ALATYR INSTALLATION: <installation-id>
```

Fresh installations that do not overwrite existing target instructions and do
not touch protected target behavior may be applied after the plan when the
programmer explicitly asked for installation.

## Installation Shape

In a typical target repository:

1. Create or adapt `AGENTS.md` and `AI_ASSISTANTS.md`.
2. Create `.ai/README.md` to explain target ownership contours.
3. Copy or adapt `framework/*.md` into `.ai/framework`.
4. Create `.ai/project/contour.md` and target project source-of-truth docs.
5. Create `.ai/assistant/contour.md` and target assistant workflows/gates.
6. Add bridge files only for assistants the target uses.
7. Add installed-operation, operation-help, operation-routing,
   AI-infrastructure-inventory, source-access policy, blueprint-creation,
   adapter-recheck, and post-install/update chat-message templates when the
   target wants post-install operation requests or AI infrastructure
   adaptation.
8. Add skills, prompts, diagrams, and deterministic checks only when useful
   for the target, after adapting them to target rules and recording source or
   provenance when applicable.
9. Run target validation that exists.
10. Report files changed, validation run, skipped checks, approvals, and
   residual risk.

## Post-Install Operations

After installation, use
`installer/installed-operation-request-template.md` when asking an assistant to
operate the installed target adapter. Typical requests include blueprint
creation or repair, adapter recheck after framework updates, drift review,
blueprint-driven product changes, and skill adaptation. Include Allowed actions
when the request should be limited to `read-only`, `docs-only`,
`adapter-only`, `code-and-tests`, or `full-with-approval`.

If the programmer asks for help, commands, or an unclear Alatyr action, the
assistant should show the installed operation menu from the target adapter
instead of guessing or inventing a CLI command.

If the programmer asks for `alatyr-ai-inventory`, inspect existing AI
infrastructure before adding anything. If the programmer asks for
`alatyr-adaptation <source>`, `alatyr-add-ai <source>`, or a similar target
alias, treat it as an adaptation request. The source may be a local path, Git
URL, HTTPS URL, assistant-native reference, package/plugin reference, or pasted
content, but it must be reviewed for existing conflicts, provenance,
permissions, safety, approval, and target normalization before becoming
canonical.

Alatyr Core does not provide a universal command or service for this. The
assistant must read the target adapter and use target evidence, approvals, and
validation.

## Rejection Criteria

Reject or stop when:

- the assistant has not inspected the target repository
- the plan copies project facts from another repository
- the plan copies source commands, scripts, CI jobs, test folders, fixtures,
  security policies, diagram tooling, lifecycle notes, or adapter owner facts
  as framework core
- target adapter files contain placeholders after the assistant claims
  installation is complete
- existing target AI instructions would be overwritten without approval
- target validation is claimed without evidence
