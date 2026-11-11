# Assistant Lifecycle Checkpoints

Closed-task evidence may be rebound with `lifecycle-checkpoint ... bind
--completion-only` after capturing the actual closure and archived projection.
It cannot reopen execution. The terminal consistency status reuses canonical
model/closure checks and is not full adapter acceptance or runtime readiness.
See the [installed flow](../templates/target/.ai/assistant/flows/lifecycle-checkpoints.flow.md).

This delivers the existing
[task-state](../framework/task-state-delivery.md),
[authorization](../framework/action-authorization.md) and
[continuity](../framework/session-continuity.md) rules, not a new task registry,
executor, security boundary or source of approval.

## Adoption

New installations include an enabled procedural/observe policy by default,
with zero reminders and unverified native evidence. Include project-local native
setup in the installation plan for an explicitly supported selected client route;
apply it only inside approved installation scope. A policy alone installs no
callbacks. Without approved/supported native setup, use procedural checks.
Scaffolding is not adoption, trust or proof that a client loaded callbacks.

Updates preserve all existing policy values, native definitions, trust decisions
and explicit opt-outs. An absent policy during update stays absent; applying
fresh-install defaults needs an explicit adoption decision. Invalid or expired
existing policy/evidence is reported, not replaced or renewed silently. Never
install plugins, alter global settings or bypass native trust prompts.

Start with `mode: observe`, `native_evidence.state: unverified` and zero automatic
reminders. The strict policy input is
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

## Setup Plan

Before projecting a new policy, run the read-only planner. Use `python` on
Windows and select the interpreter actually available in the target:

```sh
python3 tools/alatyr.py lifecycle-checkpoint --target /path/to/target setup-plan --installation-kind new
python3 tools/alatyr.py lifecycle-checkpoint --target /path/to/target --provider codex setup-plan --installation-kind new --native-setup-approved --client-version CLIENT_VERSION --config-path .client/hooks.json --interpreter python3
python3 tools/alatyr.py lifecycle-checkpoint --target /path/to/target setup-plan --installation-kind update
```

`CLIENT_VERSION` and `.client/hooks.json` are illustrative, not known target
facts. Resolve the exact client/runtime route and its project-local config path
from target evidence. The approval flag records the caller's assertion that
this setup is in the current approved plan; it is not authenticated approval.
Do not infer native capability from a model vendor or generic assistant name.

The result preserves existing policies byte-for-byte, proposes observe-only
native event argv only for explicitly approved setup, and lists events still
requiring procedural delivery. Unknown variants select `--provider procedural`.
It does not write configuration, execute argv or mark callbacks installed,
trusted, loaded, exercised or intercepted. Merge approved native definitions
without replacing unrelated entries; use selective mutating-tool matchers.
Verify delegate location, Git-root working directory and native host error
semantics. No universal client-config renderer or installer is implied.

## Session Protocol

Delivery is task-bound: project adoption does not require registered models for
small settled work by default. Only an explicitly reviewed binding activates task checks.
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
- Legacy pre-action compares selected context only. An explicitly adopted
  request guard also compares the request/action contract described below.
  The primary still checks actual human authorization and protected approval.
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

## Request-Bound Review

Every assistant follows [request reconciliation](../framework/action-authorization.md#request-reconciliation).
Small tasks keep it inline. Material tasks may place the
[brief template](../templates/target/.ai/assistant/templates/request-brief.json)
in existing task evidence or ignored runtime storage. Keep the source request
reference distinct from its lifecycle nonce. Copy no secrets or full transcript.
Bind the exact model objective, every requested outcome and its existing required
proof IDs; each outcome names a plausible substitute that must fail. Constraints,
exclusions and requested order remain human/agent review text, not parsed rules.

The parser caps briefs at 16 KiB, 1200 words and 32 rows per collection. Paths
are normalized, literal and target-relative; `{path, recursive}` admits that
exact path and, only when recursive is true, its descendants. No glob or prefix
approximation is used. Effect identities are exact reviewed labels, such as a
selected publication destination; they are not executable commands or approval.

The read-only review works without hook adoption and consumes action JSON on
stdin. Replace the illustrative IDs and paths with current bindings:

```sh
python3 tools/alatyr.py lifecycle-checkpoint --target /path/to/target review --request-brief .ai/.runtime/current-request.json < /private/path/action.json
```

```json
{"request_id":"REQUEST","task_id":"TASK","kind":"work","phase":"modify","outcome_ids":["OUTCOME"],"paths":["src/example.py"],"effects":[]}
```

`kind` is `work`, `answer` or `complete`. Answers use `inspect` and can report
partial findings; `complete` also runs canonical selected-model completion
validation and requires all mapped outcome proofs to be passed, not waived.
`request-consistent` verifies declared relationships, not task acceptance or
permission. `evidence_readiness` separately exposes current/stale/unadopted
bindings and bounded diagnostics. Affected state changes require reconciliation;
read-only recovery and proven-independent branches remain available. Missing or
budget-incomplete verification cannot establish independence. The existing
dependency map must establish an independent branch; absence is unknown. The
artifact reader/byte limits apply; review does not rerun validation or probes.

`request_progress` covers every captured outcome, with remaining IDs and declared
ready obligations. A partial answer at a completion callback returns `unfinished`
or `handoff-review`, retaining existing finite reminder/interrupt boundaries.
Publishing a supporting scope does not complete the parent request. Keep the full
inventory when decomposing; challenge necessity of supporting dependencies.
Checks cannot infer omitted outcomes, semantic relevance or real user intent;
source-first review and exercised native coverage remain necessary.

Schema 2 adds nullable `delivery_control`; schema 1 is unchanged. For uncertain
multipart or costly repeated work, the conditional
[bounded delivery contract](../framework/test-execution-selection.md#bounded-delivery-review)
defines pilot proofs, a retained bounded attempt history and pre-run budget/failure
review. Select it only when needed. The same `review` entry point and installed
delegate check an action's optional `validation` object. Bind its history alongside
the brief; changed history requires reconciliation before another bound action.
Tests are not executed or authorized by that check. Report undeclared-run,
duration-estimation and native shell-interception limitations explicitly.
### Delivery Efficiency

For adopted [delivery efficiency](../framework/test-delivery-efficiency.md),
the same review reads schema-2 history, its preceding snapshot, progress evidence
and run receipts. Retain all returned `delivery_inputs` before binding. Output
`delivery_review` separates elapsed/stalled/stale declarations from acceptance;
inspection can reassess overdue work without authorizing mutation. Old histories
and null controls stay unchanged; no automatic runner, cache or timeout is added.

### Focus And Request Guards

Schema-3 `focus_control` independently adopts
[request-bound work](../framework/task-state-delivery.md#request-bound-work).
Use the same `review` at dispatch/convergence, retaining original `brief_sha256`
and work `obligation_ids`. Current hashes cannot prove source-first reconciliation.
Legacy/null paths remain unchanged; delivery controls and TDD are independent.

### Terminal Prerequisites

For an owner-approved staged release or other dependent external action, use
the optional [terminal prerequisite contract](../framework/task-state-delivery.md#terminal-action-prerequisites)
in the same schema-3 brief. The ordinary `review`/bound-checkpoint routes consume
it; no new executor or CLI is installed. One illustrative rule is:

```json
{
  "schema_version": 1,
  "rules": [{
    "id": "previous-stage-ready",
    "phase": "publish",
    "effects": ["release:next-stage"],
    "proof_id": "previous-stage-verification",
    "command_id": "verify-previous-stage",
    "receipt": {"path": "evidence/run.json", "sha256": "<actual receipt SHA-256>"},
    "candidate": {"path": "evidence/candidate.json", "sha256": "<actual candidate SHA-256>"},
    "environment": {"path": "evidence/environment.json", "sha256": "<actual environment SHA-256>"},
    "max_age_seconds": 900
  }]
}
```

Replace illustrative paths/digests with actual bounded artifacts. The proof must
cite the receipt; the receipt's exact input digests include candidate/environment
bindings and its result artifact must remain intact. Keep the effective target
configuration distinct from the candidate. Pass the original brief digest in
the action. Retain these artifacts in the baseline before a bound mutation.
After a retry, append a new run receipt and rebind current evidence without
rewriting failed history or changing the prerequisite policy. Request replacement
revokes old actions; a new hash does not retroactively retag an old dispatch.

A receipt is a checked record, not proof of authentic command execution. The
project's actual publishing operator or verified native boundary must consume
the gate before mutation. Report disabled/procedural/native evidence separately;
never claim that this helper intercepts arbitrary shell commands.

For request guards, preserve disabled state unless the owner explicitly enables
the guard. Set `request_guard.required` to true only after review, retain the
brief in the selected context baseline, and add `--request-brief <path>` to
`bind`. Missing, stale or dropped briefs fail review. Request/resume invalidation
requires explicit reconciliation with the newest request, not silent renewal.
`required: true` is a stricter opt-in lane: selected mutation callbacks block
while no model-backed brief is bound. Scope native hook matchers accordingly;
ordinary small requests keep inline/procedural review unless the owner explicitly
chooses this additional registration cost. Never enable it merely during upgrade.

Native pre-action review additionally requires `alatyr_action` containing the
same action shape. Configure `request_guard.file_tools` only for verified
single-file mutators, for example `[{"tool_name":"Write","path_field":"file_path"}]`.
This exact shape reads `tool_name` and `tool_input.file_path` from the real event;
the declared phase/path must agree with that input. Other payload dialects need
a separately reviewed adapter. Path fields are `path`, `file_path` or `filename`;
other admitted input keys are `content`, `old_string`, `new_string`, `replace_all`.
Extra command/rename/multi-file fields are rejected. Shell/interpreter, multi-file patch and unknown
tools cannot gain coverage by supplying a harmless declaration. The mapping is
an operator's tool-semantics assertion; wire tests do not authenticate it.

Native completion supplies an explicit `answer` or `complete` action. Missing
or invalid input is a diagnostic, not an automatic retry or permission to claim
success. Request failures do not consume completion reminders or restart work.
Only an exercised checkpoint configuration can deny selected native mutations;
observe mode stays non-blocking. Retain procedural checks where callbacks cannot
observe the actual request, action or completion claim.

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

Recognized non-event commands (`review`, `bind`, `status`, `checkpoint`, `setup-plan`) retain
ordinary parser errors; an invalid `--native-output` flag cannot convert them
into successful neutral callback transport.

Measure callback I/O, wall time, context delivered and billing separately.
Deterministic tests establish protocol consistency, not improved engineering
outcomes, domain correctness or general token savings. Native smoke verification
and representative team trials remain required before claiming interception or
effectiveness.
