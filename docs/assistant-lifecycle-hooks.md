# Optional Assistant Lifecycle Checkpoints

This is an opt-in delivery mechanism for the existing
[task-state](../framework/task-state-delivery.md),
[authorization](../framework/action-authorization.md) and
[continuity](../framework/session-continuity.md) rules, not a new task registry,
executor, security boundary or source of approval.

## Adoption

Keep `.ai/assistant/policies/lifecycle-hooks.json` absent or disabled unless the
target owner approves adoption. Installation and upgrade must preserve existing
hook definitions and trust decisions. Neither operation enables hooks, installs
plugins, changes global configuration or trusts a new definition automatically.

Start with `mode: observe`, `native_evidence.state: unverified` and zero automatic
reminders. The template is deliberately disabled. The strict policy input is
limited to 64 KiB; CLI and target validation share its strict loader. An optional configuration
records one exact client route, binding lifetime and reminder ceiling. Observed
native evidence needs a concrete client version/source, aware observation/expiry
timestamps and a validity window no longer than 30 days. This is an operator
record, not authenticated proof of interception. Recheck after client or hook
changes; no other client inherits the observation.

Before `mode: checkpoint`, exercise harmless fixtures in the exact client:
request invalidation, explicit denied mutation, stale selected input, completion
reminder, interruption and callback error/timeout. Test which events actually
fire and how failures are handled. Do not bypass native trust prompts. If any
required event is missing or behavior is uncertain, retain procedural checks.

## Session Protocol

Delivery is task-bound: project adoption does not require registered models for
small settled work. Only an explicitly reviewed binding activates task checks.
New requests deactivate the prior task binding; ordinary lightweight context and
authorization rules still apply. Resume retains pending task review and cannot
clear an interruption or reopen an ended scope without a new request.

The source command is `python3 tools/alatyr.py lifecycle-checkpoint`. Installed
projects use their existing portable delegate and source locator. Use `python`
on Windows. The following commands are illustrative: replace `SESSION`, `REQUEST`
and `TASK` with the selected session/request/task identities.

```sh
python3 .ai/assistant/tools/alatyr_delegate.py lifecycle-checkpoint --target . --provider codex status --session-id SESSION
python3 .ai/assistant/tools/alatyr_delegate.py lifecycle-checkpoint --target . --provider codex bind --session-id SESSION --request-id REQUEST --baseline .ai/.runtime/continuity/current-context.json --task-id TASK
```

`bind` records that the primary reviewed the newest intent and existing task;
it grants no action phase. Capture the baseline with `session-context` after
that review, including the lifecycle policy, canonical active-task index,
selected model/projection and all still-applicable loaded context. Policy edits
require a fresh review and baseline; binding cannot acknowledge them silently.
A baseline candidate is not authorization.
The shared comparison includes knowledge expiry, installation state and input
race checks. A replaced or stale baseline cannot silently refresh a binding.

Native adapters read bounded JSON from stdin. The host supplies session identity;
configure an exact event, for example:

```sh
python3 .ai/assistant/tools/alatyr_delegate.py lifecycle-checkpoint --target . --provider codex event --event Stop --native-output
```

For a missing native event, `checkpoint --event interrupt` (or another normalized
event name) accepts explicit `{"session_id":"SESSION"}` JSON on stdin through
the same selected-provider route. This is procedural delivery, not evidence that
the client intercepted an event. It does not execute or authorize work.

Resolve the target and delegate from the Git root when the host starts in a
subdirectory. Review a platform-appropriate interpreter/launcher; never copy a
workstation's absolute path. Use selective mutating-tool matchers for pre-action
and post-change hooks. Do not intercept all read tools, helper review commands
or arbitrary shell commands as if their action phase could be inferred safely.

- A request or session start invalidates the old binding. Synthetic follow-ups
  also require review; they never grant authority or automatically rebind.
- Pre-action compares selected context only. The primary still checks the
  current action phase, protected approval and scope before any mutation.
- Post-change/compaction requires selective owner, documentation and evidence
  reconciliation. It cannot undo actions or certify documentation completeness.
- Completion reads the existing selected task view, not the full validator.
  Ready obligations may receive a bounded reminder; closed tasks and unconfigured
  dependencies do not propose active work. No disposition establishes acceptance.
- Interrupted/ended sessions do not auto-continue. An independent revocation
  marker prevents a slow completion reader from restoring an interrupted binding.
  A callback cannot cancel a tool already executing or guarantee atomic dispatch.

State is one bounded ignored record plus lock/revocation marker per session under
`.ai/.runtime/lifecycle-hooks/`. It contains no transcript, commands, domain task
status or approvals. Normal checkpoints do not append history or scan the source
tree. Remove obsolete session artifacts only through an authorized local cleanup.

## Provider Routes

The implementation includes exact event/output adapters, not pre-enabled native
configurations. Wire tests do not prove that a running host loaded a hook.

- [Codex hooks](https://learn.chatgpt.com/docs/hooks): local `UserPromptSubmit`,
  `PreToolUse`, `PostToolUse`, compaction, `Stop` and `Interrupt` routes. Review
  exact hook trust. Do not extrapolate local command hooks to cloud orchestration.
- [Claude Code hooks](https://code.claude.com/docs/en/hooks): corresponding request,
  tool, compaction and Stop routes. No equivalent Interrupt route is asserted;
  explicit interruption delivery or procedural fallback remains necessary.
- [Gemini CLI hooks](https://geminicli.com/docs/hooks/reference/): `BeforeAgent`,
  `BeforeTool`, `AfterTool`, `PreCompress` and `AfterAgent`. A denied AfterAgent
  response creates a retry, not a new human instruction.
- [Cursor hooks](https://cursor.com/docs/hooks): prompt, selected tool/edit,
  compaction and stop routes. Aborted/error stops revoke the binding. Session
  start delivery must not be assumed blocking.
- [Copilot hooks](https://docs.github.com/en/copilot/reference/hooks-reference):
  the camelCase CLI route is implemented. Extension-compatible or cloud routes
  require separate verification; they are not silently aliased to this route.
- Other supported assistants, OpenCode plugin versions and unverified client
  variants use `--provider procedural` with normalized event names until a
  separately reviewed adapter is available. No plugin is installed or executed.

Host errors/timeouts may fail open, and other matching hooks may run concurrently.
Keep native permissions, procedural authorization and canonical acceptance gates.
No command here runs project tests, edits code, commits, pushes or restarts work.

## Performance And Evidence

Disabled delivery reads only the optional bounded policy; it does not read tasks
or context. Expiry is checked before selected-content reads and again afterward.
Enabled delivery performs one canonical context comparison after task evaluation
and durable state writes, then checks policy and binding validity after the last
input read. It reuses the session-context and selected-task resolvers,
not a recursive public-source hash or full acceptance run per tool. Binding
lifetime is 1..3600 seconds. The target chooses its reminder budget within the
portable ceiling of eight per reported session; request, resume and rebind do
not reset it. Unbound completion never issues a continuation. Configure the
native host's own finite retry limit too.

Native-output errors are structured diagnostics on stderr, never completion
retry requests. Completion/non-action failures return empty wire JSON and exit
zero because several hosts interpret exit two as another turn. A valid observed
checkpoint policy can deny a selected tool explicitly on error; observe-only or
unknown policy never becomes blocking. Ordinary non-native CLI failures remain
nonzero. An invalid native-output invocation has no trustworthy
action classification and returns a neutral diagnostic, not an interception
claim; verify callback arguments before activation. None of these transport
statuses establishes acceptance.

Measure callback I/O, wall time, context delivered and billing separately.
Deterministic tests establish protocol consistency, not improved engineering
outcomes, domain correctness or general token savings. Native smoke verification
and representative team trials remain required before claiming interception or
effectiveness.
