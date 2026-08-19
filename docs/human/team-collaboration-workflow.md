# Team Collaboration Workflow

AlatyrCore's optional team module coordinates humans and interchangeable AI
assistants around project-owned actors, tasks, changed facts, decisions, and
revision-bound evidence. It supplements the project's tracker, version control,
review rules, and decision owners; it does not replace them.

> This document is a human-oriented explanation. Canonical behavior is owned by
> [team collaboration](../../framework/team-collaboration.md) and the
> [rule registry](../../framework/rule-registry.md).

## Select Local Attribution

```text
Developer:
Alatyr set actor alice

Alatyr:
Resolved actor: alice
Display name: Alice
Selection: local attribution
Verification: unverified local selection
Policy revision: team-policy-7
```

The selection is stored in ignored `.ai/local/team-identity.json`. It does not
authenticate Alice, grant authority, approve changes, or modify Git identity.
An unknown name is proposed for enrollment by the target team-policy owner.

Use `Alatyr who am I` to inspect the current selection and `Alatyr clear actor`
to remove only the local record.

## Start And Claim Work

```text
Developer:
Alatyr start add payment retry handling
```

The assistant resolves the current actor, task scope, changed facts, canonical
owners, priority, reviewers, allowed actions, and active-work overlap. It writes
one task record only when target policy and backend permissions allow it.

Before any later state-changing operation, the assistant checks the compact
active-work index. It loads full team context only for a matching task, branch,
worktree, project area, fact, owner, contract, dependency, or expected surface,
or when the compact evidence cannot rule out overlap.

## Coordinate And Resume

Use these natural-language shortcuts as needed:

- `Alatyr team status` reports up to three coordination actions.
- `Alatyr conflicts <task-id>` compares logical overlap before file overlap.
- `Alatyr checkpoint <task-id>` records bounded resume evidence.
- `Alatyr handoff <task-id>` creates an explicitly accepted handoff.
- `Alatyr decision <question>` routes an accepted fact to its canonical owner.

Task writes include the revision observed by the actor. If another actor or
backend update changed that revision, Alatyr stops, refreshes the selected task,
and re-evaluates the proposed delta instead of overwriting it.

## Review And Merge Readiness

`Alatyr review <task-id>` checks scope, concurrent work, required reviewers,
approval, validation, documentation, diagrams, generated artifacts, and
logical integrity. `Alatyr merge check <task-id>` verifies that this evidence
still applies to the current head and base revisions.

Merge readiness is evidence, not permission to merge. A changed diff, base,
approval, dependency, task record, backend revision, or relevant concurrent
task invalidates stale evidence.

## Current Limitation

AlatyrCore provides the portable policy, target templates, validator, and
conformance scenarios. A real repository must still adapt its actors, authority,
tracker or repository backend, atomic-update mechanism, authentication,
permissions, retention, and validation. Provider integrations are target tools
or reviewed extensions; AlatyrCore does not include a universal hosted team
service.
