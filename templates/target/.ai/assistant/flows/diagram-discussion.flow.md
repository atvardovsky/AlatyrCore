# Diagram Discussion Flow

Use this flow when a programmer asks to see, sketch, compare, explain, or
iteratively revise a diagram during an assistant discussion.

Replace placeholders with target facts before accepting installation.

## Required Context

- Diagram rule: `.ai/framework/diagram-guidance.md`
- Module state: `modules` in `.ai/alatyr.yaml`; load
  `.ai/assistant/module-profile.md` only for missing, conflicting, or repair
  evidence
- Presentation contract: `.ai/assistant/templates/diagram-presentation.md`
- Current assistant entry in `.ai/assistant/assistant-capabilities.json`
- Diagram owner or policy: `{TARGET_DIAGRAM_SOURCE_VISUAL_AND_RENDER_POLICY}`
- Relevant fact owners: `{TARGET_FACT_OWNERS_FOR_DIAGRAM_SCOPE}`

Load source-of-truth, risk, integrity, approval, security, privacy, or
product-change context only when the requested view proposes or exposes a fact
change, contains sensitive data, invokes an external renderer, or persists an
artifact.

## Allowed Actions

- `read-only`: present the diagram in chat and create no repository files.
- `docs-only`: persist target-owned diagram source and allowed derived visual
  artifacts with target-owned local tooling; do not use network renderers or
  change code, tests, runtime config, or accepted facts.

If the request needs broader actions, hand off to the matching decision,
documentation-sync, or product-change operation.

## Flow

1. Confirm the diagram purpose, scope, type, and whether it explains current
   facts, compares alternatives, or proposes a change.
2. Check that the `diagrams` module is enabled or required. If it is unavailable,
   report the module gap and offer a bounded textual explanation.
3. Read the canonical owners for only the facts in scope. Mark missing or
   conflicting evidence instead of filling it with plausible detail.
4. Classify the result as `draft`, `accepted-source`, or `derived-view`.
   Default to `draft` for discussion and alternatives.
5. Assign or retain a stable diagram ID. Start draft revision `1`, increment it
   for each revision, and name the superseded or parent revision. Do not reuse
   an ID for an unrelated scope.
6. Classify data sensitivity and required redactions. Neither allowed action
   invokes an external renderer. For local docs-only artifact generation,
   check target security, storage, retention, and sharing policy. Hand off any
   network action to an operation with sufficient actions and approval gates.
7. Read only the current assistant surface entry in the compact capability
   projection. Verify route, enum values, client version, verification time,
   and evidence. Do not infer support from another surface or stale claims.
8. Select the first supported presentation mode:
   - `native-inline` for a recorded supported syntax;
   - `rendered-artifact` using target-owned tooling and an attachable or
     linkable artifact;
   - `text-fallback` with a readable text diagram and editable source or source
     path.
9. Under `read-only`, keep all draft content in the assistant response. Under
   `docs-only`, write only target-owned diagram source and allowed derived
   visual artifacts, then run the target render or manual-review process.
10. If discussion accepts a new business, architecture, data, runtime,
   security, or public-contract fact, stop treating the diagram as the change
   mechanism. Route the accepted fact to its owner and the applicable decision
   or product-change flow.
11. Present the result using the diagram presentation template. Include a text
   fallback even when a richer view is available, unless the target explicitly
   records an accessible equivalent.
12. Require repository revision and source revision or content hash for
    `accepted-source` and `derived-view`. Otherwise keep the result `draft`.
    Report validation, omitted detail, unresolved facts, and stale-view risk.

## Result

```text
Diagram purpose: <purpose and scope>
Diagram ID and revision: <stable ID, draft revision, parent/superseded revision>
Status: <draft, accepted-source, or derived-view>
Presentation mode: <native-inline, rendered-artifact, or text-fallback>
Capability: <surface, client version, verified at, evidence>
Source and revision: <inline, path, revision/hash, or none>
Visual artifact: <path, attachment, unsupported, or none>
Text fallback: <included or reason for accessible equivalent>
Assumptions and unresolved facts: <items>
Security and external rendering: <classification, redactions, action, policy>
Validation or manual review: <result>
Next operation: <continue discussion, persist, decision, sync, or product change>
```

## Rejection Criteria

Reject or revise diagram discussion that:

- claims native rendering without current bridge capability evidence
- relies on missing, stale, or invalid capability enum evidence
- treats a draft or alternative as accepted project truth
- invents actors, states, dependencies, tables, APIs, or business rules
- creates files under `read-only`
- runs an unrecorded render command or writes generated artifacts outside the
  target diagram policy
- exposes restricted facts or uses an external renderer without policy and
  sufficient allowed actions and required approval
- marks a view accepted or derived without repository and source revision
  evidence
- loses diagram ID or draft lineage during iterative revision
- returns only source syntax while claiming a visible rendered result
- uses diagram edits to bypass approval or product-change requirements
