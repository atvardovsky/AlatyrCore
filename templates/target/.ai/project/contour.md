# Project Contour

This contour describes `{PROJECT_NAME}` product facts.

Replace placeholders with target facts before accepting installation.

## Project Orientation

Keep this section concise and human-readable. It routes readers to canonical
owners; it must not duplicate their detailed policy or architecture content.

Purpose: `{TARGET_PRODUCT_PURPOSE}`

Primary users or stakeholders: `{TARGET_PRIMARY_USERS_OR_STAKEHOLDERS}`

Main architectural areas and owners:

- `{TARGET_ARCHITECTURAL_AREA}` -> `{TARGET_ARCHITECTURAL_AREA_OWNER}`

Primary runtime or business workflows:

- `{TARGET_PRIMARY_WORKFLOW}` -> `{TARGET_WORKFLOW_OWNER}`

Validation entry points:

- `{TARGET_VALIDATION_SCOPE}` -> `{TARGET_VALIDATION_OWNER_OR_COMMAND_SOURCE}`

Known contradictions, missing facts, or accepted limitations:

- `{TARGET_KNOWN_GAP_OR_NONE_WITH_EVIDENCE}`

Start with `.ai/project/source-of-truth-registry.md` when ownership is unclear.
Use the architecture, vocabulary, testing, and code-documentation indexes only
when those modules are enabled and relevant to the question.

## Owns

- product purpose
- business/domain rules
- architecture facts
- project-owned architecture areas, patterns, constraints, intended states,
  decision authority, supporting documentation, and evidence revisions under
  `.ai/project/architecture` when architecture knowledge is enabled
- project-owned code-documentation areas, source-set profiles, comment content
  conventions, generator selection, output policy, owners, and evidence under
  `.ai/project/documentation` when code documentation is enabled
- project-owned vocabulary terms, aliases, acronyms, scoped meanings,
  acceptance states, owners, and canonical data links under
  `.ai/project/vocabulary` when project vocabulary is enabled
- project-owned test-first policy, trigger severity, modes, levels, commands,
  isolation, exceptions, CI/merge requirements, and decision authority under
  `.ai/project/testing` when test-first development is enabled
- use cases and workflows
- data model and persistence facts
- runtime flows and state machines
- deployment and operations facts
- project test strategy facts
- project terminology and decisions
- project needs, constraints, recurring outcomes, and measured quality or cost
  evidence that may justify assistant-infrastructure recommendations
- normalized target development-request, correction, review, rework,
  validation, and context-expansion patterns under
  `.ai/project/development-evidence.json`
- durable historical engineering evidence under
  `.ai/project/engineering-evidence`, including compact task and revision
  binding, invariant, root-cause, solution, regression, validation, and
  uncertainty conclusions that link back to canonical project owners
- optional non-canonical Debug Mode evidence under `.ai/project/debug`, with
  task/session activation, normalized contribution events, timing/capture
  quality, supervision metrics, final result, and external-projection evidence
- target team actors and roles, decision authority, priority policy, required
  review, escalation, coordination backend, synchronization, retention,
  privacy, and accepted business or architecture decisions when team
  collaboration is enabled; machine-relevant team policy is canonical in
  `.ai/project/team-policy.json`

## Does Not Own

- portable Alatyr Core framework rules
- assistant workflow mechanics
- AI infrastructure item definitions, recommendation records, router entries,
  skills, prompts, gates, and assistant-specific implementation
- assistant bridge-file mechanics
- team task, claim, checkpoint, handoff, and operation-routing mechanics
- local validation command policy outside project facts

## Source Of Truth

List target source-of-truth files:

- `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- `.ai/project/source-of-truth-registry.md`
- `.ai/project/engineering-evidence/README.md` and `index.json`
- `.ai/project/debug/README.md` and `index.json` when Debug Mode is enabled;
  these own observability records and policy, not architecture or business facts
- `.ai/project/architecture/README.md` and
  `.ai/project/architecture/catalog.json` when the architecture-knowledge
  module is enabled
- `.ai/project/documentation/README.md`,
  `.ai/project/documentation/catalog.json`, and
  `.ai/project/documentation/profiles.json` when code documentation is enabled
- `.ai/project/vocabulary/README.md`, `.ai/project/vocabulary/catalog.json`,
  `.ai/project/vocabulary/terms.json`, and
  `.ai/project/vocabulary/data-dictionary-links.json` when project vocabulary
  is enabled
- `.ai/project/testing/README.md` and
  `.ai/project/testing/test-first-policy.json` when test-first development is
  enabled

## AI Infrastructure Evidence Boundary

Project-contour sources may justify why an assistant capability is needed and
which project outcome it must improve. The assistant contour owns how a skill,
prompt, gate, checker, flow, tool, bridge, or wrapper is recommended,
implemented, routed, validated, and maintained.

Target development evidence must not directly change `.ai/framework`,
AlatyrCore source, or portable rules. Keep raw conversations, secrets,
credentials, and personal data out of the development evidence index.
Keep raw conversations, private reasoning, prompts, secrets, credentials,
unrelated personal data, and unused speculation out of Debug Mode records.

When team collaboration is enabled,
`.ai/project/team-operating-model.md` owns actor, authority, priority, review,
backend, storage, and privacy facts. The assistant work registry references
those facts; it does not replace them.
