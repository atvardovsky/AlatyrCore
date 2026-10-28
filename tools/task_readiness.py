"""Derive declared dependency readiness; never permission or evidence acceptance."""

from __future__ import annotations

from typing import Any


def execution_readiness(model: Any) -> dict[str, Any]:
    result = {"state": "not-configured", "ready": [], "blocked": [], "waiting": [],
              "retained_unresolved": [], "unsettled_prerequisites": {},
              "failures": [], "authority": "none",
              "evidence_verified": False}
    if not isinstance(model, dict) or "execution_dependencies" not in model:
        return result
    result["state"] = "invalid"
    rows, obligations = model["execution_dependencies"], model.get("proof_obligations")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 64 or not isinstance(obligations, list) or len(obligations) > 64:
        result["failures"].append("execution dependencies require 1..64 rows and bounded proof obligations")
        return result
    proofs = {}
    for proof in obligations:
        if (not isinstance(proof, dict) or not isinstance(proof.get("id"), str)
                or not proof["id"] or proof["id"] in proofs
                or not isinstance(proof.get("status"), str)
                or proof["status"] not in {"open", "passed", "failed", "blocked", "waived"}):
            result["failures"].append("execution dependencies require unique typed proof obligations")
            return result
        proofs[proof["id"]] = proof
    dependencies = {}
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"obligation_id", "requires"}
                or not isinstance(row.get("obligation_id"), str)
                or row["obligation_id"] not in proofs or row["obligation_id"] in dependencies
                or not isinstance(row.get("requires"), list) or len(row["requires"]) > 64
                or not all(isinstance(item, str) and item in proofs for item in row["requires"])):
            result["failures"].append("execution dependencies require unique known obligations and typed prerequisite IDs")
            return result
        if len(set(row["requires"])) != len(row["requires"]):
            result["failures"].append("execution dependencies cannot repeat a prerequisite")
            return result
        dependencies[row["obligation_id"]] = row["requires"]
    if dependencies.keys() != proofs.keys():
        result["failures"].append("execution dependencies must explicitly cover every proof obligation")
        return result
    visiting, visited = set(), set()

    def visit(identifier: str) -> bool:
        if identifier in visiting:
            return False
        if identifier in visited:
            return True
        visiting.add(identifier)
        if not all(visit(item) for item in dependencies[identifier]):
            return False
        visiting.remove(identifier)
        visited.add(identifier)
        return True

    if not all(visit(identifier) for identifier in dependencies):
        result["failures"].append("execution dependencies contain a cycle")
        return result
    settled = {key for key, proof in proofs.items() if proof["status"] in {"passed", "waived"}}
    for key in sorted(proofs):
        missing = sorted(set(dependencies[key]) - settled)
        if key in settled:
            if missing:
                result["failures"].append(f"settled obligation {key} has unfinished prerequisites: {', '.join(missing)}")
            continue
        result["retained_unresolved"].append(key)
        result["unsettled_prerequisites"][key] = missing
        if proofs[key]["status"] == "blocked":
            result["blocked"].append(key)
        elif missing:
            result["waiting"].append({"obligation_id": key, "requires": missing})
        else:
            result["ready"].append(key)
    if result["failures"]:
        result["ready"] = []
        return result
    result["state"] = "declared-readiness"
    return result
