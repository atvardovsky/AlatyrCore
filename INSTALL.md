# Installing Alatyr Core With An Assistant

Alatyr Core is installed by assistant reasoning, not by an installer script.

The assistant receives this repository, reads the framework and installer
documents, inspects the target repository, writes an installation plan, and
then adapts the framework into the target.

## Source Bootstrap

Treat root `AGENTS.md` as preloaded, then read
`installer/context-router.json` and the three source version files. Use the
router to select the current installation stage before opening installer,
framework, or template prose. Inspect the target repository before selecting
optional modules or creating files.

Use `framework/file-inventory.json` to identify and hash unchanged framework
files. Copying an unchanged file does not require loading its prose. Read only
the canonical owners and target templates selected by the installation scope,
changed facts, approval triggers, or failed validation.

## Rule References

Installation docs are derived routing surfaces. Canonical rule meanings live
in the owner document named by each entry in `framework/rule-registry.json`.
`framework/rule-ownership.md` is a generated routing map, not an independent
semantic owner.

- Context routing: `ALATYR-CONTEXT-001`
- Source-of-truth ownership: `ALATYR-SOURCE-001`
- Risk classification: `ALATYR-RISK-001`
- Approval records and protected changes: `ALATYR-APPROVAL-001`
- Current-scope action authorization: `ALATYR-AUTHORIZATION-001`
- Safety and imported-source handling: `ALATYR-SAFETY-001`,
  `ALATYR-SAFETY-002`
- Adapter separation: `ALATYR-ADAPTER-001`
- Module selection: `ALATYR-MODULE-001`
- Installed operation control surface: `ALATYR-OPERATION-001`
- Optional architecture knowledge and pattern discussion:
  `ALATYR-ARCHITECTURE-001`
- Optional project vocabulary and terminology lookup:
  `ALATYR-VOCABULARY-001`
- Optional target-adapted test-first development: `ALATYR-TDD-001`
- Optional externally sourced extensions: `ALATYR-EXTENSION-001`
- Optional passive dependency knowledge: `ALATYR-DEPENDENCY-001`
- Discussion diagram presentation: `ALATYR-DIAGRAM-001`
- Optional team collaboration: `ALATYR-TEAM-001`
- Lifecycle and migration evidence: `ALATYR-LIFECYCLE-001`

## Target Repository Inspection

Before creating files in the target repository, inspect:

- existing AI instruction files
- existing CODEOWNERS or equivalent file-owner metadata
- README and public docs
- architecture or design docs, decision records, documented patterns,
  boundaries, constraints, quality attributes, and architecture validation
- glossaries, terminology docs, acronym lists, data dictionaries, schemas,
  APIs, naming rules, ambiguous terms, and terminology validation
- package/build files
- test folders and test conventions
- test-first/TDD policy, defect and regression patterns, test levels, commands,
  fixtures, isolation, exceptions, feedback time, CI, and merge requirements
- CI files and validation commands
- security, live-service, credential, and destructive-operation policies
- diagram sources, visual artifacts, and generated files
- skills, prompts, third-party assistant infrastructure, and provenance notes
- existing extension package manifests, extension catalog and lock records,
  installed-file ownership, source revisions, digests, bindings, and lifecycle
  evidence
- package-manager manifests and lockfiles, native metadata for passive Alatyr
  dependency exports, local patches/forks/workspaces, dependency knowledge
  ownership, retention, trust, applicability, and validation policy
- existing assistant bridge files, prompts, skills, gates, checker rules,
  source-access policies, operation help, routing, or chat-completion message
  templates
- existing team roles, stable IDs, names/aliases and identity mappings,
  decision authority, priority/transition policy, task backend, active work,
  claims, branch/worktree conventions, atomic-write behavior, review,
  handoffs, decisions, merge policy, retention, and privacy rules

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
- current logical installation scope and whether the user authorized inspect,
  modify, commit, publish, or live-external phases; installation approval and
  protected-change approval do not imply Git publication
- generated bootstrap index, compact context router, routed gate fragments,
  selected lazy profile descriptors, and human context profiles needed for
  the target
- large-task task-scale routing, packet, checkpoint, and storage needs
- worker launch/model-selection support, target delegation policy, role
  catalog, orchestration prompt, task-plan and result contracts, native worker
  definition paths, write isolation, retry/conflict fallback, privacy, and
  validation needs
- optional team-collaboration owner, structured actor/authority/priority policy,
  local identity and verification boundary, coordination backend capabilities,
  synchronization and write-conflict behavior, active-work preflight, per-task
  storage, conflict, handoff, decision, review, retention, and privacy needs
- required core profile and optional modules needed for the target
- optional Debug Mode need, owner, explicit task/session activation and expiry,
  non-canonical storage, privacy/retention, versioned actor/causality/
  intervention/contribution attribution, structured
  architectural impacts, direction-change hypothesis/replacement causality,
  timing evidence, supervision metrics, exact durable engineering-evidence
  decision/reference resolution, repository-binding state/lineage, active-
  versus-finalized comparison, and clean-upstream projection policy
- source-of-truth registry needs
- optional consistency-map need, fact-ID strategy, relationship coverage, and
  staleness owner
- optional architecture-knowledge owner, compact catalog, pattern/area docs,
  evidence revision, decision authority, and validation needs
- optional code-documentation owner, bounded source-set profiles, existing
  frontend/backend/shared/infrastructure conventions, style proposal and
  acceptance evidence, canonical fact-owner boundaries, generator,
  output/publication policy, validation, and adapted skill needs
- optional project-vocabulary owner, decision authority, compact catalog,
  scoped term records, aliases, acronyms, ambiguity, normalization policy,
  data-dictionary links, validation, and adapted skill needs
- optional test-first owner, authority, module state, recommendation behavior,
  activation triggers, modes, levels, commands, isolation, exceptions,
  RED/GREEN/refactor evidence, validation, and adapted skill needs
- optional extensions need, owner, source-access policy, catalog and lock,
  immutable source and digest evidence, compatibility, target bindings,
  permissions, approval, installed-file ownership, update, and removal needs
- optional dependency-knowledge need, owner, selected package ecosystems and
  lockfiles, native export discovery, exact artifact identity, trust and
  semantic state, target deviations, retention, bounded graph routing,
  synchronization, explanation, impact, and validation needs
- optional workspace-mode need, workspace identity, active adapter, proposed
  application/framework/library/skeleton/dependency/workspace perspectives,
  shared root support, per-mode context, user decision authority, selection
  ambiguity, maintenance cost, and validation needs
- task-specific maturity and bridge capability needs
- diagram discussion, source/visual ownership, portable ASCII layout/width,
  per-assistant rich presentation, capability expiry/review triggers, captured-result
  evidence, and stale-view evidence needs
- optional scaffolding plan, selected `core`, `standard`, or `full` support
  profile, and explicit dependency-closed `--enable-module` set, if any
- matching `core`, `standard`, or `complete` framework pack, including any
  enabled-module expansion that the smallest matching pack does not cover
- migration diff, adapter output contract, AI infrastructure inventory and
  recommendation reports, and effectiveness report needs
- Debug Mode index/record, overlay, operation, flow, gate, summary, target
  validator, structured classification and durable evidence reference checks,
  and post-install/update guidance needs when the module is selected
- AI infrastructure router/item, recommendation, and adaptation-record needs
- target development-evidence index, owner, retention/privacy policy, and lazy
  capture needs when recommendations should learn from recurring project work
- durable engineering-evidence owner, retained storage and redaction policy,
  external-contribution boundary, compact index, lazy capture, versioned
  binding state/lineage, and validation
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
For an activated change package, also record allowed fact IDs, architecture
areas, behavior categories, excluded semantic effects, and permitted external
effects. Reapproval is required for protected semantic or path expansion.

## Installation Shape

In a typical target repository:

1. Create or adapt `AGENTS.md` and `AI_ASSISTANTS.md`.
2. Create or preserve `CODEOWNERS` or an equivalent owner map when the target
   repository uses file ownership metadata.
3. Create `.ai/alatyr.yaml` or an equivalent manifest.
4. Create `.ai/README.md` to explain target ownership contours.
5. Copy or adapt the selected portable framework pack into `.ai/framework`.
   Record `framework.pack` in the manifest. Preserve the pack-projected rule
   registry, ownership map, and file inventory; use `complete` when all
   `framework/*.md` and JSON files are installed.
6. Create `.ai/project/contour.md` and target project source-of-truth docs.
   Always create `.ai/project/engineering-evidence/README.md` and `index.json`
   for the required core capture decision. Resolve the target owner, retained
   storage mode, redaction policy, external-contribution boundary, and access
   path. Start empty unless bounded historical records were explicitly
   validated.
   When AI recommendations should use cross-task patterns, add the compact
   `.ai/project/development-evidence.json` index with target owner and retention
   policy. Do not seed it with guessed history or raw conversations.
   Add `.ai/project/consistency-map.json` only when bounded relationship
   routing is enabled and target evidence can support it.
   Add `.ai/project/architecture/README.md` and
   `.ai/project/architecture/catalog.json` only when architecture knowledge is
   enabled. Derive states and evidence from the target; do not infer accepted
   architecture from implementation frequency.
   Add `.ai/project/vocabulary/README.md`, `catalog.json`, `terms.json`, and
   `data-dictionary-links.json` only when project vocabulary is enabled.
   Derive records from target evidence, preserve scoped meanings, and keep
   observed or proposed terms unaccepted until target authority decides.
   Add `.ai/project/testing/README.md` and `test-first-policy.json` only when
   test-first development is assessed or enabled. Enabling requires accepted
   target commands, triggers, modes, isolation, exceptions, and evidence; do
   not infer strict TDD from the existence of tests.
   Add `.ai/project/team-policy.json` and its human-oriented
   `.ai/project/team-operating-model.md` only when team collaboration is
   enabled. Derive actors, aliases, authority, priorities, review, transitions,
   backend, identity verification, retention, and privacy from target evidence.
   Add `.ai/project/workspace-modes/catalog.json`, optional shared root
   support, and one directory per actual mode only when workspace roles require
   distinct context. Propose zero or more evidence-bound modes after
   inspection, but keep them proposed until a separate user decision accepts
   them. Installation approval is not mode acceptance.
7. Create `.ai/assistant/contour.md`, a generated hash-bound bootstrap index,
   compact context router, routed gate index/fragments, and selected lazy
   profile descriptors, operation catalog and its checked compact index,
   context profiles, module profile, task-specific maturity profile, bridge
   capability matrix, generated assistant-capability index and installed-
   surface records, and target workflows/gates. Keep the catalog outside routine
   routing and resolve exact aliases through the compact index.
   When team collaboration is enabled, route `team-active` through
   `.ai/assistant/team/context-overlay.json`. Check only the compact active-work
   index before state-changing operations and keep full team state outside
   routine bootstrap.
   When change packages are enabled, add the lazy `change-package` overlay and
   compact index; do not load package records for ordinary tasks.
   Add the `extension-request` intent overlay when extension inspection or
   lifecycle management is supported. Keep extension items and unrelated lock
   entries outside routine bootstrap.
8. Add bridge files only for assistants the target uses.
9. Add installed-operation, operation-help, automatic operation-routing,
   read-only adapter-health, risk-gated pre-change preview,
   diagram-discussion flow, ASCII layout template, and presentation template
   when the diagrams module is enabled,
   architecture-assistance flow, pattern/area/result templates, and lazy
   architecture intent routing when architecture knowledge is enabled,
   test-first configuration/change flows, policy intent, gate, evidence
   template, and adapted skill when test-first development is enabled or under
   explicit configuration review,
   extension catalog and lock, lifecycle flow, gate, review and lifecycle
   templates when optional extensions are supported,
   workspace-mode catalog, root descriptor, per-mode authoring template,
   intent, flow, gate, suggestion, preflight, and operation when optional
   workspace modes are enabled,
   AI-infrastructure-inventory, AI-infrastructure-recommendation, adapter output contracts, source-access
   policy, prompt-injection policy, human and machine-readable approval-record
   templates,
   migration-note template, effectiveness-report template, blueprint-creation,
   adapter-recheck, large-task orchestration and operation-packet templates,
   subagent delegation policy, worker role catalog/prompts, delegated-
   execution overlay, flow, native-binding authoring, execution-plan, packet,
   and normalized-result templates when delegation is enabled,
   change-package flow, machine record, redacted report, and index when coherent
   material-change evidence is needed,
   durable engineering-evidence task-scale overlay, capture flow, gate, and
   machine record template and contract version as lazy required-core
   finalization surfaces,
   optional Debug Mode project index/records, task-scale overlay, operation,
   flow, gate, machine record, compact summary, structured architectural-
   impact classification, versioned attribution, hypothesis replacement chain,
   durable evidence decision/reference checks, and repository-binding lineage
   when selected with its dependency closure,
   and
   post-install/update chat-message templates when the target wants
   post-install operation requests or AI infrastructure adaptation.
   Add the AI infrastructure router, recommendation flow/report, and
   adaptation-record template when the target needs routed item selection,
   evidence-based suggestions, or imported-item provenance evidence. Add the
   lazy development-evidence capture flow with the pattern index; target
   evidence must not directly change `.ai/framework` or portable rules.
   When team collaboration is enabled, add `.ai/.gitignore`, registry metadata,
   compact active-work index, backend contract, task-record template, identity/
   task/handoff/decision/review flows, team gate, adapted skill, and identity/
   checkpoint/handoff/decision templates. Initialize task storage and the index
   empty unless active target tasks are explicitly reviewed. Never overwrite
   active records or copy a local actor selection from source templates.
10. Add skills, prompts, diagrams, and deterministic checks only when useful
   for the target, after adapting them to target rules and recording source or
   provenance when applicable. Route AI infrastructure through target item IDs
   and keep unresolved permissions, gates, validation, or output contracts
   blocked.
11. Run target validation that exists.
12. Apply the durable engineering-evidence decision. Capture reusable material
   installation knowledge when triggered and authorized, or report a specific
   skip/block reason.
13. If Debug Mode is enabled for the installation operation by an explicit
   current-scope request, capture only normalized material events and finalize
   or expire that record. Module installation alone does not activate it.
14. Report files changed, validation run, skipped checks, approvals, and
   residual risk.

## Post-Install Operations

After installation, use
`installer/installed-operation-request-template.md` when asking an assistant to
operate the installed target adapter. Typical requests include blueprint
creation or repair, adapter recheck after framework updates, drift review,
blueprint-driven product changes, architecture and pattern discussion, diagram
discussion, team coordination, AI infrastructure recommendation, and skill
adaptation, extension inspection and lifecycle management, or explicit Debug
Mode activation/status/finalization/comparison. Include Allowed actions
when the request should be limited to `read-only`, `docs-only`,
`adapter-only`, `code-and-tests`, or `full-with-approval`.

If the programmer asks for help, commands, or an unclear Alatyr action, the
assistant should show the installed operation menu from the target adapter
instead of guessing or inventing a CLI command.

The target should accept `Alatyr` as one conversational entry point,
`Alatyr status` or `Alatyr doctor` as a read-only health request, and ordinary
clear development requests without requiring an operation ID. Route exact IDs
and aliases from the compact operation index; use the full machine-readable
catalog and module profile only for ambiguity or repair. Show a bounded
pre-change preview only when changed-fact risk, protected scope, boundary
crossing, external effects, or unclear allowed actions require it; a preview
does not grant approval.

When workspace modes are enabled, aliases such as `Alatyr modes`, `Alatyr
suggest modes`, `Alatyr mode <id>`, `Alatyr define mode`, and `Alatyr accept
mode <id>` route through the canonical workspace-mode operation. Suggestions
remain proposed. A selected mode can narrow context and actions but cannot
activate nested adapters or grant approval, write scope, permissions,
authority, tools, or gate bypass.

When Debug Mode is enabled, `Enable Alatyr Debug Mode for this task` starts one
explicit task-local record; `Alatyr debug status`, `Alatyr debug checkpoint`,
`Alatyr debug summary`, `Disable Alatyr Debug Mode`, and `Alatyr compare debug`
route through the canonical operation catalog. Activation grants only allowed
debug evidence writes and expires with the logical scope. It never authorizes
implementation, commit, push, publication, or live effects.

When the target enables subagent delegation, the assistant may keep its
critical-path action and dispatch bounded independent sidecars under the target
policy. Installation must record per-surface capability freshness, role/model
bindings, exact client/runtime, explicit/automatic dispatch, project worker-
definition format and paths, write and tool limits, background/nested behavior,
retry/conflict fallback, privacy, validation, and primary convergence. Create
provider-native worker definitions only for a verified supported target
surface. Keep them as thin bindings to the target-owned policy, role prompt,
packet, result, and validation. An unavailable requested model falls back; it
is never silently reported as used.

When the target enables diagrams, `Alatyr diagram`, `show as a diagram`, and
equivalent target-language requests route to `diagram-discussion`. Installation
must always provide the portable ASCII baseline and record each supported
assistant's native-inline syntax and artifact-presentation capability, client
version, verification time, expiry or review triggers, and evidence in its
indexed surface record. It must also define classification,
redaction, external-renderer, artifact storage/retention, stable diagram ID,
and revision-lineage behavior rather than assuming one client behavior for all
surfaces.

When the target enables architecture knowledge, `Alatyr architecture` and
equivalent inventory, explain, discuss, compare, review, or document requests
route to `architecture-assistance`. Installation must record the architecture
owner, decision authority, canonical sources, compact catalog, item states,
evidence revision, validation, and known gaps. Observed code is not accepted
architecture without target decision evidence.

When the target enables team collaboration, aliases such as `Alatyr team
status`, `Alatyr set actor`, `Alatyr who am I`, `Alatyr clear actor`, `Alatyr
start`, `Alatyr claim`, `Alatyr conflicts`, `Alatyr
checkpoint`, `Alatyr handoff`, `Alatyr decision`, `Alatyr discuss`, `Alatyr
review`, `Alatyr merge check`, and `Alatyr release` route through target-owned
team evidence. Team status, who-am-I, conflicts, review, and merge check remain
read-only. Local actor selection is ignored attribution, not authentication or
authority. Installation or update must preserve active task IDs, claims,
handoffs, decisions, external tracker references, and local identity without
committing it. Migrate schema-1 task arrays atomically into schema-2 per-task
records and generate the compact active-work index before replacing registry
metadata.

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

The selected support profile and compatible framework pack must be recorded in
`.ai/alatyr.yaml`. Scaffold projection must remove manifest, router, operation,
capability, and framework-rule claims for omitted optional surfaces; a smaller
profile or pack is not a complete installation with unexplained missing files.
Use repeatable `--enable-module <capability-id>` options to add only reviewed
capabilities and their dependency closure. The scaffolder raises the matched
framework pack when a selected capability requires a broader canonical owner.

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
arguments. The assessment does not install or update Alatyr. Review its
`upgrade-impact.json` first, then load only the selected changed rules,
canonical sources, target surfaces, local deviations, enabled modules, and
validation findings. Prepare a target migration note and approval scope before
applying approved changes separately.

## Optional Target Adapter Validation

After installation or update, a maintainer may use the source helper
`tools/validate_target_adapter.py` to check an installed target adapter for
machine-detectable structural drift:

```sh
python3 -m pip install -r requirements.txt
```

The dependencies provide standards-compliant YAML parsing and JSON Schema
validation for source tooling; they are not target-project runtime
dependencies.

```sh
python3 tools/validate_target_adapter.py --target /path/to/target-repo
python3 tools/validate_target_adapter.py --target /path/to/target-repo --framework-source /path/to/AlatyrCore
python3 tools/validate_target_adapter.py --target /path/to/target-repo --json --output tmp/alatyr-adapter-report.json
python3 tools/validate_target_adapter.py --target /path/to/target-repo --diff-ref origin/main --approval-record .ai/assistant/approvals/change-approval.json --enforce-approval-scope
python3 tools/validate_target_adapter.py --target /path/to/target-repo --change-package .ai/assistant/change-packages/change-package.json --enforce-change-package
python3 tools/validate_target_adapter.py --target /path/to/target-repo --framework-source /path/to/AlatyrCore --migration-diff /path/to/migration-report.md
python3 tools/validate_target_adapter.py --target /path/to/target-repo --validation-phase migration-staging
python3 tools/validate_target_adapter.py --target /path/to/target-repo --validation-phase acceptance
```

Windows users may run the same helper through `py -3` or the provided
Command Prompt and PowerShell wrappers under `tools/`.

`migration-staging` is an intermediate adaptation check. It reports unresolved
active placeholders and always remains non-accepting even when it exits zero.
The default `acceptance` phase rejects those placeholders. Final update
evidence must name the checked-out branch and revision, show manifest/module-
profile agreement, and come from acceptance validation on that same state.
Validation of one branch does not establish that another branch is updated.

This validator can check generated bootstrap and routed-gate drift, router
  references, enabled-module contracts, manifest/module-profile agreement, and
  live enabled-capability placeholders without running every optional module
check. It can also inspect exact registry Fact Type to consistency-map node
coverage, semantic routing context, consistency-map and AI infrastructure
router contracts when enabled, unresolved placeholders and stale enabled-
module claims on live support surfaces, and composed semantic context budgets,
absolute local path leakage, stale checker claims, manifest fields,
target-local checker coverage, advisory legacy approval scope, and strict
complete changed-path enforcement through explicitly selected JSON records
bound to a supplied Git diff. It also checks optional framework baseline drift,
explicitly selected change-package refs, hashes, declared semantic/path scope,
companion decisions, correction impact, provenance strength, and migration-
diff evidence when supplied. Its JSON is current-state structural evidence, not
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
