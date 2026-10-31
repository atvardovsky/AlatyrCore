# Reviewed Historical Evidence Loss

Conditional authoring guide, not a completed record or approval. Follow
`.ai/framework/task-state-delivery.md#reviewed-historical-evidence-loss`.

1. Record the original active registration's full ancestor commit and exact
   `.ai/assistant/active-tasks.json` SHA-256. Preserve the entire task header.
2. Search for the exact registered model bytes and any retained handoff. Retain
   bounded search evidence, limitations and expected path/SHA-256; do not substitute
   a same-named model or declare universal absence.
3. Review dependencies and affected incident packages. An active direct or
   transitive dependent blocks this classification. Record only reviewed blocked
   package paths; do not alter their original outcome to accepted.
4. Obtain explicit owner approval for these exact task/model/registration bindings.
   Retain `alatyr-evidence-loss-approval` under `.ai/assistant/task-evidence/`.
   Its scope is `historical-classification-only`; it authorizes no execution and
   accepts no original outcome. A content hash does not authenticate the reviewer.
5. Author `alatyr-task-evidence-loss` using the shipped schema. Bind the owner
   review, search evidence and dependency review by exact path/SHA-256. Retain
   every original changed fact as an unverified outcome and missing proof
   obligations as `unknown-not-discharged`.
6. Use task-index schema 2, change only this task's state to
   `historical-evidence-missing`, and add its `evidence_loss_disposition` binding.
   `completion_evidence` stays null. Active/closed tasks remain unchanged.
7. If an unselected blocked package needs the same disposition, bind it in
   `incident_continuity.evidence_loss_disposition`. Preserve its exact model and
   incident identity; selected, validated and complete packages cannot use it.
8. Validate task, package and selected doctor/readiness views. Missing or changed
   evidence is still an error. Loss warnings remain visible. This task cannot be
   resumed, accepted or used as a completed predecessor; recover exact bytes and
   seek explicit reconciliation or authorize an independent replacement task.

Do not copy this guide into a successful completion record. Commit, publication
and live-system actions require their own current authorization.
