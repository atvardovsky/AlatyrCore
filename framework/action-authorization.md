---
alatyr_doc:
  id: framework.action-authorization
  type: framework-rule-owner
  owns_rules:
    - ALATYR-AUTHORIZATION-001
  depends_on:
    - ALATYR-APPROVAL-001
  applies_to:
    - all
---
# Action Authorization

This document defines how an assistant determines whether the current user
request permits inspection, repository mutation, Git history mutation,
publication, or live external action.

Action authorization is not the same as operation routing, allowed actions,
protected-change approval, tool permission, task assignment, or project
decision authority. Each is an independent boundary and all applicable
boundaries must pass.

## Current Logical Scope

Authorization belongs to one current logical scope. A scope starts from the
latest user request that selects a concrete goal, or from an explicit
continuation of an unfinished task. It ends when:

- the requested outcome is completed or reported as complete
- the user redirects to another issue, backlog item, task, project, or goal
- the requested operation materially changes
- the expected changed facts, surfaces, or external effects expand materially
- the user pauses, cancels, or replaces the request

Authorization from a completed or replaced scope must not be reused. A prior
request to commit or push does not authorize commit or push for a later task.

`Continue` may retain only the already explicit phases of the same unfinished
scope. If no unfinished scope can be identified unambiguously, continue is
read-only until the user identifies the task and requested next action.

## Authorization Phases

Evaluate authorization separately before each phase:

- `inspect`: read, analyze, discuss, review, plan, explain, compare, or report
  without meaningful repository or external state mutation
- `modify`: create, edit, delete, generate, or otherwise change repository
  working-tree content
- `commit`: stage or unstage changes; create, amend, rewrite, merge, rebase,
  stash, reset, fetch, pull, switch, branch, tag, or otherwise change the Git
  index, local repository history, references, or checked-out revision
- `publish`: push Git refs, create or mutate pull requests, publish releases or
  packages, comment on or change issues/reviews, or otherwise mutate a remote
  collaboration or distribution system
- `live-external`: deploy, call a live service with effects, change production
  state, spend money, rotate credentials, or perform another operational side
  effect

A phase authorizes only itself and lower-risk inspection needed to perform it.
It does not authorize another state-changing phase. In particular:

- implementation intent does not authorize commit or publish
- commit intent does not authorize publish
- approval of a protected semantic change does not authorize implementation,
  commit, publish, or a live action by itself
- tool availability or client permission does not authorize use

The user may authorize several phases in one clear current-scope request, such
as `implement, commit, and push`. Do not ask again for a phase already stated
unambiguously unless scope or risk changed. Ask before the first unauthorized
phase.

## Intent Classification

Use the newest user instruction and its current scope. Do not rely on isolated
keywords when the surrounding request changes their meaning.

Treat these intents as read-only unless the same current request explicitly
asks for a state-changing phase:

- return or switch to an issue, backlog item, discussion, report, or topic
- status, explanation, analysis, review, audit, comparison, recommendation,
  planning, or "what next"
- a pasted issue or incident report without an implementation request
- ambiguous requests that identify a subject but not an action

Clear verbs such as `fix`, `implement`, `update`, `add`, `remove`, or equivalent
target-language imperatives may authorize `modify` for the named scope. They do
not authorize `commit`, `publish`, or `live-external` unless those phases are
also explicit.

Clear intent to stage, commit, amend, merge, rebase, pull, switch, branch,
stash, reset, or otherwise mutate local Git state may authorize `commit` for
the named scope. Clear push, publish, pull-request/issue/review mutation,
release, or deployment intent is required for its matching phase. When the
subject, phase, or scope remains ambiguous, state the read-only result and ask
the smallest confirmation.

## Independent Boundaries

Before a state-changing action, verify all applicable controls:

1. Current user authorization includes the phase and current logical scope.
2. Operation allowed actions permit the affected surface.
3. Protected-change approval exists when risk policy requires it.
4. Tool, network, filesystem, credential, and assistant permissions permit the
   action.
5. Team, workspace-mode, extension, dependency, and delegation constraints do
   not narrow or prohibit it.

These controls can narrow one another. None can grant a missing permission from
another control.

## Commit And Publication Boundary

Before committing, restate the current scope and confirm that the newest user
request authorizes `commit`. Inspect the diff and avoid unrelated changes.

Before publication, confirm explicit current-scope `publish` authorization
immediately before mutating remote state. Name the repository, branch, ref,
pull request, release, package, or other destination when it is not already
unambiguous. A successful commit, passing validation, an approved plan, a team
claim, or a previous push request is not publication authorization.

Do not use a broad phrase such as `full-with-approval` as a substitute for
current publish intent. It is an allowed-action ceiling, not a grant.

## Delegation And Automation

Subagents, scripts, hooks, tools, extensions, MCP servers, CI helpers, and
assistant-native automation inherit the parent operation's current scope and
authorized phases. They may narrow the phase or run read-only checks, but they
must not commit, publish, deploy, broaden scope, or request credentials on the
parent's behalf unless the parent request already authorizes that phase and
all other gates pass.

The primary assistant remains responsible for checking the newest user
instruction before integrating delegated writes, committing, publishing, or
performing live actions.

## Evidence

Before edits and in final evidence, record `current_user_authorization` with:

- current logical scope or operation ID
- source request or message reference
- authorized phases
- phases deliberately not authorized
- whether prior authorization was invalidated and why
- latest confirmation used for commit, publish, or live action
- state-changing actions actually performed

This evidence is declarative unless the assistant surface exposes trustworthy
conversation provenance. Repository validators can verify that the policy and
evidence fields exist; they cannot prove that an assistant interpreted a chat
message correctly.

## Rejection Criteria

Reject or stop work that:

- treats a topic switch or backlog return as implementation authorization
- carries commit, push, publish, or live-action authorization into a new scope
- infers publish permission from commit permission or tool availability
- treats allowed actions, protected approval, assignment, mode selection,
  operation routing, or a passing validator as user authorization
- lets a subagent or automation broaden authorized phases
- omits current authorization from final evidence after a state-changing phase
