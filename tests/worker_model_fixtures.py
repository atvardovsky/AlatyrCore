"""Small provider-neutral model-selection fixtures shared by receipt tests."""

import hashlib
import json


def selection_fixture(packet_id="packet-1", node_id="worker-1", capability_sha256="a" * 64):
    return {"schema_version": 1, "packet_id": packet_id, "node_id": node_id,
        "capability_sha256": capability_sha256, "task_class": "mechanical",
        "options": [
            {"id": "economy", "model": "fixture-economy", "reasoning": "low", "cost_rank": 1,
             "eligible_for": ["mechanical"], "availability": "available", "authorized": True, "evidence_ref": "review/economy",
             "selection_modes": ["explicit-model", "inherit", "client-default"]},
            {"id": "reasoning", "model": "fixture-reasoning", "reasoning": "high", "cost_rank": 3,
             "eligible_for": ["mechanical", "bounded-code", "semantic"], "availability": "available", "authorized": True,
             "evidence_ref": "review/reasoning", "selection_modes": ["explicit-model", "inherit", "client-default"]}],
        "exclusions": [], "selected_option": "economy", "selection_mode": "explicit-model",
        "rationale": "Bounded mechanically reviewable extraction", "max_cost_rank": 3,
        "observed": {"state": "verified", "model": "fixture-economy", "reasoning": "low", "evidence_ref": "runtime/model"}}


def write_selection(root, relative, record):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(record, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    return {"path": relative, "sha256": hashlib.sha256(raw).hexdigest()}
