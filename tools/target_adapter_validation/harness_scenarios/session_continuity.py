"""Target-validator scenarios for session continuity."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from analysis_strategy_contract import build_active_problem_model_projection
from target_adapter_validation.session_continuity import validate_session_continuity
from target_validation_support import canonical_json_sha256

from .common import ROOT, validator, write_json


STATIC_PATHS = (
    ".ai/assistant/policies/session-continuity.json",
    ".ai/assistant/flows/session-continuity.flow.md",
    ".ai/assistant/flows/session-presence.flow.md",
    ".ai/assistant/gates/session-continuity.md",
    ".ai/assistant/context/task-scales/session-continuity.json",
    ".ai/assistant/context-router.json",
    ".ai/assistant/gates/index.json",
    ".ai/.gitignore",
    ".ai/assistant/assistant-capabilities/generic.json",
    ".ai/assistant/templates/context-packet.json",
)


def _git(target: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=target,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _digest(packet: dict[str, object]) -> str:
    payload = dict(packet)
    payload.pop("integrity", None)
    return canonical_json_sha256(payload)


def _packet(
    *,
    branch: str,
    head: str,
    change_set_sha256: str,
    changed_paths: list[str],
    capability_sha256: str,
    context_packet_sha256: str,
) -> dict[str, object]:
    packet: dict[str, object] = {
        "schema_version": 3,
        "packet_kind": "alatyr-session-continuity",
        "packet_id": "fixture-continuity",
        "packet_sequence": 1,
        "previous_packet_sha256": "none",
        "task": {
            "task_id": "fixture-task",
            "operation_id": "ad-hoc",
            "objective": "verify continuity",
            "status": "active",
            "current_phase": "implementation",
        },
        "boundary": {
            "kind": "automatic-compaction",
            "observed_at": "2026-09-15T12:00:00Z",
            "assistant_surface": "generic",
            "client_version": "fixture-1",
            "model": "fixture-model",
            "capability_record_state": "available",
            "capability_record": ".ai/assistant/assistant-capabilities/generic.json",
            "capability_record_sha256": capability_sha256,
            "capability_evidence_state": "unverified",
        },
        "routing": {
            "profiles": ["code-local"],
            "overlays": ["session-continuity"],
            "project_areas": [],
            "rule_ids": ["ALATYR-CONTINUITY-001"],
            "context_packet": {
                "state": "available",
                "path": ".ai/assistant/templates/context-packet.json",
                "sha256": context_packet_sha256,
            },
            "loaded_paths": ["src/example.txt"],
            "omitted_context": ["full corpus: no expansion trigger"],
        },
        "authorization": {
            "logical_scope": "fixture task",
            "source_reference": "fixture user request",
            "evidence_state": "declarative",
            "recorded_phases": ["inspect", "modify"],
            "deliberately_not_authorized": ["commit", "live-external", "publish"],
            "resume_mode": "inspect-only-pending-current-scope-revalidation",
            "revalidation_required": True,
        },
        "repository": {
            "evidence_state": "available",
            "branch": branch,
            "base_revision": head,
            "head_revision": head,
            "change_set_hash_contract": "canonical-git-change-set-v1",
            "change_set_sha256": change_set_sha256,
            "changed_paths": changed_paths,
        },
        "approvals": [],
        "decisions": [],
        "analysis": {
            "primary_strategy_id": "direct-local",
            "problem_model": {
                "state": "not-required",
                "path": "unavailable",
                "sha256": "unavailable",
            },
            "active_projection": {
                "state": "not-required",
                "path": "unavailable",
                "sha256": "unavailable",
                "source_model_sha256": "unavailable",
                "payload_utf8_bytes": 0,
                "payload_words": 0,
            },
            "open_proof_obligation_ids": [],
            "completed_review_ids": [],
            "invalidated_assumption_ids": [],
        },
        "validation": [],
        "unresolved": [],
        "next_safe_action": "revalidate current modify authorization",
    }
    packet["integrity"] = {
        "digest_contract": "alatyr-session-continuity-v3",
        "packet_sha256": _digest(packet),
    }
    return packet


def _problem_model(*, branch: str, head: str) -> dict[str, object]:
    from analysis_strategy_contract import materialize_authoring_template
    model = materialize_authoring_template(json.loads((ROOT / "templates/target/.ai/assistant/templates/problem-model.json").read_text(encoding="utf-8")))
    model.update(model_id="fixture-problem", operation_id="ad-hoc", primary_strategy_id="direct-local", objective="verify continuity")
    model["active_projection"]["path"] = ".ai/.runtime/problem-model-projections/fixture-problem.json"
    model["repository_binding"].update(branch=branch, base_revision=head)
    model["task_binding"]["task_ids"] = ["fixture-task"]
    return model


def run(target: Path, failures: list[str]) -> None:
    continuity_target = target / "session-continuity"
    continuity_target.mkdir(parents=True)
    for relpath in STATIC_PATHS:
        source = ROOT / "templates" / "target" / relpath
        destination = continuity_target / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    write_json(
        continuity_target / ".ai/framework/rule-registry.json",
        {
            "schema_version": 1,
            "category_owners": [
                {
                    "category": "CONTINUITY",
                    "owner": "framework/session-continuity.md",
                    "rule_ids": ["ALATYR-CONTINUITY-001"],
                    "derived_surfaces": [],
                }
            ],
        },
    )
    source_path = continuity_target / "src/example.txt"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("before\n", encoding="utf-8")
    _git(continuity_target, "init")
    _git(continuity_target, "config", "user.email", "fixture@example.test")
    _git(continuity_target, "config", "user.name", "Fixture")
    _git(continuity_target, "add", ".")
    _git(continuity_target, "commit", "-m", "fixture baseline")
    source_path.write_text("after\n", encoding="utf-8")

    probe = validator(continuity_target)
    head = probe.git.head_revision()
    branch = probe.git.branch_name()
    change_set = probe.git.change_set(head or "")
    if head is None or branch is None or change_set is None:
        failures.append("session continuity fixture could not resolve Git evidence")
        return
    packet_path = continuity_target / ".ai/.runtime/continuity/fixture.json"
    capability_path = (
        continuity_target
        / ".ai/assistant/assistant-capabilities/generic.json"
    )
    context_packet_path = (
        continuity_target / ".ai/assistant/templates/context-packet.json"
    )
    write_json(
        packet_path,
        _packet(
            branch=branch,
            head=head,
            change_set_sha256=change_set.content_sha256,
            changed_paths=list(change_set.changed_files),
            capability_sha256=hashlib.sha256(capability_path.read_bytes()).hexdigest(),
            context_packet_sha256=hashlib.sha256(
                context_packet_path.read_bytes()
            ).hexdigest(),
        ),
    )

    valid = validator(continuity_target, continuity_packets=[packet_path])
    validate_session_continuity(valid)
    valid_errors = {
        finding.code
        for finding in valid.findings
        if finding.level == "error" and finding.code.startswith("SESSION_CONTINUITY")
    }
    if valid_errors:
        failures.append(
            "valid session continuity packet produced errors: "
            + ", ".join(sorted(valid_errors))
        )

    original_context, original_packet = context_packet_path.read_bytes(), packet_path.read_bytes()
    wrong_context = json.loads(original_context)
    wrong_context["schema_version"] += 1
    write_json(context_packet_path, wrong_context)
    wrong_packet = json.loads(original_packet)
    wrong_packet["routing"]["context_packet"]["sha256"] = hashlib.sha256(context_packet_path.read_bytes()).hexdigest()
    wrong_packet["integrity"]["packet_sha256"] = _digest(wrong_packet)
    write_json(packet_path, wrong_packet)
    wrong_version = validator(continuity_target, continuity_packets=[packet_path])
    validate_session_continuity(wrong_version)
    if "SESSION_CONTINUITY_CONTEXT_IDENTITY" not in {finding.code for finding in wrong_version.findings}:
        failures.append("continuity policy upgrades must not accept unsupported context packet schemas")
    context_packet_path.write_bytes(original_context)
    packet_path.write_bytes(original_packet)

    model_path = (
        continuity_target / ".ai/.runtime/problem-models/fixture.json"
    )
    model = _problem_model(branch=branch, head=head)
    write_json(model_path, model)
    projection_path = (
        continuity_target
        / ".ai/.runtime/problem-model-projections/fixture-problem.json"
    )
    projection = build_active_problem_model_projection(
        model,
        source_path=".ai/.runtime/problem-models/fixture.json",
        source_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
    )
    write_json(projection_path, projection)
    bound_packet = _packet(
        branch=branch,
        head=head,
        change_set_sha256=change_set.content_sha256,
        changed_paths=list(change_set.changed_files),
        capability_sha256=hashlib.sha256(capability_path.read_bytes()).hexdigest(),
        context_packet_sha256=hashlib.sha256(
            context_packet_path.read_bytes()
        ).hexdigest(),
    )
    bound_packet["analysis"] = {
        "primary_strategy_id": "direct-local",
        "problem_model": {
            "state": "available",
            "path": ".ai/.runtime/problem-models/fixture.json",
            "sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        },
        "active_projection": {
            "state": "available",
            "path": ".ai/.runtime/problem-model-projections/fixture-problem.json",
            "sha256": hashlib.sha256(projection_path.read_bytes()).hexdigest(),
            "source_model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
            "payload_utf8_bytes": projection["measurements"]["payload_utf8_bytes"],
            "payload_words": projection["measurements"]["payload_words"],
        },
        "open_proof_obligation_ids": [],
        "completed_review_ids": [],
        "invalidated_assumption_ids": [],
    }
    bound_packet["integrity"] = {
        "digest_contract": "alatyr-session-continuity-v3",
        "packet_sha256": _digest(bound_packet),
    }
    write_json(packet_path, bound_packet)
    valid_analysis = validator(
        continuity_target, continuity_packets=[packet_path]
    )
    validate_session_continuity(valid_analysis)
    if any(
        finding.level == "error"
        and finding.code.startswith(("SESSION_CONTINUITY_ANALYSIS", "ANALYSIS_"))
        for finding in valid_analysis.findings
    ):
        failures.append("valid continuity problem-model binding was rejected")

    stale_projection = json.loads(projection_path.read_text(encoding="utf-8"))
    stale_projection["payload"]["objective"] = "stale continuity projection"
    write_json(projection_path, stale_projection)
    stale_projection_result = validator(
        continuity_target, continuity_packets=[packet_path]
    )
    validate_session_continuity(stale_projection_result)
    if "SESSION_CONTINUITY_ACTIVE_PROJECTION_DRIFT" not in {
        finding.code for finding in stale_projection_result.findings
    }:
        failures.append("continuity must reject a changed active projection")
    write_json(projection_path, projection)

    bound_packet["analysis"]["active_projection"]["payload_words"] += 1
    bound_packet["integrity"] = {
        "digest_contract": "alatyr-session-continuity-v3",
        "packet_sha256": _digest(bound_packet),
    }
    write_json(packet_path, bound_packet)
    measurement_result = validator(
        continuity_target, continuity_packets=[packet_path]
    )
    validate_session_continuity(measurement_result)
    if "SESSION_CONTINUITY_ACTIVE_PROJECTION_MEASUREMENT_DRIFT" not in {
        finding.code for finding in measurement_result.findings
    }:
        failures.append("continuity must reject stale projection measurements")
    bound_packet["analysis"]["active_projection"]["payload_words"] -= 1

    bound_packet["analysis"]["primary_strategy_id"] = "invariant-first"
    bound_packet["integrity"]["packet_sha256"] = _digest(bound_packet)
    write_json(packet_path, bound_packet)
    mismatched_analysis = validator(
        continuity_target, continuity_packets=[packet_path]
    )
    validate_session_continuity(mismatched_analysis)
    if "SESSION_CONTINUITY_ANALYSIS_DRIFT" not in {
        finding.code for finding in mismatched_analysis.findings
    }:
        failures.append(
            "continuity must reject strategy drift from its bound problem model"
        )

    wrong_capability = json.loads(packet_path.read_text(encoding="utf-8"))
    wrong_capability["boundary"]["capability_record"] = (
        ".ai/assistant/templates/context-packet.json"
    )
    wrong_capability["boundary"]["capability_record_sha256"] = hashlib.sha256(
        context_packet_path.read_bytes()
    ).hexdigest()
    wrong_capability["integrity"]["packet_sha256"] = _digest(wrong_capability)
    write_json(packet_path, wrong_capability)
    wrong_capability_result = validator(
        continuity_target, continuity_packets=[packet_path]
    )
    validate_session_continuity(wrong_capability_result)
    if "SESSION_CONTINUITY_CAPABILITY_PATH" not in {
        finding.code for finding in wrong_capability_result.findings
    }:
        failures.append("capability evidence must bind the selected surface path")

    context_identity = json.loads(packet_path.read_text(encoding="utf-8"))
    context_identity["boundary"] = _packet(
        branch=branch,
        head=head,
        change_set_sha256=change_set.content_sha256,
        changed_paths=list(change_set.changed_files),
        capability_sha256=hashlib.sha256(capability_path.read_bytes()).hexdigest(),
        context_packet_sha256=hashlib.sha256(context_packet_path.read_bytes()).hexdigest(),
    )["boundary"]
    context_identity["routing"]["context_packet"]["path"] = (
        ".ai/assistant/assistant-capabilities/generic.json"
    )
    context_identity["routing"]["context_packet"]["sha256"] = hashlib.sha256(
        capability_path.read_bytes()
    ).hexdigest()
    context_identity["integrity"]["packet_sha256"] = _digest(context_identity)
    write_json(packet_path, context_identity)
    context_identity_result = validator(
        continuity_target, continuity_packets=[packet_path]
    )
    validate_session_continuity(context_identity_result)
    if "SESSION_CONTINUITY_CONTEXT_IDENTITY" not in {
        finding.code for finding in context_identity_result.findings
    }:
        failures.append("context evidence must bind an Alatyr context packet")

    original_packet = _packet(
        branch=branch,
        head=head,
        change_set_sha256=change_set.content_sha256,
        changed_paths=list(change_set.changed_files),
        capability_sha256=hashlib.sha256(capability_path.read_bytes()).hexdigest(),
        context_packet_sha256=hashlib.sha256(context_packet_path.read_bytes()).hexdigest(),
    )
    write_json(packet_path, original_packet)

    source_path.write_text("changed after checkpoint\n", encoding="utf-8")
    stale = validator(continuity_target, continuity_packets=[packet_path])
    validate_session_continuity(stale)
    if "SESSION_CONTINUITY_CHANGE_SET_DRIFT" not in {
        finding.code for finding in stale.findings
    }:
        failures.append("stale session continuity change-set evidence must be rejected")

    tampered_packet = json.loads(packet_path.read_text(encoding="utf-8"))
    tampered_packet["next_safe_action"] = "modify without revalidation"
    write_json(packet_path, tampered_packet)
    tampered = validator(continuity_target, continuity_packets=[packet_path])
    validate_session_continuity(tampered)
    if "SESSION_CONTINUITY_PACKET_DIGEST" not in {
        finding.code for finding in tampered.findings
    }:
        failures.append("tampered session continuity packets must be rejected")

    _git(continuity_target, "add", "-f", ".ai/.runtime/continuity/fixture.json")
    tracked = validator(continuity_target, continuity_packets=[packet_path])
    validate_session_continuity(tracked)
    if "SESSION_CONTINUITY_PACKET_TRACKED" not in {
        finding.code for finding in tracked.findings
    }:
        failures.append("tracked session continuity packets must be rejected")
