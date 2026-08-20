# Bridge Capability Matrix

Use this matrix in `{PROJECT_NAME}` to keep supported assistant bridge files
aligned.

Replace placeholders with target facts before accepting installation.

This matrix owns human precedence and limitation notes. Runtime diagram
selection reads only the current entry in
`.ai/assistant/assistant-capabilities.json`; keep that checked projection
aligned with the references below.

Each delegation capability record must select `native`, `external`,
`suggestion-only`, `unsupported`, or `unknown`. External dispatch must name a
routed target AI-infrastructure item. The shared packet and primary-
convergence contract apply regardless of assistant vendor or backend.

## Supported Assistant Surfaces

Resolve these entries from target evidence before claiming a bridge is
supported. If the target does not use a surface, keep the entry and mark it
unsupported or not applicable with the reason.

### Assistant Surface: `generic`

Assistant: `Generic assistant`
Surface id: `generic`
Bridge paths:

- `AI_ASSISTANTS.md`

Auto-load behavior: `{GENERIC_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{GENERIC_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{GENERIC_SUPPORTED_SURFACES}`
Tool permission model: `{GENERIC_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{GENERIC_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{GENERIC_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{GENERIC_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{GENERIC_ROUTES_PRE_CHANGE_PREVIEW}`
Routes enabled team operations: `{GENERIC_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{GENERIC_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{GENERIC_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{GENERIC_ROUTES_TEST_FIRST}`
Routes extension aliases: `{GENERIC_ROUTES_EXTENSIONS}`
Routes subagent delegation: `{GENERIC_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/generic.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/generic.json`
Routes `alatyr-ai-inventory`: `{GENERIC_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{GENERIC_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{GENERIC_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{GENERIC_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{GENERIC_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{GENERIC_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{GENERIC_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{GENERIC_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

### Assistant Surface: `agents`

Assistant: `AGENTS-aware assistant`
Surface id: `agents`
Bridge paths:

- `AGENTS.md`

Auto-load behavior: `{AGENTS_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{AGENTS_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{AGENTS_SUPPORTED_SURFACES}`
Tool permission model: `{AGENTS_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{AGENTS_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{AGENTS_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{AGENTS_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{AGENTS_ROUTES_PRE_CHANGE_PREVIEW}`
Routes enabled team operations: `{AGENTS_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{AGENTS_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{AGENTS_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{AGENTS_ROUTES_TEST_FIRST}`
Routes extension aliases: `{AGENTS_ROUTES_EXTENSIONS}`
Routes subagent delegation: `{AGENTS_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/agents.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/agents.json`
Routes `alatyr-ai-inventory`: `{AGENTS_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{AGENTS_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{AGENTS_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{AGENTS_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{AGENTS_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{AGENTS_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{AGENTS_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{AGENTS_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

### Assistant Surface: `codex`

Assistant: `Codex`
Surface id: `codex`
Bridge paths:

- `AGENTS.md`
- `AI_ASSISTANTS.md`

Auto-load behavior: `{CODEX_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{CODEX_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{CODEX_SUPPORTED_SURFACES}`
Tool permission model: `{CODEX_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{CODEX_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{CODEX_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{CODEX_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{CODEX_ROUTES_PRE_CHANGE_PREVIEW}`
Routes enabled team operations: `{CODEX_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{CODEX_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{CODEX_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{CODEX_ROUTES_TEST_FIRST}`
Routes extension aliases: `{CODEX_ROUTES_EXTENSIONS}`
Routes subagent delegation: `{CODEX_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/codex.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/codex.json`
Routes `alatyr-ai-inventory`: `{CODEX_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{CODEX_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{CODEX_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{CODEX_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{CODEX_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{CODEX_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{CODEX_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{CODEX_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

### Assistant Surface: `claude`

Assistant: `Claude`
Surface id: `claude`
Bridge paths:

- `CLAUDE.md`

Auto-load behavior: `{CLAUDE_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{CLAUDE_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{CLAUDE_SUPPORTED_SURFACES}`
Tool permission model: `{CLAUDE_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{CLAUDE_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{CLAUDE_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{CLAUDE_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{CLAUDE_ROUTES_PRE_CHANGE_PREVIEW}`
Routes enabled team operations: `{CLAUDE_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{CLAUDE_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{CLAUDE_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{CLAUDE_ROUTES_TEST_FIRST}`
Routes extension aliases: `{CLAUDE_ROUTES_EXTENSIONS}`
Routes subagent delegation: `{CLAUDE_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/claude.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/claude.json`
Routes `alatyr-ai-inventory`: `{CLAUDE_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{CLAUDE_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{CLAUDE_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{CLAUDE_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{CLAUDE_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{CLAUDE_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{CLAUDE_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{CLAUDE_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

### Assistant Surface: `gemini`

Assistant: `Gemini`
Surface id: `gemini`
Bridge paths:

- `GEMINI.md`

Auto-load behavior: `{GEMINI_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{GEMINI_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{GEMINI_SUPPORTED_SURFACES}`
Tool permission model: `{GEMINI_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{GEMINI_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{GEMINI_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{GEMINI_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{GEMINI_ROUTES_PRE_CHANGE_PREVIEW}`
Routes enabled team operations: `{GEMINI_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{GEMINI_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{GEMINI_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{GEMINI_ROUTES_TEST_FIRST}`
Routes extension aliases: `{GEMINI_ROUTES_EXTENSIONS}`
Routes subagent delegation: `{GEMINI_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/gemini.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/gemini.json`
Routes `alatyr-ai-inventory`: `{GEMINI_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{GEMINI_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{GEMINI_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{GEMINI_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{GEMINI_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{GEMINI_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{GEMINI_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{GEMINI_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

### Assistant Surface: `github-copilot`

Assistant: `GitHub Copilot`
Surface id: `github-copilot`
Bridge paths:

- `.github/copilot-instructions.md`
- `.github/prompts/gate-review.prompt.md`

Auto-load behavior: `{GITHUB_COPILOT_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{GITHUB_COPILOT_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{GITHUB_COPILOT_SUPPORTED_SURFACES}`
Tool permission model: `{GITHUB_COPILOT_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{GITHUB_COPILOT_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{GITHUB_COPILOT_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{GITHUB_COPILOT_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{GITHUB_COPILOT_ROUTES_PRE_CHANGE_PREVIEW}`
Routes enabled team operations: `{GITHUB_COPILOT_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{GITHUB_COPILOT_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{GITHUB_COPILOT_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{GITHUB_COPILOT_ROUTES_TEST_FIRST}`
Routes extension aliases: `{GITHUB_COPILOT_ROUTES_EXTENSIONS}`
Routes subagent delegation: `{GITHUB_COPILOT_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/github-copilot.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/github-copilot.json`
Routes `alatyr-ai-inventory`: `{GITHUB_COPILOT_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{GITHUB_COPILOT_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{GITHUB_COPILOT_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{GITHUB_COPILOT_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{GITHUB_COPILOT_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{GITHUB_COPILOT_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{GITHUB_COPILOT_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{GITHUB_COPILOT_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

### Assistant Surface: `cursor`

Assistant: `Cursor`
Surface id: `cursor`
Bridge paths:

- `.cursor/rules/alatyr-core.mdc`
- `.cursorrules`

Auto-load behavior: `{CURSOR_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{CURSOR_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{CURSOR_SUPPORTED_SURFACES}`
Tool permission model: `{CURSOR_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{CURSOR_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{CURSOR_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{CURSOR_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{CURSOR_ROUTES_PRE_CHANGE_PREVIEW}`
Routes enabled team operations: `{CURSOR_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{CURSOR_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{CURSOR_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{CURSOR_ROUTES_TEST_FIRST}`
Routes extension aliases: `{CURSOR_ROUTES_EXTENSIONS}`
Routes subagent delegation: `{CURSOR_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/cursor.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/cursor.json`
Routes `alatyr-ai-inventory`: `{CURSOR_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{CURSOR_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{CURSOR_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{CURSOR_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{CURSOR_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{CURSOR_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{CURSOR_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{CURSOR_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

### Assistant Surface: `devin-cascade`

Assistant: `Devin/Cascade`
Surface id: `devin-cascade`
Bridge paths:

- `.devin/rules/alatyr-core.md`

Auto-load behavior: `{DEVIN_CASCADE_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{DEVIN_CASCADE_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{DEVIN_CASCADE_SUPPORTED_SURFACES}`
Tool permission model: `{DEVIN_CASCADE_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{DEVIN_CASCADE_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{DEVIN_CASCADE_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{DEVIN_CASCADE_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{DEVIN_CASCADE_ROUTES_PRE_CHANGE_PREVIEW}`
Routes enabled team operations: `{DEVIN_CASCADE_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{DEVIN_CASCADE_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{DEVIN_CASCADE_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{DEVIN_CASCADE_ROUTES_TEST_FIRST}`
Routes extension aliases: `{DEVIN_CASCADE_ROUTES_EXTENSIONS}`
Routes subagent delegation: `{DEVIN_CASCADE_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/devin-cascade.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/devin-cascade.json`
Routes `alatyr-ai-inventory`: `{DEVIN_CASCADE_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{DEVIN_CASCADE_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{DEVIN_CASCADE_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{DEVIN_CASCADE_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{DEVIN_CASCADE_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{DEVIN_CASCADE_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{DEVIN_CASCADE_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{DEVIN_CASCADE_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

### Assistant Surface: `windsurf`

Assistant: `Windsurf`
Surface id: `windsurf`
Bridge paths:

- `.windsurf/rules/alatyr-core.md`
- `.windsurfrules`

Auto-load behavior: `{WINDSURF_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{WINDSURF_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{WINDSURF_SUPPORTED_SURFACES}`
Tool permission model: `{WINDSURF_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{WINDSURF_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{WINDSURF_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{WINDSURF_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{WINDSURF_ROUTES_PRE_CHANGE_PREVIEW}`
Routes enabled team operations: `{WINDSURF_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{WINDSURF_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{WINDSURF_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{WINDSURF_ROUTES_TEST_FIRST}`
Routes extension aliases: `{WINDSURF_ROUTES_EXTENSIONS}`
Routes subagent delegation: `{WINDSURF_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/windsurf.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/windsurf.json`
Routes `alatyr-ai-inventory`: `{WINDSURF_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{WINDSURF_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{WINDSURF_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{WINDSURF_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{WINDSURF_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{WINDSURF_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{WINDSURF_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{WINDSURF_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

## Canonical Entry Points

Every supported bridge should point back to:

- `AGENTS.md`
- `AI_ASSISTANTS.md`
- `.ai/alatyr.yaml`
- `.ai/README.md`
- `.ai/assistant/context-profiles.md`
- `.ai/assistant/help.md`
- `.ai/assistant/help-reference.md`
- `.ai/assistant/operation-index.json`
- `.ai/assistant/operation-catalog.json`
- `.ai/assistant/flows/operation-routing.flow.md`
- `.ai/assistant/flows/diagram-discussion.flow.md`
- `.ai/assistant/templates/diagram-presentation.md`
- `.ai/assistant/assistant-capabilities.json`

## Recheck Steps

1. Verify each supported bridge file exists or is intentionally skipped.
2. Verify each bridge stays short and points to canonical target files.
3. Verify the operation index exactly derives aliases, modules, flows, and
   allowed actions from the canonical operation catalog.
4. Verify `Alatyr`, status/doctor, automatic routing, preview, and other aliases
   route to canonical operation catalog and flows.
5. Verify diagram discussion uses the current surface's compact capability
   entry, allowed enum values, client version, verification time, and evidence.
6. Verify assistant-specific limitations are recorded.
7. Report unsupported, stale, or manual-load-only surfaces as residual risk.
