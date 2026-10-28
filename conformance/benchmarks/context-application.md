# Context Application Comparison

Status: evaluation protocol, not executed assistant results.

Use the existing [benchmark workflow](README.md), `context-application-review`
class, paired `none`/`minimal`/`full` snapshots and independently reviewed run
reports. Preserve identical project sources, requests, authorized actions and
acceptance criteria. Hold reviewer answers outside the agent's supplied packet.
No additional runner, model call or provider capability is required by this
protocol. Source regressions exercise routing, not assistant comprehension.

## Scenarios And Review Oracles

1. Exact question: prepare two unresolved probes with different inputs. Ask for
   the non-first obligation explicitly. The answer must address that obligation,
   cite its inputs and owner, and not substitute the cheapest or first probe.
2. Exception: provide an accepted base constraint and an applicable, authorized
   exception with a narrow scope. Review both an in-scope and an out-of-scope
   change. The answer must apply the exception only inside its accepted scope;
   citing both sources without using the distinction does not pass.
3. Accepted versus observed: introduce implementation that contradicts recorded
   accepted architecture. The answer must describe the discrepancy, identify the
   decision owner and avoid promoting implementation into accepted intent.
4. Freshness: change an owner after a question or guidance route was prepared.
   Review whether the agent invalidates dependent claims and reopens the needed
   investigation. A matching old digest or a no-match in an unrelated shard
   must not establish that the current constraint is absent.
5. Ripple: change a domain fact whose accepted relationships reach a contract,
   code and test. Check the actual companion changes or an explicit blocker;
   mentioning file names alone is not sufficient. Include an unrelated source
   as a distractor without requiring extra exploration of it.
6. Probe selection and retry: compare one decision-relevant falsifier with many
   redundant predictions. Ask which observation would change the conclusion.
   Include an inconclusive prior result and a justified unchanged retry of a
   variable phenomenon. Require a reason for the next experiment, not a rule
   that repetition is always wrong. Required duties remain visible.

## Measurement And Acceptance

Record each oracle as a separate `acceptance_criteria_results` entry in the
existing run report, with evidence references and independent review. A false
completion, unauthorized action or lost mandatory constraint fails its own
criterion; do not average it away. A truthful blocked outcome can be correct.

Compare missed obligations, rework, unnecessary expansions, human interventions
and end-to-end duration, including metadata preparation and worker review.
Report retrieval I/O, delivered words, accumulated session context, all worker
tokens and billing separately. Unknown telemetry remains unknown. Repeat paired
runs and inspect uncertainty; the suite's minimum repetitions are a starting
point, not proof of statistical equivalence or universal non-degradation.

Tune optional delivery only after these comparisons. Retain a baseline and
rollback path. Automatic code pruning, additional orchestration and default
enablement require their own measured benefit; smaller output is not enough.
