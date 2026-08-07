# Project Contour

This contour describes `{PROJECT_NAME}` product facts.

Replace placeholders with target facts before accepting installation.

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
- target team actors and roles, decision authority, priority policy, required
  review, escalation, coordination backend, synchronization, retention,
  privacy, and accepted business or architecture decisions when team
  collaboration is enabled

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

## AI Infrastructure Evidence Boundary

Project-contour sources may justify why an assistant capability is needed and
which project outcome it must improve. The assistant contour owns how a skill,
prompt, gate, checker, flow, tool, bridge, or wrapper is recommended,
implemented, routed, validated, and maintained.

Target development evidence must not directly change `.ai/framework`,
AlatyrCore source, or portable rules. Keep raw conversations, secrets,
credentials, and personal data out of the development evidence index.

When team collaboration is enabled,
`.ai/project/team-operating-model.md` owns actor, authority, priority, review,
backend, storage, and privacy facts. The assistant work registry references
those facts; it does not replace them.
