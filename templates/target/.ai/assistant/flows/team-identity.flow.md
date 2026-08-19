# Team Identity Flow

Use this flow in `{PROJECT_NAME}` to inspect, select, or clear the current
local actor when `team-collaboration` is enabled.

The local identity file is `.ai/local/team-identity.json`. It is ignored by
`.ai/.gitignore` and must never be treated as authentication, approval, or a
canonical actor registry.

## Sources

- Canonical team policy: `.ai/project/team-policy.json`
- Local identity example:
  `.ai/assistant/templates/team-identity.example.json`
- Target identity provider or mapping: `{TARGET_IDENTITY_PROVIDER_OR_NONE}`
- Team gate: `.ai/assistant/gates/team-collaboration.md`

## Who Am I

For `Alatyr who am I`:

1. Keep allowed actions `read-only`.
2. Read the local identity when present and resolve its actor ID against the
   current policy revision.
3. Report actor ID, display name, roles, status, selection source,
   verification state, and policy staleness.
4. Do not claim authentication or authority from a local selection.

## Set Actor

For `Alatyr set actor {ACTOR_ID_OR_NAME}`:

1. Require an explicit user request and `adapter-only` local-state permission.
2. Match the input against active actor IDs, display names, and aliases.
3. If exactly one active actor matches, show the resolved actor ID and write a
   local identity record with selection time, policy revision, and verification
   state.
4. If no actor matches, return an enrollment proposal for the team-policy owner.
5. If multiple actors match, ask for the stable actor ID.
6. Never add an actor, grant a role, change authority, or modify Git
   configuration as part of local selection.

## Clear Actor

For `Alatyr clear actor`, remove only `.ai/local/team-identity.json` after an
explicit request. Preserve the canonical team policy, task attribution, Git
identity, and historical records.

## Final Evidence

Report the operation, resolved actor ID or unresolved input, local-state path,
selection source, verification state, policy revision, actions not taken, and
next owner when enrollment or verification is needed.
