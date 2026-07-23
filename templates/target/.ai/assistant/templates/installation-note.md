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
- Operation catalog: `.ai/assistant/operation-catalog.json`
- Context router: `.ai/assistant/context-router.json`
- Context profiles: `.ai/assistant/context-profiles.md`
- Module profile: `.ai/assistant/module-profile.md`
- Source-of-truth registry: `.ai/project/source-of-truth-registry.md`
- Consistency map: `.ai/project/consistency-map.json`
- Consistency-map module state: `{ENABLED_DEFERRED_DISABLED_OR_BLOCKED}`
- Maturity profile: `.ai/assistant/maturity-profile.md`
- Bridge capability matrix: `.ai/assistant/bridge-capability-matrix.md`
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
- Team operating model: `.ai/project/team-operating-model.md`
- Lazy team context: `.ai/assistant/team/context-overlay.json`
- Team work registry: `.ai/assistant/team/work-registry.json`
- Team coordination backend and synchronization:
  `{TARGET_BACKEND_AND_SYNCHRONIZATION_DIRECTION}`
- Team record storage, retention, and privacy:
  `{TARGET_TEAM_RECORD_STORAGE_RETENTION_AND_PRIVACY_POLICY}`
- Team flows and gate:
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
being visible. Treat `AGENTS.md` as preloaded, then read `.ai/alatyr.yaml`,
`.ai/README.md`, and `.ai/assistant/context-router.json`. Load this note after
installation/update or when adapter state is unclear. Load human profiles,
module state, registries, help, and operation routing only when selected by the
router or required by ambiguity or drift.

Use `Alatyr` as the single conversational entry, `Alatyr status` for read-only
health, automatic routing for clear requests, and the risk-gated pre-change
preview before applicable edits.

When team collaboration is enabled, use `Alatyr team status` and the target
team aliases through the canonical operation catalog. Keep team-active context
lazy and do not treat assignment, priority, claim, review, or handoff as
approval.

If this note lists gaps or bridge-file uncertainty, run
`recheck-after-installation` or `recheck-after-framework-update` before broad
work.
