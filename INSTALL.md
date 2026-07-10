# Installing Alatyr Core With An Assistant

Alatyr Core is installed by assistant reasoning, not by an installer script.

The assistant receives this repository, reads the framework and installer
documents, inspects the target repository, writes an installation plan, and
then adapts the framework into the target.

## Source Bootstrap

Before planning an installation, read the source bootstrap:

- `README.md`
- `AGENTS.md`
- `AI_ASSISTANTS.md`
- `framework/README.md`
- `framework/context-profiles.md`
- `framework/project-adapter-contract.md`
- `framework/portability.md`
- `framework/module-profile.md`
- `framework/rule-ownership.md`
- `framework/rule-registry.md`
- `framework/rule-registry.json`
- `installer/assistant-installation.flow.md`
- `installer/readiness-checklist.md`
- `installer/installation-plan-template.md`

Then inspect the target repository and choose the smallest installation scope.
Read additional framework, installer, and target template files only when that
scope needs them. Read every framework file before copying or adapting it into
the target `.ai/framework`; full-core installations therefore read the full
`framework/*.md` set at the copy/adaptation stage, not as a default bootstrap.

## Rule References

Installation docs are derived routing surfaces. Canonical rule meanings live
in `framework/rule-registry.*` and `framework/rule-ownership.md`.

- Context routing: `ALATYR-CONTEXT-001`
- Source-of-truth ownership: `ALATYR-SOURCE-001`
- Risk classification: `ALATYR-RISK-001`
- Approval records and protected changes: `ALATYR-APPROVAL-001`
- Safety and imported-source handling: `ALATYR-SAFETY-001`,
  `ALATYR-SAFETY-002`
- Adapter separation: `ALATYR-ADAPTER-001`
- Module selection: `ALATYR-MODULE-001`
- Lifecycle and migration evidence: `ALATYR-LIFECYCLE-001`

## Target Repository Inspection

Before creating files in the target repository, inspect:

- existing AI instruction files
- existing CODEOWNERS or equivalent file-owner metadata
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
- framework version, adapter schema version, and template version
- adapter owner, backup owner, review cadence, and CODEOWNERS or equivalent
  owner map when the target supports file ownership metadata
- supported assistants
- context profiles needed for the target
- required core profile and optional modules needed for the target
- source-of-truth registry needs
- task-specific maturity and bridge capability needs
- optional scaffolding plan, if any
- migration diff, adapter output contract, AI infrastructure inventory report,
  and effectiveness report needs
- files to create, adapt, preserve, or skip
- framework core versus target adapter decisions
- target validation plan
- approvals needed
- unresolved facts and residual risk

## Approval Rule

Apply `ALATYR-APPROVAL-001` with the target adapter's approval policy.
Protected categories are classified through `ALATYR-RISK-001`,
`ALATYR-SAFETY-001`, and `ALATYR-SAFETY-002`.

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
2. Create or preserve `CODEOWNERS` or an equivalent owner map when the target
   repository uses file ownership metadata.
3. Create `.ai/alatyr.yaml` or an equivalent manifest.
4. Create `.ai/README.md` to explain target ownership contours.
5. Copy or adapt portable framework files into `.ai/framework`, including
   `framework/*.md` and `framework/rule-registry.json`.
6. Create `.ai/project/contour.md` and target project source-of-truth docs.
7. Create `.ai/assistant/contour.md`, context profiles, module profile,
   task-specific maturity profile, bridge capability matrix, and target
   assistant workflows/gates.
8. Add bridge files only for assistants the target uses.
9. Add installed-operation, operation-help, operation-routing,
   AI-infrastructure-inventory, adapter output contracts, source-access
   policy, prompt-injection policy, approval-record template,
   migration-note template, effectiveness-report template, blueprint-creation,
   adapter-recheck, and
   post-install/update chat-message templates when the target wants
   post-install operation requests or AI infrastructure adaptation.
10. Add skills, prompts, diagrams, and deterministic checks only when useful
   for the target, after adapting them to target rules and recording source or
   provenance when applicable.
11. Run target validation that exists.
12. Report files changed, validation run, skipped checks, approvals, and
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
permissions, prompt injection, safety, approval, and target normalization
before becoming canonical.

Alatyr Core does not provide a universal command or service for this. The
assistant must read the target adapter and use target evidence, approvals, and
validation.

## Optional Scaffolding

The AlatyrCore source repository may include helper tools such as
`tools/scaffold_target_structure.py`. Use them only as optional scaffolding
for placeholder files.

The scaffolder is Python-based and can be run on Linux, macOS, and Windows.
Windows users may use the provided Command Prompt or PowerShell wrappers under
`tools/`.

Scaffolding does not replace target inspection, installation planning,
approval gates, adapter rewriting, validation, logical integrity review, or
final evidence. Do not present a scaffolder run as a completed installation.

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
