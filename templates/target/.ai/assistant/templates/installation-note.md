# Alatyr Core Installation Note

Installation id: `{INSTALLATION_ID}`

- Installed from: `{ALATYR_CORE_SOURCE}`
- Framework version: `{ALATYR_CORE_VERSION}`
- Adapter schema version: `{ALATYR_ADAPTER_SCHEMA_VERSION}`
- Template version: `{ALATYR_TEMPLATE_VERSION}`
- Adapter manifest: `.ai/alatyr.yaml`
- Installation date: `{DATE}`
- Adapter owner: `{TECHNICAL_OWNER_OR_ROLE}`
- Backup owner: `{BACKUP_OWNER_OR_ROLE}`
- Review cadence: `{TARGET_ADAPTER_REVIEW_CADENCE}`
- CODEOWNERS or equivalent owner map: `{CODEOWNERS_OR_EQUIVALENT_OWNER_MAP}`
- Supported assistants: `{SUPPORTED_ASSISTANTS}`
- Target validation: `{TARGET_VALIDATION}`
- Known adapter gaps: `{KNOWN_GAPS}`
- Local deviations from Alatyr Core: `{LOCAL_DEVIATIONS}`
- Root assistant entry points checked: `{ROOT_ENTRY_POINTS_CHECKED}`
- Supported bridge files checked: `{SUPPORTED_BRIDGE_FILES_CHECKED}`
- Installed-operation request template: `.ai/assistant/templates/operation-request.md`
- Adapter output contracts:
  `.ai/assistant/templates/adapter-output-contracts.md`
- Operation help: `.ai/assistant/help.md`
- Operation help reference: `.ai/assistant/help-reference.md`
- Compact operation index: `.ai/assistant/operation-index.json`
- Operation catalog: `.ai/assistant/operation-catalog.json`
- Action authorization policy:
  `.ai/assistant/policies/action-authorization.json`
- Context router: `.ai/assistant/context-router.json`
- Generated bootstrap index: `.ai/assistant/bootstrap-index.json`
- Recursive context indexes: `.ai/framework/context-index.json`,
  `.ai/project/context-index.json`, `.ai/assistant/context-index.json`
- Support-information policy/state: `.ai/project/support-policy.json`,
  `.ai/support-state.json`
- Optional impact/generation derivatives:
  `.ai/assistant/consistency-reverse-index.json`,
  `.ai/assistant/support-generation-index.json`
- Semantic codebook: `.ai/framework/semantics/index.json`
- Context packet template: `.ai/assistant/templates/context-packet.json`
- Routed gate index: `.ai/assistant/gates/index.json`
- Context profiles: `.ai/assistant/context-profiles.md`
- Module profile: `.ai/assistant/module-profile.md`
- Source-of-truth registry: `.ai/project/source-of-truth-registry.md`
- Durable engineering-evidence index:
  `.ai/project/engineering-evidence/index.json`
- Durable engineering-evidence owner, storage, retention/redaction, and
  external-contribution policy: `{TARGET_ENGINEERING_EVIDENCE_POLICY}`
- Durable engineering-evidence overlay, flow, gate, and record template:
  `.ai/assistant/context/task-scales/engineering-evidence.json`,
  `.ai/assistant/flows/engineering-evidence-capture.flow.md`,
  `.ai/assistant/gates/engineering-evidence.md`,
  `.ai/assistant/templates/engineering-evidence-record.json`
- Consistency map: `.ai/project/consistency-map.json`
- Consistency-map module state: `{ENABLED_DEFERRED_DISABLED_OR_BLOCKED}`
- Workspace-mode module state:
  `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
- Workspace-mode catalog: `.ai/project/workspace-modes/catalog.json`
- Workspace identity, active adapter, shared root support, proposed modes,
  accepted modes, and user decision evidence:
  `{WORKSPACE_MODE_INSTALLATION_RESULT}`
- Maturity profile: `.ai/assistant/maturity-profile.md`
- Bridge capability matrix: `.ai/assistant/bridge-capability-matrix.md`
- Compact assistant capabilities: `.ai/assistant/assistant-capabilities.json`
- AI infrastructure inventory template:
  `.ai/assistant/templates/ai-infrastructure-inventory.md`
- AI infrastructure recommendation flow and template:
  `.ai/assistant/flows/ai-infrastructure-recommendation.flow.md`,
  `.ai/assistant/templates/ai-infrastructure-recommendation.md`
- Development evidence index and lazy capture flow:
  `.ai/project/development-evidence.json`,
  `.ai/assistant/flows/development-evidence-capture.flow.md`
- Development evidence owner and retention/privacy policy:
  `{TARGET_DEVELOPMENT_EVIDENCE_OWNER_AND_POLICY}`
- AI infrastructure router:
  `.ai/assistant/ai-infrastructure-router.json`
- AI infrastructure adaptation record:
  `.ai/assistant/templates/ai-infrastructure-adaptation-record.md`
- Operation routing flow: `.ai/assistant/flows/operation-routing.flow.md`
- Adapter health flow: `.ai/assistant/flows/adapter-health.flow.md`
- Pre-change preview: `.ai/assistant/templates/pre-change-preview.md`
- Large-task orchestration flow:
  `.ai/assistant/flows/large-task-orchestration.flow.md`
- Large-task operation packet:
  `.ai/assistant/templates/large-task-operation-packet.md`
- Operation packet storage policy: `{TARGET_OPERATION_PACKET_POLICY}`
- Team-collaboration module state:
  `{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED}`
- Canonical team policy: `.ai/project/team-policy.json`
- Human team operating model: `.ai/project/team-operating-model.md`
- Lazy team context: `.ai/assistant/team/context-overlay.json`
- Compact active-work index: `.ai/assistant/team/active-work-index.json`
- Team registry metadata and task records:
  `.ai/assistant/team/work-registry.json` and
  `.ai/assistant/team/tasks/{TASK_ID}.json`
- Backend contract: `.ai/assistant/team/backend-contract.json`
- Local identity: ignored `.ai/local/team-identity.json`
- Team coordination backend and synchronization:
  `{TARGET_BACKEND_AND_SYNCHRONIZATION_DIRECTION}`
- Team record storage, retention, and privacy:
  `{TARGET_TEAM_RECORD_STORAGE_RETENTION_AND_PRIVACY_POLICY}`
- Team flows and gate:
  `.ai/assistant/flows/team-identity.flow.md`,
  `.ai/assistant/flows/team-task-coordination.flow.md`,
  `.ai/assistant/flows/team-handoff.flow.md`,
  `.ai/assistant/flows/team-decision.flow.md`,
  `.ai/assistant/flows/team-review.flow.md`,
  `.ai/assistant/gates/team-collaboration.md`
- Active team records created, migrated, preserved, or skipped:
  `{TEAM_ACTIVE_RECORD_RESULT}`
- Approval record template: `.ai/assistant/approvals/approval-template.md`
- Prompt-injection policy: `.ai/assistant/policies/prompt-injection.md`
- Migration note template: `.ai/assistant/templates/migration-note.md`
- Effectiveness report template:
  `.ai/assistant/templates/effectiveness-report.md`
- Post-install chat message template: `.ai/assistant/templates/post-install-message.md`
- Post-update chat message template: `.ai/assistant/templates/post-update-message.md`

## Future Session Bootstrap

Future assistants should not rely on the installation or update chat message
being visible. Treat `AGENTS.md` as preloaded, then read
`.ai/assistant/bootstrap-index.json`. Use its resolved core semantic
definitions once, then follow only matching branches from the framework,
project, and assistant root `context-index.json` files. Parent selection does
not select every child. Resolve lazy semantic references through
`.ai/framework/semantics/index.json` and fall back to the named canonical owner
on missing, stale, ambiguous, or conflicting terms. Repair stale recursive
indexes before regenerating the bootstrap from `.ai/alatyr.yaml`,
`.ai/README.md`, `.ai/assistant/context-router.json`, and the semantic index.
Load this note after
installation/update or when adapter state is unclear. Load human profiles,
module state, registries, help, and operation routing only when selected by the
router or required by ambiguity or drift.

Use `Alatyr` as the single conversational entry, `Alatyr status` for read-only
health, automatic routing for clear requests, and the risk-gated pre-change
preview before applicable edits.

Apply the current-scope action policy before `modify`, `commit`, `publish`, or
`live-external`. A previous task's authorization expires when that task is
complete or the subject changes. Backlog/issue returns, status, discussion,
analysis, reports, plans, and ambiguous continuation default to `inspect`.

When workspace modes are enabled, read only the compact catalog first. Use
`Alatyr modes`, `Alatyr suggest modes`, or `Alatyr mode <id>` for read-only
state, proposals, or task selection. A proposal is not accepted by this
installation note or its installation approval; only a separate user decision
may accept it.

When team collaboration is enabled, use `Alatyr set actor`, `Alatyr who am I`,
`Alatyr team status`, and the target team aliases through the catalog. Check
the compact active-work index before state-changing operations. Keep full team
context lazy, and do not treat local selection, assignment, priority, claim,
review, or handoff as authentication, authority, or approval.

If this note lists gaps or bridge-file uncertainty, run
`recheck-after-installation` or `recheck-after-framework-update` before broad
work.
