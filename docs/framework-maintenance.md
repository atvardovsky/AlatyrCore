# Framework Maintenance

Use this guide when changing Alatyr Core itself.

## Change Categories

- Framework rule change: update `framework/`, installer docs, target
  templates, README, and changelog when affected.
- Installation process change: update `installer/`, README, target templates,
  and assistant compatibility docs when affected.
- Target template change: update `templates/target`, installer docs, and
  README when the installation contract changes.
- Installed-operation catalog, routing, health, preview, help, or chat-message
  change: update `framework/`,
  `installer/`, `templates/target`, assistant compatibility docs, and
  changelog when affected.
- Manifest, ownership, context-router, context-profile, approval-record,
  change-package, code-documentation profile/generator, project-vocabulary,
  test-first policy/recommendation/enablement/evidence,
  extension package/catalog/lock/lifecycle,
  output-contract, AI-infrastructure inventory or recommendation, or
  prompt-injection contract change: update
  `framework/`, `installer/`, `templates/target`, checker rules, README, and
  changelog when affected.
- Module-profile contract change: update `framework/`,
  `templates/target/.ai/assistant/module-profile.md`, installer docs,
  manifest template, checker rules, README, and changelog when affected.
- Source-of-truth registry, task-specific maturity, bridge capability, or
  migration-note contract change: update `framework/`, `installer/`,
  `templates/target`, assistant compatibility docs, checker rules, README, and
  changelog when affected.
- Rule registry, framework pack, scaffolding helper, conformance fixture,
  migration-diff, or effectiveness metrics change: update `framework/`,
  `installer/`, `tools/`, `conformance/`, README, checker rules, and changelog
  when affected.
- Rule ownership or duplicate-policy change: update
  `framework/rule-registry.json`, regenerate the Markdown registry and
  ownership map, then update source lists, checker rules, README, and changelog
  when affected.
- Framework metadata change: update the owning framework document front
  matter, rule registry or ownership map when affected, checker rules, README,
  and changelog.
- Release or versioning change: update `VERSION`, `ADAPTER_SCHEMA_VERSION`,
  `TEMPLATE_VERSION`, `CHANGELOG.md`, `docs/release-process.md`, checker
  rules, README, and changelog when affected.
- Source-repository validation change: update `tools/`, maintainer docs,
  `AGENTS.md`, README, and changelog when affected.
- Wording-only change: update only the owning document when no behavior,
  installation step, or adapter requirement changes.

## Self-Application Reviews

When using Alatyr Core to inspect or improve this source repository, treat
generated target-adapter output as scratch unless the task is explicitly to
change tracked templates or docs.

- Put self-installation plans, readiness notes, trial `.ai` trees, copied
  bridge files, and assistant-local adapter folders in ignored paths such as
  `tmp/` or the root-local assistant paths listed in `.gitignore`.
- Do not commit a generated self-installation of Alatyr Core into this source
  repository.
- Promote reusable findings into the canonical owning files: `framework/`,
  `installer/`, `templates/target/`, `docs/`, `README.md`, `INSTALL.md`,
  `AI_ASSISTANTS.md`, `AGENTS.md`, or `CHANGELOG.md`.

## Manual Gate Review

Before accepting a change, check:

- `python3 tools/check_all.py` passes when the source validation wrapper is
  available. This is the preferred AlatyrCore source-repository check set, not
  a portable target-project requirement.
- `python3 tools/check_framework_consistency.py` passes when the helper is
  available.
- `python3 tools/check_framework_metadata.py` passes when rule-owner framework
  docs, owned rule IDs, rule dependencies, or task-profile scope changes.
- `python3 tools/check_framework_packs.py` passes when support-profile pack
  mapping, rule dependency closure, or projected registry/inventory behavior
  changes.
- `python3 tools/render_rule_registry_docs.py --check` passes when generated
  human rule and ownership surfaces match the machine registry.
- `python3 tools/render_target_validator_findings.py --check` passes when the
  generated validator finding catalog matches diagnostic source calls.
- `python3 tools/render_framework_file_inventory.py --check` passes when the
  complete source framework inventory matches current versions and files.
- `python3 tools/check_architecture_knowledge.py` passes when architecture
  knowledge statuses, catalog records, pattern discussion, documentation
  maintenance, lazy routing, operation output, gates, or module paths change.
- `python3 tools/check_approval_template.py` passes when approval-record
  fields, machine-readable scope, diff-base binding, protected scope, plan
  hash, invalidation, usage result, evidence, or residual-risk guidance
  changes.
- `python3 tools/check_change_packages.py` passes when package activation,
  semantic scope, companion decisions, implementation corrections, compact
  discussion evidence, provenance grades, target records, or validator
  enforcement changes.
- `python3 tools/check_code_documentation.py` passes when source-set profile
  selection, comment-style proposals, canonical fact boundaries, generators,
  output policy, documentation intent routing, adapted skill, gates, installer
  wiring, or target structural validation changes.
- `python3 tools/check_project_vocabulary.py` passes when vocabulary term
  states, compact lookup, aliases, acronyms, scoped ambiguity, data-dictionary
  links, canonical-owner boundaries, operation routing, adapted skill, gates,
  installer wiring, or target structural validation changes.
- `python3 tools/check_test_first_development.py` passes when test-first policy
  state, bounded recommendation, enablement, trigger/mode/command/isolation,
  RED/GREEN/refactor evidence, operation routing, skill/gate, installer wiring,
  or target structural validation changes.
- `python3 tools/check_extensions.py` passes when extension package format,
  compatibility, catalog/lock, target bindings, lifecycle, ownership,
  inspection tooling, routing, bridges, installer wiring, or target structural
  validation changes.
- `python3 tools/check_ai_infrastructure_inventory.py` passes when AI
  infrastructure inventory fields, source/provenance, permission, license,
  prompt-injection risk, approval, recommendation, or residual-risk evidence
  changes.
- `python3 tools/check_ai_infrastructure_recommendations.py` passes when
  recommendation triggers, project-contour evidence, existing-item review,
  development-pattern capture/retention/privacy, framework scope boundaries,
  quality/context/maintenance cost, acceptance criteria, read-only behavior,
  aliases, routes, flows, templates, or manifest paths change.
- `python3 tools/check_ai_infrastructure_router.py` passes when AI item types,
  routes, lazy context, item contracts, permissions, gates, adaptation records,
  validation, output contracts, or manifest routing change.
- `python3 tools/check_bridge_capability_matrix.py` passes when supported
  assistant surfaces, bridge paths, auto-load behavior, skill/prompt support,
  tool permissions, help alias routing, limitations, or conformance guidance
  changes.
- `python3 tools/check_discussion_diagrams.py` passes when diagram discussion,
  draft/source status, ASCII grammar/width, inline or artifact presentation,
  source-revision evidence, security/privacy, stable lineage, compact routing,
  conformance fixture, or assistant capability fields change.
- `python3 tools/check_diagram_conformance_results.py` passes when captured
  diagram result, selected capability, loaded-context, read-only, ASCII
  readability, or residual-risk evidence changes.
- `python3 tools/prepare_diagram_conformance_run.py --check` passes when the
  cross-assistant diagram operation fixture or prompt contract changes.
- `python3 tools/check_assistant_surface_conformance.py` passes when supported
  surface IDs, bridge paths, compact bootstrap, help routing, or prepared
  conformance prompts change.
- `python3 tools/check_context_router.py` passes when target context-router
  schema, lazy descriptors, profile names, required context, approval gates,
  validation, final evidence, or framework-routing coverage changes.
- `python3 tools/check_bootstrap_routing.py` passes when generated bootstrap,
  gate fragments, profile defaults, or core scaffold routing changes. Refresh
  the target projection with `python3 tools/render_target_bootstrap_index.py
  --target templates/target --write` only after reviewing canonical sources.
- `python3 tools/check_context_costs.py` passes when bootstrap/profile paths,
  consistency composition, context budgets, or routed source word counts
  change; refresh the golden baseline only after reviewing the cost difference.
  The installed validator must enforce the same total, portable, reserved-
  target, and file limits over profile-plus-consistency composition.
- `python3 tools/check_consistency_map.py` passes when consistency levels,
  relationship types, impact traversal, exact source-registry node linkage,
  semantic routing, or map placeholders change.
- `python3 tools/check_cross_platform_tools.py` passes when the unified tool
  manifest, platform launchers, write scopes, or migration-first upgrade
  assessment changes. The source workflow must also run `check_all.py` on
  native Linux, macOS, and Windows runners.
- `python3 tools/check_large_task_orchestration.py` passes when large-task
  activation, task-scale routing, workstream, packet, checkpoint, resume, or
  convergence contracts change.
- `python3 tools/check_subagent_delegation.py` passes when delegation policy,
  lazy overlay, packet, model/capability evidence, bridge routing, fallback,
  or primary-convergence contracts change.
- `python3 tools/check_manifest_contract.py` passes when the target manifest
  template, versioning fields, path references, or adapter metadata contract
  changes.
- `python3 tools/check_markdown_links.py` passes when source Markdown links,
  docs, templates, or maintainer references change.
- `python3 tools/check_maturity_profile.py` passes when target maturity task
  areas, fields, placeholders, blocking criteria, approval needs, residual
  risks, or final-evidence guidance changes.
- `python3 tools/check_module_profile.py` passes when required core items,
  optional module fields, required files, approvals, next actions, or module
  residual-risk guidance changes.
- `python3 tools/check_operation_contracts.py` passes when installed-operation
  help, aliases, flow routing, allowed-action boundaries, or ordered pipeline
  steps change.
- `python3 tools/check_operation_catalog.py` passes when operation IDs,
  automatic routing, single-entry behavior, adapter health, preview triggers,
  or catalog/manifest/router alignment changes.
- `python3 tools/render_operation_index.py` and
  `python3 tools/render_assistant_capability_index.py` pass when tracked compact
  indexes still derive from canonical catalog or per-surface records.
- `python3 tools/check_operation_help.py` passes when short help,
  help-reference sections, allowed-action text, alias wording, or operation
  block shape changes.
- `python3 tools/check_output_contracts.py` passes when installation,
  framework-update, or adapter-recheck evidence fields change.
- `python3 tools/check_release_migration_template.py` passes when release
  migration evidence, release template fields, or migration-diff output shape
  changes.
- `python3 tools/check_migration_diff_report.py` passes when
  `tools/report_migration_diff.py` Markdown/JSON output, self-compare behavior,
  adapter-contract impact, affected categories, task profiles, canonical
  sources, or action hints change.
- `python3 tools/check_rule_ownership.py` passes when rule IDs, rule
  categories, canonical owners, or duplicate-policy boundaries change.
- `python3 tools/check_source_of_truth_registry.py` passes when target
  source-of-truth registry fact types, fields, placeholders, or conflict
  resolution guidance changes.
- `python3 tools/check_target_adapter_validator.py` passes when portable target
  validator routing, route-map schemas, strict complete changed-path approval
  scope matching, Git diff collection, or evidence classification changes.
- `python3 tools/check_team_collaboration.py` passes when the optional team
  rule, structured policy, local identity boundary, active-work index,
  registry/task schemas, backend contract, lazy overlay, flows, records, gate,
  skill, operation routes, help aliases, or manifest wiring changes.
- `python3 tools/check_team_collaboration_scenarios.py` passes when multi-actor
  revision conflict, reviewer separation, active-index freshness, local
  identity, or revision-bound merge behavior changes.
- `python3 tools/check_versioning.py` passes when source versions, changelog,
  release process, migration evidence, adapter schema version, or template
  version changes.
- `python3 tools/check_release_drift.py` passes when source versions and
  migration evidence are correctly bound to the latest reachable release tag.
- `python3 tools/check_conformance_fixtures.py` passes when conformance fixture
  metadata changes.
- `python3 tools/materialize_conformance_fixtures.py --output tmp/conformance-targets`
  can create seed-only fixture repositories for reviewed assistant-run
  conformance.
- `python3 tools/prepare_conformance_run.py --output tmp/conformance-run --assistant-surface codex`
  can create fixture targets, per-fixture prompts, and a report directory for
  an actual assistant-run conformance pass.
- `python3 tools/check_conformance_reports.py` passes when fixture expected
  evidence contracts or golden assistant-result reports change.
- `python3 tools/check_conformance_matrix.py` passes when matrix/run manifests,
  all-surface preparation, report provenance, or matrix completeness changes.
- `python3 tools/check_conformance_summary.py` passes when captured-run context
  cost, logical-integrity evidence, or summary output changes.
- `python3 tools/check_conformance_reports.py --actual-root conformance/runs/assistant-results`
  validates every indexed committed captured run, including its declared
  expected fixture scope.
- Add `--require-actual-reports` when the maintenance task expects captured
  run reports to exist.
- Add `--require-all-fixtures` when a conformance run should prove every
  fixture produced a valid report.
- `python3 tools/summarize_conformance_reports.py --actual-root conformance/runs/assistant-results`
  can compare reviewed assistant-run reports by assistant surface and fixture.
- `python3 tools/run_conformance_scaffold.py` passes when fixture seed files,
  scaffolder behavior, required scaffold surfaces, or scaffolded-adapter
  golden snapshots change.
- `python3 tools/run_conformance_scaffold.py --write-golden-snapshots` is used
  only after reviewing intentional scaffold output changes.
- `python3 tools/check_bridge_templates.py` passes when supported assistant
  bridge templates or bridge capability guidance changes.
- `python3 tools/render_bridge_templates.py` passes when generated bridge
  templates or `tools/bridge_template_manifest.json` changes.
- `python3 tools/report_migration_diff.py --from-rules framework/rule-registry.json`
  can compare rule manifests without modifying target files.
- `python3 tools/report_migration_diff.py --from-rules <old-rule-registry.json> --from-framework-dir <old-framework-dir>`
  can also compare framework file names and content hashes.
- `python3 tools/report_migration_diff.py --from-rules <old-rule-registry.json> --from-template-dir <old-template-dir>`
  can also compare target template surface names and content hashes.
- `python3 tools/alatyr.py assess-upgrade --target <target-repo> --framework-source . --output-dir <assessment-dir>`
  can prepare migration and structural evidence before target upgrade changes.
- `python3 tools/summarize_effectiveness_reports.py --input conformance/golden/effectiveness-sample.json`
  passes when effectiveness report tooling or sample contracts change.
- `python3 tools/check_effectiveness_benchmark.py` and
  `python3 tools/summarize_effectiveness_benchmark.py` pass when paired mode
  isolation, report provenance, independent review, or relative-delta
  contracts change.
- `python3 tools/validate_target_adapter.py --target <target-repo>` can check
  an installed target adapter for structural drift and operation-catalog health
  when a real target
  repository is available. Use `--json --output <report.json>` when a target
  CI job or assistant recheck needs machine-readable findings, and use
  `--migration-diff <report.md>` when framework drift should be tied to rule
  and action evidence. Framework baseline and missing migration evidence are
  blocking unless the target explicitly records an accepted deviation or
  severity decision. Use `--validation-phase migration-staging` only for a
  non-accepting unresolved-fact inventory and rerun the default strict
  `acceptance` phase on the checked-out branch/revision before completion.
  The deprecated `--allow-placeholders` flag is a staging alias and cannot
  produce ready or acceptance-eligible evidence. It is optional target-adapter validation, not a
  source-template check and not proof of project business truth.
  The equivalent `python3 tools/alatyr.py doctor --target <target-repo>` alias
  remains read-only and returns prioritized repair operation IDs.
- `framework/` contains no target business facts.
- `framework/` contains no required local commands, scripts, package managers,
  CI jobs, test folders, fixture helpers, security policies, or diagram tools.
- `installer/assistant-installation.flow.md`,
  `installer/readiness-checklist.md`, and
  `installer/installation-plan-template.md` agree.
- `templates/target` remains placeholder-based.
- target manifest, context router, context profiles, approval templates,
  source-access policy, prompt-injection policy, help, help reference, output
  contracts, and AI infrastructure inventory report agree.
- AI infrastructure router, inventory, adaptation record, selected profile,
  bridge capability matrix, source access, prompt-injection, gates, manifest,
  and output contracts agree.
- development-pattern index, capture flow, project/assistant ownership,
  recommendation route, manifest, module profile, and target validator agree.
- durable engineering-evidence rule, compact index, lazy routing, capture gate,
  record schema, task/revision binding, privacy/publication policy, operation,
  installation/update surfaces, and target validator agree.
- optional Debug Mode rule, explicit task/session activation and expiry,
  non-canonical index/records, lazy overlay, flow, gate, summary, event
  attribution, privacy, timing, event-derived metrics, clean-upstream policy,
  installation/update preservation, and target validator agree.
- target gate, operation-catalog, operation-routing, adapter-health,
  pre-change-preview, adapter-recheck, and output-contract
  templates preserve context-router bootstrap references and adapter drift
  evidence for local path leakage, stale checker statements, duplicate profile
  references, unresolved owner placeholders, and target-local checker status.
- large-task routing, flow, packet, manifest, module profile, request shape,
  and installation evidence agree; small tasks are not required to create
  packets.
- target approval templates include human evidence plus machine-readable plan
  identity, diff base, protected scope, allowed and excluded files, excluded
  actions, approval source, invalidation, use result, evidence, validation,
  and residual risk fields.
- module profile agrees with manifest, installer docs, context profiles, and
  checker rules.
- source-of-truth registry, maturity profile, bridge capability matrix, and
  migration-note template agree with installer docs and checker rules.
- optional consistency-map schema, exact human registry Fact Type and node
  identity, relationship routing, measured semantic composition, module state,
  impact evidence, and checker rules agree.
- target source-of-truth registry baseline entries include canonical owner,
  stable fact ID, consistency level, project area, relationship coverage,
  derived surfaces, sync direction, validation, conflict resolver, approval,
  and final evidence fields.
- target maturity profile baseline entries include maturity level, supported
  work, required context, owners, validation, approval needs, blockers,
  residual risks, and final evidence fields.
- target bridge capability matrix baseline entries include assistant surface,
  bridge paths, auto-load behavior, instruction priority, supported surfaces,
  tool permission model, help, team-operation, and AI-infrastructure alias
  routing, known limitations, and conformance check fields.
- optional team rule, policy, local identity, active-work index, registry/task
  schemas, backend contract, optimistic concurrency, lazy overlay, flows,
  records, gate, skill, catalog, module profile, installation/update migration,
  and validator contracts agree without adding full team state to bootstrap.
- rule registry, scaffolding helper, conformance fixtures, conformance report
  contracts, migration-diff guidance, and effectiveness metrics agree with
  checker rules.
- rule ownership map agrees with the rule registry and repeated docs reference
  canonical owners instead of becoming independent policy owners.
- framework rule-owner front matter agrees with the registry, rule
  dependencies, and canonical context profiles.
- source release process, version files, and changelog structure remain
  consistent.
- source release migration report template agrees with migration-diff output.
- migration-diff output is validated by executing the reporter against the
  current source baseline.
- source entry points use bootstrap plus task-specific context routing instead
  of requiring every task to read the full framework corpus.
- `tools/check_manifest.json` keeps fast, full, change-baseline, and release
  validation explicit; fast checks never replace the full acceptance gate.
- derived installer docs, target templates, request templates, and entry
  points reference canonical rule IDs instead of owning repeated policy text.
- `README.md` still gives an assistant enough context to install the
  framework into a target repository.
- `CHANGELOG.md` records framework behavior or installation contract changes.

The helper is source-repository validation for AlatyrCore only. Do not present
it as a portable framework requirement for target repositories.

## Rejection Criteria

Reject changes that:

- add project-specific behavior as framework core
- add an installer script as the installation mechanism
- make target validation commands universal
- weaken approval gates for overwrites or protected target changes
- make bridge files authoritative instead of pointers
- leave templates with source-project facts instead of placeholders
- require every task to read the whole framework when a task profile can route
  a smaller context set
