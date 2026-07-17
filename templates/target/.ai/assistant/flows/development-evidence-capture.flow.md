# Development Evidence Capture Flow

Use this lazy subflow in `{PROJECT_NAME}` only when current or historical
target evidence indicates repeated development friction or one high-impact
failure worth later AI infrastructure review.

This flow captures project-process evidence. It does not recommend or change
skills, prompts, gates, checkers, flows, tools, bridges, wrappers, framework
files, product behavior, or permissions.

## Sources

- Current task final evidence, corrections, review findings, rework,
  validation failures, skipped checks, or context-expansion evidence
- Project contour: `.ai/project/contour.md`
- Source-of-truth registry: `.ai/project/source-of-truth-registry.md`
- Development evidence index: `.ai/project/development-evidence.json`
- Target retention, privacy, and evidence-reference policy:
  `{TARGET_DEVELOPMENT_EVIDENCE_POLICY}`

For explicit historical backfill, inspect only target-permitted issue, review,
commit, incident, operation, or effectiveness sources selected for the bounded
project area. Do not assume prior assistant conversations are available.

## Capture Gate

Capture only when at least one condition is evidenced:

- an existing pattern receives another independent occurrence
- the same friction appears more than once in bounded evidence
- a correction, review failure, rework cycle, skipped check, or context
  expansion exposes a reusable process gap
- one security, data-loss, approval, or similarly high-impact failure warrants
  review even without recurrence

Do not record routine successful one-off work, preferences without an outcome,
or speculative future problems.

## Steps

1. Confirm allowed actions. Under `read-only`, report a capture candidate and
   do not edit the index. Updating the index requires `adapter-only` or an
   explicitly broader allowed-action mode.
2. Select the smallest project area and its canonical owner.
3. Normalize the problem category and outcome signal. Do not copy raw request,
   prompt, review, or conversation text.
4. Remove secrets, credentials, personal data, and target-prohibited details.
5. Find a semantically matching active pattern before creating a new ID.
6. Add one independently identifiable evidence reference, update first/last
   observation dates and occurrence count, and keep references within the
   target retention limit.
7. Record affected existing AI item IDs only when evidence connects them to
   the outcome. Do not infer item failure from mere activation.
8. Classify evidence quality as `measured`, `observed`, `anecdotal`,
   `conflicting`, or `unresolved`.
9. Keep the pattern `unresolved` when the owner, occurrence, evidence reference,
   or outcome cannot be verified.
10. Do not recommend an AI item during capture. A later `recommend` route
    evaluates selected pattern IDs against current inventory and cost.
11. Do not modify `.ai/framework`, AlatyrCore source, portable rules, project
    product facts, or existing AI infrastructure items.

## Pattern Contract

Each populated `patterns` entry must contain:

```text
id: <stable target-owned ID>
category: <normalized target category>
project_area: <bounded project area>
source_owner: <canonical project owner>
normalized_problem: <minimal non-sensitive signal>
occurrence_count: <positive integer>
first_observed: <target date or operation reference>
last_observed: <target date or operation reference>
evidence_quality: <measured/observed/anecdotal/conflicting/unresolved>
evidence_refs: <bounded list of target-permitted references>
outcome_signals: <bounded list of observed effects>
existing_ai_item_ids: <bounded list or empty>
status: <active/resolved/deferred/unresolved>
```

## Final Evidence

Report the pattern ID, project area, evidence reference added or rejected,
whether an existing pattern was updated, redactions performed, occurrence
count, evidence quality, actions not taken, and residual risk.
