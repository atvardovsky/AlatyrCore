# Fixture: Mixed Monorepo

This fixture describes a target repository with multiple packages.

## Target Shape

- Multiple package directories exist
- Shared docs exist
- Tests and validation vary by package
- Existing assistant bridge files may exist
- Ownership of public docs versus package code is ambiguous

## Expected Alatyr Behavior

- Start from bootstrap context and select task profiles per package or fact
  type.
- Require a source-of-truth registry before broad consistency claims.
- Record package-specific validation gaps instead of inventing one command.
- Use bridge capability matrix for supported assistant surfaces.
- Report task-specific maturity per work type rather than one global result.
