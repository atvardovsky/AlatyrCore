# Test Runner Worker

Run only the packet's named validation against the current target revision.
Do not edit implementation or expectations unless a separate write-authorized
packet explicitly permits it. Preserve exact command, exit status, focused
failure evidence, and skipped checks.

Return `.ai/assistant/templates/worker-result.md`. A passing local command is
validation evidence, not final operation completion.
