"""Provider-neutral cold-start questions and source-bound answer-shape checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from context_input_snapshot import read_regular_context_bytes
from project_evidence import ProjectEvidence, MAX_FILE_BYTES
from target_adapter_validation.values import is_resolved_string, is_string_list

SCENARIO = Path(__file__).resolve().parents[1] / "conformance/operations/project-understanding.json"
STATES = {"observed", "proposed", "accepted", "unknown", "contradicted"}
MAX_ANSWERS = 16
MAX_CITATIONS = 128


def understanding_request() -> dict[str, Any]:
    raw = read_regular_context_bytes(SCENARIO, max_bytes=MAX_FILE_BYTES)
    scenario = json.loads(raw)
    if (not isinstance(scenario, dict) or type(scenario.get("schema_version")) is not int
            or scenario["schema_version"] != 1 or scenario.get("operation") != "project-understanding"
            or scenario.get("fixture_kind") != "assistant-operation-conformance"
            or scenario.get("allowed_actions") != ["read-only"]):
        raise ValueError("project-understanding scenario is invalid")
    if not is_string_list(scenario.get("required_for_every_surface"), resolved=True):
        raise ValueError("project-understanding requirements must be concrete non-empty strings")
    questions = scenario.get("questions")
    if (not isinstance(questions, list) or not 1 <= len(questions) <= MAX_ANSWERS
            or any(not isinstance(row, dict) or not is_resolved_string(row.get("id"))
                   or not is_resolved_string(row.get("question")) for row in questions)
            or len({row["id"] for row in questions}) != len(questions)):
        raise ValueError("project-understanding questions must have unique concrete IDs and questions")
    return {"schema_version": 1, "report_kind": "project-understanding-request",
            "status": "prepared-not-executed", "scenario_sha256": hashlib.sha256(raw).hexdigest(),
            "questions": questions, "requirements": scenario["required_for_every_surface"],
            "result_shape": {"schema_version": 1, "report_kind": "project-understanding-result",
                             "scenario_sha256": hashlib.sha256(raw).hexdigest(),
                             "assistant_surface": "<actual surface>",
                             "session_evidence": "<actual isolation/context evidence or explicit unknown>",
                             "exposed_context": [{"path": "<target-relative path>", "sha256": "<SHA-256>"}],
                             "answers": [{"question_id": "<one row per question>",
                                          "answer": "<evidence-backed answer or concrete unknown>",
                                          "knowledge_state": "observed|proposed|accepted|unknown|contradicted",
                                          "sources": [{"path": "<target-relative path>", "sha256": "<SHA-256>"}],
                                          "limitations": ["<specific gaps or unresolved conflicts>"]}]},
            "acceptance_granted": False}


def _citations(value: Any, label: str, evidence: ProjectEvidence) -> set[str]:
    if not isinstance(value, list) or len(value) > MAX_CITATIONS:
        raise ValueError(f"{label} requires at most {MAX_CITATIONS} file bindings")
    seen = set()
    for row in value:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise ValueError(f"{label} requires exact path/SHA-256 bindings")
        path, digest = row["path"], row["sha256"]
        if not isinstance(path, str) or path in seen:
            raise ValueError(f"{label} paths must be unique strings")
        if (not isinstance(digest, str) or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)):
            raise ValueError(f"{label} requires lowercase SHA-256 values")
        seen.add(path)
        if hashlib.sha256(evidence.exact(path)).hexdigest() != digest:
            raise ValueError(f"{label} source is stale: {path}")
    return seen


def check_understanding(target: Path, report: Path) -> dict[str, Any]:
    request = understanding_request()
    with ProjectEvidence(report.absolute().parent) as records, ProjectEvidence(target) as evidence:
        data = records.object(report.name)
        if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
            raise ValueError("understanding result schema_version must be 1")
        if data.get("report_kind") != "project-understanding-result":
            raise ValueError("understanding result report_kind is invalid")
        if data.get("scenario_sha256") != request["scenario_sha256"]:
            raise ValueError("understanding scenario binding is stale")
        for field in ("assistant_surface", "session_evidence"):
            if not is_resolved_string(data.get(field)):
                raise ValueError(f"understanding result {field} requires concrete evidence or an explained unknown")
        exposed = _citations(data.get("exposed_context"), "exposed_context", evidence)
        rows = data.get("answers")
        if not isinstance(rows, list) or len(rows) != len(request["questions"]):
            raise ValueError("understanding result must answer every scenario question exactly once")
        expected = {row["id"] for row in request["questions"]}
        seen, unknown = set(), []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("understanding answers must be objects")
            question = row.get("question_id")
            if not isinstance(question, str) or question not in expected or question in seen:
                raise ValueError("understanding question IDs must be unique and match the scenario")
            seen.add(question)
            state = row.get("knowledge_state")
            if not isinstance(state, str) or state not in STATES:
                raise ValueError(f"{question}.knowledge_state is invalid")
            if not is_resolved_string(row.get("answer")):
                raise ValueError(f"{question}.answer must be concrete")
            if not is_string_list(row.get("limitations"), non_empty=False, resolved=True):
                raise ValueError(f"{question}.limitations must be concrete strings")
            sources = _citations(row.get("sources"), question, evidence)
            if not sources <= exposed:
                raise ValueError(f"{question} cites sources missing from exposed_context")
            if state == "unknown":
                if not row["limitations"]:
                    raise ValueError(f"{question} must explain unknown coverage")
                unknown.append(question)
            elif not sources:
                raise ValueError(f"{question} requires current source evidence")
            if state == "contradicted" and (len(sources) < 2 or not row["limitations"]):
                raise ValueError(f"{question} requires both conflicting sources and a retained limitation")
        result = {"status": "structurally-valid-review-required", "operation": "project-understanding",
                  "unknown_questions": unknown, "input_bindings": evidence.bindings(),
                  "report_sha256": records.bindings()[0]["sha256"],
                  "semantic_review": "required-against-target-specific-oracle",
                  "fresh_session_isolation": "not-independently-verified", "acceptance_granted": False}
        if understanding_request()["scenario_sha256"] != request["scenario_sha256"]:
            raise ValueError("understanding scenario changed during result validation")
    return result
