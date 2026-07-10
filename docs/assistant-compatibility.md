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
- `.ai/assistant/context-profiles.md`
- `.ai/assistant/bridge-capability-matrix.md`
- `.ai/assistant/help.md`
- `.ai/assistant/help-reference.md`
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

## Installed Operations

After installation, assistant-specific surfaces should still point back to the
target adapter. Requests such as blueprint creation, adapter recheck after a
framework update, drift review, or skill adaptation should use canonical target
flows under `.ai/assistant/flows` and the target
`.ai/assistant/templates/operation-request.md` template.

When a request is unclear or asks for "Alatyr help", assistant-specific
surfaces should route back to `.ai/assistant/help.md` and
`.ai/assistant/flows/operation-routing.flow.md` instead of inventing a command.
The short help file may point to `.ai/assistant/help-reference.md` for the
full operation menu.

Targets may define request aliases such as `alatyr-ai-inventory`,
`alatyr-adaptation <source>`, or `alatyr-add-ai <source>`. Assistant-specific
surfaces should treat those aliases as chat/request shortcuts, not shell
commands. Route them to the canonical inventory and skill-adaptation flows,
preserve source provenance, source hash or commit evidence when available,
and avoid importing the source directly.

Every supported bridge template should include a short pointer to
`.ai/assistant/help.md` and
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
