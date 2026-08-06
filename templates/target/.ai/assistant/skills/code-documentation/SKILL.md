# Project Code Documentation Skill

Status: `{PROPOSED_ACCEPTED_DEPRECATED_CONTRADICTED_OR_UNKNOWN}`
Canonical profiles: `.ai/project/documentation/profiles.json`
Canonical catalog: `.ai/project/documentation/catalog.json`
Portable rule: `.ai/framework/code-documentation.md`

Use this skill only after the target has adapted it and recorded an accepted
profile for the selected source scope.

## Activation

- The request asks to propose, review, write, synchronize, or generate code
  documentation.
- The changed source path matches one unambiguous accepted profile.
- Allowed actions permit the requested source, configuration, generation, or
  publication work.

## Process

1. Load the compact catalog and select the most specific accepted profile.
2. Stop and report ambiguity when equally specific accepted profiles conflict.
3. Resolve canonical fact owners before drafting comments.
4. Apply the profile's syntax, required symbol set, semantic sections, and
   avoid rules; do not narrate obvious code or repeat type information.
5. Treat business, architecture, security, API-specification, data, and
   operational facts as links or derived explanations unless the target
   registry explicitly assigns comment ownership.
6. Never edit generated output directly.
7. Run only the target-recorded generation and validation entry points allowed
   by the request.
8. Report selected profile, comments changed, symbols skipped, generated
   output, validation, skipped checks, and residual risk.

## Prohibited

- Do not activate this placeholder as an accepted project skill.
- Do not mass-edit source with a proposed, unknown, contradicted, deprecated,
  or ambiguous profile.
- Do not install dependencies, change CI, publish externally, or broaden source
  scope without required approval.
- Do not claim semantic correctness because generation succeeded.
