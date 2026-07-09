# Logical Consistency Review Flow

## Purpose

Tell an assistant how to reason about consistency before using target
validation as evidence.

## Steps

1. Apply the Semantic Change Decision Gate.
2. List changed facts in concrete language.
3. Map each changed fact to target contracts:
   - business/domain rules
   - use cases or workflows
   - architecture levels or module boundaries
   - object/data contracts
   - diagrams
   - tests and validation
   - prompts, gates, skills, and bridge files
4. Compare code, docs, tests, diagrams, and assistant rules.
5. Choose the source of truth.
6. Repair the smallest coherent set of files.
7. Run target validation that exists.

## Explanation Format

```text
Logical issue: <short category>
Changed fact: <what changed>
Expected contract: <which target source says otherwise>
Conflict: <what disagrees with what>
Source of truth: <code/docs/proposal/manifest and why>
Repair: <files or behavior to change>
Gate: <target validation or manual review>
```

