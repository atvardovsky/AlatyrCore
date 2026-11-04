# Source Change Management

Source-only guidance; load it for cross-module maintenance, not routine bootstrap.
The [release process](../release-process.md), [check manifest](../../tools/check_manifest.json)
and [architecture guide](../source-architecture.md) retain canonical ownership.

## Plan One Coherent Change

Use `python3 tools/alatyr.py plan-work --impact --compact` to join existing
capability, contract and check declarations. Review groups list candidate owners
and companions once; unmapped paths require explicit reasoning. Candidates are
not mandatory edits, a complete dependency proof, approval or acceptance.
Generated projections are distinguished from authored inputs. Review the full
projection closure until a narrower generator dependency is proven safe.

Prefer one responsibility per increment with public-path tests. Extract a helper
only when it isolates a real responsibility or removes repeated work. Avoid
line-only fragmentation, parallel registries and new permanent receipts.

## Review Contracts, Not Only Shapes

For each affected contract, record its canonical owner and test mapping in the
change/migration evidence: valid public dispatch; malformed and below/at/above
boundaries; disabled/minimal installations; freshness/concurrency; cross-contract
parity. Mark inapplicable dimensions with a concrete reason. A helper-only pass
does not prove integration, and matching parsers do not prove semantic acceptance.

Validator-only changes still need an explicit acceptance/compatibility assessment.
Advance the adapter version when previously accepted evidence becomes invalid,
even if JSON shape is unchanged. Source-only scheduling or presentation does not
justify a path-only version bump. Use the existing release report, not a second
approval or migration registry.

## Keep Operational Facts Derived

`prepare-worker-context --source-worker-bootstrap` derives a compact inspect-only
view from the selected source packet and policy. Supply every actual host-visible
bootstrap artifact too. The helper cannot remove host instructions, dispatch or
prove provenance. Hash-bound limits, primary responsibilities and cumulative
budgets remain canonical; omission retains the existing path.

The manifest owns deadlines, inputs and routing. `derive_trigger_paths: true`
derives triggers from declared inputs plus explicit extras; dependency-trigger
mode remains separate. Compatibility artifacts must be covered by their check's
inputs and routes. Do not repeat mutable values in prose.

`check_tool_complexity.py` reuses the canonical import graph. Foundation modules
cannot back-import consumers; new static cycles fail. Existing exact member/edge
exceptions carry the allowlist's owner and review deadline. Removal is allowed,
growth is not. Static cycles include deferred/type-only imports and are not
proof of runtime failure. Entry-point checks validate signatures/annotations, not
full type correctness. Branch counts are review signals, not a quality score.

Measure equivalent baseline/candidate work: routing and diagnostics, mandatory
context, selected tests, I/O, latency and delivered words/characters separately.
Do not claim billing or reasoning improvements from smaller files alone. Preserve
full acceptance and private Test project regression coverage after focused checks.
