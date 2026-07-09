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
- `framework/security-safety-guidance.md`
- `framework/diagram-guidance.md`
- `framework/testing-guidance.md`
- `framework/adapter-maturity.md`
- `framework/lifecycle.md`
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
- existing assistant bridge files, prompts, skills, gates, or checker rules

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
7. Add skills, prompts, diagrams, and deterministic checks only when useful
   for the target.
8. Run target validation that exists.
9. Report files changed, validation run, skipped checks, approvals, and
   residual risk.

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

