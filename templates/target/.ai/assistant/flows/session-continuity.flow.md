# Session Continuity Flow

Use this flow before a predictable context boundary and after an observed or
suspected compaction, resume, fork, handoff, client/model change, context
reset, or subagent convergence.

Canonical rule: `ALATYR-CONTINUITY-001` in
`.ai/framework/session-continuity.md`.
Compact semantic reference: `alatyr:session-continuity@1`.

## Prepare

1. Keep the current task scope and action authorization separate.
2. Select the current operation, profiles, overlays, project areas, rule IDs,
   changed paths, approvals, decisions, checks, risks, and next safe action.
3. Increment `packet_sequence` for the same task and bind
   `previous_packet_sha256`; sequence 1 uses `none`.
4. Record current Git evidence with the canonical change-set hash when Git is
   available.
5. Bind any referenced capability record and context packet by target-relative
   path and file-content SHA-256.
6. Record the primary analysis strategy, problem-model path and digest, and the
   active-projection path, digest, source-model digest, and measured size.
   Keep open proof obligations, completed reviews, and invalidated assumptions
   in the bounded projection instead of copying full history into the packet.
7. Prefer identifiers, target-relative paths, and digests. Do not copy raw
   chat, hidden reasoning, secrets, or unnecessary source content.
8. During inspect-only work, use a host-native or in-memory checkpoint. Write
   `.ai/.runtime/continuity/<task-id>.json` only when the current request
   authorizes that local adapter/runtime mutation.
9. Compute `integrity.packet_sha256` over canonical JSON with the complete
   `integrity` object omitted.

## Rehydrate

1. Enter inspect-only recovery mode.
2. Load the compact bootstrap, continuity policy, packet, and this flow.
3. Validate packet structure and digest.
4. Compare its branch, revisions, changed paths, change-set digest, approval
   hashes, and referenced rule IDs with current evidence.
5. Load only owners or evidence whose identity changed or cannot be verified.
6. Verify the active projection against both its content digest and bound
   problem-model digest. Load the projection for routine recovery; load the
   full model only when the projection is stale, invalid, or insufficient for
   a named conflict. Reopen affected obligations when strategy, assumptions,
   or evidence changed.
7. Re-evaluate current logical scope and every action phase from the newest
   user instruction. Never restore publish or live-external authority from the
   packet.
8. Reclassify risk and approval needs if facts, scope, or effects changed.
9. Run the smallest focused validation that proves the resumed next action.
10. Continue only after `.ai/assistant/gates/session-continuity.md` passes.

## Failure Behavior

- Packet missing: reconstruct from durable current evidence and remain
  inspect-only until authorization is re-established.
- Packet invalid or stale: do not use it to justify state-changing work; load
  only the mismatched owners and refresh the packet when authorized.
- Capability unknown: use this provider-neutral flow without claiming native
  compaction, hooks, instruction reload, or summary inspection.
- Repository evidence unavailable: report the limitation and do not claim
  branch, revision, or change-set continuity.

Do not reload the full framework or project corpus solely because a boundary
occurred.
