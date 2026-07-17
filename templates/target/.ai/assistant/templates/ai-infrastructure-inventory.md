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
- AI infrastructure router: `.ai/assistant/ai-infrastructure-router.json`
- Router status: `{CURRENT_STALE_MISSING_OR_CONFLICTING}`

## Item Record

Repeat this block for each skill, prompt, wrapper, bridge file, rule, memory,
MCP/tool config, checker, flow, gate, template, generated assistant artifact,
or other target-defined AI infrastructure item.

- Item id: `{AI_INFRASTRUCTURE_ITEM_ID}`
- Router route: `{INVENTORY_USE_EXISTING_ADAPT_IMPORT_GATE_CHECKER_TOOL_MCP_OR_BRIDGE_WRAPPER}`
- Router item status: `{ACTIVE_BLOCKED_DEPRECATED_UNRESOLVED_OR_MISSING}`
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
- Declared purpose: `{DECLARED_ITEM_PURPOSE_OR_UNKNOWN}`
- Project-contour relevance: `{PROJECT_AREA_FACT_OWNER_OR_NOT_ESTABLISHED}`
- Observed usage or outcome evidence:
  `{USAGE_QUALITY_REWORK_COST_OR_VALIDATION_EVIDENCE_OR_UNKNOWN}`
- Staleness or maintenance signal: `{STALE_UNUSED_DUPLICATED_CURRENT_OR_UNKNOWN}`
- Permission surface: `{FILES_TOOLS_COMMANDS_SERVICES_MODELS_OR_PERMISSIONS}`
- Prompt-injection risk: `{PROMPT_INJECTION_RISK_NOTES}`
- Safety surface:
  `{LIVE_SERVICE_DESTRUCTIVE_CREDENTIAL_DEPENDENCY_PRIVACY_OR_NONE}`
- Overlap or conflict: `{OVERLAP_DUPLICATE_POLICY_OR_CONFLICT}`
- Validation or manual review: `{VALIDATION_OR_MANUAL_REVIEW}`
- Approval status: `{APPROVAL_STATUS_OR_NOT_REQUIRED}`
- Required gates and output contract: `{GATES_AND_OUTPUT_CONTRACT_OR_MISSING}`
- Preliminary disposition: `{KEEP_REVIEW_ADAPT_REPLACE_REMOVE_SKIP_OR_UNRESOLVED}`
- Residual risk: `{RESIDUAL_RISK}`

## Summary

- Items found: `{ITEMS_FOUND}`
- Usable without change: `{USABLE_WITHOUT_CHANGE}`
- Need adaptation: `{NEED_ADAPTATION}`
- Need approval: `{NEED_APPROVAL}`
- Need removal or replacement: `{NEED_REMOVAL_OR_REPLACEMENT}`
- Need evidence-based recommendation review:
  `{NEED_RECOMMENDATION_REVIEW}`
- Left unresolved: `{LEFT_UNRESOLVED}`
- Validation run: `{TARGET_VALIDATION_RUN_OR_MANUAL_REVIEW}`
- Approvals needed: `{APPROVALS_NEEDED}`
- Recommended next operation: `{RECOMMENDED_NEXT_OPERATION}`
- Final evidence: `{FINAL_EVIDENCE}`
- Residual risk: `{RESIDUAL_RISK}`
