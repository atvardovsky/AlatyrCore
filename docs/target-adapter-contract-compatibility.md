# Target Adapter Contract Compatibility

This generated source-maintainer reference projects the canonical
compatibility data in
`tools/target_adapter_validation/contract-compatibility.json`.
It does not replace portable framework rules or target-owned project facts.

## debug-mode

Manifest key: `debug_mode.contract_version`.
Current contract version: `5`.

Artifact: `index`
Current version: `5`.
Supported versions: `2`, `3`, `4`, `5`.
Migration-limited versions: `2`, `3`, `4`.

Artifact: `record`
Current version: `5`.
Supported versions: `1`, `2`, `3`, `4`, `5`.
Migration-limited versions: `1`, `2`, `3`, `4`.

## engineering-evidence

Manifest key: `engineering_evidence.contract_version`.
Current contract version: `3`.

Artifact: `index`
Current version: `4`.
Supported versions: `2`, `3`, `4`.
Migration-limited versions: `2`.

Artifact: `record`
Current version: `3`.
Supported versions: `1`, `2`, `3`.
Migration-limited versions: `1`, `2`.

## project-knowledge

Manifest key: `project_knowledge.contract_version`.
Current contract version: `3`.

Artifact: `index`
Current version: `3`.
Supported versions: `1`, `2`, `3`.
Migration-limited versions: `1`, `2`.

Artifact: `promotion`
Current version: `2`.
Supported versions: `1`, `2`.
Migration-limited versions: `1`.

Artifact: `route-shard`
Current version: `2`.
Supported versions: `1`, `2`.
Migration-limited versions: `1`.

Regenerate this reference with:

```sh
python3 tools/render_target_contract_compatibility.py
```
