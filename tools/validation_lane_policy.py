"""Resolve one target-owned validation objective; no execution or acceptance."""

from __future__ import annotations

import re

from cli_inputs import json_object
from request_values import fields, integer, request_path, text

POLICY = ".ai/project/testing/validation-lanes.json"
MAX_BYTES = 65536
MAX_CASES = 256
STATES = {"passed", "failed", "not-run"}


def _object(read, path):
    raw = read(path)
    if len(raw) > MAX_BYTES:
        raise ValueError("validation lane input exceeds 64 KiB")
    return json_object(raw, path)


def case_ids(value, label):
    if not isinstance(value, list) or len(value) > MAX_CASES:
        raise ValueError(label + " requires a bounded case ID list")
    parsed = [text(item, label, 160) for item in value]
    if len(set(parsed)) != len(parsed):
        raise ValueError(label + " contains duplicate case IDs")
    return parsed


def _probe(commands, identity, inputs, consumer):
    selected = commands.get(text(identity, "validation probe command"))
    if selected is None or selected is consumer:
        raise ValueError("validation probe requires a distinct registered command")
    execution = selected["execution"]
    argv = selected.get("argv")
    required = set(execution.get("harness_inputs", [])) | set(execution["configuration_paths"])
    if (execution["kind"] != "metadata-check" or execution["proof_boundary"] != "static-metadata"
            or execution["environment"] != "none" or execution["effects"]
            or any(resource["access"] != "read" for resource in execution["resources"])
            or any(item.startswith("alatyr:validation-lane:") for item in execution["prerequisites"])
            or not required <= inputs.keys() or not argv
            or any("\0" in part for part in argv)):
        raise ValueError("validation probe must be scoped read-only metadata with all its inputs bound")
    return argv


def _retry(read, run, model, brief):
    path = run.get("lane_retry")
    if path is None:
        return None
    row = fields(_object(read, path), {"previous_attempt", "reason", "condition", "condition_input",
                                      "cleanup_confirmed"}, "validation lane retry")
    from delivery_receipts import artifact
    import hashlib
    ref = artifact(row["condition_input"], "validation retry condition")
    digest = hashlib.sha256(read(ref["path"])).hexdigest()
    if digest != ref["sha256"]:
        raise ValueError("validation retry condition input changed")
    text(row["previous_attempt"], "validation retry attempt", 64)
    text(row["condition"], "validation retry condition", 512)
    if (row["reason"] not in ("changed-input", "execution-repair", "distinct-required-evidence")
            or type(row["cleanup_confirmed"]) is not bool):
        raise ValueError("validation retry requires an exact reason and cleanup disposition")
    proofs = {item["id"]: item for item in model["proof_obligations"]}
    pilot_ids = set(brief["delivery_control"]["pilot_outcome_ids"])
    pilots = {key for x in brief["outcomes"] if x["id"] in pilot_ids for key in x["proof_obligation_ids"]}

    def reviewed(identity):
        proof = proofs.get(identity, {})
        return (identity not in pilots and proof.get("required") is True and proof.get("status") == "passed"
                and {path, ref["path"]} <= set(proof.get("evidence_refs", ())))

    diagnosis = run["diagnosis_proof_id"]
    independent = run["independent_review_proof_id"]
    if not reviewed(diagnosis):
        raise ValueError("validation retry needs a required passed diagnosis linked to its changed condition")
    return {**row, "independent_review": diagnosis != independent and reviewed(independent)}


def resolve_lane(markers, read, policy, command, record, run, model, brief):
    if len(markers) != 1:
        raise ValueError("validation lane requires one canonical objective marker")
    identity = markers[0].removeprefix("alatyr:validation-lane:")
    if re.fullmatch(r"[a-z][a-z0-9-]{0,63}", identity) is None:
        raise ValueError("validation lane objective requires a stable lowercase ID")
    configuration = fields(_object(read, POLICY), {"schema_version", "objectives"}, "validation lane policy")
    objectives = configuration["objectives"]
    if (type(configuration["schema_version"]) is not int or configuration["schema_version"] != 1
            or not isinstance(objectives, dict) or not 1 <= len(objectives) <= 64):
        raise ValueError("validation lane policy requires schema 1 and 1..64 objectives")
    objective = fields(objectives.get(identity), {"max_attempts", "max_seconds", "commands"}, "selected objective")
    limits = (integer(objective["max_attempts"], "objective max_attempts", 1, 32),
              integer(objective["max_seconds"], "objective max_seconds", 1, 86400))
    entries = objective["commands"]
    if not isinstance(entries, dict) or not 1 <= len(entries) <= 64:
        raise ValueError("validation objective requires 1..64 registered command entries")
    entry = fields(entries.get(command["id"]), {"probe", "expected_cases", "material_inputs", "artifact"},
                   "selected lane command")
    cases = case_ids(entry["expected_cases"], "expected cases")
    testing = command["execution"]["kind"] == "automated-test"
    if testing != bool(cases):
        raise ValueError("only automated-test lanes require a nonempty exact case selection")
    inputs = record["input_sha256"]
    roles = entry["material_inputs"]
    if not isinstance(roles, dict) or not 1 <= len(roles) <= 32:
        raise ValueError("validation lane needs 1..32 stable material input roles")
    material_inputs = {}
    for role, path in roles.items():
        text(role, "material input role", 80)
        path = request_path(path)
        if path not in inputs:
            raise ValueError("validation lane material input must bind actual bytes: " + path)
        material_inputs[role] = inputs[path]
    commands = {item["id"]: item for item in policy["commands"]}
    preflight = _probe(commands, entry["probe"], inputs, command)
    artifact = entry["artifact"]
    if artifact is not None:
        if testing or not command["execution"].get("harness_inputs"):
            raise ValueError("artifact reuse requires a non-test command and explicit material harness inputs")
        spec = fields(artifact, {"receipt", "verifier"}, "artifact reuse")
        artifact = {"receipt": request_path(spec["receipt"]),
                    "argv": _probe(commands, spec["verifier"], inputs, command)}
    return {"objective": identity, "limits": limits, "cases": cases, "probe_argv": preflight,
            "artifact": artifact, "retry": _retry(read, run, model, brief),
            "inputs": inputs, "material_inputs": material_inputs,
            "policy_sha256": record["policy_sha256"], "estimate": run["estimated_seconds"]}
