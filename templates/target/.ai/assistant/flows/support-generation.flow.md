# Support Generation Flow

Use this flow only when the `support-generation` module is enabled.

1. Read the generated support-generation plan, not the complete support corpus.
2. Resolve each artifact's canonical owner before interpreting its inputs.
   Require every declared input to meet its `min_matches` contract unless it
   is explicitly optional. Propagate stale state through every declared
   downstream dependency.
3. Treat `deterministic-derived`, `assistant-proposed`, and `owner-maintained`
   as different execution contracts.
4. Never execute assistant-proposed or owner-maintained records as commands.
5. For deterministic application, require current `modify` authorization, the
   current plan digest and repository base, non-escaping non-symlink staged
   output, successful required command validation, and any protected-change
   approval named by the artifact and bound to the plan, base, and output
   scope. Reject directory destinations. Generate and validate the complete set
   before replacement; rollback all applied outputs to their exact prior files
   if replacement fails.
6. Recheck the generation index, recursive context indexes, support state, and
   logical integrity after generated output is applied.
   Applying deterministic outputs must remove stale review evidence from any
   changed assistant-proposed or owner-maintained dependent; it must not record
   that dependent as current.
7. Record an assistant-proposed or owner-maintained artifact as current only
   with current `modify` authorization and target-relative review evidence
   supplied through `--review-evidence ARTIFACT_ID=PATH`. Bind that evidence by
   content digest so later edits or deletion make the artifact stale. Never use
   `--record` to bypass stale deterministic generation.
8. Report stale artifacts, actions deliberately not applied, validation, and
   residual risk.

Generated indexes route work. They do not replace generator policy owners or
authorize repository changes.
