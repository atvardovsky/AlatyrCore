# Fixture: Python CLI With Existing AI Instructions

This fixture describes a target repository shape. It is not a generated target
adapter.

## Target Shape

- Existing `AGENTS.md`
- Python package metadata exists
- CLI source directory exists
- Basic tests exist
- No source-of-truth registry exists
- No adapter manifest exists
- No bridge capability matrix exists

## Expected Alatyr Behavior

- Preserve existing `AGENTS.md` unless explicit approval allows overwrite.
- Create or propose `.ai/alatyr.yaml`.
- Create or propose `.ai/framework`.
- Create or propose `.ai/project/source-of-truth-registry.md` with missing
  owners marked.
- Create or propose `.ai/assistant/context-profiles.md`.
- Mark security-sensitive and data work as blocked until target policies exist.
- Report target validation commands only if discovered from target evidence.
