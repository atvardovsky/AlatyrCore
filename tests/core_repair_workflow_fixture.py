"""Synthetic core-only workflow, reusable in isolated integration workspaces."""

from __future__ import annotations

import json
import copy
import hashlib
import shlex
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_lifecycle_conformance import (approval_record, make_validator, mark_fixture_selected_assistant,
    refresh_context_and_bootstrap, resolve_adapter, run_git, transition_installation_state)
from scaffold_target_structure import plan as scaffold_plan
from tests.active_task_fixture import ActiveTaskFixture
from target_adapter_validation.harness_scenarios.analysis_strategies import _model


def documented_doctor_arguments(document: str, target: Path) -> list[str]:
    prefix = "python3 tools/alatyr.py doctor "
    examples = [line for line in document.splitlines() if line.startswith(prefix)]
    if len(examples) != 1:
        raise ValueError("core walkthrough must retain one complete source doctor example")
    replacements = {"/path/to/project": str(target), "REPAIR-1": "fixture-task"}
    return [replacements.get(token, token) for token in shlex.split(examples[0])[2:]]


def run_core_repair_workflow(target: Path, *, outcome_checks: bool = False) -> dict:
    """Exercise real CLIs; fixture approvals never authorize production actions."""
    def run(*arguments, expected=0, structured=True):
        result = subprocess.run([sys.executable, str(ROOT / "tools/alatyr.py"), *map(str, arguments)],
                                capture_output=True, text=True, cwd=target, timeout=120)
        if result.returncode != expected:
            raise AssertionError(result.stdout + result.stderr)
        return json.loads(result.stdout) if structured else result.stdout

    if not (target / ".git").exists():
        run_git(target, "init", "-q")
    run_git(target, "config", "user.email", "fixture@example.invalid")
    run_git(target, "config", "user.name", "Workflow Fixture")
    run_git(target, "config", "core.autocrlf", "false")
    if not (target / "README.md").exists():
        (target / "README.md").write_text("# Core workflow fixture\n", encoding="utf-8")
    product = target / "workflow-product.txt"
    product.write_text("broken\n", encoding="utf-8")
    run_git(target, "add", ".")
    run_git(target, "commit", "-qm", "prepare synthetic workflow fixture")
    protected = {path: (target / path).read_bytes() for path in run_git(target, "ls-files", "-z").split("\0")
                 if path and path != "workflow-product.txt"}
    _, blocked = scaffold_plan(SimpleNamespace(target=target, write=True, overwrite_existing=False,
        profile="core", framework_pack="matched", enable_module=[], assistant_surface=[]))
    if blocked:
        raise AssertionError(blocked)
    resolve_adapter(target, "core")
    if any((target / path).read_bytes() != raw for path, raw in protected.items()):
        raise AssertionError("fixture adaptation changed existing product files")
    mark_fixture_selected_assistant(target)
    refresh_context_and_bootstrap(target)
    staged = make_validator(target, ROOT)
    errors = [item for item in staged.run() if item.level == "error"]
    if errors:
        raise AssertionError(errors)
    transition_installation_state(target, next_state="accepted", reason="strict-acceptance",
        operation_id="fixture-install", validation_status="passed", validation_evidence="executed staged fixture validation")
    run_git(target, "add", ".")
    run_git(target, "commit", "-qm", "install controlled core workflow fixture")
    base = run_git(target, "rev-parse", "HEAD")
    evidence = target / "evidence/workflow"
    evidence.mkdir(parents=True)
    oracle = evidence / "outcome-oracle.md"
    if outcome_checks:
        oracle.write_text("The requested fixture outcome is workflow-product.txt containing repaired.\n"
                          "A green helper without that actual file result is rejected.\n", encoding="utf-8")
    check = [sys.executable, "-c", "from pathlib import Path; assert Path('workflow-product.txt').read_text() == 'repaired\\n'"]
    diagnostic = subprocess.run(check, cwd=target, capture_output=True, text=True)
    if diagnostic.returncode == 0:
        raise AssertionError("negative control must reproduce the seeded fault")
    (evidence / "diagnostic.txt.snapshot").write_text(diagnostic.stderr, encoding="utf-8")
    product.write_text("repaired\n", encoding="utf-8")
    accepted = subprocess.run(check, cwd=target, capture_output=True, text=True)
    if accepted.returncode:
        raise AssertionError(accepted.stderr)
    (evidence / "validation.txt.snapshot").write_text("Synthetic original case passed after evidence packaging\n", encoding="utf-8")
    fixture = ActiveTaskFixture()
    fixture.target, fixture.base, fixture.result = target, base, base
    fixture.model, fixture.model_path = _model(), target / ".ai/.runtime/problem-models/fixture-problem.json"
    fixture.model["incident"].update(mode="new", family_id="workflow-incident", trigger="reported-defect")
    fixture.model["original_case"] = {"actor": "synthetic workflow caller", "input": "Read workflow-product.txt",
        "expected_outcome": "The synthetic workflow product returns repaired", "status": "verified-fixed",
        "source_ref": "evidence/workflow/diagnostic.txt.snapshot", "evidence_refs": ["evidence/workflow/validation.txt.snapshot"],
        "supersession": None}
    fixture.model["repository_binding"].update(branch=run_git(target, "branch", "--show-current"), base_revision=base)
    fixture.model["changed_facts"][0].update(owner_ref="README.md", statement="Synthetic workflow product returns its repaired value")
    fixture.model["invariants"][0]["owner_ref"] = "README.md"
    fixture.model["proof_obligations"][0].update(id="generic-repair-review", evidence_refs=["evidence/workflow/validation.txt.snapshot"])
    if outcome_checks:
        from outcome_evidence import case_binding
        proof = fixture.model["proof_obligations"][0]["id"]
        result_ref = "evidence/workflow/validation.txt.snapshot"
        artifact = {"path": result_ref, "sha256": hashlib.sha256((target / result_ref).read_bytes()).hexdigest()}
        scope = {"actor": fixture.model["original_case"]["actor"], "system": "Test project isolated file workflow",
                 "entrypoint": "ordinary workflow product file read", "conditions": "actual seeded failure and repaired result",
                 "surfaces": ["workflow-product.txt"]}
        case = {"id": "original-case", "source_ref": fixture.model["original_case"]["source_ref"],
            "oracle": {"path": oracle.relative_to(target).as_posix(), "sha256": hashlib.sha256(oracle.read_bytes()).hexdigest()},
            "expected_result": fixture.model["original_case"]["expected_outcome"],
            "rejected_substitute": "A green component result without the requested original effect",
            "scope": scope, "evidence_class": "original-case", "proof_obligation_ids": [proof], "observation": None}
        case["observation"] = {"case_sha256": case_binding(fixture.model, case), "scope": copy.deepcopy(scope),
            "evidence_class": "original-case", "status": "supported", "decisive_check_reached": True,
            "actual_result": "Actual file assertion failed before repair and passed after repair",
            "input_sha256": {"workflow-product.txt": hashlib.sha256(product.read_bytes()).hexdigest()}, "artifacts": [artifact]}
        fixture.model["counterexamples"].append({"id": "component-only", "statement": case["rejected_substitute"],
                                                "evidence_refs": [result_ref]})
        fixture.model["analysis_evidence"] = {"schema_version": 1, "probes": [], "updates": [],
            "outcome_checks": [case], "review_challenges": [{"id": "original-outcome", "original_source_ref": case["source_ref"],
                "normative_source_ref": case["oracle"]["path"], "counterexample_ids": ["component-only"],
                "proof_obligation_ids": [proof], "artifacts": [artifact], "status": "passed", "reviewer_kind": "primary-separate-pass"}]}
    fixture.task = {"task_id": "fixture-task", "operation_id": "fixture-operation", "state": "active",
        "task_class": "standard-task", "problem_model": None, "completion_evidence": None,
        "canonical_owners": ["README.md"], "changed_fact_ids": ["change-1"], "incident_family_id": "workflow-incident",
        "predecessor_task_ids": [], "latest_failed_gate_id": "none", "repair_review_required": False}
    fixture.write_index([])
    draft = target / ".ai/.runtime/drafts/workflow.json"
    draft.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text(json.dumps(fixture.model), encoding="utf-8")
    registration = draft.with_name("registration.json")
    registration.write_text(json.dumps(fixture.task), encoding="utf-8")
    publication = run("publish-task", "--target", target, "--task-id", "fixture-task", "--draft",
                      draft.relative_to(target), "--registration", registration.relative_to(target), "--write")
    fixture.task = json.loads((target / ".ai/assistant/active-tasks.json").read_text())["tasks"][0]
    fixture.close()
    fixture.closure["repository_binding"] = {"kind": "selected-file-snapshot", "binding_state": "final",
        "base_revision": base, "result_revision": fixture.snapshot(["README.md", "workflow-product.txt"]),
        "selected_paths": ["README.md", "workflow-product.txt"],
        "snapshot_sha256": fixture.snapshot(["README.md", "workflow-product.txt"]), "prior_bindings": []}
    fixture.closure["canonical_owners"] = ["README.md"]
    fixture.closure["incident_family_id"] = "workflow-incident"
    fixture.closure["implementation_surfaces"] = ["workflow-product.txt"]
    fixture.write_closure()
    run("archive-task-evidence", "--target", target, "--task-id", "fixture-task",
        "--retention-review", "fixture:explicit-retention-review", "--write")
    approval = approval_record(base, "core")
    approval["approval_id"] = "workflow-repair"
    approval["operation"] = {"id": "fixture-operation", "type": "product-change"}
    approval["scope"].update(allowed_files_or_surfaces=[".ai/**", "README.md", "workflow-product.txt", "evidence/**"],
        excluded_files_or_surfaces=[], allowed_actions_mode="code-and-tests",
        allowed_changed_fact_ids=["change-1"], allowed_behavior_categories=["synthetic-repair"],
        excluded_semantic_effects=["non-fixture product changes"])
    approval_path = target / ".ai/assistant/approvals/workflow-repair.json"
    approval_path.write_text(json.dumps(approval), encoding="utf-8")
    common = ["finalize-support", "--target", target, "--diff-ref", base, "--approval-record", approval_path,
              "--require-current-change", "--task-id", "fixture-task", "--task-class", "standard-task", "--require-task-acceptance"]
    run(*common, "--write", structured=False)
    final = run("validate-adapter", "--target", target, "--framework-source", ROOT,
        "--validation-phase", "acceptance", "--validation-scope", "full", "--approval-archive-mode", "full",
        "--diff-ref", base, "--approval-record", approval_path, "--enforce-approval-scope",
        "--task-id", "fixture-task", "--task-class", "standard-task", "--require-task-acceptance", "--json")
    if final["task_acceptance"]["state"] != "accepted":
        raise AssertionError(final)
    # Probe only after projection reconciliation; stale health must not pass.
    protocol = {}
    for operation in ("status", "doctor"):
        if operation == "doctor":
            arguments = documented_doctor_arguments((ROOT / "docs/core-repair-workflow.md").read_text(encoding="utf-8"), target)
        else:
            arguments = [operation, "--target", target, "--framework-source", ROOT, "--current-task", "fixture-task", "--json"]
        value = run(*arguments)
        if value["target"] != str(target) or value["current_task"]["incident_outcome"]["original_case"]["expected_outcome"] != fixture.model["original_case"]["expected_outcome"]:
            raise AssertionError("documented protocol lost its target or original-case identity")
        if value["current_task"]["repair_preflight"]["next_action"] != "continue-core-repair-with-generic-obligations":
            raise AssertionError("core repair guidance unexpectedly requires optional policy adoption")
        protocol[operation] = value["current_task"]["state"]
    delegate = [sys.executable, str(target / ".ai/assistant/tools/alatyr_delegate.py"), "status",
                "--target", str(target), "--framework-source", str(ROOT), "--current-task", "fixture-task"]
    delegated = subprocess.run(delegate, cwd=target, capture_output=True, text=True, timeout=120)
    if delegated.returncode or "Alatyr adapter health:" not in delegated.stdout:
        raise AssertionError(delegated.stdout + delegated.stderr)
    unsupported = subprocess.run([*delegate, "--json"], cwd=target, capture_output=True, text=True, timeout=120)
    if unsupported.returncode != 2 or "unrecognized arguments: --json" not in unsupported.stderr:
        raise AssertionError("operator protocol no longer matches the installed delegate parser")
    protocol["delegate_status"] = "text-output-verified"
    protocol["unsupported_delegate_json"] = "rejected-use-source-json-route"
    product.write_text("regressed\n", encoding="utf-8")
    blocked = run("validate-adapter", "--target", target, "--framework-source", ROOT,
        "--validation-phase", "acceptance", "--validation-scope", "full", "--diff-ref", base,
        "--approval-record", approval_path, "--enforce-approval-scope", "--task-id", "fixture-task",
        "--task-class", "standard-task", "--require-task-acceptance", "--json", expected=1)
    product.write_text("repaired\n", encoding="utf-8")
    return {"publication": publication, "accepted": final, "stale_result": blocked, "protocol": protocol,
            "outcome_checks_adopted": outcome_checks,
            "optional_policy_created": (target / ".ai/project/testing/test-first-policy.json").exists()}
