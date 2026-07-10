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
- Context profiles: `.ai/assistant/context-profiles.md`
- Module profile: `.ai/assistant/module-profile.md`
- Source-of-truth registry: `.ai/project/source-of-truth-registry.md`
- Maturity profile: `.ai/assistant/maturity-profile.md`
- Bridge capability matrix: `.ai/assistant/bridge-capability-matrix.md`
- AI infrastructure inventory template:
  `.ai/assistant/templates/ai-infrastructure-inventory.md`
- Operation routing flow: `.ai/assistant/flows/operation-routing.flow.md`
- Approval record template: `.ai/assistant/approvals/approval-template.md`
- Prompt-injection policy: `.ai/assistant/policies/prompt-injection.md`
- Migration note template: `.ai/assistant/templates/migration-note.md`
- Effectiveness report template:
  `.ai/assistant/templates/effectiveness-report.md`
- Post-install chat message template: `.ai/assistant/templates/post-install-message.md`
- Post-update chat message template: `.ai/assistant/templates/post-update-message.md`

## Future Session Bootstrap

Future assistants should not rely on the installation or update chat message
being visible. At session start, read:

- `AGENTS.md`
- `AI_ASSISTANTS.md`
- `.ai/alatyr.yaml`
- `.ai/README.md`
- `.ai/assistant/context-profiles.md`
- `.ai/assistant/module-profile.md`
- `.ai/project/source-of-truth-registry.md`
- this installation note
- `.ai/assistant/help.md`
- `.ai/assistant/flows/operation-routing.flow.md` when the request is unclear

If this note lists gaps or bridge-file uncertainty, run
`recheck-after-installation` or `recheck-after-framework-update` before broad
work.
