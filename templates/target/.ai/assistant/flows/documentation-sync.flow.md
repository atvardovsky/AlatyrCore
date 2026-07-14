# Documentation Sync Flow

## Purpose

Keep target code, docs, diagrams, prompts, gates, skills, bridge files, and
assistant workflows synchronized after relevant changes.

## Steps

1. Inspect changed files.
2. Apply the Semantic Change Decision Gate from
   `.ai/assistant/gates/checklist.md`.
3. Apply `.ai/framework/logical-integrity.md` for changed facts, source of
   truth, repair direction, and evidence.
4. Identify changed facts, not only changed files.
5. Resolve changed fact IDs and canonical owners. When the optional
   `consistency-map` module is enabled, follow applicable `documents`,
   `visualizes`, `generates`, `verifies`, and dependent-contract edges.
6. Record selected and skipped relationships instead of scanning unrelated
   project areas.
7. Update companion code, docs, tests, diagrams, prompts, gates, skills,
   bridge files, or checker rules when affected.
8. Run target validation that exists.
9. Report skipped edges, skipped checks, and residual risk.

## Target Sources

- `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- `{TARGET_PUBLIC_DOCS}`
- `{TARGET_BLUEPRINT_OR_EQUIVALENT}`
- `{TARGET_TEST_STRATEGY}`
- `{TARGET_DIAGRAM_POLICY}`
- `.ai/project/consistency-map.json` when the optional module is enabled
