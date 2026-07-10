# Fixture: Minimal Frontend App

This fixture describes a frontend target shape.

## Target Shape

- README exists
- UI source exists
- Build metadata exists
- Visual regression or accessibility policy is missing
- Diagram policy is missing
- Existing assistant instructions are absent

## Expected Alatyr Behavior

- Create or propose root assistant entry points from templates.
- Mark visual validation and accessibility checks as missing unless target
  evidence defines them.
- Use `docs-local` for wording-only docs updates.
- Use `business-change` when UI behavior or public product behavior changes.
- Do not invent local build, test, or screenshot commands.
