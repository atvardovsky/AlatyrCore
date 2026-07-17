# AI Infrastructure Routing

This file defines how a target adapter discovers and loads only the skills,
prompts, gates, checkers, flows, tools, MCP configurations, bridges, wrappers,
and policies required for one assistant task.

It composes `ALATYR-CONTEXT-001`, `ALATYR-ADAPTER-001`,
`ALATYR-SAFETY-002`, `ALATYR-APPROVAL-001`, and `ALATYR-BRIDGE-001`.
Canonical policy remains in those rule owners and in `skill-adaptation.md`.

Concrete items, triggers, files, assistant surfaces, permissions, commands,
validation, provenance, and output contracts belong to the target adapter.

## Purpose

An inventory proves an item exists, but it does not tell an assistant when to
load or use it. Loading every skill, prompt, gate, tool description, and safety
policy for each task increases cost and creates instruction conflicts.

A target AI infrastructure router provides compact capability selection. It
routes one request to one item or adaptation mode, then loads only that item's
canonical source, required context, gates, permissions, validation, and output
contract.

Recommendation is a separate read-only route. It compares bounded project-
contour needs with existing item contracts before any adaptation or import.

## Route Categories

An adapted router should distinguish at least:

- `inventory`: inspect existing items without importing or executing anything
- `recommend`: propose new items or evidence-based changes to existing items
  without fetching, editing, installing, removing, or activating anything
- `use-existing`: use one target-owned item already accepted by the adapter
- `adapt-import`: review or normalize external, remote, pasted, package/plugin,
  or assistant-native infrastructure
- `gate-checker-change`: change recurring acceptance or deterministic rules
- `tool-mcp-change`: change tool, model, connector, MCP, permission, network,
  or execution capabilities
- `bridge-wrapper-change`: adapt thin assistant-specific routing surfaces

The target may add narrower routes. It should not collapse protected tool
changes into ordinary prompt or skill use.

## Item Contract

Each routable item should define:

- stable item ID, type, purpose, status, and activation triggers
- canonical target source and minimum required context
- supported assistant surfaces and wrapper locations
- allowed-action modes and required permissions
- approval triggers and gates
- target validation or manual review
- output contract and final evidence
- conflicts, superseded items, and provenance/adaptation record

An item is not routable when its canonical source, permission scope, required
gate, or validation is missing. Keep it blocked or unresolved instead of
loading nearby files and guessing.

## Selection Protocol

1. Load the compact adapter bootstrap and the AI infrastructure router.
2. Match the request to one route and the smallest set of item IDs.
3. If the item is unknown or multiple items conflict, run inventory and report
   the ambiguity before use. If the request asks what should be added or
   improved, select `recommend` and apply
   `ai-infrastructure-recommendations.md`.
4. Load only selected item sources, required context, gates, validation, and
   output contracts.
5. Expand to provenance, source-access, prompt-injection, approval, or safety
   policy only when the selected route or item requires it.
6. Record selected/rejected items, route, loaded context, permission scope,
   validation, and residual risk.

Do not interpret a trigger match as permission to execute tools, access a
network, install packages, or change canonical files.

## Adaptation Contract

Every imported or materially changed item should leave a durable target-owned
adaptation record. The record captures source/hash/license evidence, rejected
source instructions, target purpose and non-goals, canonical normalized
surfaces, assistant wrappers, permissions, gates, output format, validation,
approval, and residual risk.

The record is provenance and decision evidence. The normalized target item is
the routable source; imported source content does not remain active policy.

## Cost Boundary

For `use-existing`, do not load import policy when the selected item is
target-owned, current, permission-bounded, and has no external source action.

For `inventory`, inspect router-declared locations and supported assistant
surfaces before broad directory search. Expand only for missing inventory,
unknown ownership, stale paths, or conflicting declarations.

For `recommend`, load only the selected project area, its canonical owner,
current inventory, and relevant item contracts. Do not load unrelated project
areas or all item content. Recommendation does not permit source fetching or
canonical changes.

For protected routes, cost savings never bypass source access,
prompt-injection, permission, approval, or validation rules.

## Drift

Report adapter drift when a routed canonical source, wrapper, gate,
permission, validation, output contract, provenance record, or supported
assistant surface no longer exists or disagrees with target evidence.

## Evidence

Report:

- selected route and item IDs
- project-contour evidence and recommendation IDs when `recommend` is selected
- rejected or conflicting items and reason
- loaded item context and expansion reason
- provenance/adaptation record when applicable
- permission and allowed-action scope
- gates, approvals, and validation
- output contract result and residual risk

## Rejection Criteria

Reject or revise routing that:

- loads all skills, prompts, gates, and tools without selecting an item
- treats an inventory entry as permission to use or execute an item
- treats a recommendation as permission to fetch, edit, install, remove, or
  activate an item
- uses an item whose canonical source or permission scope is missing
- bypasses adaptation for imported infrastructure
- lets wrappers or prompts duplicate canonical framework/project policy
- treats a trigger as approval for network, package, tool, or protected action
