"""Load the canonical source-tooling contract compatibility matrix."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "target-adapter-contract-compatibility.json"
)


def load_contract_compatibility() -> dict[str, Any]:
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != 1
        or data.get("catalog_kind") != "target-adapter-contract-compatibility"
        or not isinstance(data.get("contracts"), dict)
    ):
        raise ValueError(f"invalid target adapter compatibility catalog: {CATALOG_PATH}")
    return data


CONTRACT_COMPATIBILITY = load_contract_compatibility()["contracts"]


def contract_compatibility(contract_id: str) -> dict[str, Any]:
    contract = CONTRACT_COMPATIBILITY.get(contract_id)
    if not isinstance(contract, dict):
        raise ValueError(f"unknown target adapter contract: {contract_id}")
    return contract


def artifact_compatibility(contract_id: str, artifact_id: str) -> dict[str, Any]:
    contract = contract_compatibility(contract_id)
    artifacts = contract.get("artifacts")
    artifact = artifacts.get(artifact_id) if isinstance(artifacts, dict) else None
    if not isinstance(artifact, dict):
        raise ValueError(
            f"unknown target adapter contract artifact: {contract_id}.{artifact_id}"
        )
    return artifact


def minimum_index_version(contract_id: str, record_version: Any) -> int | None:
    record = artifact_compatibility(contract_id, "record")
    mapping = record.get("minimum_index_by_record")
    value = mapping.get(str(record_version)) if isinstance(mapping, dict) else None
    return value if isinstance(value, int) else None
