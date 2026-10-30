# Project Knowledge Promotion And Delivery Flow

Propose, review, promote, route, revalidate, supersede or explain knowledge in
`{PROJECT_NAME}`. This flow grants no action authority.

## Sources

- Rule owner: `.ai/framework/project-knowledge.md`
- Source-of-truth registry: `.ai/project/source-of-truth-registry.md`
- Routing index: `.ai/project/knowledge/index.json`
- Descriptor: `.ai/assistant/context/project-knowledge-routing.json`
- Templates: `.ai/assistant/templates/project-knowledge-promotion.json` and
  `.ai/assistant/templates/project-knowledge-route-shard.json`
- Gate: `.ai/assistant/gates/project-knowledge.md`
- Selected engineering evidence, canonical owners and repository evidence

## Delivery

1. Select the smallest profile/areas and read the compact index. Match bounded
   shard descriptors by profile plus a concrete area, subsystem, architecture,
   dependency, contract, path, symbol, fact or issue signal. Never load unrelated
   shards or treat profile-only matches as sufficient.
2. Enforce initial packet limits and verify selected owners/freshness. Supply
   accepted/current items as candidate constraints, stale items as warnings and
   contradictions as blockers; keep other states lazy.
3. After inspection identifies concrete selectors, perform one refined route.
   Record selected, used, inapplicable, stale, blocked, rejected and omitted IDs.
4. Bind used ready plans through session continuity. Recheck owners, sources,
   query/index/shards and expiry at checkpoints, preserving warnings. New matches
   after an empty result require rerouting.

## Completion Proposals And Promotion

1. At non-trivial completion, use available `suggest-knowledge --task-id ID
   --limit 3` or explicit `--owner` files. Review relevant recurrence proposals,
   contributing evidence and omissions. No match/empty index is not a defect.
2. Suggestions use validated/completed summaries with verified record projections,
   bounded samples and existing-promotion suppression. Frequency/digests are not
   semantic proof; never invent area/owner pairs or promote automatically.
3. Apply the owner's Promotion Lifecycle: distinguish `engineering-discovery`
   from `decision-owner-directive`. Verify durable evidence, current authority,
   fact IDs, canonical/decision owners and route hints. Report gaps, not guessed
   owners. Current-scope authorization is required for canonical/promotion edits.
4. Obtain the owner's accept/narrow/reject/defer disposition. First verify/update
   the canonical owner and SHA-256; retain accepted wording and decision sources.
   Messages, silence, repeated use and previous approvals do not establish authority.
5. Publish one bounded route entry linked to promotion/evidence and register its
   shard. Bind literal code/contract dependencies with `source-sha256`;
   undeclared dependency coverage remains unverified.
6. Validate reciprocal contradiction/supersession links and run target validation.
   Reconcile adoption state: `enabled-empty`, `populated`, or `reuse-observed`
   only with the owner's required evidence; never infer measured benefit.

## Exceptions, Coverage And Revalidation

Follow the owner's Narrowing And Authorized Exceptions contract: name base
guidance, scope, authority, rationale, validation, revalidation and expiry.
No global precedence shortcut permits safety override.

Maintain area/fact coverage as `mapped`, `known-gap` or `unknown`; mapped
entries reference existing guidance. Do not publish completeness percentages
or infer absent guidance from index gaps.

Compare owner/source digests and applicable freshness triggers. Changed or
unverifiable evidence requires `revalidation-required`; hashes cannot infer
new facts. Preserve provenance for contradictions, resolve through canonical
ownership and retain replaced entries as `superseded`, never current.

## Final Evidence

Report mode/authorization, proposal/disposition, canonical and route changes,
initial/refined selectors, selected/omitted IDs, freshness/conflicts, packet
limits, adoption/reuse evidence or enabled-empty limitations, validation and risk.
