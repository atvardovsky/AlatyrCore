# Native Worker Binding

Use this provider-neutral authoring template only after the selected assistant
capability record verifies project-owned worker definitions for the exact
target client/runtime. The installed native file uses that client's required
format; this template remains the adaptation evidence.

Assistant surface: `{ASSISTANT_SURFACE}`
Client product/runtime: `{CLIENT_PRODUCT_AND_RUNTIME_VARIANT}`
Client version: `{CLIENT_VERSION}`
Native definition format: `{VERIFIED_NATIVE_FORMAT}`
Native definition path: `{TARGET_REPOSITORY_RELATIVE_PATH}`
Role ID: `{ENABLED_TARGET_ROLE_ID}`
Role prompt: `{TARGET_ROLE_PROMPT_PATH}`
Model selection: `{EXPLICIT_MODEL_INHERIT_OR_CLIENT_DEFAULT}`
Model/reasoning evidence: `{CAPABILITY_EVIDENCE_OR_UNVERIFIED}`
Tool restrictions: `{TARGET_NATIVE_TOOL_RESTRICTIONS}`
Write isolation: `{TARGET_VERIFIED_WRITE_ISOLATION}`
Verification/expiry: `{VERIFIED_AT_AND_EXPIRY_OR_REVIEW_TRIGGER}`

Canonical references:

- `.ai/assistant/delegation-policy.json`
- `.ai/assistant/workers/role-catalog.json`
- `.ai/assistant/prompts/worker-orchestration.md`
- `.ai/assistant/templates/subagent-task-packet.md`
- `.ai/assistant/templates/worker-result.md`

The native definition must stay thin. It may express client-required metadata,
role purpose, model selection, tool restrictions, and pointers to canonical
target contracts. It must not duplicate full project/framework policy, grant
new action phases or approval, activate nested adapters, or infer unsupported
client features.

After creating or changing the native file, record its exact path in the
selected capability record and rerun target validation. If support becomes
unknown, unsupported, or stale, disable the binding and use suggestion-only or
sequential-primary fallback rather than relocating it by assumption.
