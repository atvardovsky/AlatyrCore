# Team Collaboration Skill

Status: `{PROPOSED_ACCEPTED_DEPRECATED_CONTRADICTED_OR_UNKNOWN}`
Target policy: `.ai/project/team-policy.json`
Portable rule: `.ai/framework/team-collaboration.md`

Use this thin skill only after the target has enabled `team-collaboration` and
adapted it for the supported assistant. Canonical behavior remains in the team
flows and gate.

## Activation

- The user asks to set or inspect the current actor.
- A team task, claim, conflict, checkpoint, handoff, decision, review, merge
  check, or release operation is selected.
- A write operation matches an active task by task reference, branch,
  worktree, project area, changed fact, contract, dependency, or surface.

## Process

1. Read the compact active-work index before the full registry or unrelated
   task records.
2. Resolve the current actor from explicit request or ignored local identity.
3. Load only the selected task, relevant overlaps, target policy, backend
   contract, matching team flow, and gate.
4. Recheck task record revision before writing and stop on concurrent change.
5. Keep assignment, attribution, authority, review, and approval distinct.
6. Record revision-bound evidence and the next responsible actor.

## Prohibited

- Do not treat a selected display name as authentication or authority.
- Do not infer identity from Git author, OS username, or assistant account.
- Do not edit global Git configuration.
- Do not overwrite another actor's task update or load unrelated team history.
- Do not duplicate target policy or project facts in this skill.
