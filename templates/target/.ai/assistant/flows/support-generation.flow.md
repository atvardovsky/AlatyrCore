# Support Generation Flow

Use this flow only when the `support-generation` module is enabled.

1. Read the generated support-generation plan, not the complete support corpus.
2. Resolve each artifact's canonical owner before interpreting its inputs.
   Propagate stale state through every declared downstream dependency.
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
7. Report stale artifacts, actions deliberately not applied, validation, and
   residual risk.

Generated indexes route work. They do not replace generator policy owners or
authorize repository changes.
