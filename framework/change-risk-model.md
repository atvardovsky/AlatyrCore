---
alatyr_doc:
  id: framework.change-risk-model
  type: framework-rule-owner
  owns_rules:
    - ALATYR-RISK-001
  depends_on:
    - ALATYR-SOURCE-001
  applies_to:
    - all
---
# AI Framework Change Risk Model

This file defines a portable way to classify change risk before deciding tests,
docs, diagrams, approvals, and validation.

The risk model is framework core. Concrete gates and commands belong to the
project adapter.

## Risk Classes

Classify each changed fact, not only each changed file:

- Documentation-only: wording, index, or explanation that does not alter an
  accepted contract.
- Test-only: validation changes without production behavior changes.
- Business logic: formulas, thresholds, decisions, rule order, reasons,
  eligibility, permissions, or domain invariants.
- Architecture: module boundaries, dependencies, ownership, runtime
  responsibilities, data ownership, public interfaces, or deployment shape.
- Data and persistence: schema, migrations, indexes, keys, serialization,
  retention, money/time/id formats, or query behavior.
- External boundary: API, webhook, queue, file, shell command, email, payment,
  third-party service, or live side effect.
- Security and privacy: secrets, credentials, tokens, permissions, PII,
  redaction, audit, destructive operations, or dependency trust.
- Tooling and validation: package manager, CI, linter, formatter, checker,
  generated files, test framework, or assistant gate.
- AI governance: framework, adapter, prompt, skill, bridge, flow, checker, or
  documentation-sync rule.
- AI infrastructure adaptation: imported skill, prompt, wrapper, bridge, rule,
  assistant-native format, MCP/tool permission, output format, provenance, or
  third-party assistant infrastructure.

One change may belong to multiple classes. Use the highest-risk applicable
class for approval and evidence.

## Required Reasoning By Risk

For each risk class, decide:

- source of truth
- affected contracts
- required tests or manual validation
- documentation and diagram sync
- approval requirement
- rollback or repair direction
- final evidence needed

High-risk changes require explicit reasoning before relying on scripts.
Scripts are evidence for known contracts; they do not decide what changed.

## Approval Triggers

The framework treats these as protected categories:

- architecture changes
- accepted business-policy changes
- spend, money, billing, data loss, destructive operation, or live external
  side-effect changes
- weakened tests, gates, approval rules, or documentation-sync rules
- new production dependencies, services, permissions, or credentials
- third-party AI infrastructure integration into canonical files
- overwriting existing target assistant instructions during framework
  installation

The project adapter may add stricter approval triggers.

## Test And Documentation Impact

Use the risk class to choose companion work:

- business logic needs tests for edge cases and plain-language rationale
- architecture needs level or boundary documentation and approval evidence
- data changes need schema/data-contract docs and persistence validation
- external boundaries need contract fixtures, retry/failure/idempotency
  reasoning, and no-live-call policy
- security changes need redaction, permission, and secret-handling checks
- AI governance changes need bridge, skill, prompt, gate, and consistency
  sync
- routed AI infrastructure changes need item permission, gate, validation,
  output-contract, provenance, and supported-assistant checks
- AI infrastructure adaptation needs inventory, provenance review, wrapper
  sync, safety review, target validation, and approval when protected assistant
  infrastructure or permissions change

If no companion update is needed, final evidence must explain why no semantic
or logical fact changed.

## Rejection Criteria

Reject changes that:

- classify risk only by filename while ignoring changed facts
- lower risk to avoid tests, docs, diagrams, or approval
- weaken validation to make a patch pass
- change protected behavior without explicit approval
- treat a script pass as proof that no logical impact exists
