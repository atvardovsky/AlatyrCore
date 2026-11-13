"""Canonical bounded model prerequisites, independent of generated projections."""

from __future__ import annotations

from analysis_strategy_contract import required_obligations_resolved, required_reviews_passed


def validate_model_prerequisites(validator, model, source, *, require_completion, frozen=False, current_task=False,
                                 artifact_locations=None, original_source_path=None):
    if model.get("schema_version") == 7:
        from analysis_evidence import evidence_failures, verify_artifacts
        explicit_models = getattr(validator, "problem_models", [])
        # Explicit runtime-model selection cannot gain archive fallback through
        # another task/lineage consumer in the same validation run.
        selected_runtime_model = original_source_path is not None and any(
            validator.rel(path) == original_source_path for path in explicit_models)
        def read(path, limit):
            location = (artifact_locations or {}).get(path, path) if not current_task and not selected_runtime_model else path
            result = validator.context.read_bytes_result(validator.target_path(location), max_bytes=limit)
            if result.value is None:
                raise ValueError(result.error or "missing evidence artifact")
            return result.value
        if not frozen or current_task and require_completion:
            for failure in verify_artifacts(model, read):
                validator.error("ANALYSIS_EVIDENCE_ARTIFACT", failure, source)
        elif "outcome_checks" in model.get("analysis_evidence", {}):
            for failure in verify_artifacts(model, read, historical_outcomes=True):
                validator.error("ANALYSIS_EVIDENCE_ARTIFACT", failure, source)
        for failure in evidence_failures(model, completion=require_completion):
            validator.error("ANALYSIS_EVIDENCE_INVALID", failure, source)
    if require_completion and not required_obligations_resolved(model):
        validator.error("ANALYSIS_REQUIRED_OBLIGATION_OPEN", "selected problem model has unresolved required proof obligations", source)
    if require_completion and not required_reviews_passed(model):
        validator.error("ANALYSIS_REQUIRED_REVIEW_OPEN", "selected problem model has an incomplete required review", source)
