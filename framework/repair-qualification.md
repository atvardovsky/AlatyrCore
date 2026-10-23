# Incident Repair Qualification

Conditional details of `ALATYR-TDD-001`, delegated by the canonical
[test-first owner](test-first-development.md#incident-repair-review). Load only
for schema-2 adoption, authoring, validation, or a named evidence conflict.
This is not another policy, incident registry, runtime-observation module, or
authorization source. Targets retain their own commands and domain meanings.

Schema 2 keeps `diagnostic`, `qualified-repair`, and `acceptance` stages in the
same record. The target policy owns assertion IDs, command applicability,
fixture boundary, expected finite scalar, non-root JSON artifact pointer, and
optional control pointer. Observations select assertion/run IDs, never copy
expected or actual values. The validator reads the digest-bound JSON result
artifact, limited to 128 KiB, rejecting duplicate members, non-finite values,
missing/unresolved observations and coercive Boolean/number matches. Required
diagnostic observations include an actual control/experiment distinction.
Assertions address actual child scenario, branch, topology, ownership, resource
and prerequisite evidence where relevant; requested flags alone are not proof.
Captured same-task schema-2 assertions and measurement requirements cannot be
removed, rewritten or downgraded to schema 1 to obtain acceptance. Reassess
changed intent through target-owned policy/incident decisions, not a silent
mid-repair change of the expected result or performance threshold.

A faithful known-failing diagnostic may qualify repair before functional
acceptance is GREEN. Unknown fixture boundaries cannot qualify repair. Setup,
syntax, missing modules and unavailable suites are not causal RED. Before a
related production repair, review the selected hypothesis, qualified diagnostic
and original incident effect; otherwise continue bounded investigation. This
instruction does not physically prevent edits or grant execution permission.
Independent authorized work may continue around a named blocked dependency.
Qualification never clears failed acceptance or replaces diagnostic retry
evidence, valid RED, original-flow acceptance, or the frozen full matrix.

Optional schema-2 performance policies select metric pointer/unit, median
direction, minimum samples, maximum relative spread/regression and comparable
condition pointers. Artifacts contain `{unit, samples}` at the metric pointer;
samples are finite non-negative numbers, bounded to 256. Compare actual runtime
branch, workload/topology and instrumentation, not requested configuration.
Incomparable or noisy measurements cannot qualify a selected optimization.
Captured baseline run/policy/output bindings are measurement-only: historical
passes never become current acceptance or fixture qualification. Baselines
retain separate output paths and distinct completed windows preceding the
candidate; copying the candidate under a new record path is not a baseline.
No selected performance policy means
no new performance gate. These comparisons do not prove statistical confidence,
benchmark relevance, instrumentation truth, domain causality or production speed.
