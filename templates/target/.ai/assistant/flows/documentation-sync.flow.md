# Documentation Sync Flow

## Purpose

Keep target code, docs, diagrams, prompts, gates, skills, bridge files, and
assistant workflows synchronized after relevant changes.

## Steps

1. Inspect changed files.
2. Apply the Semantic Change Decision Gate from
   `.ai/assistant/gates/checklist.md`.
3. Identify changed facts, not only changed files.
4. Map changed facts to target source-of-truth docs.
5. Update companion code, docs, tests, diagrams, prompts, gates, skills,
   bridge files, or checker rules when affected.
6. Run target validation that exists.
7. Report skipped checks and residual risk.

## Target Sources

- `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- `{TARGET_PUBLIC_DOCS}`
- `{TARGET_TEST_STRATEGY}`
- `{TARGET_DIAGRAM_POLICY}`

