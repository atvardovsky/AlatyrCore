# Security Policy

## Scope

Security reports may cover AlatyrCore framework documents, schemas, target
templates, source tools, assistant bridges, extension and dependency handling,
approval enforcement, or target-validator behavior.

AlatyrCore is currently an alpha project. It does not provide a hosted runtime,
execute target-project code by itself, or provide a guaranteed response SLA.

## Reporting

Do not publish credentials, private target-project material, exploit details,
or sensitive imported AI infrastructure in a public issue.

Use GitHub private vulnerability reporting for this repository when the
repository setting is available. If it is unavailable, open a minimal public
issue asking the maintainer for a private reporting channel without including
the vulnerability details.

Include:

- affected AlatyrCore version or commit
- affected framework, schema, template, or tool surface
- reproduction steps using non-sensitive fixtures
- expected and observed security boundary
- known impact and suggested containment

## Target Repositories

Installing AlatyrCore does not transfer ownership or security responsibility
for target-project code, architecture, business facts, credentials, or adapter
content. Target repositories must retain their own disclosure, access-control,
secret-handling, dependency, and incident-response policies.
