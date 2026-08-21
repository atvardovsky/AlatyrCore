# Workspace Mode Gate

Apply when the optional module is configured, changed, or used to route
state-changing work.

## Identity And Ownership

- The selected workspace root and active adapter are explicit.
- Workspace identity is supported by target evidence, not directory naming.
- Mode owner and decision authority are resolved.
- Artifact relationship, adapter role, and ownership are recorded separately.
- Dependency and scaffold adapters remain passive or provenance-only.

## Definition And Selection

- Every active catalog entry points to its own mode directory and `mode.json`.
- `_template` is not an active catalog mode.
- Accepted mode IDs and paths are unique and target-relative.
- Positive and negative selection signals are present.
- Explicit user selection wins when it is valid and accepted.
- Automatic selection occurs only for one unambiguous accepted match.
- Contradictory default or local preference evidence does not select a mode.

## Context And Permissions

- Root context is loaded only when enabled and applicable.
- Only one selected mode descriptor and named support paths are loaded.
- Context paths remain target-relative and exist or are recorded as gaps.
- The selected mode is composed with task, intent, area, gate, and scale routes.
- Mode constraints do not grant write scope, approval, permissions, authority,
  tool access, or gate bypass.

## Changes And Evidence

- Suggestions remain proposed until the required user decision.
- Mode changes receive a preview and preserve referenced history.
- Protected fact changes use their normal operation and approval path.
- Preflight, selection basis, validation, skipped checks, context cost,
  ambiguity, and residual risk are reported.

Structural checks cannot prove that a mode is strategically correct, that
workspace evidence is complete, or that an assistant followed the selected
mode.
