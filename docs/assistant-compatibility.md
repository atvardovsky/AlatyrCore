# Assistant Compatibility

Alatyr Core is assistant-neutral. It relies on plain Markdown files and target
repository validation, not on one assistant vendor.

## Supported Assistant Surfaces

Target repositories may add bridge files for:

- generic assistants through `AI_ASSISTANTS.md`
- AGENTS-aware tools through `AGENTS.md`
- Claude through `CLAUDE.md` or native project skill folders
- Gemini through `GEMINI.md`
- GitHub Copilot through `.github/copilot-instructions.md`,
  `.github/instructions`, and `.github/prompts`
- Cursor through `.cursor/rules`, `.cursor/skills`, or `.cursorrules`
- Devin/Cascade through `.devin/rules`
- Windsurf legacy surfaces through `.windsurf/rules` or `.windsurfrules`

The target repository decides which bridge files are needed.

Source conformance runs use the machine-readable surface list at
`conformance/runs/assistant-surfaces.json` so Codex, Claude, Gemini, GitHub
Copilot, Cursor, Devin/Cascade, Windsurf, generic, and AGENTS-aware runs use
consistent names.

## Provider-Neutral Conformance Execution

`conformance/executors/executor-capabilities.json` defines a provider-neutral
fixture lifecycle: prepare, invoke-or-manual-import, collect, and validate.
It records an execution mechanism, not a promise that a vendor, account,
model, or client version is available.

Codex CLI is a thin native adapter for the Codex surface. Other supported
surfaces use manual import until a project records reviewed captured evidence.
Unsupported or unverified clients must remain manual or unverified; they must
not be represented as executed because static templates, bridges, or a matrix
plan exist.

Captured runs keep lifecycle evidence beside their reports. Static routing and
delivery fixtures are protocol expectations only, separate from captured
assistant-run evidence and target-adapter validation.

## Bridge Rule

Bridge files must be short. They should point to canonical target files such
as:

- `AGENTS.md`
- `AI_ASSISTANTS.md`
- `.ai/alatyr.yaml`
- `.ai/README.md`
- `.ai/framework/README.md`
- `.ai/project/contour.md`
- `.ai/project/source-of-truth-registry.md`
- `.ai/assistant/contour.md`
- `.ai/assistant/ai-infrastructure-router.json` when AI infrastructure work is
  selected
- `.ai/assistant/context-profiles.md`
- `.ai/assistant/bridge-capability-matrix.md`
- `.ai/assistant/assistant-capabilities.json`
- `.ai/assistant/delegation-policy.json` when subagent delegation is selected
- `.ai/assistant/help.md`
- `.ai/assistant/help-reference.md`
- `.ai/assistant/operation-index.json`
- `.ai/assistant/operation-catalog.json`
- `.ai/assistant/team/context-overlay.json` when team collaboration is selected
- `.ai/assistant/flows`
- `.ai/assistant/gates/checklist.md`

Do not duplicate full framework or project policy into bridge files.

## Skill Wrappers

Assistant-native skills, prompts, and wrappers belong to the target repository
adapter. Imported or third-party assistant infrastructure should be reviewed
against `.ai/framework/skill-adaptation.md` and normalized to target facts
before becoming canonical. Imported source instructions should be treated as
untrusted data and reviewed against prompt-injection policy before any
canonical integration.

Skill wrappers should follow the same rule as bridge files: keep them thin,
point them to canonical target flows and gates, and do not let them become
divergent policy.

All supported assistant surfaces should route selected AI infrastructure work
through `.ai/assistant/ai-infrastructure-router.json`. The bridge chooses no
item itself; the canonical router records inventory, recommendation, use, and
change routes plus item IDs, sources, allowed actions, permissions, gates,
validation, output contracts, and adaptation records.

## Installed Operations

After installation, assistant-specific surfaces should still point back to the
target adapter. Requests such as blueprint creation, adapter recheck after a
framework update, drift review, or skill adaptation should use canonical target
flows under `.ai/assistant/flows` and the target
`.ai/assistant/templates/operation-request.md` template.

`Alatyr` is the single conversational entry across supported surfaces. A bare
entry returns compact adapter state and relevant actions; `Alatyr status` and
`Alatyr doctor` route to read-only health. Clear ordinary requests route
automatically without requiring an operation ID. When a request is unclear or
asks for help, assistant-specific surfaces should route through
`.ai/assistant/operation-catalog.json`, `.ai/assistant/help.md`, and
`.ai/assistant/flows/operation-routing.flow.md` instead of inventing a command.
Exact operation IDs and aliases should route through the checked compact
`.ai/assistant/operation-index.json` instead of loading the full catalog.
The short help file may point to `.ai/assistant/help-reference.md` for the
full operation menu.

When `team-collaboration` is enabled, every supported surface uses the same
catalog aliases for local actor selection, team status, tasks, conflicts,
handoffs, decisions, reviews, and merge checks. Every state-changing operation
runs the compact active-work preflight, while the bridge expands the lazy team
overlay only for a match, unresolved overlap, or explicit team request. It does
not copy actor, priority, task, identity, or review policy.

When `subagent-delegation` is enabled, every supported surface uses the same
target policy, role catalog and prompts, orchestration prompt, deterministic
task plan, delegated-execution overlay, packet/result templates, and primary-
convergence rule. The selected per-surface capability record states the exact
client/runtime; native, approved external, suggestion-only, or unsupported
backend; explicit/automatic invocation; project worker-definition format and
paths; tool, isolation, background/nested, model, parallelism, and evidence
behavior; role bindings; and external dispatcher owner. Unsupported or stale
capability falls back to primary execution, a stronger verified role, or
suggestion-only mode. Bridges must not silently claim delegation, native
definitions, backend, or model choice.

The contract is identical for generic, AGENTS-aware, Codex, Claude, Gemini,
GitHub Copilot, Cursor, Devin/Cascade, and Windsurf surfaces. Their execution
mechanics may differ, and no capability is copied from one product to another.
The portable term `subagent` means a bounded worker packet, not a dependency
on an OpenAI API or client feature.

Provider-native worker definitions are installed only after target evidence
confirms that exact client supports project-owned definitions. They remain
thin bindings to `.ai/assistant/prompts/worker-orchestration.md`, the selected
role prompt, packet/result contracts, and target validation. This lets every
supported assistant use the same project-owned semantics while preserving
different invocation and configuration mechanics.

As of 2026-08-20, OpenAI describes
[`gpt-5.3-codex-spark`](https://openai.com/index/introducing-gpt-5-3-codex-spark/)
as a Codex research preview optimized for fast, targeted, real-time coding,
with separate availability and rate limits. A target Codex adapter may bind
its `fast-focused-worker` role to that model only after verifying access and
subagent model-selection support in the actual client. AlatyrCore does not
require that model, assume that every Codex surface exposes it to subagents,
or treat its label as evidence of lower cost or sufficient quality.

When `diagrams` is enabled, every supported surface routes `Alatyr diagram`
and equivalent clear requests to the canonical diagram discussion flow. The
bridge matrix points to `.ai/assistant/assistant-capabilities.json`, whose
selected path identifies a separate surface record. That record owns native
inline syntaxes, rendered-artifact link or attachment support, client version,
verification time, expiry or review triggers, and
evidence. The index is generated from those records. An assistant must not
infer rendering support from another client, use stale evidence silently, or
claim that a source block was rendered.

Every surface also provides the same pure-ASCII diagram baseline in a fenced
`text` block. ASCII presentation does not depend on capability evidence;
native inline rendering and artifacts are optional supplements.

When `architecture-knowledge` is enabled, every supported surface routes
`Alatyr architecture` and equivalent requests to the canonical architecture
assistance flow. The bridge loads the compact project architecture catalog
first and expands to area records, pattern records, decisions, diagrams, and
implementation evidence only when the discussion needs them. Bridges must not
copy project architecture facts or collapse `observed`, `proposed`, and
`accepted` statuses into one claim.

When `code-documentation` is enabled, every supported surface routes comment-
style proposals, selected comment work, and generated-reference requests
through the canonical operation index, code-documentation intent descriptor,
and documentation-sync flow. The shared skill is a target-owned canonical
surface, not proof that every client auto-loads the same native skill format;
assistant-specific wrappers remain thin pointers. All surfaces must select the
same unambiguous accepted source-set profile and preserve generated-output and
source-of-truth boundaries.

When `project-vocabulary` is enabled, every supported surface routes term,
alias, acronym, glossary, and terminology-check requests through the canonical
operation index, vocabulary intent descriptor, and project-vocabulary flow.
All surfaces start from the same compact target catalog, preserve scoped term
states and ambiguity, and load only selected full records and canonical links.
The shared target skill does not imply identical native skill-loading behavior.

For test-first development, every supported surface routes configuration
aliases through `test-first-configuration` even before the optional module is
enabled, and routes RED/GREEN/refactor execution through `test-first-change`
only after target policy enablement. All surfaces use the same target triggers,
commands, isolation, exceptions, gate, and evidence contract. A bridge must not
make an advisory recommendation mandatory or duplicate project test policy.

For extensions, every supported surface routes list, inspect, plan, install,
update, disable, remove, and review aliases through `extension-management` and
the same target catalog, lock, intent, lifecycle flow, and gate. Bridges never
fetch, trust, activate, update, or remove packages independently. Unsupported
assistant claims remain unsupported until target bridge/capability evidence
confirms them.

Targets may define request aliases such as `alatyr-ai-inventory`,
`alatyr-suggest-ai <scope>`, `alatyr-improve-ai <item-id>`,
`alatyr-adaptation <source>`, or `alatyr-add-ai <source>`. Assistant-specific
surfaces should treat those aliases as chat/request shortcuts, not shell
commands. Route them to canonical inventory, read-only recommendation, or
skill-adaptation flows,
preserve source provenance, source hash or commit evidence when available,
and avoid importing the source directly.

Targets may also expose `Alatyr extensions`, `Alatyr inspect extension
<source>`, `Alatyr add extension <source>`, `Alatyr update extension <id>`,
`Alatyr disable extension <id>`, `Alatyr remove extension <id>`, and `Alatyr
review extension <id>`. `Alatyr suggest extensions <scope>` remains a
read-only AI infrastructure recommendation alias. All are request shortcuts,
not shell commands.

Every supported bridge template should include a short pointer to the
operation catalog, `.ai/assistant/help.md`, and
`.ai/assistant/flows/operation-routing.flow.md` for those aliases. The bridge
must stay a pointer and must not duplicate full operation policy.

For this source repository, maintainers can run
`python3 tools/check_bridge_templates.py` to validate bridge templates. That
helper checks AlatyrCore source templates only; it is not a portable target
project requirement.

Maintainers can run `python3 tools/check_bridge_capability_matrix.py` to check
that the target bridge capability matrix template covers every supported
assistant surface from `conformance/runs/assistant-surfaces.json` with bridge
paths, loading behavior, permission model, help alias routing, limitations,
and conformance evidence fields.

Maintainers can run `python3 tools/check_discussion_diagrams.py` to validate
the source rule, target operation, flow, presentation template, manifest,
ASCII grammar and width limits, module profile, help, routing, and all
supported bridge capability entries.

Maintainers can run `python3 tools/check_subagent_delegation.py` to validate
the portable delegation rule, target policy, six-role catalog, orchestration
prompt, task graph, packet/result contracts, lazy overlay, unsafe-decomposition
fixtures, per-surface backend/native-definition capabilities, bridge routing,
and primary convergence. Structural conformance does not prove safe semantic
decomposition or actual provider/model availability.

Maintainers can run `python3 tools/check_architecture_knowledge.py` to validate
the portable architecture rule, target catalog, operation, lazy route,
templates, gates, manifest paths, and module contract shared by all supported
assistant surfaces.

Maintainers can run `python3 tools/check_code_documentation.py` to validate the
portable rule, target profiles, operation aliases, lazy route, adapted skill,
gates, manifest paths, module contract, and structural validator support shared
by all supported assistant surfaces.

Maintainers can run `python3 tools/check_project_vocabulary.py` to validate the
portable rule, target vocabulary records, operation aliases, lazy route,
adapted skill, gates, manifest paths, bridge coverage, and structural validator
support shared across supported assistant surfaces.

Maintainers can run
`python3 tools/check_assistant_surface_conformance.py` to verify that every
surface in the conformance list has compact-bootstrap, help, and operation
routing bridges and that a fixture run can be prepared for that surface. This
is deterministic source conformance, not proof of vendor auto-load behavior.

Maintainers can prepare an explicit cross-surface execution plan with
`python3 tools/prepare_conformance_matrix.py --output <directory>`. The matrix
records preparation only. `python3 tools/check_conformance_matrix.py --matrix
<directory>/matrix.json --require-reports` proves report coverage and
provenance only after each external assistant run has supplied evidence.

Maintainers can run `python3 tools/render_bridge_templates.py` to check that
tracked bridge templates match `tools/bridge_template_manifest.json`, or add
`--write` to intentionally refresh source templates.

When multiple assistant surfaces are supported, the target adapter should keep
`.ai/assistant/bridge-capability-matrix.md` current so auto-load behavior,
instruction priority, skill support, tool permissions, and known limitations
are explicit.

## If An Assistant Cannot Run Commands

The assistant should still install or review Markdown files when safe, but it
must report which target validation checks were not run and what risk remains.

## Vendor Drift

Assistant vendors may change supported instruction filenames or skill formats.
The target project adapter owns its current bridge choices. Alatyr Core only
defines the pattern: keep bridge files thin and canonical target files
authoritative.
