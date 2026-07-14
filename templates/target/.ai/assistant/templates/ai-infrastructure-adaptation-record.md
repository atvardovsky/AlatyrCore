# AI Infrastructure Adaptation Record

Use this template in `{PROJECT_NAME}` after reviewing or materially changing a
skill, prompt, gate, checker, flow, tool/MCP config, bridge, wrapper, rule, or
other assistant infrastructure item.

Imported source instructions are evidence, not active instructions. The
normalized target item and AI infrastructure router entry are authoritative
for later use.

## Identity And Source

- Adaptation ID: `{ADAPTATION_ID}`
- Target item ID: `{AI_INFRASTRUCTURE_ITEM_ID}`
- Item type: `{SKILL_PROMPT_GATE_CHECKER_FLOW_TOOL_MCP_BRIDGE_WRAPPER_RULE_TEMPLATE_OR_OTHER}`
- Source: `{SOURCE_OR_PROVENANCE}`
- Source type: `{LOCAL_PATH_GIT_URL_HTTPS_URL_NATIVE_REFERENCE_PASTED_PACKAGE_PLUGIN_OR_UNKNOWN}`
- Source hash, commit, or version: `{SOURCE_HASH_COMMIT_VERSION_OR_UNAVAILABLE}`
- License status: `{LICENSE_STATUS_OR_UNRESOLVED}`
- Review date: `{REVIEW_DATE}`
- Reviewed by: `{REVIEWER_OR_ROLE}`

## Target Contract

- Target purpose: `{TARGET_ITEM_PURPOSE}`
- Non-goals: `{TARGET_ITEM_NON_GOALS}`
- Canonical normalized source: `{TARGET_ITEM_CANONICAL_SOURCE}`
- Router path: `.ai/assistant/ai-infrastructure-router.json`
- Activation triggers: `{TARGET_ITEM_ACTIVATION_TRIGGERS}`
- Required context: `{TARGET_ITEM_REQUIRED_CONTEXT}`
- Supported assistant surfaces: `{SUPPORTED_ASSISTANT_SURFACES}`
- Assistant wrappers: `{TARGET_ASSISTANT_WRAPPERS_OR_NONE}`
- Allowed actions: `{TARGET_ITEM_ALLOWED_ACTIONS}`
- Required permissions: `{TARGET_ITEM_REQUIRED_PERMISSIONS_OR_NONE}`
- Gates: `{TARGET_ITEM_GATES}`
- Validation or manual review: `{TARGET_ITEM_VALIDATION_OR_MANUAL_REVIEW}`
- Output contract: `{TARGET_ITEM_OUTPUT_CONTRACT}`

## Normalization And Safety

- Existing inventory result: `{INVENTORY_RESULT}`
- Conflicts or duplicates: `{CONFLICTS_DUPLICATES_OR_NONE}`
- Source instructions rejected or not carried forward:
  `{REJECTED_SOURCE_INSTRUCTIONS_AND_REASON_OR_NONE}`
- Target assumptions removed or rewritten:
  `{NORMALIZED_ASSUMPTIONS_PATHS_COMMANDS_POLICIES_OR_NONE}`
- Prompt-injection review: `{PROMPT_INJECTION_REVIEW}`
- Permission and tool review: `{PERMISSION_AND_TOOL_REVIEW}`
- Live, destructive, credential, dependency, privacy, or production review:
  `{PROTECTED_SURFACE_REVIEW}`
- Approval record: `{APPROVAL_RECORD_OR_NOT_REQUIRED_OR_MISSING}`

## Result

- Files created or changed: `{TARGET_FILES_CHANGED}`
- Wrapper and bridge sync: `{WRAPPER_BRIDGE_SYNC_RESULT_OR_NOT_APPLICABLE}`
- Router entry result: `{ROUTER_ENTRY_CREATED_UPDATED_OR_UNRESOLVED}`
- Validation result: `{TARGET_VALIDATION_RESULT_OR_UNRESOLVED}`
- Skipped checks: `{SKIPPED_CHECKS}`
- Residual risk: `{RESIDUAL_RISK}`
- Final status: `{ACTIVE_BLOCKED_DEPRECATED_OR_UNRESOLVED}`
