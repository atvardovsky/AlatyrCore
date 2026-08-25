# AlatyrCore Source Worker Strategy

Scope: AlatyrCore source repository only.

Canonical portable rule: `ALATYR-DELEGATION-001` in
`framework/subagent-delegation.md`.

This source-contour policy applies when AlatyrCore itself is the active project
being inspected or changed. It does not become a portable target rule, alter a
generated target adapter, or govern a host repository merely because that
repository installs, vendors, or depends on AlatyrCore. The host project's
active adapter owns its worker policy; this document is passive dependency
evidence outside the AlatyrCore source contour.

## Activation

Evaluate worker delegation only after selecting the source task profile and
identifying the primary assistant's immediate critical-path action. Use a
worker when a bounded independent packet is likely to reduce wall-clock time
or provide materially stronger review after accounting for preparation,
review, and integration cost. Keep work local when coordination cost is likely
to exceed the benefit.

## Model Routing

Choose the least costly verified model that can complete the packet reliably:

- fast, lightweight model: bounded read-only discovery, inventories, log or
  test-output parsing, and mechanical checks
- balanced coding model: scoped implementation or review with objective
  acceptance criteria
- strongest available reasoning model: ambiguous cross-cutting analysis,
  architecture, security, semantic invariants, conflict resolution, and final
  synthesis

Model names alone are not capability evidence. Verify that the current client
can launch the worker and select or report the intended model. Otherwise use a
verified fallback or keep the work with the primary assistant.

## Responsibility

The primary assistant retains project decisions, current-scope authorization,
integration, logical integrity review, final validation, and completion
evidence.

Every worker packet must define bounded context, explicit non-goals, allowed
actions, write ownership, and objective validation. A worker must not broaden
permissions, approval, action phases, or repository scope. Do not dispatch
concurrent overlapping writes. Reject results without inspectable file or
symbol evidence and required validation.
