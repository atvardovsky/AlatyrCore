# Validation Lanes

Use this source-tool feature only for expensive registered commands. It extends
the [existing delivery gate](assistant-lifecycle-hooks.md#request-bound-review),
not product test selection, review approval, or required coverage. Unconfigured
commands do not read a lane policy, open a journal, or launch a discovery probe.

## Adopt an Objective

In both the canonical testing policy and its projection, add
`alatyr:validation-lane:<objective-id>` to the registered command's execution
prerequisites. Reuse the same owner-assigned objective for aliases, wrapped
invocations and retries of the same required evidence. Do not allocate a new ID
to recover budget. Keep the configured read-only metadata commands separate
from fixture provisioning and tests. The ordinary registered launch still
requires current authority, exact argv and an input-bound pre-run record.

Add `.ai/project/testing/validation-lanes.json` to the reviewed target context.
The selected policy and any retry artifacts must be in the retained session
baseline alongside existing execution inputs. Example shape:

```json
{
  "schema_version": 1,
  "objectives": {
    "review-journey": {
      "max_attempts": 3,
      "max_seconds": 180,
      "commands": {
        "review-browser": {
          "probe": "list-review-cases",
          "expected_cases": ["review:open", "review:save"],
          "material_inputs": {"source": "evidence/review-source.json"},
          "artifact": null
        }
      }
    }
  }
}
```

Material input roles must bind the pre-run record's actual input bytes. Use
stable roles for project-owned source, cases, lockfile, toolchain, environment
and fixtures where relevant. Keep wrapper names, checkout paths and request
receipts out of this set. Use verified fingerprint records for large input
closures, with the project probe checking the underlying current material.
Exact reuse is stricter than objective identity and also binds the worktree,
argv, policy, selected input hashes and process environment.

## Admission and Results

The registered read-only probe runs first with no setup effects declared. It
returns `{"schema_version":1,"cases":[...]}`; the exact case set must match
before the runner starts. Use an empty set for a build or other non-test check.
Each probe can use at most 30 seconds of the attempt window. For adopted lanes,
the declared `estimated_seconds` is a hard attempt cap. Collect full native
errors outside the compact gate output.

One cooperating expensive launch holds the Git-common lane at a time. A
bounded journal under the Git common directory's `alatyr-validation-lanes/`
tracks each objective across linked worktrees and sessions. It charges
preflight failures and reserves time before launching. A policy edit cannot
increase a retained budget. Exhaustion calls for owner reassessment, not a
new objective. After a crash, do not clear a retained reservation unless the
owner verifies the owned child and its resources are stopped.

To repeat, set `validation.lane_retry` to a reviewed target-relative JSON file
with `previous_attempt` (the latest lane attempt ID), `reason`, `condition`,
`condition_input` (an exact `{ "path": "...", "sha256": "..." }` binding),
and Boolean `cleanup_confirmed`. The existing required diagnosis proof
must pass and link both the retry file and its concrete changed-condition
input. The second failure also needs distinct independent review. Use
`changed-input` for different material, `execution-repair` for a repaired
failure, or `distinct-required-evidence` for a genuinely different proof.
Uncertain execution or failed cleanup requires execution repair and a
reviewed cleanup confirmation. Request-level retry policies still apply.

For automated tests, the runner writes its bounded case map to
`ALATYR_VALIDATION_CASE_RESULT` after execution and cleanup:

```json
{"schema_version":1,"cases":{"review:open":"passed","review:save":"failed"},"cleanup":"passed"}
```

Account for every selected ID as `passed`, `failed`, or `not-run`; cleanup
is `passed`, `failed`, or `not-applicable`. Retained case observations can
inform a separately authorized focused selection when still applicable.
A cleanup failure does not relabel failed or passed assertions, and passed
assertions do not waive cleanup, current proof, coverage or acceptance.

## Artifact Reuse

For a registered non-test command with explicit harness inputs, configure
`artifact` as `{"receipt":"path/to/receipt.json","verifier":"registered-metadata-check"}`.
The build must produce a new receipt; the target-owned verifier checks the
actual artifact, compatibility, and provenance, and reports an empty case
set. An identical current receipt and exact binding can return
`artifact-available` after verification instead of running the build.
Move or reconcile a stale receipt before requesting a rebuild. This reports
the build artifact only; no test was run or accepted.

This is local cooperation, not host-wide process interception, resource
reservation across independent clones, or a sandbox for target commands.
Process timeouts cover the direct child; the target still owns descendant
lifecycle, fixtures, and cleanup. A configured verifier is not proof until
its actual output passes for the current artifact.
