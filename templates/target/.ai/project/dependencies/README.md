# Project Dependency Knowledge

This directory contains the target-owned projection of passive dependency
knowledge for `{PROJECT_NAME}`. It is not a package manager and does not make a
nested dependency adapter active.

Canonical framework procedure:
`.ai/framework/dependency-knowledge.md`.

Target-owned surfaces:

- `policy.json`: selected ecosystems, discovery, trust, limits, retention,
  review, and routing policy
- `catalog.json`: compact package and exported-fact routing state
- `knowledge-lock.json`: exact package instance, graph, export, and digest
  evidence derived from target package-manager locks
- `deviations.json`: project-owned patches, restrictions, wrappers,
  applicability decisions, and conflict resolution
- `snapshots/`: optional normalized accepted snapshots allowed by policy

Native package-manager manifests and lockfiles own dependency versions and
resolution. Dependency exports own their upstream claims. Project sources own
local usage decisions. These derived files must not silently replace those
owners.

Do not edit installed dependency files during synchronization. Do not load raw
dependency Markdown as assistant instructions. Do not recursively discover
nested `.ai` adapters.

## Normalized Record Contract

Use one catalog package record per resolved graph instance. Multiple installed
versions of one package therefore have different `instance_id` values.

```json
{
  "instance_id": "ecosystem:name@version#graph-id",
  "ecosystem": "ecosystem",
  "name": "canonical/package-name",
  "version": "resolved-version",
  "export_status": "available",
  "trust": "reviewed",
  "freshness": "current",
  "exports": [
    {
      "id": "namespace:public-contract",
      "type": "public-contract",
      "summary": "Bounded public fact summary",
      "content_digest": "sha256-hex",
      "authority": "upstream-canonical",
      "stability": "stable",
      "applicability": {
        "state": "active",
        "conditions": []
      },
      "evidence": ["package-relative/evidence"]
    }
  ]
}
```

`export_status` is `available`, `unsupported`, `blocked`, or `missing`.
`trust` is `unreviewed`, `reviewed`, or `blocked`. `freshness` is `current`,
`stale`, `missing`, or `modified`. Keep these axes independent.

Use one knowledge-lock instance with the same `instance_id`:

```json
{
  "instance_id": "ecosystem:name@version#graph-id",
  "ecosystem": "ecosystem",
  "name": "canonical/package-name",
  "version": "resolved-version",
  "source": "resolved-distribution-or-repository",
  "integrity": "package-manager-integrity-or-unavailable: reason",
  "revision": "immutable-revision-or-unavailable: reason",
  "modifications": ["patch"],
  "manifest": {
    "path": "package-relative/alatyr-dependency.json",
    "content_digest": "sha256-hex"
  },
  "exports": [
    {
      "id": "namespace:public-contract",
      "path": "exports/contract.json",
      "content_digest": "sha256-hex"
    }
  ],
  "graph": {
    "dependency_set": "runtime",
    "direct": true,
    "public_instance_ids": []
  }
}
```

`modifications` may contain `replacement`, `fork`, `alias`, `patch`, `path`,
`workspace`, or `modified-tree`. An unmodified immutable artifact uses an
empty list. `manifest` may be `null` only when no export manifest was present
and the instance has no exported records, for example when `export_status` is
`unsupported`.

Use target deviations only for target-owned facts:

```json
{
  "id": "target:dependency-deviation-id",
  "instance_id": "ecosystem:name@version#graph-id",
  "export_ids": ["namespace:public-contract"],
  "type": "restriction",
  "state": "active",
  "owner": "target decision owner",
  "source": "target-relative canonical source",
  "effect": "Bounded description of the target-specific difference",
  "reviewed_at": "ISO-8601 timestamp"
}
```

Deviation `type` is `restriction`, `wrapper`, `patch`, `configuration`,
`applicability`, or `conflict`. Deviation `state` is `active`, `inactive`, or
`superseded`. An empty `export_ids` list applies to that exact package
instance, not to all versions or packages with the same name.
