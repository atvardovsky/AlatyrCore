# Adapter Health Flow

Use this read-only flow in `{PROJECT_NAME}` for `Alatyr status`, `Alatyr
doctor`, or a request for the current installed adapter state.

Replace placeholders with target facts before accepting installation.

## Boundaries

- Allowed actions are `read-only`.
- Do not repair files, fetch remote sources, install dependencies, change
  permissions, or invoke live project services.
- Health is current structural evidence, not task-specific maturity and not a
  claim that project business logic is correct.
- A repository-local checker may be run only when its command is recorded in
  the target manifest or adapter documentation.

## Target Sources

- Adapter manifest: `.ai/alatyr.yaml`
- Context router: `.ai/assistant/context-router.json`
- Operation catalog: `.ai/assistant/operation-catalog.json`
- Module profile: `.ai/assistant/module-profile.md`
- Maturity profile: `.ai/assistant/maturity-profile.md`
- Bridge matrix: `.ai/assistant/bridge-capability-matrix.md`
- Adapter recheck flow: `.ai/assistant/flows/adapter-recheck.flow.md`
- Target validation: `{TARGET_VALIDATION_OR_MANUAL_REVIEW}`

## Steps

1. Treat `AGENTS.md` as preloaded and load only the compact bootstrap plus the
   operation catalog and module profile.
2. Record observation time and repository revision when available. If neither
   is available, mark freshness as unknown.
3. Check bootstrap agreement between the manifest, context router, root entry
   point, and `.ai/README.md`.
4. Check manifest, framework baseline, adapter schema, template version,
   operation catalog, module profile, and known-gap consistency.
5. Check unresolved placeholders, hard-coded absolute local paths, stale
   checker claims, and missing referenced files.
6. Check that supported assistant bridges route to the same compact help,
   operation catalog, context router, and health operation.
7. Run a recorded target-local adapter validator when it exists and read-only
   execution is permitted. Otherwise record the check as unavailable; do not
   invent a command.
8. Classify health as:
   - `ready`: required current checks passed with no blocking findings;
   - `attention`: actionable non-blocking drift or stale evidence exists;
   - `blocked`: a required adapter contract is missing, invalid, or unsafe;
   - `unverified`: evidence is insufficient to classify the current state.
9. For each finding record severity, stable finding code, owning surface,
   evidence, proposed repair operation, approval need, and automatic-repair
   eligibility from target policy.
10. Return no more than three prioritized repair operations. Do not apply them
    in this flow.

## Final Evidence

```text
Alatyr adapter health: <ready, attention, blocked, or unverified>
Evidence: <time and repository revision, or unknown>
Checks run: <commands and manual checks>
Checks unavailable: <checks and reasons>
Finding: <severity, code, owner, evidence, repair operation, approval need>
Next actions: <up to three operation IDs>
Files changed: none
```

## Rejection Criteria

Reject or revise a health result that:

- changes repository files
- claims freshness without a time, revision, or explicit unknown marker
- treats maturity as the same thing as structural health
- invents a local checker or validation command
- reports a finding without an owner and repair route
- hides blocking safety, approval, bootstrap, or manifest failures
