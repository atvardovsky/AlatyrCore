# AI Infrastructure Inventory

Use this file in `{PROJECT_NAME}` to record the result of
`ai-infrastructure-inventory` or `alatyr-ai-inventory`.

Replace placeholders with target facts before accepting installation.

Inventory-only work must not import, install, execute, or normalize external
AI infrastructure into canonical target files.

## Inventory Scope

- Operation id: `{OPERATION_ID}`
- Inventory date: `{INVENTORY_DATE}`
- Requested by: `{REQUESTER_OR_ROLE}`
- Allowed actions: `{READ_ONLY_OR_ADAPTER_ONLY}`
- Target assistant surfaces: `{TARGET_ASSISTANT_SURFACES}`
- Source access policy:
  `.ai/assistant/policies/ai-infrastructure-source-access.md`
- Prompt-injection policy: `.ai/assistant/policies/prompt-injection.md`
- Surfaces inspected: `{SURFACES_INSPECTED}`
- Surfaces skipped: `{SURFACES_SKIPPED_AND_REASON}`
- Existing inventory source: `{EXISTING_INVENTORY_SOURCE_OR_NONE}`

## Item Record

Repeat this block for each skill, prompt, wrapper, bridge file, rule, memory,
MCP/tool config, checker, flow, gate, template, generated assistant artifact,
or other target-defined AI infrastructure item.

- Item id: `{AI_INFRASTRUCTURE_ITEM_ID}`
- Item type:
  `{SKILL_PROMPT_WRAPPER_BRIDGE_RULE_MEMORY_MCP_TOOL_CHECKER_FLOW_GATE_TEMPLATE_GENERATED_ARTIFACT_OR_OTHER}`
- Path or reference: `{PATH_OR_EXTERNAL_REFERENCE}`
- Owner:
  `{FRAMEWORK_PROJECT_REPOSITORY_ADAPTER_BRIDGE_GENERATED_EXTERNAL_UNKNOWN}`
- Source/provenance: `{SOURCE_OR_PROVENANCE}`
- Source type:
  `{LOCAL_PATH_GIT_URL_HTTPS_URL_NATIVE_REFERENCE_PASTED_PACKAGE_PLUGIN_UNKNOWN}`
- Source hash or commit: `{SOURCE_HASH_COMMIT_VERSION_OR_UNAVAILABLE}`
- License: `{LICENSE_UNKNOWN_NOT_APPLICABLE}`
- Supported assistants: `{SUPPORTED_ASSISTANTS}`
- Permission surface: `{FILES_TOOLS_COMMANDS_SERVICES_MODELS_OR_PERMISSIONS}`
- Prompt-injection risk: `{PROMPT_INJECTION_RISK_NOTES}`
- Safety surface:
  `{LIVE_SERVICE_DESTRUCTIVE_CREDENTIAL_DEPENDENCY_PRIVACY_OR_NONE}`
- Overlap or conflict: `{OVERLAP_DUPLICATE_POLICY_OR_CONFLICT}`
- Validation or manual review: `{VALIDATION_OR_MANUAL_REVIEW}`
- Approval status: `{APPROVAL_STATUS_OR_NOT_REQUIRED}`
- Recommended action: `{KEEP_ADAPT_ADD_REPLACE_REMOVE_SKIP_OR_UNRESOLVED}`
- Residual risk: `{RESIDUAL_RISK}`

## Summary

- Items found: `{ITEMS_FOUND}`
- Usable without change: `{USABLE_WITHOUT_CHANGE}`
- Need adaptation: `{NEED_ADAPTATION}`
- Need approval: `{NEED_APPROVAL}`
- Need removal or replacement: `{NEED_REMOVAL_OR_REPLACEMENT}`
- Left unresolved: `{LEFT_UNRESOLVED}`
- Validation run: `{TARGET_VALIDATION_RUN_OR_MANUAL_REVIEW}`
- Approvals needed: `{APPROVALS_NEEDED}`
- Recommended next operation: `{RECOMMENDED_NEXT_OPERATION}`
- Final evidence: `{FINAL_EVIDENCE}`
- Residual risk: `{RESIDUAL_RISK}`

