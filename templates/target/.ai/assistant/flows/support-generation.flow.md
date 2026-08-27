# Support Generation Flow

Use this flow only when the `support-generation` module is enabled.

1. Read the generated support-generation plan, not the complete support corpus.
2. Resolve each artifact's canonical owner before interpreting its inputs.
3. Treat `deterministic-derived`, `assistant-proposed`, and `owner-maintained`
   as different execution contracts.
4. Never execute assistant-proposed or owner-maintained records as commands.
5. For deterministic application, require current `modify` authorization, the
   current plan digest and repository base, staged output, validation, and any
   protected-change approval named by the artifact.
6. Recheck the generation index, recursive context indexes, support state, and
   logical integrity after generated output is applied.
7. Report stale artifacts, actions deliberately not applied, validation, and
   residual risk.

Generated indexes route work. They do not replace generator policy owners or
authorize repository changes.
