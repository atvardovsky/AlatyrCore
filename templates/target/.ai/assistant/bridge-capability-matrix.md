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

When delegation is selected, every surface routes through
`.ai/assistant/prompts/worker-orchestration.md` and the project-owned role,
task, packet, and result contracts. Native worker definitions are thin target
bindings whose verified format and paths belong to the selected capability
record; no surface inherits support claims from another.

Each schema-4 surface record also separates assistant client from model
provider and records context-cache mode, exposed controls and telemetry,
retention/minimum-size evidence, freshness, stable-prefix ordering, and the
bounded-context fallback. Unknown provider or client behavior remains unknown.
Caching is optional and does not reduce context-window occupancy.

## Supported Assistant Surfaces

Resolve these entries from target evidence before claiming a bridge is
supported. If the target does not use a surface, keep the entry and mark it
unsupported or not applicable with the reason.

### Assistant Surface: `generic`

Assistant: `Generic assistant`
Surface id: `generic`
Capability state: {GENERIC_CAPABILITY_STATE}
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
Routes action authorization: `{GENERIC_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{GENERIC_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{GENERIC_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{GENERIC_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{GENERIC_ROUTES_TEST_FIRST}`
Routes extension aliases: `{GENERIC_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/generic.json`
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
Capability state: {AGENTS_CAPABILITY_STATE}
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
Routes action authorization: `{AGENTS_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{AGENTS_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{AGENTS_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{AGENTS_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{AGENTS_ROUTES_TEST_FIRST}`
Routes extension aliases: `{AGENTS_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/agents.json`
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
Capability state: {CODEX_CAPABILITY_STATE}
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
Routes action authorization: `{CODEX_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{CODEX_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{CODEX_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{CODEX_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{CODEX_ROUTES_TEST_FIRST}`
Routes extension aliases: `{CODEX_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/codex.json`
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

### Assistant Surface: `junie`

Assistant: `JetBrains Junie`
Surface id: `junie`
Capability state: {JUNIE_CAPABILITY_STATE}
Bridge paths:

- `AGENTS.md`

Auto-load behavior: `{JUNIE_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{JUNIE_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{JUNIE_SUPPORTED_SURFACES}`
Tool permission model: `{JUNIE_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{JUNIE_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{JUNIE_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{JUNIE_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{JUNIE_ROUTES_PRE_CHANGE_PREVIEW}`
Routes action authorization: `{JUNIE_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{JUNIE_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{JUNIE_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{JUNIE_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{JUNIE_ROUTES_TEST_FIRST}`
Routes extension aliases: `{JUNIE_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/junie.json`
Routes subagent delegation: `{JUNIE_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/junie.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/junie.json`
Routes `alatyr-ai-inventory`: `{JUNIE_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{JUNIE_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{JUNIE_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{JUNIE_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{JUNIE_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{JUNIE_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{JUNIE_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{JUNIE_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

### Assistant Surface: `cline`

Assistant: `Cline`
Surface id: `cline`
Capability state: {CLINE_CAPABILITY_STATE}
Bridge paths:

- `AGENTS.md`

Auto-load behavior: `{CLINE_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{CLINE_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{CLINE_SUPPORTED_SURFACES}`
Tool permission model: `{CLINE_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{CLINE_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{CLINE_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{CLINE_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{CLINE_ROUTES_PRE_CHANGE_PREVIEW}`
Routes action authorization: `{CLINE_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{CLINE_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{CLINE_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{CLINE_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{CLINE_ROUTES_TEST_FIRST}`
Routes extension aliases: `{CLINE_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/cline.json`
Routes subagent delegation: `{CLINE_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/cline.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/cline.json`
Routes `alatyr-ai-inventory`: `{CLINE_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{CLINE_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{CLINE_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{CLINE_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{CLINE_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{CLINE_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{CLINE_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{CLINE_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

### Assistant Surface: `roo-code`

Assistant: `Roo Code (legacy)`
Surface id: `roo-code`
Capability state: {ROO_CODE_CAPABILITY_STATE}
Bridge paths:

- `.roo/rules/alatyr-core.md`
- `AGENTS.md`

Auto-load behavior: `{ROO_CODE_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{ROO_CODE_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{ROO_CODE_SUPPORTED_SURFACES}`
Tool permission model: `{ROO_CODE_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{ROO_CODE_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{ROO_CODE_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{ROO_CODE_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{ROO_CODE_ROUTES_PRE_CHANGE_PREVIEW}`
Routes action authorization: `{ROO_CODE_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{ROO_CODE_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{ROO_CODE_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{ROO_CODE_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{ROO_CODE_ROUTES_TEST_FIRST}`
Routes extension aliases: `{ROO_CODE_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/roo-code.json`
Routes subagent delegation: `{ROO_CODE_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/roo-code.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/roo-code.json`
Routes `alatyr-ai-inventory`: `{ROO_CODE_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{ROO_CODE_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{ROO_CODE_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{ROO_CODE_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{ROO_CODE_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{ROO_CODE_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{ROO_CODE_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{ROO_CODE_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

### Assistant Surface: `kiro`

Assistant: `Kiro`
Surface id: `kiro`
Capability state: {KIRO_CAPABILITY_STATE}
Bridge paths:

- `AGENTS.md`

Auto-load behavior: `{KIRO_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{KIRO_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{KIRO_SUPPORTED_SURFACES}`
Tool permission model: `{KIRO_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{KIRO_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{KIRO_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{KIRO_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{KIRO_ROUTES_PRE_CHANGE_PREVIEW}`
Routes action authorization: `{KIRO_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{KIRO_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{KIRO_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{KIRO_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{KIRO_ROUTES_TEST_FIRST}`
Routes extension aliases: `{KIRO_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/kiro.json`
Routes subagent delegation: `{KIRO_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/kiro.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/kiro.json`
Routes `alatyr-ai-inventory`: `{KIRO_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{KIRO_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{KIRO_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{KIRO_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{KIRO_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{KIRO_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{KIRO_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{KIRO_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

### Assistant Surface: `zed-agent`

Assistant: `Zed Agent`
Surface id: `zed-agent`
Capability state: {ZED_AGENT_CAPABILITY_STATE}
Bridge paths:

- `.rules`

Auto-load behavior: `{ZED_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{ZED_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{ZED_SUPPORTED_SURFACES}`
Tool permission model: `{ZED_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{ZED_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{ZED_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{ZED_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{ZED_ROUTES_PRE_CHANGE_PREVIEW}`
Routes action authorization: `{ZED_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{ZED_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{ZED_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{ZED_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{ZED_ROUTES_TEST_FIRST}`
Routes extension aliases: `{ZED_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/zed-agent.json`
Routes subagent delegation: `{ZED_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/zed-agent.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/zed-agent.json`
Routes `alatyr-ai-inventory`: `{ZED_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{ZED_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{ZED_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{ZED_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{ZED_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{ZED_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{ZED_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{ZED_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

### Assistant Surface: `opencode`

Assistant: `OpenCode`
Surface id: `opencode`
Capability state: {OPENCODE_CAPABILITY_STATE}
Bridge paths:

- `AGENTS.md`

Auto-load behavior: `{OPENCODE_AUTO_LOAD_BEHAVIOR}`
Instruction priority: `{OPENCODE_INSTRUCTION_PRIORITY_OR_UNKNOWN}`
Supported rule/prompt/skill surfaces: `{OPENCODE_SUPPORTED_SURFACES}`
Tool permission model: `{OPENCODE_TOOL_PERMISSION_MODEL_OR_UNKNOWN}`
Routes operation help: `{OPENCODE_ROUTES_OPERATION_HELP}`
Routes single `Alatyr` entry: `{OPENCODE_ROUTES_ALATYR_ENTRY}`
Routes adapter health: `{OPENCODE_ROUTES_ADAPTER_HEALTH}`
Routes pre-change preview: `{OPENCODE_ROUTES_PRE_CHANGE_PREVIEW}`
Routes action authorization: `{OPENCODE_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{OPENCODE_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{OPENCODE_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{OPENCODE_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{OPENCODE_ROUTES_TEST_FIRST}`
Routes extension aliases: `{OPENCODE_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/opencode.json`
Routes subagent delegation: `{OPENCODE_ROUTES_SUBAGENT_DELEGATION}`
Subagent delegation capability record: `.ai/assistant/assistant-capabilities/opencode.json`
Diagram capability record: `.ai/assistant/assistant-capabilities/opencode.json`
Routes `alatyr-ai-inventory`: `{OPENCODE_ROUTES_AI_INVENTORY}`
Routes `alatyr-suggest-ai`: `{OPENCODE_ROUTES_AI_RECOMMENDATION}`
Routes `alatyr-improve-ai`: `{OPENCODE_ROUTES_AI_IMPROVEMENT}`
Routes `alatyr-adaptation`: `{OPENCODE_ROUTES_ADAPTATION}`
Routes `alatyr-add-ai`: `{OPENCODE_ROUTES_ADD_AI}`
Routes AI infrastructure items: `{OPENCODE_ROUTES_AI_INFRASTRUCTURE_ITEMS}`
Known limitations: `{OPENCODE_KNOWN_LIMITATIONS_OR_NONE}`
Conformance check: `{OPENCODE_CONFORMANCE_CHECK_OR_MANUAL_REVIEW}`

### Assistant Surface: `claude`

Assistant: `Claude`
Surface id: `claude`
Capability state: {CLAUDE_CAPABILITY_STATE}
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
Routes action authorization: `{CLAUDE_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{CLAUDE_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{CLAUDE_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{CLAUDE_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{CLAUDE_ROUTES_TEST_FIRST}`
Routes extension aliases: `{CLAUDE_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/claude.json`
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
Capability state: {GEMINI_CAPABILITY_STATE}
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
Routes action authorization: `{GEMINI_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{GEMINI_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{GEMINI_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{GEMINI_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{GEMINI_ROUTES_TEST_FIRST}`
Routes extension aliases: `{GEMINI_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/gemini.json`
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
Capability state: {GITHUB_COPILOT_CAPABILITY_STATE}
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
Routes action authorization: `{GITHUB_COPILOT_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{GITHUB_COPILOT_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{GITHUB_COPILOT_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{GITHUB_COPILOT_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{GITHUB_COPILOT_ROUTES_TEST_FIRST}`
Routes extension aliases: `{GITHUB_COPILOT_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/github-copilot.json`
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
Capability state: {CURSOR_CAPABILITY_STATE}
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
Routes action authorization: `{CURSOR_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{CURSOR_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{CURSOR_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{CURSOR_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{CURSOR_ROUTES_TEST_FIRST}`
Routes extension aliases: `{CURSOR_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/cursor.json`
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
Capability state: {DEVIN_CASCADE_CAPABILITY_STATE}
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
Routes action authorization: `{DEVIN_CASCADE_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{DEVIN_CASCADE_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{DEVIN_CASCADE_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{DEVIN_CASCADE_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{DEVIN_CASCADE_ROUTES_TEST_FIRST}`
Routes extension aliases: `{DEVIN_CASCADE_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/devin-cascade.json`
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
Capability state: {WINDSURF_CAPABILITY_STATE}
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
Routes action authorization: `{WINDSURF_ROUTES_ACTION_AUTHORIZATION}`
Routes enabled team operations: `{WINDSURF_ROUTES_TEAM_OPERATIONS}`
Routes code-documentation aliases: `{WINDSURF_ROUTES_CODE_DOCUMENTATION}`
Routes project-vocabulary aliases: `{WINDSURF_ROUTES_PROJECT_VOCABULARY}`
Routes test-first aliases: `{WINDSURF_ROUTES_TEST_FIRST}`
Routes extension aliases: `{WINDSURF_ROUTES_EXTENSIONS}`
Context caching: `{TARGET_SURFACE_CONTEXT_CACHE_SUPPORT_AND_CLIENT_EXPOSURE}`
Context caching capability record: `.ai/assistant/assistant-capabilities/windsurf.json`
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
