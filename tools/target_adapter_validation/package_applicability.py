"""Shared selected-task package applicability; no validator construction or execution."""

from __future__ import annotations

def package_requirement(validator, *, module_enabled: bool, automatic: bool,
                        explicit: bool = False) -> dict:
    """Classify applicability once; capability enablement alone proves no exemption."""
    explicit = explicit or bool(validator.change_packages)
    result = {"required": explicit or module_enabled and automatic,
              "reason": "explicit package enforcement" if explicit else "enabled current-change default",
              "exemption": None, "failures": []}
    if explicit or not automatic or not module_enabled or not validator.current_task_id:
        return result
    raw_index = validator.context.read_bytes_result(validator.target_path(".ai/assistant/active-tasks.json"),
                                                    max_bytes=512 * 1024).value
    if raw_index is None:
        return result
    from inspect_session_context import json_object
    try:
        index = json_object(raw_index, "package applicability task index")
    except (ValueError, RecursionError):
        return result
    if not isinstance(index, dict) or not isinstance(index.get("tasks"), list):
        return result
    tasks = [row for row in index["tasks"] if isinstance(row, dict) and row.get("task_id") == validator.current_task_id]
    if len(tasks) != 1 or not isinstance(tasks[0].get("problem_model"), dict):
        return result
    from target_adapter_validation.active_tasks import _bound_object
    model = _bound_object(validator, tasks[0]["problem_model"], "package applicability model")
    if not isinstance(model, dict) or not isinstance(model.get("analysis_evidence"), dict):
        return result
    if "package_applicability" not in model["analysis_evidence"]:
        return result
    claim = model["analysis_evidence"]["package_applicability"]
    try:
        if not validator.require_task_acceptance or validator.current_task_class != tasks[0].get("task_class"):
            raise ValueError("package exemption requires explicit selected task class and named-task acceptance")
        from current_task_view import current_task_view
        initial_findings = len(validator.findings)
        selected = current_task_view(validator, validator.current_task_id)
        if selected["state"] != "bound-recorded-disposition":
            raise ValueError("package exemption requires a current valid selected task: "
                             + "; ".join(selected["diagnostics"][:4]))
        if selected.get("evidence_readiness", {}).get("state") == "stale-or-unavailable":
            raise ValueError("package exemption evidence is stale or unavailable")
        if any(item.level == "error" for item in validator.findings[initial_findings:]):
            raise ValueError("package exemption selected-task validation has errors")
        if len(model["changed_facts"]) != 1 or len(tasks[0]["changed_fact_ids"]) != 1:
            raise ValueError("package exemption requires exactly one actual declared changed fact")
        if any(claim["activation"].values()):
            raise ValueError("a positive package activation condition defeats the local-task exemption")
        if claim["router"]["path"] != ".ai/assistant/context-router.json":
            raise ValueError("package exemption must bind the canonical target context router")
        from delivery_receipts import read_bound
        from analysis_evidence import MAX_ARTIFACT_BYTES
        for key in ("router", "ordinary_result", "profile"):
            if claim.get(key) is not None:
                read_bound(validator.context, validator.target, claim[key], {}, limit=MAX_ARTIFACT_BYTES)
        router = validator.context.read_json_result(validator.target_path(claim["router"]["path"])).value
        if not isinstance(router, dict):
            raise ValueError("package exemption requires a valid bound target router")
        initial_findings = len(validator.findings)
        descriptors = {}
        profiles = validator.router_profiles(router, selected_profile=claim["profile_id"], descriptor_bindings=descriptors)
        if any(item.level == "error" for item in validator.findings[initial_findings:]):
            raise ValueError("package exemption selected profile descriptor is invalid")
        if claim["profile_id"] not in profiles:
            raise ValueError("package exemption profile is absent from the bound target router")
        if claim["profile_id"] in descriptors:
            descriptor = descriptors[claim["profile_id"]]
            if claim.get("profile") is None or claim["profile"]["path"] != descriptor:
                raise ValueError("package exemption must bind its selected profile descriptor")
        elif claim.get("profile") is not None:
            raise ValueError("legacy inline profile exemption must use null profile binding")
        result.update(required=False, reason=claim["reason"], exemption={
            "task_id": validator.current_task_id, "model": tasks[0]["problem_model"],
            "profile_id": claim["profile_id"], "project_area": claim["project_area"],
            "changed_fact_id": tasks[0]["changed_fact_ids"][0],
            "scope_truth": "primary-semantic-review-required"})
    except (OSError, ValueError, RecursionError) as exc:
        result["failures"].append(str(exc))
    return result
