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
- `.ai/assistant/flows`
- `.ai/assistant/gates/checklist.md`

Do not duplicate full framework or project policy into bridge files.

## If An Assistant Cannot Run Commands

The assistant should still install or review Markdown files when safe, but it
must report which target validation checks were not run and what risk remains.

## Vendor Drift

Assistant vendors may change supported instruction filenames or skill formats.
The target project adapter owns its current bridge choices. Alatyr Core only
defines the pattern: keep bridge files thin and canonical target files
authoritative.

