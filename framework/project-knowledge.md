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

This rule provides the derived guidance layer of the Project Development Model.
It closes the loop from either a material engineering discovery or an explicit
decision-owner directive to later related work. It lets an assistant propose
reusable knowledge, lets an authorized project decision owner record guidance
directly, requires project-owned acceptance, and routes a small derived packet
to later developers or assistants.

Project knowledge is not automatically project authority. Only an accepted
fact recorded by its canonical project owner represents project intent. A
historical evidence record, repeated implementation pattern, assistant
conclusion, or newer timestamp does not become project will by itself.

The guidance layer is an envelope and routing projection, not a new source of
truth. Architecture, business policy, validation, security, API, data, and
other project facts remain owned by the canonical sources registered for their
fact types.

## Guidance Kinds And Required Identity

Classify every version-2 routed item as one of:

- `development-rule`: an accepted way the target expects engineering work to
  be performed
- `architectural-intent`: a recorded design boundary or rationale owned by an
  architecture source
- `reviewed-knowledge`: a reusable conclusion accepted after engineering
  discovery
- `validation-contract`: a required proof or check owned by target validation
  policy
- `known-restriction`: an accepted limitation, compatibility boundary, or
  prohibited direction

Each item needs a stable ID, kind, canonical owner, decision owner, authority,
rationale, applicability, freshness evidence, validation, exception or
narrowing state, and supersession lineage. The route may summarize those facts
for selection, but it must retain owner references and content digests.

## Responsibility Boundaries

Keep these surfaces separate:

- durable engineering evidence records what a completed investigation found
- a promotion record preserves the human disposition of one reusable
  conclusion or the intake of one authorized decision-owner directive
- the source-of-truth registry identifies the canonical owner and conflict
  resolver for the accepted fact type
- the canonical target source owns the accepted project fact
- the project-knowledge routing index and shards are compact derived
  projections used to find that owner during later work

The routing projection must never become a second canonical repository. It may
carry a short bounded summary for selection, but the assistant must cite and
reverify the canonical owner before relying on the fact for a material
decision.

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

The assistant may propose a candidate when the conclusion is expensive to
reconstruct, non-obvious from local code, cross-area, dependency-sensitive,
historically important, a compatibility trap, a rejected direction likely to
recur, or an explanation of why a constraint exists. Do not propose line
numbers, obvious declarations, complete source summaries, or facts that are
already cheaply and reliably routed from their canonical owner.

Each proposal or directive should identify:

- the candidate statement and reuse rationale
- knowledge kind, fact type, fact IDs, project areas, and task profiles
- dependency, contract, path, symbol, and issue-lineage hints when applicable
- subsystem and architecture-item relationships when applicable
- origin as `engineering-discovery` or `decision-owner-directive`
- source engineering-evidence IDs for an engineering discovery, plus bounded
  repository evidence for either origin
- proposed canonical owner and decision owner, or an explicit ownership gap

Promotion requires a target-authorized decision owner. A direct directive is
valid only when the target can identify that authority and a durable decision
reference; an arbitrary human message does not become project guidance. The reviewer
may accept, narrow, reject, or defer the candidate. Acceptance is incomplete
until the canonical owner is updated or already contains the exact accepted
fact. A promotion record cannot itself substitute for that owner.

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

## Two-Stage Delivery

Every non-trivial selected task profile should perform a bounded knowledge
preflight after bootstrap and project-area selection:

1. Initial route: select candidate shards from the task profile, project area,
   subsystem, architecture item, named dependency, contract, and explicit task
   wording.
2. Load no more than the configured initial item limit. Current accepted items
   become candidate constraints; stale or contradicted items become warnings or
   blockers.
3. Read each selected canonical owner before using the summary in a material
   decision.
4. Refined route: after initial inspection identifies changed fact IDs, paths,
   symbols, subsystem or architecture relationships, contracts, dependencies,
   or issue lineage, query the selected shards again.
5. Load no more than the configured refined item limit and record which items
   were used, rejected as inapplicable, stale, conflicted, or intentionally
   omitted.

Task-profile matching alone is not enough to load an item. At least one
project-area, subsystem, architecture item, dependency, fact, contract, path,
symbol, or issue-lineage signal must match. A target may add deterministic
retrieval tooling, but natural-
language similarity, embeddings, or model judgment must not silently override
authority, freshness, applicability, or packet limits.

If no item matches, continue with normal repository discovery. Absence from the
routing index does not prove that the project has no relevant knowledge.

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

The compact index may publish a derived coverage view by project area and fact
type. Use only `mapped`, `known-gap`, and `unknown` states. `Mapped` entries
name existing guidance IDs. `Known-gap` entries state the missing evidence or
owner. `Unknown` means coverage has not been established.

Do not calculate a completeness percentage or infer that an area has no rule
because no routing entry exists. The coverage view is discovery evidence, not
project authority.

## Adoption State

The routing index records one machine-checkable adoption state:

- `enabled-empty`: the module is installed but has no promotions, coverage, or
  route entries; installation remains valid, but reuse is not demonstrated
- `populated`: at least one reviewed route entry exists, but no later-task reuse
  evidence is claimed
- `reuse-observed`: reviewed route entries exist and the index names explicit
  delivery or operation evidence from a later task

An empty module must not block adapter acceptance or imply that the project has
no knowledge. It must also not be presented as proof that Project Development
Model guidance affected engineering work. Move to `reuse-observed` only from
recorded delivery evidence, never from the mere presence of a route entry.

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
