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

## Bridge Rule

Bridge files must be short. They should point to canonical target files such
as:

- `AGENTS.md`
- `AI_ASSISTANTS.md`
- `.ai/README.md`
- `.ai/framework/README.md`
- `.ai/project/contour.md`
- `.ai/assistant/contour.md`
- `.ai/assistant/help.md`
- `.ai/assistant/flows`
- `.ai/assistant/gates/checklist.md`

Do not duplicate full framework or project policy into bridge files.

## Skill Wrappers

Assistant-native skills, prompts, and wrappers belong to the target repository
adapter. Imported or third-party assistant infrastructure should be reviewed
against `.ai/framework/skill-adaptation.md` and normalized to target facts
before becoming canonical.

Skill wrappers should follow the same rule as bridge files: keep them thin,
point them to canonical target flows and gates, and do not let them become
divergent policy.

## Installed Operations

After installation, assistant-specific surfaces should still point back to the
target adapter. Requests such as blueprint creation, adapter recheck after a
framework update, drift review, or skill adaptation should use canonical target
flows under `.ai/assistant/flows` and the target
`.ai/assistant/templates/operation-request.md` template.

When a request is unclear or asks for "Alatyr help", assistant-specific
surfaces should route back to `.ai/assistant/help.md` and
`.ai/assistant/flows/operation-routing.flow.md` instead of inventing a command.

Targets may define request aliases such as `alatyr-ai-inventory`,
`alatyr-adaptation <source>`, or `alatyr-add-ai <source>`. Assistant-specific
surfaces should route those aliases to the canonical inventory and
skill-adaptation flows, preserve source provenance, and avoid importing the
source directly.

Every supported bridge template should include a short pointer to
`.ai/assistant/help.md` and
`.ai/assistant/flows/operation-routing.flow.md` for those aliases. The bridge
must stay a pointer and must not duplicate full operation policy.

## If An Assistant Cannot Run Commands

The assistant should still install or review Markdown files when safe, but it
must report which target validation checks were not run and what risk remains.

## Vendor Drift

Assistant vendors may change supported instruction filenames or skill formats.
The target project adapter owns its current bridge choices. Alatyr Core only
defines the pattern: keep bridge files thin and canonical target files
authoritative.
