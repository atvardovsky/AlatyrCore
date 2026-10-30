---
alatyr_doc:
  id: framework.project-knowledge
  type: framework-rule-owner
  owns_rules:
    - ALATYR-KNOWLEDGE-001
  depends_on:
    - ALATYR-CONTEXT-001
    - ALATYR-SOURCE-001
    - ALATYR-ENGINEERING-EVIDENCE-001
    - ALATYR-INTEGRITY-001
    - ALATYR-LIFECYCLE-001
  applies_to:
    - docs-local
    - code-local
    - business-change
    - architecture-change
    - data-change
    - security-sensitive
---
# Project Development Guidance And Knowledge Delivery

This derived Project Development Model routes reviewed discoveries and authorized
directives. Architecture, business, validation, security, API and data owners
retain authority; routing and promotion records cannot replace them.

Discovery concerns target-owned knowledge, excluding normalized `.ai/framework/`
owners. Mixed packages retain target-owned signals only. Bounded task/package
headers may suggest candidates, not semantic correctness or promotion authority.
Report stale, unavailable and incomplete coverage. Historical evidence,
implementation frequency, assistant conclusions and timestamps do not establish
project intent.

## Guidance Kinds And Required Identity

Classify every version-2 routed item as one of:

- `development-rule`: accepted engineering practice
- `architectural-intent`: an architecture-owned boundary or rationale
- `reviewed-knowledge`: an accepted reusable engineering discovery
- `validation-contract`: a validation-owned proof requirement
- `known-restriction`: an accepted limitation, compatibility boundary or prohibition

Each item needs a stable ID, kind, canonical owner, decision owner, authority,
rationale, applicability, freshness evidence, validation, exception or
narrowing state, and supersession lineage. The route may summarize those facts
for selection, but it must retain owner references and content digests.

## Responsibility Boundaries

Keep these surfaces separate:

- engineering evidence records completed investigation findings
- promotions retain human dispositions or authorized directive intake
- the source-of-truth registry identifies fact owners and conflict resolvers
- canonical target sources own accepted facts
- derived routing indexes/shards locate those owners for later work

Routing carries bounded summaries, never canonical authority. Cite and reverify
the owner before material decisions.

## Promotion Lifecycle

Use one of these entry paths for reusable guidance:

```text
engineering discovery
        -> candidate proposal
        -> human review
        -> accepted / narrowed / rejected / deferred
        -> canonical owner update when accepted
        -> reviewed routing projection
        -> bounded delivery to a later task

authorized decision-owner directive
        -> authority and scope verification
        -> canonical owner update
        -> reviewed routing projection
        -> bounded delivery to a later task
```

Suggest conclusions that are costly to reconstruct, non-obvious, cross-area,
dependency-sensitive, historically important, compatibility traps, recurring
rejected directions or constraint rationales. Exclude line numbers, obvious
declarations, full source summaries and facts already cheaply/reliably routed.

Start from compact validated package/evidence summaries. Area/owner recurrence,
cross-area owners, incident families, failed gates, corrective ownership, stable
facts, invariants, rejected directions and compatibility traps can trigger
read-only suggestions. Frequency cannot prove semantics, create promotions,
edit owners or accept guidance. When available, source helper
`tools/suggest_project_knowledge.py` supplies this bounded route.

At non-trivial task completion, review a small set of existing candidates
selected by that task's canonical owners, especially after recurring repairs.
Return contributing evidence and explicit omitted counts, or explain why no
reusable candidate is indicated. Keep this conditional and review-only: empty
knowledge indexes are valid, frequency is not authority, and completion must not
automatically promote proposals or preload unrelated project history.

The helper combines area/owner signals for single-area packages. For multi-area
packages it may suggest owner recurrence but never invented Cartesian pairs.
Incident families, failed gates and corrective owners remain separate signals.
Verify contributing compact entries against source records before applying
occurrence thresholds; select only facts owned by the candidate owner. Retain
bounded evidence samples and deterministic selector/evidence snapshot IDs.
Suppress unchanged snapshots already referenced by promotions; new evidence
creates review candidates. Index hashes support external invalidation, not
trusted cached candidates or automatic promotion.

Each proposal or directive should identify:

- the candidate statement and reuse rationale
- knowledge kind, fact type, fact IDs, project areas, and task profiles
- dependency, contract, path, symbol, and issue-lineage hints when applicable
- subsystem and architecture-item relationships when applicable
- origin as `engineering-discovery` or `decision-owner-directive`
- source engineering-evidence IDs for an engineering discovery, plus bounded
  repository evidence for either origin
- proposed canonical owner and decision owner, or an explicit ownership gap

Promotion needs a target-authorized decision owner; directives need verified
authority and durable decisions, not arbitrary human messages. Review may accept,
narrow, reject or defer. Acceptance requires the canonical owner to contain the
exact fact, through an update or existing wording; promotions cannot substitute.

## Authority And Freshness

Record authority and freshness independently.

Authority states:

- `accepted`: approved and owned by the named canonical project source
- `observed`: supported by repository evidence but not accepted as intent
- `proposed`: awaiting a project decision
- `unresolved`: evidence or ownership conflicts prevent classification

Freshness states:

- `current`: all required freshness evidence remains valid
- `revalidation-required`: a trigger changed or cannot be checked safely
- `contradicted`: applicable evidence conflicts with the retained conclusion
- `historical`: retained for explanation but not routine current guidance
- `superseded`: replaced by a named accepted knowledge item

Only `accepted` plus `current` may be delivered as a current project
constraint. `revalidation-required` may be delivered as a warning with the
canonical owner and next review action. `contradicted` must block a definitive
answer and route the conflict to the registered decision owner. `observed`,
`proposed`, `historical`, and `superseded` items remain outside routine task
packets unless the user explicitly requests investigation or history.

Freshness evidence should include the canonical owner content digest. Add
dependency version, upstream behavior, ownership, public-contract, replacement
decision, or review-expiry triggers when those conditions affect validity. A
digest difference proves that revalidation is needed; it does not prove which
statement is now correct.

For knowledge derived from code or contracts, bind applicable literal source
files with `source-sha256` triggers: target-relative `subject`, file-byte SHA-256
`expected`,
review `evidence` and revalidation `action`. At most 32 source bindings per item;
no globs, commands or inferred dependency closure. Missing coverage stays
unverified. Selection checks these hashes; unknown trigger kinds remain warnings.

Bind used ready plans to continuity: knowledge, owners, explicit sources and
query/index/shards. Without tooling, retain equivalent bounded versions and
expiry; unresolved coverage remains unverified. Recheck before material
decisions, edits, worker convergence and finalization. A changed source can
invalidate knowledge even when its prose is unchanged; changed routing requires
bounded reselection, including prior empty results. Preserve unresolved warnings
and reconsider affected conclusions, plans, tests and worker evidence. Hashes
locate changes, never decide which fact is accepted. Canonical updates require
current authorization; per-session check times never rewrite shared knowledge.

## Two-Stage Delivery

Non-trivial profiles preflight knowledge after bootstrap and area selection:

1. Select initial shards by profile, area, subsystem, architecture item,
   dependency, contract and task wording.
2. Enforce the initial item limit: accepted/current items are candidate
   constraints; stale/contradicted items are warnings/blockers.
3. Read each selected canonical owner before using the summary in a material
   decision.
4. Refine selected shards after inspection identifies fact IDs, paths, symbols,
   subsystem/architecture relationships, contracts, dependencies or issue lineage.
5. Enforce the refined limit; record used, inapplicable, stale, conflicted and
   intentionally omitted items.

Profile-only matches cannot load items: require an area, subsystem, architecture,
dependency, fact, contract, path, symbol or issue-lineage match. Deterministic
retrieval is optional; similarity, embeddings and model judgment cannot override
authority, freshness, applicability or packet limits.

No match resumes normal discovery, without proving absent relevant knowledge.

## Compact Index And Shards

The root index owns routing policy, packet limits, promotion references, and a
small shard directory. Each shard descriptor exposes only selectors needed to
decide whether that shard should be opened. Large targets should shard by
stable project area or bounded dependency domain rather than loading every
knowledge item.

Each route entry should include:

- stable knowledge ID and bounded summary
- fact type and stable fact IDs
- separate authority and freshness state
- canonical and decision owners with review evidence
- task, area, subsystem, architecture-item, dependency, path, symbol, contract,
  and issue selectors
- source engineering-evidence and promotion records
- freshness triggers and last checked evidence
- contradiction, supersession, and replacement relationships
- validation and residual uncertainty

The target chooses retention and redaction policy. Do not route secrets,
credentials, personal data, undisclosed vulnerabilities, raw chats, private
reasoning, or third-party content beyond the target's approved policy.

## Contradiction And Supersession

Do not merge conflicting knowledge by recency, frequency, agent vote, or
quantity of evidence.

When two applicable items conflict:

1. mark the affected entries `contradicted` or `revalidation-required`
2. preserve both provenance chains
3. identify the fact type and registered canonical owner
4. route the conflict to the target decision owner
5. update the canonical owner after a decision
6. record reciprocal conflict, supersession, or replacement links
7. regenerate the routing projection and revalidate affected packets

A superseded item remains historical. Do not delete it merely to make the
current index appear consistent.

## Narrowing And Authorized Exceptions

Do not impose one global precedence order across project fact types. The
registered target owner and conflict resolver determine whether guidance can be
narrowed or excepted.

A routed item identifies itself as a `base-rule`, `narrower-rule`, or
`authorized-exception`. A narrower rule or exception must name its base
guidance ID, bounded applicability scope, target authority reference,
rationale, validation, revalidation triggers, and expiry when the target uses
one. A lower-authority item cannot override a higher-authority owner or a
safety boundary. An absent or expired exception is not permission.

## Coverage And Known Gaps

Coverage is derived by area/fact type: `mapped` names existing guidance IDs;
`known-gap` identifies missing evidence/owners; `unknown` means unestablished.
No completeness percentages or absence-of-rule claims from missing entries.
Coverage supports discovery, not authority.

## Adoption State

The routing index records one machine-checkable adoption state:

- `enabled-empty`: the module is installed but has no promotions, coverage, or
  route entries; installation remains valid, but reuse is not demonstrated
- `populated`: at least one reviewed route entry exists, but no later-task reuse
  evidence is claimed
- `reuse-observed`: reviewed route entries exist and the index names explicit
  delivery or operation evidence from a later task

An empty module cannot block adapter acceptance, imply absent knowledge or prove
Project Development Model impact. `reuse-observed` requires recorded later-task
delivery, not merely installed entries.

## Cost And Evidence

Knowledge delivery is successful only when it preserves quality while reducing
repeated orientation. Record observable evidence rather than hidden reasoning:

- candidate, current, warning, and blocked items supplied
- selected item IDs and canonical owners reverified
- guidance kinds, origins, precedence states, and authorized exceptions
- mapped, known-gap, and unknown coverage relevant to the task
- orientation files opened and repeated known-fact searches when observable
- dependency source reopened only to recover a retained fact, and repeated
  discovery of a recorded invariant
- repeated human explanations
- routed knowledge used versus known context independently reconstructed
- time to the first evidence-supported hypothesis when observable
- context volume, packet-limit result, validation, and residual risk

Do not claim that one run proves rediscovery avoidance. Use a paired scenario
with the same later task and fresh execution surfaces: one without routed
knowledge and one with the reviewed route. Keep source state, acceptance
criteria, and validation equivalent, and report unavailable provider metrics
as unknown.

Cross-assistant conformance checks whether each supported surface receives the
same accepted authority, protected boundaries, required validation, and
unresolved decisions. It does not require identical implementation strategies
and does not treat human developers as assistant clients; human walkthroughs
are separate usability evidence.

## Explicit Planner Queries

Verified tooling may accept `context-plan --knowledge-request`: target-relative
schema-1 query, initial/refined stage, 1..8 registered shard IDs, bounded selectors
and a policy-limited item count. Reuse existing stage selectors; facts, paths and
symbols require refinement. Ordinary planning does not scan knowledge.

Report unsearched shards and incomplete global coverage. Contradictions and
applicable constraint/warning overflow block, not truncate. Count selected owners
and delivered results against existing budgets. Verify owner hashes and review
expiry plus explicit source hashes; expose other freshness triggers as unverified for target review.
Selection neither promotes authority nor demonstrates reuse/comprehension.
Full validation still owns complete registry consistency.

Examples retain applicability, exceptions, falsifying cases and freshness in
existing owners/routes. Curate incrementally, not through another registry or
growing bootstrap. Evaluate [later application](effectiveness-metrics.md);
output success alone does not authorize promotion.

## Final Evidence

Report:

- promotion candidates and human dispositions
- adoption state and explicit reuse evidence, or the enabled-empty limitation
- canonical owners updated or unresolved
- initial and refined selectors and selected shard IDs
- current items supplied, warnings, contradictions, and omissions
- freshness checks and supersession relationships
- packet limits and measured or unknown context cost
- canonical sources reverified
- validation, skipped checks, and residual risk

## Rejection Criteria

Reject or repair project-knowledge work that:

- promotes an assistant conclusion without target-owned review
- treats an arbitrary message as an authorized decision-owner directive
- treats an evidence or promotion record as the canonical owner
- routes observed, proposed, stale, contradicted, historical, or superseded
  knowledge as a current accepted constraint
- loads every retained item for an ordinary task
- uses profile similarity alone as sufficient applicability
- silently resolves conflicts by recency, frequency, or agent consensus
- marks an item current after its required owner digest or expiry changed
- duplicates large canonical explanations into routing summaries
- treats derived coverage as proof that unindexed guidance does not exist
- claims rediscovery savings without a comparable paired run
- stores prohibited private, secret, or raw reasoning content
