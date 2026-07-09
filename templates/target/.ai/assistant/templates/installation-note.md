# Alatyr Core Installation Note

Installation id: `{INSTALLATION_ID}`

- Installed from: `{ALATYR_CORE_SOURCE}`
- Installation date: `{DATE}`
- Supported assistants: `{SUPPORTED_ASSISTANTS}`
- Target validation: `{TARGET_VALIDATION}`
- Known adapter gaps: `{KNOWN_GAPS}`
- Local deviations from Alatyr Core: `{LOCAL_DEVIATIONS}`
- Root assistant entry points checked: `{ROOT_ENTRY_POINTS_CHECKED}`
- Supported bridge files checked: `{SUPPORTED_BRIDGE_FILES_CHECKED}`
- Installed-operation request template: `.ai/assistant/templates/operation-request.md`
- Operation help: `.ai/assistant/help.md`
- Operation routing flow: `.ai/assistant/flows/operation-routing.flow.md`
- Post-install chat message template: `.ai/assistant/templates/post-install-message.md`
- Post-update chat message template: `.ai/assistant/templates/post-update-message.md`

## Future Session Bootstrap

Future assistants should not rely on the installation or update chat message
being visible. At session start, read:

- `AGENTS.md`
- `AI_ASSISTANTS.md`
- `.ai/README.md`
- this installation note
- `.ai/assistant/help.md`
- `.ai/assistant/flows/operation-routing.flow.md` when the request is unclear

If this note lists gaps or bridge-file uncertainty, run
`recheck-after-installation` or `recheck-after-framework-update` before broad
work.
