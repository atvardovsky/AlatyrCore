# Target Adapter Validator Findings

This generated reference lists stable finding identifiers emitted by the
portable target-adapter validator. A finding describes structural evidence;
it does not prove project semantics or replace logical integrity review.

Regenerate both catalog surfaces with:

```sh
python3 tools/render_target_validator_findings.py
```

Catalog entries: 1080

## Families

- `AI`: 16 codes.
- `APPROVAL`: 31 codes.
- `ARCHITECTURE`: 33 codes.
- `ASSISTANT`: 15 codes.
- `AUTHORIZATION`: 16 codes.
- `BACKUP`: 1 codes.
- `BOOTSTRAP`: 8 codes.
- `CAPABILITY`: 7 codes.
- `CODEDOC`: 32 codes.
- `CONSISTENCY`: 32 codes.
- `DEBUG`: 117 codes.
- `DELEGATION`: 59 codes.
- `DEPENDENCY`: 55 codes.
- `DEVELOPMENT`: 15 codes.
- `DIAGRAM`: 32 codes.
- `DIFF`: 3 codes.
- `ENABLED`: 1 codes.
- `ENGINEERING`: 41 codes.
- `EVIDENCE`: 1 codes.
- `EXTENSION`: 65 codes.
- `FRAMEWORK`: 16 codes.
- `GATE`: 1 codes.
- `INSTALLATION`: 3 codes.
- `LOCAL`: 1 codes.
- `MANIFEST`: 11 codes.
- `MIGRATION`: 8 codes.
- `MODULE`: 5 codes.
- `OPERATION`: 29 codes.
- `PACKAGE`: 78 codes.
- `PLACEHOLDERS`: 1 codes.
- `PROFILE`: 2 codes.
- `PROJECT`: 52 codes.
- `REQUIRED`: 1 codes.
- `ROUTED`: 1 codes.
- `ROUTER`: 52 codes.
- `ROUTING`: 2 codes.
- `RULE`: 1 codes.
- `STALE`: 2 codes.
- `TARGET`: 6 codes.
- `TDD`: 44 codes.
- `TEAM`: 98 codes.
- `UNRESOLVED`: 1 codes.
- `VOCABULARY`: 44 codes.
- `WORKSPACE`: 40 codes.
- `{prefix}`: 1 codes.

## Codes

- `AI_ROUTER_ALLOWED_ACTION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AI_ROUTER_ITEMS`
  Level: error. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `AI_ROUTER_ITEM_DUPLICATE`
  Level: error. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `AI_ROUTER_ITEM_FIELD`
  Level: error. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `AI_ROUTER_ITEM_ID`
  Level: error. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `AI_ROUTER_ITEM_SHAPE`
  Level: error. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `AI_ROUTER_ITEM_STATUS`
  Level: error. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `AI_ROUTER_ITEM_TYPE`
  Level: error. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `AI_ROUTER_ITEM_TYPES`
  Level: error. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `AI_ROUTER_KIND`
  Level: error. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `AI_ROUTER_LEGACY_SCHEMA`
  Level: warning. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `AI_ROUTER_RECOMMENDATION_TEMPLATE`
  Level: error. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `AI_ROUTER_ROUTES`
  Level: error. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `AI_ROUTER_ROUTE_MISSING`
  Level: error. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `AI_ROUTER_ROUTE_SHAPE`
  Level: error. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `AI_ROUTER_SCHEMA`
  Level: error. Source: `tools/target_adapter_validation/ai_infrastructure.py`.
- `APPROVAL_ARCHIVE_CHECKED`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_DIFF_BASE_MISMATCH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_DIFF_REF_REQUIRED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_PATCH_CHANGED`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_PATCH_HASH_MATCH`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_PATCH_HASH_MISMATCH`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_PATCH_HASH_NOT_VERIFIABLE`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_PATCH_HASH_SKIPPED`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_PATCH_HASH_UNAVAILABLE`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_PLAN_FILE_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_PLAN_FILE_OUTSIDE_TARGET`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_PLAN_HASH_MATCH`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_PLAN_HASH_MISMATCH`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_PLAN_HASH_NOT_VERIFIABLE`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_PLAN_HASH_UNVERIFIED`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_RECORD_EVIDENCE_CLASS`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_RECORD_FIELD_MISSING`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_RECORD_INVALID_JSON`
  Level: dynamic, error. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_RECORD_INVALID_SHAPE`
  Level: dynamic, error. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_RECORD_KIND`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_RECORD_MACHINE_READABLE_REQUIRED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_RECORD_MISSING`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_RECORD_OUTSIDE_TARGET`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_RECORD_SCHEMA`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_RECORD_SCOPE_EMPTY`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_RECORD_SCOPE_INVALID`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_RECORD_SELECTION_REQUIRED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_SCOPE_DECLARED_BROKEN`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_SCOPE_ENFORCED`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_SCOPE_EXCLUDED`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `APPROVAL_SCOPE_MISMATCH`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_ACCEPTED_EVIDENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_AREAS_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_AREA_FIELDS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_AREA_ID_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_AREA_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_CATALOG_INDEX`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_CATALOG_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_CATALOG_LIST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_CATALOG_METADATA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_CATALOG_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_CONTRACT_INCOMPLETE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_ENABLED_METADATA_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_ITEM_EVIDENCE_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_ITEM_FIELD_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_ITEM_IDENTITY_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_ITEM_STATUS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_KNOWN_GAP_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_MANIFEST_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_MODULE_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_MODULE_STATE_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_MODULE_UNDECLARED`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_OPERATION_ACTIONS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_OPERATION_FLOW`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_OPERATION_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_OPERATION_MODULE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_OPERATION_UNROUTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_PATTERNS_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_PATTERN_FIELDS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_PATTERN_ID_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_PATTERN_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_PATTERN_REFERENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_PATTERN_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ARCHITECTURE_REQUIRED_FILE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_AUTO_LOAD_UNPROVEN`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_CAPABILITY_FIELDS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_CAPABILITY_ID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_CAPABILITY_INDEX_ENTRY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_CAPABILITY_LIST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_CAPABILITY_REVIEW_TRIGGERS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_CAPABILITY_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_CAPABILITY_SECTION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_CAPABILITY_SELECTED_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_CAPABILITY_SURFACES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_INSTRUCTION_LOADING_UNVERIFIED`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_INSTRUCTION_ROUTE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_PERMISSION_AUTHORIZATION_CONFLICT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_SELECTED_ENTRY_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ASSISTANT_SELECTED_UNSUPPORTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_BOUNDARY_CONFLATED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_CATALOG_EVIDENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_CATALOG_PHASES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_CATALOG_ROUTE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_DELEGATION_ESCALATION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_EVIDENCE_FIELD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_PHASE_GATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_POLICY_EFFECTS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_POLICY_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_POLICY_PHASES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_POLICY_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_POLICY_SCOPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_SCOPE_INVALIDATION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_SCOPE_REUSE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_SURFACE_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `AUTHORIZATION_SURFACE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `BACKUP_OWNER_UNRESOLVED`
  Level: configured. Source: `tools/validate_target_adapter.py`.
- `BOOTSTRAP_AREA_MAP_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `BOOTSTRAP_CONTEXT_ROUTER_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `BOOTSTRAP_INDEX_CURRENT`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `BOOTSTRAP_INDEX_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `BOOTSTRAP_INDEX_INVALID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `BOOTSTRAP_INDEX_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `BOOTSTRAP_INDEX_REFERENCE_MISSING`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `BOOTSTRAP_INDEX_SOURCE_INVALID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CAPABILITY_CATALOG_INVALID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CAPABILITY_CATALOG_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CAPABILITY_DEPENDENCY_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CAPABILITY_FRAMEWORK_FILE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CAPABILITY_MODULE_UNKNOWN`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CAPABILITY_PACK_TOO_SMALL`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CAPABILITY_TARGET_FILE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_ACCEPTED_AMBIGUITY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_ACCEPTED_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_AREAS_EMPTY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_AREA_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_CATALOG_INDEX`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_CATALOG_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_CATALOG_PROFILES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_CATALOG_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_COMMENT_CONTRACT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_CONTRACT_INCOMPLETE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_DIRECT_EDIT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_ENABLED_METADATA_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_EVIDENCE_LIMIT`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_GENERATION_CONTRACT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_LIST_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_MANIFEST_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_MODULE_STATE_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_MODULE_UNDECLARED`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_NO_ACCEPTED_PROFILE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_OPERATION_UNROUTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_OUTPUT_POLICY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_PROFILES_EMPTY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_PROFILE_FIELDS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_PROFILE_ID_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_PROFILE_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_PROFILE_MATCH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_PROFILE_REFERENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_PROFILE_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_PROFILE_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_PROFILE_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_REQUIRED_FILE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CODEDOC_SELECTION_POLICY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `CONSISTENCY_MAP_DIRECTION`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_EDGES`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_EDGE_DUPLICATE`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_EDGE_ID`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_EDGE_SHAPE`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_EDGE_TYPE`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_IMPACT_POLICY`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_KIND`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_LEVELS`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_NODES`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_NODE_AREA`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_NODE_DUPLICATE`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_NODE_FACT_TYPE`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_NODE_ID`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_NODE_LEVEL`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_NODE_SHAPE`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_OWNER_MISSING`
  Level: warning. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_OWNER_PATH`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_REGISTRY`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_REGISTRY_EMPTY`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_REGISTRY_MISSING`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_REGISTRY_SYNC_POLICY`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_RELATIONSHIPS`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_SCHEMA`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_SCHEMA_LEGACY`
  Level: warning. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_MAP_TARGET_LEVEL`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_REGISTRY_FACT_TYPE_DRIFT`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_REGISTRY_FACT_TYPE_DUPLICATE`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_REGISTRY_NODE_FACT_TYPE_DRIFT`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_REGISTRY_NODE_MISSING`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_REGISTRY_NODE_REUSED`
  Level: error. Source: `tools/target_adapter_validation/consistency_map.py`.
- `CONSISTENCY_REGISTRY_NODE_UNRESOLVED`
  Level: configured. Source: `tools/target_adapter_validation/consistency_map.py`.
- `DEBUG_MODE_ACTIVATION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_ACTIVE_COMPLETION_TIME`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_AGENT_CLASSIFICATION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_ARCHITECTURAL_IMPACT_MISSING`
  Level: dynamic. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_ARCHITECTURAL_SUPERVISION_DRIFT`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_ARCHITECTURAL_SUPERVISION_ORIGIN`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_CAPTURE_QUALITY`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_CHECKED`
  Level: info. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_CLAIM_EVIDENCE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_CLAIM_FIDELITY`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_CLAIM_UNCERTAINTY`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_COMPLETED_EMPTY`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_COMPLETED_METRICS`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_COMPLETION_TIME_REQUIRED`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_CONTINUATION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_CONTINUATION_CYCLE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_CONTINUATION_LINEAGE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_CONTINUATION_REFERENCE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_CONTINUATION_SCOPE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_CONTINUATION_STATE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_CONTRACT_VERSION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_DERIVATION_CAUSE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_DIRECTION_HYPOTHESIS_MISSING`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_DIRECTION_IMPACT_MISSING`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_DIRECTION_REPLACEMENT_MISSING`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_ENGINEERING_EVIDENCE_EVENT_ID`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_ENGINEERING_EVIDENCE_LINEAGE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_ENGINEERING_EVIDENCE_RECIPROCITY`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_ENGINEERING_EVIDENCE_REFERENCE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVENT_CAUSAL_TIME`
  Level: dynamic. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVENT_CAUSE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVENT_CAUSE_ORDER`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVENT_DUPLICATE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVENT_EVIDENCE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVENT_ID`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVENT_SEQUENCE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVENT_TIME_ORDER`
  Level: dynamic. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVENT_TIME_WINDOW`
  Level: dynamic. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVIDENCE_BLOCKED`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVIDENCE_CAPTURE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVIDENCE_DECISION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVIDENCE_EVENT_LINK`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVIDENCE_EVENT_ROLE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVIDENCE_PENDING`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVIDENCE_SKIP`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVIDENCE_SKIP_UNKNOWN`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EVIDENCE_TRIGGER`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EXPIRY`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_EXTERNAL_RECORD_UNCHECKED`
  Level: warning. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_IMPLEMENTATION_CONTINUATION_MISSING`
  Level: warning. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEPENDENCE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_DRIFT`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_DUPLICATE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_ENTRY`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_FIELD`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_ID`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_KIND`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_LEGACY`
  Level: warning. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_LIST`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_METADATA`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_METADATA_UNRESOLVED`
  Level: dynamic. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_METRICS`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_RECORD`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_RECORDS`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_RECORD_VERSION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INDEX_SCHEMA`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_INTERVENTION_CLASSIFICATION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_KNOWLEDGE_CANDIDATE_COVERAGE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_KNOWLEDGE_CANDIDATE_DUPLICATE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_KNOWLEDGE_CANDIDATE_EVENT`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_KNOWLEDGE_CANDIDATE_EVIDENCE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_KNOWLEDGE_CANDIDATE_OWNER`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_KNOWLEDGE_CANDIDATE_PROMOTION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_LEGACY_ATTRIBUTION`
  Level: warning. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_LIFECYCLE_COMPLETE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_LIFECYCLE_CONTINUATION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_LIFECYCLE_FINALIZATION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_LIFECYCLE_IMPLEMENTATION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_LIFECYCLE_PARTITION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_LIFECYCLE_PHASE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_LIFECYCLE_STATE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_LIFECYCLE_VALIDATION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_MANIFEST_PATH`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_MATERIALITY_EVENT`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_MATERIALITY_EVENT_LINK`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_MATERIALITY_EVIDENCE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_MATERIALITY_SET`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_MATERIALITY_TRIGGER`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_METRIC_DRIFT`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_METRIC_EVENT`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_METRIC_UNAVAILABLE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_OBSERVER_EFFECT`
  Level: warning. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_POST_REVIEW_CAUSE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_PRESERVATION_OWNER`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_PRESERVATION_REGISTRY`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_PRESERVATION_SCOPE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_PRESERVATION_SOURCE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_PRIVACY`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_PROHIBITED_CONTENT_FIELD`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_PUBLICATION_SCOPE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_RECORD_DUPLICATE`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_RECORD_LOCATION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_RECORD_PATH`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_RECORD_SCHEMA`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_REVIEW_CORRECTION_UNASSESSED`
  Level: warning. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_SOURCE_SCHEMA`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_STRUCTURED_CLASSIFICATION_MISSING`
  Level: warning. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_TEMPLATE_BINDING`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_TEMPLATE_CONTINUATION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_TEMPLATE_EVIDENCE_DECISION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_TEMPLATE_VERSION`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_TIMING`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_TIMING_DRIFT`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_TIMING_ORDER`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_UPSTREAM_BOUNDARY`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_UPSTREAM_PATH`
  Level: error. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DEBUG_MODE_V2_CONTRACT`
  Level: warning. Source: `tools/target_adapter_validation/debug_mode.py`.
- `DELEGATION_CAPABILITY_FIELDS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_CAPABILITY_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_CAPABILITY_SURFACES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_CAPABILITY_VALUE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_CONFLICT_GUARDS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_DECISION_MODE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_DEFAULT_PREFERENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_DISPATCH_BACKEND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ENABLED_ROLES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ENABLED_ROLE_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ENABLED_ROLE_INACTIVE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ENABLED_ROLE_UNBOUND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ENABLED_ROLE_UNKNOWN`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_EXPLICIT_MODEL_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_EXTERNAL_DISPATCHER`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_EXTERNAL_ROUTE_UNSUPPORTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_MODEL_OVERRIDE_UNSUPPORTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_MODEL_SELECTION_MODE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_NATIVE_BACKEND_UNSUPPORTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_NATIVE_INVOCATION_UNSUPPORTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_NATIVE_ROUTE_UNSUPPORTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_OVERLAY_CONTEXT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_OVERLAY_CONTRACT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_PARALLEL_LIMIT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_POLICY_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_POLICY_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_POLICY_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_REQUIRED_FILE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_REQUIRED_GUARDS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_RESULT_GUARDS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_RETRY_LIMIT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_RETRY_POLICY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_RETRY_SCOPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLES_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_ACTION_CEILING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_BINDINGS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_BINDING_AVAILABILITY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_BINDING_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_BINDING_ROUTE_CONFLICT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_BINDING_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_BINDING_UNKNOWN`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_CATALOG_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_CATALOG_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_PROMPT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_RESULT_CONTRACT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_WRITE_CEILING_CONFLICT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_ROLE_WRITE_MODE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_SHARED_WRITE_ISOLATION`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_UNSUPPORTED_ROUTE_CONFLICT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_WORKER_DEFINITION_FORMAT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_WORKER_DEFINITION_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_WORKER_DEFINITION_NOT_THIN`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_WORKER_DEFINITION_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_WORKER_DEFINITION_PATHS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_WORKER_DEFINITION_STATE_CONFLICT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DELEGATION_WRITE_ISOLATION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_APPLICABILITY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_AUTHORITY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_CATALOG_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_CATALOG_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_DEVIATIONS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_DEVIATION_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_DEVIATION_EXPORT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_DEVIATION_EXPORTS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_DEVIATION_INSTANCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_DEVIATION_RECORD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_DEVIATION_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_DEVIATION_SOURCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_DEVIATION_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_DEVIATION_TYPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_DISCOVERY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_EVIDENCE_LIMIT`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_EXPORT_DIGEST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_EXPORT_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_EXPORT_EVIDENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_EXPORT_RECORD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_EXPORT_SET_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_EXPORT_STATUS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_FINGERPRINT_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_FRESHNESS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_GRAPH_RECORD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_GRAPH_REFERENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_INSTANCES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_INSTANCE_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_INSTANCE_RECORD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_INTENT_UNROUTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_LIMIT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_LIMITS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_LOCK_EXPORT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_LOCK_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_LOCK_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_MANIFEST_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_MANIFEST_RECORD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_METADATA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_MODIFICATIONS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_OPERATION_UNROUTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_PACKAGES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_PACKAGE_RECORD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_POLICY_OWNER`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_POLICY_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_POLICY_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_REQUIRED_FILE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_ROUTING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_SOURCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_SOURCES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_SOURCE_LOCATOR`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_SOURCE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_SOURCE_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_STABILITY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_TRUST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEPENDENCY_KNOWLEDGE_TRUST_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_CONTENT_POLICY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_METADATA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_METADATA_UNRESOLVED`
  Level: configured. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_OCCURRENCE_COUNT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_PATTERNS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_PATTERN_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_PATTERN_FIELD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_PATTERN_LIST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_PATTERN_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_QUALITY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_REFERENCE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DEVELOPMENT_EVIDENCE_STATUS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_BRIDGE_CAPABILITY_FIELD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_BRIDGE_CAPABILITY_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_ARTIFACT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_ASCII_FALLBACK`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_CLIENT_VERSION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_EVIDENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_EXPIRED`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_EXPIRY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_FIELDS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_FRESHNESS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_INDEX_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_REVIEW_TRIGGERS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_ROUTE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_SURFACES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_SURFACE_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CAPABILITY_SYNTAXES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_CONTRACT_INCOMPLETE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_MANIFEST_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_MODULE_STATE_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_MODULE_UNDECLARED`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_OPERATION_ACTIONS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_OPERATION_FLOW`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_OPERATION_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_OPERATION_MODULE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_OPERATION_UNROUTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_REQUIRED_FILE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_SURFACE_CAPABILITY_ID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_SURFACE_CAPABILITY_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIAGRAM_SURFACE_CAPABILITY_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `DIFF_SCOPE_CLEAN`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `DIFF_SCOPE_SKIPPED`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `DIFF_SCOPE_UNAVAILABLE`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `ENABLED_MODULE_STALE_STATUS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ENGINEERING_EVIDENCE_ALTERNATIVES`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_CHECKED`
  Level: info. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_CONTRACT_VERSION`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_DEBUG_LINEAGE`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_DEBUG_RECIPROCITY`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_DEBUG_REFERENCE`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_EXTERNAL_RECORD_UNCHECKED`
  Level: warning. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_HYPOTHESIS`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_HYPOTHESIS_OUTCOME`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INDEX_DRIFT`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INDEX_DUPLICATE`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INDEX_ENTRY`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INDEX_FIELD`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INDEX_ID`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INDEX_KIND`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INDEX_LEGACY`
  Level: warning. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INDEX_LIST`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INDEX_METADATA`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INDEX_METADATA_UNRESOLVED`
  Level: dynamic. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INDEX_RECORD`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INDEX_RECORDS`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INDEX_RECORD_VERSION`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INDEX_SCHEMA`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INVARIANT`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_INVARIANT_STATUS`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_MANIFEST_PATH`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_MANIFEST_POLICY_DRIFT`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_PRIVACY`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_PROHIBITED_CONTENT_FIELD`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_PUBLICATION_SCOPE`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_RECORD_DUPLICATE`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_RECORD_LIST`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_RECORD_LOCATION`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_RECORD_PATH`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_RECORD_SCHEMA`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_REGRESSION`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_SOURCE_SCHEMA`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_TASK_REFERENCE`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_TEMPLATE_BINDING`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_TEMPLATE_DEBUG_LINK`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `ENGINEERING_EVIDENCE_TEMPLATE_VERSION`
  Level: error. Source: `tools/target_adapter_validation/engineering_evidence.py`.
- `EVIDENCE_SCOPE_CURRENT_STATE`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_APPROVAL_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_APPROVAL_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_BINDING_CONTRACT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_BINDING_ENTRIES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_BINDING_ENTRY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_BINDING_ID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_BINDING_IDENTITY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_BINDING_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_CATALOG_API`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_CATALOG_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_CATALOG_ENTRIES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_CATALOG_ENTRY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_CATALOG_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_CATALOG_LIST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_CATALOG_LOCK_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_CATALOG_METADATA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_CATALOG_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_CATALOG_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_CATALOG_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_CATALOG_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_COMPATIBILITY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_EVIDENCE_LIMIT`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_FILE_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_FILE_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_FILE_HASH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_FILE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_FILE_OWNER`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_FILE_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_FILE_RECORD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_FILE_SYMLINK`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_ID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_INSTALLED_DEPENDENCIES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_INSTALLED_FILES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_INSTALLED_HOOK`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_INSTALLED_ITEM`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_INSTALLED_ITEMS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_INSTALLED_ITEM_ID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_INSTALLED_ITEM_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_INSTALLED_MANIFEST_IDENTITY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_INSTALLED_MANIFEST_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_INTEGRATION_SURFACES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_ITEM_INDEX_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_ITEM_UNLOCKED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_LOCK_API`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_LOCK_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_LOCK_ENTRIES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_LOCK_ENTRY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_LOCK_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_LOCK_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_LOCK_PATH_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_LOCK_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_LOCK_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_LOCK_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_MANIFEST_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_MODULE_STATE_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_MODULE_UNDECLARED`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_NAMESPACE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_OPERATION_UNROUTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_PACKAGE_DIGEST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_REQUIRED_BINDING_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_REQUIRED_FILE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_SOURCE_TYPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_TARGET_BASELINE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_TARGET_BASELINE_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `EXTENSION_VALIDATION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_COMPARE_SKIPPED`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_DIR_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_FILE_DRIFT`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_FILE_EXTRA`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_FILE_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_PACK_INVENTORY_CONTENT_DRIFT`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_PACK_INVENTORY_DIGEST_DRIFT`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_PACK_INVENTORY_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_PACK_INVENTORY_ENTRY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_PACK_INVENTORY_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_PACK_INVENTORY_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_PACK_REGISTRY_DRIFT`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_PACK_REGISTRY_INVALID`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_PACK_SELECTION_DRIFT`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_SOURCE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `FRAMEWORK_SOURCE_PACK_INVALID`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `GATE_CONTEXT_ROUTER_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `INSTALLATION_STATE_RECORD_MISSING`
  Level: error. Source: `tools/target_adapter_validation/installation_state.py`.
- `INSTALLATION_STATE_RECORD_PATH`
  Level: error. Source: `tools/target_adapter_validation/installation_state.py`.
- `INSTALLATION_STATE_TRANSITION`
  Level: error. Source: `tools/target_adapter_validation/installation_state.py`.
- `LOCAL_PATH_LEAKAGE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MANIFEST_CONTEXT_BUDGET`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MANIFEST_CONTEXT_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MANIFEST_FIELD_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MANIFEST_FIELD_UNRESOLVED`
  Level: configured. Source: `tools/validate_target_adapter.py`.
- `MANIFEST_FRAMEWORK_PACK`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MANIFEST_PARSE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MANIFEST_PATH_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MANIFEST_PATH_NOT_AI`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MANIFEST_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MANIFEST_SCHEMA_UNAVAILABLE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MANIFEST_SUPPORT_PROFILE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MIGRATION_DIFF_FILE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MIGRATION_DIFF_IMPACT`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `MIGRATION_DIFF_INVALID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MIGRATION_DIFF_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `MIGRATION_DIFF_NO_IMPACT`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `MIGRATION_DIFF_NO_RULE_IMPACT`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `MIGRATION_DIFF_SECTION_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `MIGRATION_DIFF_SKIPPED`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `MODULE_MANIFEST_ENABLED_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MODULE_PROFILE_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MODULE_PROFILE_ENABLED_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MODULE_PROFILE_STATE_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `MODULE_PROFILE_UNKNOWN`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CANDIDATES_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CANDIDATE_COVERAGE`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CANDIDATE_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CANDIDATE_UNKNOWN`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_DUPLICATE_ALIAS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_DUPLICATE_ID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_FALLBACK`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_FIELD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_IN_BOOTSTRAP`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_ITEM`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_LIST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_OPERATIONS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_PREVIEW`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_PROFILE`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_REQUIRED_OPERATION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_CATALOG_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_INDEX_ALIAS_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_INDEX_CATALOG`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_INDEX_CONTRACT_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_INDEX_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_INDEX_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_INDEX_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_ROUTING_CATALOG`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_ROUTING_HEALTH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_ROUTING_INDEX`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `OPERATION_ROUTING_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_ACTUAL_PATH`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_AFTER_REF`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_APPROVAL_PATH`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_APPROVAL_RECORD`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_APPROVAL_SCOPE`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_APPROVAL_SEMANTIC_SCOPE`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_ARCHITECTURE_APPLIES`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_ARCHITECTURE_DISCUSSION`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_ARCHITECTURE_FIELD`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_ARCHITECTURE_LIST`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_ARCHITECTURE_REQUIRED`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_BEFORE_REF`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_CHANGED_FACT`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_CHANGED_FACTS`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_CHANGED_FACT_FIELD`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_CHECKED`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_CHECK_SKIPPED`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_COMPANION_DECISION`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_COMPANION_DECISIONS`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_COMPANION_FIELD`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_COMPANION_STATE`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_CORRECTION`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_CORRECTIONS`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_CORRECTION_FACT`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_CORRECTION_FACTS`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_CORRECTION_FIELD`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_CORRECTION_KIND`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_CORRECTION_SCOPE`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_ENGINEERING_EVIDENCE_REFERENCE`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_EVIDENCE_CLASS`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_EVIDENCE_QUALITY`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_EXCLUDED_PATH`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_FACT_DECLARATION`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_FIELD_MISSING`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_FIELD_UNAVAILABLE`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_GIT_RANGE`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_INDEX_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_INDEX_ENTRY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_INDEX_FIELD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_INDEX_JSON`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_INDEX_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_INDEX_RECORDS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_INDEX_RECORD_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_INDEX_REQUIRED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_INDEX_ROOT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_INDEX_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_INVALID_JSON`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_INVALID_ROOT`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_INVARIANTS`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_KIND`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_LIST_MISSING`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_LIST_VALUE`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_MISSING`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_MISSING_COMPANION_RISK`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_NOT_INDEXED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_OUTSIDE_TARGET`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_PATH_SCOPE`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_PLAN_HASH`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_PLAN_HASH_FORMAT`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_PLAN_MISSING`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_PLAN_PATH`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_PUBLIC_CLAIM`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_PULL_REQUEST`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_RANGE_PATHS`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_RAW_CHAT`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_RAW_CHAT_REVIEW`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_REAPPROVAL_MISSING`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_REVISION_ANCESTRY`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_SCHEMA`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_SELECTION_REQUIRED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_SEMANTIC_SCOPE`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_SNAPSHOT_HASH`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_SNAPSHOT_HISTORICAL`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_SNAPSHOT_PATH`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_SNAPSHOT_READ`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_STATUS`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_TYPE`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PACKAGE_WORKTREE_STATE`
  Level: dynamic. Source: `tools/validate_target_adapter.py`.
- `PLACEHOLDERS_ALLOWED`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `PROFILE_DUPLICATE_CONTEXT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `PROFILE_MARKDOWN_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `PROJECT_GUIDANCE_BASE_FACT_TYPE`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_GUIDANCE_BASE_REFERENCE`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_GUIDANCE_COVERAGE_DUPLICATE`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_GUIDANCE_COVERAGE_GAP`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_GUIDANCE_COVERAGE_REFERENCE`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_GUIDANCE_COVERAGE_STATE`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_GUIDANCE_EXCEPTION_AUTHORITY`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_GUIDANCE_EXCEPTION_SCOPE`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_GUIDANCE_KIND`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_GUIDANCE_ORIGIN`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_GUIDANCE_PRECEDENCE`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_ADOPTION_STATE`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_CONFLICT_RECIPROCITY`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_CONTRACT_VERSION`
  Level: error. Source: `tools/target_adapter_validation/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_CONTRADICTION_LINK`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_CONTRADICTION_STATE`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_CURRENT_OWNER`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_CURRENT_OWNER_DRIFT`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_ENABLED_EMPTY`
  Level: info. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_FRESHNESS_TRIGGER`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_ID_DUPLICATE`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_INDEX_MISSING`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_INDEX_PATH`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_LOAD`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_MANIFEST_PATH`
  Level: error. Source: `tools/target_adapter_validation/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_MANIFEST_POLICY_DRIFT`
  Level: error. Source: `tools/target_adapter_validation/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_POLICY_DRIFT`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_POLICY_MISSING`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_PRIVACY`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_PROFILE`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_PROMOTION_DRIFT`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_PROMOTION_DUPLICATE`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_PROMOTION_LOAD`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_PROMOTION_OWNER_DRIFT`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_PROMOTION_PATH`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_PROMOTION_REFERENCE`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_REVIEW_EXPIRED`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_ROUTING_DRIFT`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_ROUTING_LOAD`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_ROUTING_MISSING`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_ROUTING_PATH`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_ROUTING_POLICY`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_ROUTING_SELECTORS`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_SELECTOR_MISSING`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_SHARD_DRIFT`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_SHARD_DUPLICATE`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_SHARD_LOAD`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_SHARD_PATH`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_SUMMARY_BUDGET`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_SUPERSESSION_LINK`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_SUPERSESSION_RECIPROCITY`
  Level: error. Source: `tools/project_knowledge.py`.
- `PROJECT_KNOWLEDGE_SUPERSESSION_STATE`
  Level: error. Source: `tools/project_knowledge.py`.
- `REQUIRED_FILE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTED_PATH_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `ROUTER_BOOTSTRAP_BROAD`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `ROUTER_BOOTSTRAP_COST`
  Level: error. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_BOOTSTRAP_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_BUDGETS_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_BUDGET_BOOTSTRAP`
  Level: error. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_BUDGET_ON_EXCEED`
  Level: error. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_BUDGET_ORDER`
  Level: error. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_BUDGET_PROFILE`
  Level: error. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_BUDGET_VALUE`
  Level: error. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_CONDITIONAL_CONTEXT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_CONSISTENCY_COMPOSITION_COST`
  Level: error. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_CONSISTENCY_COMPOSITION_MEASURED`
  Level: info. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_CONSISTENCY_CONDITIONAL`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_CONSISTENCY_CONTEXT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_CONSISTENCY_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_CONSISTENCY_PORTABLE_EAGER`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `ROUTER_CONTEXT_COST_UNREADABLE`
  Level: warning. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_CONTEXT_COST_UNRESOLVED`
  Level: configured. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_CONTEXT_PATH_MISSING`
  Level: warning. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_CONTEXT_PATH_UNSAFE`
  Level: error. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_DESCRIPTOR`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_DESCRIPTOR_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_DESCRIPTOR_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_DUPLICATE_BOOTSTRAP`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_DUPLICATE_ENTRY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_DUPLICATE_PROFILE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_HUMAN_REFERENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_INVALID_JSON`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_INVALID_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_MANIFEST_SCHEMA_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_MIGRATION_ASSESSMENT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_MIGRATION_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_PATH_MISSING`
  Level: error, warning. Source: `tools/validate_target_adapter.py`.
- `ROUTER_PRELOADED_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `ROUTER_PROFILES_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_PROFILE_COST`
  Level: error. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_PROFILE_COST_EMPTY`
  Level: warning. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_PROFILE_COST_MEASURED`
  Level: info. Source: `tools/target_adapter_validation/router_costs.py`.
- `ROUTER_PROFILE_IDENTITY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_PROFILE_INDEX`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_PROFILE_INDEX_ITEM`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_PROFILE_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `ROUTER_PROFILE_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_PROJECT_KNOWLEDGE_BUDGET`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_PROJECT_KNOWLEDGE_INDEX`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_PROJECT_KNOWLEDGE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_PROJECT_KNOWLEDGE_PROFILE_ONLY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_RECEIPT_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `ROUTER_SCHEMA_LEGACY`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `ROUTER_UPGRADE_CONTEXT_BROAD`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `ROUTING_BROAD_CONTEXT`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `ROUTING_LOADS_BROAD_CONTEXT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `RULE_REGISTRY_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `STALE_CHECKER_MISSING_CLAIM`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `STALE_CHECKER_REFERENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TARGET_CHECKER_COVERAGE_GAP`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `TARGET_CHECKER_FOUND`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `TARGET_CHECKER_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `TARGET_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TARGET_NOT_DIRECTORY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TARGET_PATH_ESCAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_COMMAND_EXTERNAL_ACTIONS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_COMMAND_REFERENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_COMMAND_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_CONFIGURATION_UNROUTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_EVIDENCE_LIMIT`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `TDD_EVIDENCE_REQUIREMENTS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_EXCEPTIONS_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_EXCEPTION_REASON`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_EXCEPTION_REFERENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_EXCEPTION_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_EXECUTION_UNROUTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_INTENT_UNROUTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_ISOLATION_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_ISOLATION_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_KNOWN_GAPS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_MANIFEST_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_MODES_INVALID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_MODULE_STATE_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `TDD_MODULE_UNDECLARED`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `TDD_POLICY_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_POLICY_LIST_EMPTY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_POLICY_METADATA_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_POLICY_NOT_ENABLED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_POLICY_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_RECORD_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_RECORD_ID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_REQUIRED_FILE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_SUGGESTION_BOUNDS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_SUGGESTION_COST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_SUGGESTION_MODE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_SUGGESTION_RESULT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_SUGGESTION_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_TEST_LEVEL_LIST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_TEST_LEVEL_REFERENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_TEST_LEVEL_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_TRIGGERS_EMPTY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_TRIGGER_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_TRIGGER_EXCEPTIONS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_TRIGGER_LIST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_TRIGGER_MODE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_TRIGGER_MODE_UNAVAILABLE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_TRIGGER_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_TRIGGER_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TDD_TRIGGER_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTIVE_CLAIM_INCOMPLETE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTIVE_INDEX_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTIVE_INDEX_ENTRIES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTIVE_INDEX_ENTRY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTIVE_INDEX_FIELD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTIVE_INDEX_INCOMPLETE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTIVE_INDEX_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTIVE_INDEX_LIST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTIVE_INDEX_REGISTRY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTIVE_INDEX_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTIVE_INDEX_STALE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTIVE_INDEX_TASK_ID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTIVE_OVERLAP_BLOCKED`
  Level: configured. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTIVE_TASK_WITHOUT_CLAIM`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTORS_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTOR_ALIAS_AMBIGUOUS`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTOR_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTOR_ID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTOR_LIST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTOR_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ACTOR_UNKNOWN`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_BACKEND_CAPABILITIES`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_BACKEND_FIELD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_BACKEND_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_BACKEND_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_CLAIM_FIELD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_CLAIM_MODE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_CLAIM_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_CLAIM_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_CONTEXT_OVERLAY_CONDITIONAL`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_CONTEXT_OVERLAY_DESCRIPTOR`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_CONTEXT_OVERLAY_ID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_CONTEXT_OVERLAY_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_CONTEXT_OVERLAY_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_CONTEXT_OVERLAY_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_CONTEXT_OVERLAY_PREFLIGHT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_CONTEXT_OVERLAY_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_CONTEXT_OVERLAY_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_ENABLED_METADATA_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_GIT_IDENTITY_AUTHORITY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_HANDOFF_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_IDENTITY_POLICY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_LOCAL_IDENTITY_INACTIVE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_LOCAL_IDENTITY_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_LOCAL_IDENTITY_NOT_IGNORED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_LOCAL_IDENTITY_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_LOCAL_IDENTITY_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_LOCAL_IDENTITY_SELECTION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_LOCAL_IDENTITY_STALE`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `TEAM_LOCAL_IDENTITY_UNKNOWN`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_MERGE_READY_OVERLAP`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_MERGE_READY_REVIEW`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_MERGE_READY_REVIEWERS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_MERGE_READY_REVIEW_EVIDENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_MERGE_READY_REVIEW_REVISIONS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_MERGE_READY_REVIEW_STALE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_MERGE_READY_REVISION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_MERGE_READY_STALE`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `TEAM_MERGE_READY_VALIDATION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_MODULE_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_OPERATING_MODEL_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_OVERLAP_FIELD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_OVERLAP_LIST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_OVERLAP_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_OVERLAP_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_POLICY_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_POLICY_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_POLICY_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_PRIORITIES_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_PRIORITY_AUTHORITY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_PRIORITY_UNKNOWN`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_REGISTRY_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_REGISTRY_METADATA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_REGISTRY_MIGRATION_REQUIRED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_REGISTRY_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_REGISTRY_MONOLITHIC_TASKS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_REGISTRY_OPERATING_MODEL`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_REGISTRY_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_REGISTRY_REVISION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_REGISTRY_REVISION_STALE`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `TEAM_REGISTRY_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_REVIEWER_SEPARATION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_REVIEW_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_TASK_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_TASK_EXPECTED_REVISION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_TASK_FIELD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_TASK_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_TASK_LIST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_TASK_RECORD_REVISION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_TASK_REVISION_CONFLICT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_TASK_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_TASK_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_TASK_STATUS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_TERMINAL_TASK_ACTIVE_CLAIM`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `TEAM_TRANSITION_NOT_ALLOWED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_TRANSITION_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_TRANSITION_STATUS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `TEAM_VALIDATION_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `UNRESOLVED_NOT_DEFINED`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_ACCEPTED_AMBIGUITY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_ACCEPTED_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_CATALOG_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_CATALOG_EMPTY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_CATALOG_ENTRY_FIELDS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_CATALOG_ENTRY_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_CATALOG_ID_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_CATALOG_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_CATALOG_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_CATALOG_RECORD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_CATALOG_REFERENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_CATALOG_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_CONTRACT_INCOMPLETE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_DATA_REFERENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_ENABLED_METADATA_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_EVIDENCE_LIMIT`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_LINKS_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_LINK_FIELDS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_LINK_ID_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_LINK_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_LINK_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_LINK_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_LINK_TERM_REFERENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_LINK_UNRESOLVED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_MANIFEST_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_MODULE_STATE_MISSING`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_MODULE_UNDECLARED`
  Level: warning. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_NO_ACCEPTED_TERM`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_OPERATION_ACTIONS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_OPERATION_FLOW`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_OPERATION_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_OPERATION_MODULE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_OPERATION_UNROUTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_REQUIRED_FILE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_STRING_LIST`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_TERMS_EMPTY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_TERM_FIELDS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_TERM_ID_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_TERM_KIND`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_TERM_REFERENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_TERM_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_TERM_SHAPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_TERM_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `VOCABULARY_TERM_UNINDEXED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_ACTIVE_ROOT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_AUTO_ACCEPT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_CATALOG_ENTRY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_CATALOG_OWNER`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_CATALOG_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_CATALOG_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_CONSTRAINTS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_CONTEXT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_DEFAULT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_DESCRIPTOR_DRIFT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_DESCRIPTOR_FIELD`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_DESCRIPTOR_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_DESCRIPTOR_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_DUPLICATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_EMPTY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_EVIDENCE_LIMIT`
  Level: info. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_GRANT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_ID`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_INTENT_UNROUTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_MANIFEST_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_NESTED_ADAPTER`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_OPERATION_UNROUTED`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_PATH`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_README_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_RELATIONSHIP`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_RELATIONSHIPS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_REQUIRED_FILE_MISSING`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_ROOT_CONTEXT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_ROOT_DISABLED_CONTENT`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_ROOT_OWNER`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_ROOT_REFERENCE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_ROOT_SCHEMA`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_ROOT_STATE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_ROUTER`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_SCOPE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_SELECTION`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_SELECTION_POLICY`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_SIGNALS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_SUGGESTIONS`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `WORKSPACE_MODE_WORKSPACE`
  Level: error. Source: `tools/validate_target_adapter.py`.
- `{prefix}_INVALID_JSON`
  Level: error. Source: `tools/validate_target_adapter.py`.

The machine-readable catalog is
`tools/target_adapter_validation/finding-codes.json`.
