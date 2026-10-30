# Project Knowledge Promotion And Delivery Flow

Propose, review, promote, route, revalidate, supersede or explain knowledge in
`{PROJECT_NAME}`. This flow authorizes no edits, commits, publication or live actions.

## Sources

- Rule owner: `.ai/framework/project-knowledge.md`
- Source-of-truth registry: `.ai/project/source-of-truth-registry.md`
- Routing index: `.ai/project/knowledge/index.json`
- Routing descriptor: `.ai/assistant/context/project-knowledge-routing.json`
- Promotion template: `.ai/assistant/templates/project-knowledge-promotion.json`
- Route-shard template: `.ai/assistant/templates/project-knowledge-route-shard.json`
- Gate: `.ai/assistant/gates/project-knowledge.md`
- Selected engineering evidence, canonical owners, and repository evidence

## Delivery

1. Select the smallest task profile and applicable project areas.
2. Read the compact root index. Select shard descriptors using profile plus at
   least one area, subsystem, architecture item, dependency, contract, path,
   symbol, fact, or issue signal.
3. Apply the initial packet limit. Do not open unrelated shards.
4. Reverify each selected canonical owner and applicable freshness trigger.
5. Supply only accepted and current items as candidate constraints. Supply
   stale items as warnings and contradictions as blockers. Keep all other
   states lazy.
6. After initial inspection identifies concrete facts, paths, symbols,
   subsystems, architecture items, dependencies, contracts, or issue lineage,
   perform one refined route.
7. Record selected, used, stale, blocked, rejected-as-inapplicable, and omitted
   item IDs in the context receipt.
8. Bind the used ready plan through the session-continuity flow. Recheck owners,
   declared sources, query/index/shards and expiry at work checkpoints; retain
   warnings. New matches after an empty result require rerouting too.

## Promotion Or Direct Guidance Intake

1. Suggestions inspect only validated/completed package and engineering-evidence
   summaries. Return bounded candidates and contributing evidence IDs. Verify
   compact entries against records, combine area/owner signals, bound samples
   and suppress unchanged snapshots already named by promotions. Input hashes
   permit external invalidation, never trusted cached candidates. `read-only`
   creates neither promotions nor knowledge edits.
2. Classify `engineering-discovery` (durable engineering evidence required) or
   recorded `decision-owner-directive` (verified authority and durable decision
   required). Both need bounded repository evidence and a registered owner.
3. Promotion records and canonical edits require current-scope target-compatible
   authorization. Read-only results remain proposals.
4. Identify the fact type, fact IDs, proposed canonical owner, decision owner,
   and route hints. Report an ownership gap instead of inventing an owner.
5. The target owner accepts, narrows, rejects or defers discoveries. Directives
   require authority for this fact type/scope; arbitrary messages, silence,
   frequency, passing tests and previous-scope approvals cannot establish it.
6. Acceptance/narrowing first verifies or updates the canonical owner and its
   SHA-256. Promotions preserve accepted wording and decision references.
7. Create or update one bounded route entry, link its promotion and engineering
   evidence, add freshness triggers, and register its shard in the root index.
   Bind applicable literal code/contract dependencies with `source-sha256`;
   unknown dependency coverage is not proof of freshness.
   Curate reusable examples through the canonical owner's applicability,
   exception and falsifying-case guidance, not a separate memory registry.
8. Validate reciprocal contradiction and supersession links. A contradicted
   entry cannot remain current.
9. Run adapter/project validation; report disposition, canonical/route changes
   and residual uncertainty.
10. Synchronize the index adoption state. Use `enabled-empty` only with no
   promotions, coverage, or route entries; use `populated` after reviewed route
   entries exist; use `reuse-observed` only with explicit later-task delivery
   or operation evidence.

## Narrowing, Exceptions, And Coverage

1. Classify each routed entry as a base rule, narrower rule, or authorized
   exception. A narrowing or exception names its base guidance ID.
2. Verify scope, decision authority, rationale, validation, revalidation
   triggers, and expiry. Never use a global precedence shortcut or let a lower
   authority override target safety.
3. Maintain the derived coverage view with `mapped`, `known-gap`, or `unknown`
   states by area and fact type. Mapped entries reference existing guidance IDs.
4. Do not publish a completeness percentage or treat missing index coverage as
   proof that no guidance exists.

## Revalidation And Conflict

1. Compare canonical-owner/source digests and applicable dependency, ownership,
   contract, upstream, replacement, maintainer-review, and expiry triggers.
2. Change `current` to `revalidation-required` when evidence changed or cannot
   be checked. Do not infer the new fact from a digest difference.
3. Mark conflicting applicable items `contradicted`, preserve provenance, and
   route the issue to the source-of-truth conflict resolver.
4. After a decision, update the canonical owner and reciprocal relationship
   links. Keep replaced entries as `superseded` historical evidence.

## Final Evidence

Report operation mode, current authorization, proposal and disposition,
canonical owner update, initial and refined selectors, selected and omitted
items, freshness and conflict results, packet limits, adoption state and reuse
evidence or enabled-empty limitation, validation, and residual risk.
