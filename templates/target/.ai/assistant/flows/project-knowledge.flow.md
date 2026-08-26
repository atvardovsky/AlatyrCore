# Project Knowledge Promotion And Delivery Flow

Use this flow to propose, review, promote, route, revalidate, supersede, or
explain reusable project knowledge in `{PROJECT_NAME}`. It does not authorize
project edits, commits, publication, or live external actions.

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

## Promotion Or Direct Guidance Intake

1. Classify the origin as an `engineering-discovery` or an explicitly recorded
   `decision-owner-directive`. Engineering discovery requires durable
   engineering evidence. A directive requires verified target decision
   authority and a durable decision reference. Both require bounded repository
   evidence and a registered canonical owner.
2. Under `read-only`, return a proposal only. Creating a promotion record or
   changing a canonical source requires current-scope authorization compatible
   with target policy.
3. Identify the fact type, fact IDs, proposed canonical owner, decision owner,
   and route hints. Report an ownership gap instead of inventing an owner.
4. Ask the target decision owner to accept, narrow, reject, or defer an
   engineering-discovery candidate. For a direct directive, verify that the
   named decision owner is authorized for the fact type and scope. Do not treat
   an arbitrary human message as project authority. Do not infer acceptance
   from silence, implementation frequency, test success, or previous approval
   for another scope.
5. For acceptance or narrowing, update or verify the canonical owner first and
   record its content SHA-256. Preserve the accepted wording and decision
   reference in the promotion record.
6. Create or update one bounded route entry, link its promotion and engineering
   evidence, add freshness triggers, and register its shard in the root index.
7. Validate reciprocal contradiction and supersession links. A contradicted
   entry cannot remain current.
8. Run target adapter and project validation. Report the promotion disposition,
   canonical update, route result, and residual uncertainty.
9. Synchronize the index adoption state. Use `enabled-empty` only with no
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

1. Compare canonical-owner digests and applicable dependency, ownership,
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
