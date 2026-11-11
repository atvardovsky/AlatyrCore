"""Optional terminal prerequisites over canonical receipts, never an executor."""

from __future__ import annotations

import hashlib
import json
import time

from delivery_receipts import artifact, parse_receipt, read_bound, timestamp
from request_values import fields, integer, strings, text


MAX_RULES = 16


def parse_terminal_control(value: object, brief: dict) -> dict:
    control = fields(value, {"schema_version", "rules"}, "terminal_control")
    if type(control["schema_version"]) is not int or control["schema_version"] != 1:
        raise ValueError("terminal_control requires schema 1")
    rules = control["rules"]
    if not isinstance(rules, list) or not 1 <= len(rules) <= MAX_RULES:
        raise ValueError("terminal_control requires 1..16 rules")
    seen = set()
    for rule in rules:
        fields(rule, {"id", "phase", "effects", "proof_id", "command_id", "receipt",
                      "candidate", "environment", "max_age_seconds"}, "terminal prerequisite")
        for key in ("id", "proof_id", "command_id"):
            text(rule[key], "terminal prerequisite." + key)
        if rule["id"] in seen:
            raise ValueError("terminal prerequisite IDs must be unique")
        seen.add(rule["id"])
        phase = rule["phase"]
        if not isinstance(phase, str) or phase not in {"commit", "publish", "live-external"}:
            raise ValueError("terminal prerequisite requires commit, publish or live-external")
        if phase not in brief["authorized_phases"]:
            raise ValueError("terminal prerequisite phase exceeds the current request ceiling")
        effects = strings(rule["effects"], "terminal prerequisite.effects", minimum=1)
        if not set(effects) <= set(brief["effect_scope"]):
            raise ValueError("terminal prerequisite effects exceed the current request scope")
        integer(rule["max_age_seconds"], "terminal prerequisite.max_age_seconds", 1, 86400)
        for key in ("receipt", "candidate", "environment"):
            artifact(rule[key], "terminal prerequisite." + key)
        if rule["candidate"]["path"] == rule["environment"]["path"]:
            raise ValueError("terminal prerequisite candidate and environment must be distinct bindings")
    return control


def terminal_policy_digest(control: dict | None) -> str | None:
    """Fresh run hashes may change on rebind; the prerequisite policy may not vanish."""
    if control is None:
        return None
    rows = [{key: value for key, value in rule.items() if key not in {"receipt", "candidate", "environment"}}
            | {key: rule[key]["path"] for key in ("candidate", "environment")}
            for rule in control["rules"]]
    raw = json.dumps(sorted(rows, key=lambda row: row["id"]), sort_keys=True,
                     separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def terminal_prerequisite_failures(context, target, brief: dict, action: dict,
                                   model: dict, inputs: dict, *, now: float | None = None,
                                   deadlines: list[tuple[float, float]] | None = None) -> list[str]:
    control = brief.get("terminal_control")
    if control is None or action["kind"] != "work" or action["phase"] == "inspect":
        return []
    selected = [rule for rule in control["rules"] if rule["phase"] == action["phase"]
                and set(rule["effects"]) & set(action["effects"])]
    if not selected:
        return []
    from request_focus import prerequisite_closure
    roots = {key for outcome in brief["outcomes"] for key in outcome["proof_obligation_ids"]}
    allowed = prerequisite_closure(model, roots)
    proofs = {row["id"]: row for row in model["proof_obligations"]}
    observed = time.time() if now is None else now
    failures = []
    for rule in selected:
        label = "terminal prerequisite " + rule["id"]
        try:
            proof = proofs.get(rule["proof_id"])
            if (rule["proof_id"] not in allowed or proof is None or not proof["required"]
                    or proof["status"] != "passed"):
                raise ValueError("requires a passed required proof within the original outcome dependencies")
            if rule["receipt"]["path"] not in proof.get("evidence_refs", []):
                raise ValueError("required proof must cite the selected receipt")
            receipt = parse_receipt(read_bound(context, target, rule["receipt"], inputs))
            for key in ("request_id", "task_id"):
                if receipt[key] != brief[key]:
                    raise ValueError("receipt differs in current " + key)
            if receipt["command_id"] != rule["command_id"]:
                raise ValueError("receipt differs in required command_id")
            if receipt["result"] != "passed" or receipt["exit_code"] != 0:
                raise ValueError("requires terminal passed exit_code=0, not a running, failed or interrupted command")
            finished = timestamp(receipt["finished_at"], "receipt.finished_at")
            if not 0 <= observed - finished <= rule["max_age_seconds"]:
                raise ValueError("receipt is future-dated or exceeds max_age_seconds")
            for key in ("candidate", "environment"):
                binding = rule[key]
                if receipt["input_sha256"].get(binding["path"]) != binding["sha256"]:
                    raise ValueError("receipt differs in exact " + key + " binding")
                read_bound(context, target, binding, inputs)
            from analysis_evidence import MAX_ARTIFACT_BYTES
            read_bound(context, target, receipt["result_artifact"], inputs, limit=MAX_ARTIFACT_BYTES)
            deadline = finished + rule["max_age_seconds"]
            final_time = time.time() if now is None else now
            if not finished <= final_time <= deadline:
                raise ValueError("receipt expired during prerequisite review")
            if deadlines is not None:
                deadlines.append((finished, deadline))
        except (OSError, ValueError, RecursionError) as exc:
            failures.append(label + ": " + str(exc))
    return failures
