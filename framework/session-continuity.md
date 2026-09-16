---
alatyr_doc:
  id: framework.session-continuity
  type: framework-rule-owner
  owns_rules:
    - ALATYR-CONTINUITY-001
  depends_on:
    - ALATYR-AUTHORIZATION-001
    - ALATYR-CONTEXT-001
    - ALATYR-EVIDENCE-001
  applies_to:
    - all
---
# Session Continuity

This document defines the portable safeguard for context compaction, session
resume, assistant handoff, and comparable boundaries where conversational
state may be shortened, replaced, or lost.

The safeguard preserves task continuity without treating a generated summary
as authority. It complements provider-native compaction when that capability
is verified, and provides a provider-neutral fallback when it is unavailable
or unknown.

## Boundary Model

A continuity boundary exists when any of these events may change the context
available to the acting assistant:

- automatic or manual context compaction
- session, task, or process restart
- conversation fork or handoff
- assistant, client, provider, or model change
- primary/subagent convergence
- explicit context reset or recovery

The assistant should prepare a bounded continuity packet before a predictable
boundary. After any observed or suspected boundary, it must rehydrate before
the next state-changing action.

## Authority

A continuity packet and a compacted conversation are evidence, not sources of
truth. Current repository state, canonical project owners, the newest user
instruction, active approval records, and current tool or host constraints
remain authoritative in their own domains.

Compaction, resume, or handoff must not:

- create, broaden, or renew user authorization
- carry publish or live-external authorization across the boundary
- revive an expired, superseded, or out-of-scope approval
- replace current Git, validation, or canonical-owner evidence
- hide unresolved conflicts, failed checks, or residual risks

If current scope or authorization cannot be re-established, continuation is
inspect-only. The assistant may explain the recovery state and ask for the
smallest missing confirmation.

## Continuity Packet

The target adapter defines the machine-readable packet schema and storage
route. A packet should remain bounded and contain only the state needed to
resume safely:

- task and operation identity, objective, phase, and next safe action
- selected profiles, modes, areas, rule owners, and context digests
- current logical scope and recorded authorization evidence
- Git branch, revision, changed paths, and change-set digest when available
- selected approval references and content digests
- accepted decisions, unresolved questions, validation results, and risks
- boundary kind, assistant surface, and capability evidence state

Do not store raw conversation history, hidden reasoning, secrets, credentials,
or unnecessary source content. Prefer identifiers, hashes, and target-relative
paths over copied prose.

Creating a persistent packet is itself a repository or local-state mutation.
For inspect-only work, use a host-native or in-memory checkpoint when possible;
otherwise report that durable continuity is unavailable. A target may write an
ignored local packet only when the current request authorizes the applicable
local adapter/runtime mutation.

## Rehydration Gate

Before state-changing work resumes:

1. Load the compact bootstrap and selected continuity packet.
2. Verify packet shape and digest.
3. Compare repository, branch, revision, changed paths, and approval evidence
   with the current state.
4. Re-resolve only changed or stale canonical owners, rules, and validation
   evidence named by the packet.
5. Re-evaluate current-scope authorization from the newest user instruction.
6. Reclassify risk when scope, changed facts, or external effects differ.
7. Continue from the recorded next safe action only when every applicable
   boundary still passes.

No full framework or project reread is required merely because compaction
occurred. Expand context only for a concrete mismatch, stale digest, named
dependency, failed check, or unresolved authority boundary.

## Assistant Capability

Each selected assistant surface should record whether it exposes automatic or
manual compaction, boundary hooks or signals, summary inspection, and project
instruction reload behavior. Unknown capability remains `unknown`; it must not
be inferred from provider marketing or from another client using the same
model.

Provider-native compaction may optimize delivery, but the portable continuity
flow remains the fallback. Context caching is a separate capability and does
not prove compaction, context-window reduction, or safe rehydration.

## Completion Evidence

For a resumed state-changing task, final evidence should identify:

- the boundary and continuity packet used, or why no durable packet existed
- packet and repository verification result
- context selectively reloaded because of detected drift
- current user authorization re-established after the boundary
- invalidated approvals or decisions
- validation performed after resume
- unresolved continuity risk

## Rejection Criteria

Reject or stop a state-changing continuation that:

- relies only on a compacted summary or memory of earlier instructions
- restores authorization without checking the newest user instruction
- restores publish or live-external authority from a packet
- ignores branch, revision, changed-path, approval, or digest drift
- reloads the entire corpus without a named expansion reason
- claims a provider compaction capability without current target evidence
