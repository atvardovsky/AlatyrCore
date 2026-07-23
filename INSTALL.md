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
- `framework/context-router.md`
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
- Installed operation control surface: `ALATYR-OPERATION-001`
- Optional team collaboration: `ALATYR-TEAM-001`
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
- existing team roles and decision authority, priority policy, task tracker,
  active work, claims, branch/worktree conventions, review requirements,
  handoffs, decision records, merge policy, retention, and privacy rules

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
- context router and context profiles needed for the target
- large-task task-scale routing, packet, checkpoint, and storage needs
- optional team-collaboration owner, coordination backend, synchronization
  direction, actor/authority/priority evidence, registry, conflict, handoff,
  decision, review, storage, retention, and privacy needs
- required core profile and optional modules needed for the target
- source-of-truth registry needs
- optional consistency-map need, fact-ID strategy, relationship coverage, and
  staleness owner
- task-specific maturity and bridge capability needs
- optional scaffolding plan, if any
- migration diff, adapter output contract, AI infrastructure inventory and
  recommendation reports, and effectiveness report needs
- AI infrastructure router/item, recommendation, and adaptation-record needs
- target development-evidence index, owner, retention/privacy policy, and lazy
  capture needs when recommendations should learn from recurring project work
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

When approval is scoped to files or a reusable plan, create an explicitly
selected machine-readable record from
`.ai/assistant/approvals/approval-record-template.json`. Bind it to the
approved Git diff base and verify the complete changed path set before final
evidence.

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
   When AI recommendations should use cross-task patterns, add the compact
   `.ai/project/development-evidence.json` index with target owner and retention
   policy. Do not seed it with guessed history or raw conversations.
   Add `.ai/project/consistency-map.json` only when bounded relationship
   routing is enabled and target evidence can support it.
   Add `.ai/project/team-operating-model.md` only when team collaboration is
   enabled, and derive actors, authority, priorities, review, backend,
   retention, and privacy from target evidence.
7. Create `.ai/assistant/contour.md`, context router, operation catalog,
   context profiles, module profile, task-specific maturity profile, bridge
   capability matrix, and target assistant workflows/gates. Keep the catalog
   outside routine bootstrap and expose compact operation candidates through
   the router.
   When team collaboration is enabled, route `team-active` through
   `.ai/assistant/team/context-overlay.json` and keep team state outside
   routine bootstrap.
8. Add bridge files only for assistants the target uses.
9. Add installed-operation, operation-help, automatic operation-routing,
   read-only adapter-health, risk-gated pre-change preview,
   AI-infrastructure-inventory, AI-infrastructure-recommendation, adapter output contracts, source-access
   policy, prompt-injection policy, human and machine-readable approval-record
   templates,
   migration-note template, effectiveness-report template, blueprint-creation,
   adapter-recheck, large-task orchestration and operation-packet templates,
   and
   post-install/update chat-message templates when the target wants
   post-install operation requests or AI infrastructure adaptation.
   Add the AI infrastructure router, recommendation flow/report, and
   adaptation-record template when the target needs routed item selection,
   evidence-based suggestions, or imported-item provenance evidence. Add the
   lazy development-evidence capture flow with the pattern index; target
   evidence must not directly change `.ai/framework` or portable rules.
   When team collaboration is enabled, add the work registry, task/handoff/
   decision/review flows, team gate, and checkpoint/handoff/decision
   templates. Initialize the registry empty unless active target tasks are
   explicitly reviewed; never overwrite active records from source templates.
10. Add skills, prompts, diagrams, and deterministic checks only when useful
   for the target, after adapting them to target rules and recording source or
   provenance when applicable. Route AI infrastructure through target item IDs
   and keep unresolved permissions, gates, validation, or output contracts
   blocked.
11. Run target validation that exists.
12. Report files changed, validation run, skipped checks, approvals, and
   residual risk.

## Post-Install Operations

After installation, use
`installer/installed-operation-request-template.md` when asking an assistant to
operate the installed target adapter. Typical requests include blueprint
creation or repair, adapter recheck after framework updates, drift review,
blueprint-driven product changes, team coordination, AI infrastructure
recommendation, and skill adaptation. Include Allowed actions
when the request should be limited to `read-only`, `docs-only`,
`adapter-only`, `code-and-tests`, or `full-with-approval`.

If the programmer asks for help, commands, or an unclear Alatyr action, the
assistant should show the installed operation menu from the target adapter
instead of guessing or inventing a CLI command.

The target should accept `Alatyr` as one conversational entry point,
`Alatyr status` or `Alatyr doctor` as a read-only health request, and ordinary
clear development requests without requiring an operation ID. Route from the
machine-readable operation catalog and enabled module profile. Show a bounded
pre-change preview only when changed-fact risk, protected scope, boundary
crossing, external effects, or unclear allowed actions require it; a preview
does not grant approval.

When the target enables team collaboration, aliases such as `Alatyr team
status`, `Alatyr start`, `Alatyr claim`, `Alatyr conflicts`, `Alatyr
checkpoint`, `Alatyr handoff`, `Alatyr decision`, `Alatyr discuss`, `Alatyr
review`, `Alatyr merge check`, and `Alatyr release` route through target-owned
team evidence. Team status, conflicts, review, and merge check remain
read-only. Installation or update must preserve active task IDs, claims,
handoffs, decisions, and external tracker references.

If the programmer asks for `alatyr-ai-inventory`, inspect existing AI
infrastructure before adding anything. If the programmer asks for
`alatyr-suggest-ai <scope>` or `alatyr-improve-ai <item-id>`, compare bounded
project-contour evidence with relevant existing items in read-only mode before
proposing additions or changes. If the programmer asks for
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

## Optional Migration-First Upgrade Assessment

Before changing an installed adapter, a maintainer may generate source
migration and current-state structural evidence into an explicit scratch
directory:

```sh
python3 tools/alatyr.py assess-upgrade --target /path/to/target-repo --framework-source . --output-dir tmp/upgrade-assessment
```

On Windows use `tools\alatyr.cmd` or `tools\alatyr.ps1` with the same command
arguments. The assessment does not install or update Alatyr. Review its changed
rules, canonical sources, target surfaces, local deviations, and validation
findings first; then prepare a target migration note and approval scope. Load
only the affected context before applying approved changes separately.

## Optional Target Adapter Validation

After installation or update, a maintainer may use the source helper
`tools/validate_target_adapter.py` to check an installed target adapter for
machine-detectable structural drift:

```sh
python3 tools/validate_target_adapter.py --target /path/to/target-repo
python3 tools/validate_target_adapter.py --target /path/to/target-repo --framework-source /path/to/AlatyrCore
python3 tools/validate_target_adapter.py --target /path/to/target-repo --json --output tmp/alatyr-adapter-report.json
python3 tools/validate_target_adapter.py --target /path/to/target-repo --diff-ref origin/main --approval-record .ai/assistant/approvals/change-approval.json --enforce-approval-scope
python3 tools/validate_target_adapter.py --target /path/to/target-repo --framework-source /path/to/AlatyrCore --migration-diff /path/to/migration-report.md
```

Windows users may run the same helper through `py -3` or the provided
Command Prompt and PowerShell wrappers under `tools/`.

This validator can check router/bootstrap references, consistency-map and AI
infrastructure router contracts when present, unresolved placeholders,
absolute local path leakage, stale checker claims, manifest fields,
target-local checker coverage, advisory legacy approval scope, and strict
complete changed-path enforcement through explicitly selected JSON records
bound to a supplied Git diff. It also checks optional framework baseline drift
and migration-diff evidence when supplied. Its JSON is current-state structural evidence, not
proof of historical actions. It does not inspect target business truth,
approve protected changes, replace target validation, or replace assistant
logical integrity review.

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
