"""Shared, non-executing test-policy and result-evidence invariants."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from path_spec import PathSpec, logical_path
from yaml import YAMLError
from target_adapter_validation.context import TargetRepositoryView
from target_validation_support import is_placeholder, is_target_relative_path, is_unresolved_value
from yaml_support import safe_load
from resource_access import resource_failures, effect_resource_failures

SCHEMA = Path(__file__).resolve().parents[1] / "schemas/test-execution-contract.schema.json"
BINDING = {"policy": ".ai/project/testing/test-first-policy.json", "timing": "target-policy",
           "red_evidence": "target-policy", "coverage_writes": "canonical-owner"}
SURFACES = (
    ".ai/assistant/skills/test-first-development/SKILL.md",
    ".ai/assistant/flows/test-first-change.flow.md",
    ".ai/assistant/gates/test-first-development.md",
    ".ai/assistant/templates/test-first-evidence.md",
)

REPAIR_POLICY = ".ai/project/testing/test-first-policy.json"
REPAIR_OBLIGATION = "repair-evidence-review"


def repair_review_capture_failures(model: dict[str, Any], policy: Any, *,
                                   contract: TestExecutionContract | None = None) -> list[str]:
    """Validate optional-policy adoption before retaining its reserved obligation."""
    obligations = [item for item in model.get("proof_obligations", [])
                   if item.get("id") == REPAIR_OBLIGATION]
    if not obligations:
        return []
    failures = []
    if len(obligations) != 1 or obligations[0].get("required") is not True:
        failures.append("reserved repair-evidence-review must be one required obligation")
    if model.get("incident", {}).get("mode") not in {"new", "continuation", "systemic-repair"}:
        failures.append("captured incident review cannot drop its incident identity")
    review = policy.get("repair_review") if isinstance(policy, dict) else None
    if not isinstance(review, dict) or review.get("state") != "enabled":
        failures.append("reserved repair-evidence-review requires explicit enabled repair_review policy; use generic proof obligations for core-only work")
        return failures
    failures.extend((contract or TestExecutionContract()).policy_failures(policy))
    return failures


def has_placeholders(value: Any) -> bool:
    if isinstance(value, dict):
        return any(has_placeholders(item) for item in value.values())
    if isinstance(value, list):
        return any(has_placeholders(item) for item in value)
    return is_placeholder(value)


def policy_projection_failures(projected: Any, canonical: Any) -> list[str]:
    return [] if isinstance(canonical, dict) and projected == canonical else ["adapter policy must equal its canonical project owner; reconcile from the owner, never overwrite it from the mirror"]


def execution_authority_failures(record: dict, execution: dict, contract: dict) -> list[str]:
    """Shared pre/post execution checks; callers validate canonical shapes first."""
    failures = []
    if record["authorization"] != "authorized" or record["availability"] != "available" or not record["prerequisites_satisfied"]:
        failures.append("execution requires current authorization, availability and satisfied prerequisites independently")
    timing = {"before-implementation": "pre-implementation-authorized", "after-manual-review": "manual-review-complete", "explicit-request-only": "explicit-request-authorized"}
    if execution["kind"] == "automated-test" and record["timing_disposition"] != timing[contract["timing"]]:
        failures.append("execution timing disposition does not satisfy the target's review/authorization gate")
    coordination = record["resource_coordination"]
    if any(item["access"] != "read" for item in record["resources"]):
        ref = coordination["evidence_ref"]
        if (coordination["decision"] not in ("serialized", "isolated") or not isinstance(ref, str)
                or not ref.strip() or is_placeholder(ref) or is_unresolved_value(ref)):
            failures.append("executed resource writes require resolved serialization or verified-isolation evidence")
        if coordination["decision"] == "isolated" and any(item["access"] != "read" and
                (item["namespace"] is None or item["isolation"] != "verified-isolated") for item in record["resources"]):
            failures.append("isolated execution requires verified, concrete writable namespaces")
    return failures


def review_execution_request(context, target: Path, brief: dict, action: dict) -> tuple[dict, dict[str, str]]:
    """Use the same policy/evidence invariants as registered target validation."""
    import hashlib
    from cli_inputs import json_object
    from request_values import request_path
    bindings = {}
    def read(path):
        request_path(path)
        result = context.read_bytes_result(target / path, max_bytes=1024 * 1024)
        if result.value is None:
            raise ValueError("required validation input is unavailable: " + path)
        bindings[path] = hashlib.sha256(result.value).hexdigest()
        return result.value
    policy = json_object(read(REPAIR_POLICY), REPAIR_POLICY)
    contract = TestExecutionContract()
    failures = contract.policy_failures(policy)
    if failures:
        raise ValueError("; ".join(failures[:8]))
    owner = policy["execution_contract"]["canonical_policy"]
    canonical = json_object(read(owner), owner)
    if policy_projection_failures(policy, canonical):
        raise ValueError("testing policy differs from its canonical owner")
    run = action["validation"]
    command = next((row for row in policy["commands"] if row["id"] == run["command_id"]), None)
    if command is None:
        raise ValueError("validation command_id is not registered")
    execution = command["execution"]
    if (execution["environment"] not in {"none", "disposable"} or
            not set(execution["effects"]) <= {"temporary-files", "disposable-db-writes"}):
        raise ValueError("external/shared services, network, installation and service startup require their separately authorized project-owned route")
    argv = command.get("argv")
    if (not isinstance(argv, list) or not 1 <= len(argv) <= 128 or
            any(not isinstance(part, str) or not part or len(part) > 4096 or "\0" in part for part in argv)):
        raise ValueError("registered validation requires an explicit bounded argv vector")
    path = run["execution_evidence"]
    record = json_object(read(path), path)
    failures = contract.evidence_failures(record, command, policy["execution_contract"])
    if failures:
        raise ValueError("; ".join(failures[:8]))
    failures = execution_authority_failures(record, command["execution"], policy["execution_contract"])
    if failures:
        raise ValueError("; ".join(failures))
    if (record["command_id"] != run["command_id"] or record["authorization_source"] != brief["source_ref"]
            or record["policy_sha256"] != bindings[owner]):
        raise ValueError("pre-run evidence must bind the current command, request source and canonical policy")
    if (record["state"] not in {"authored", "discovered"} or record["claim"] != "none"
            or record["counts"]["executed"] != 0 or record["result_artifact"] is not None):
        raise ValueError("pre-run evidence cannot claim a future execution or reuse a prior passed run")
    from target_validation_support import GitEvidenceView
    if record["repository_revision"] != GitEvidenceView(target).resolve_ref("HEAD"):
        raise ValueError("pre-run evidence repository revision is stale")
    required = set(command["execution"].get("harness_inputs", []))
    if not required <= record["input_sha256"].keys():
        raise ValueError("pre-run evidence must bind every declared harness input")
    if len(record["input_sha256"]) > 128:
        raise ValueError("pre-run evidence exceeds 128 input bindings")
    for selected, expected in record["input_sha256"].items():
        if hashlib.sha256(read(selected)).hexdigest() != expected:
            raise ValueError("pre-run evidence input is stale: " + selected)
    if command["execution"]["suite_scope"] == "full" and run["scope"] != "broad":
        raise ValueError("a full registered suite must consume the broad-run budget")
    return {"command_id": command["id"], "argv": argv, "kind": command["execution"]["kind"],
            "input_sha256": bindings, "authorization_provenance": "caller-declared-not-authenticated"}, bindings


class TestExecutionContract:
    __test__ = False

    def __init__(self):
        self.view = TargetRepositoryView(SCHEMA.parent)
        result = self.view.read_json_result(SCHEMA)
        if result.error:
            raise ValueError(result.error)
        self.schema = result.value
        self._repair_schema = None
        self._legacy_schemas = {}
        try:
            Draft202012Validator.check_schema(self.schema)
        except SchemaError as exc:
            raise ValueError(f"invalid testing schema: {exc.message}") from exc

    def repair_schema(self) -> dict[str, Any]:
        if self._repair_schema is None:
            read = self.view.read_json_result(SCHEMA.with_name("repair-review.schema.json"))
            if read.error:
                raise ValueError(read.error)
            Draft202012Validator.check_schema(read.value)
            self._repair_schema = read.value
        return self._repair_schema

    def shape(self, value: Any, definition: str, *, placeholders: bool = False) -> list[str]:
        try:
            owner = self.repair_schema() if definition in {"repair_policy", "repair_evidence"} else self.schema
            version = (value.get("schema_version") if definition == "evidence" else
                       value.get("execution_contract", {}).get("schema_version") if isinstance(value.get("execution_contract"), dict) else None) if isinstance(value, dict) else None
            if definition in {"policy", "evidence"} and type(version) is int and version in (2, 3):
                if version not in self._legacy_schemas:
                    read = self.view.read_json_result(SCHEMA.with_name(f"test-execution-contract-v{version}.schema.json"))
                    if read.error:
                        return ["legacy execution schema is unavailable: " + read.error]
                    Draft202012Validator.check_schema(read.value)
                    self._legacy_schemas[version] = read.value
                owner = self._legacy_schemas[version]
        except (OSError, ValueError, SchemaError) as exc:
            return [f"repair schema is unavailable or invalid: {exc}"]
        schema = {"$ref": f"#/$defs/{definition}", "$defs": owner["$defs"]}
        failures = []
        for error in Draft202012Validator(schema).iter_errors(value):
            if placeholders and isinstance(error.instance, str) and is_placeholder(error.instance):
                continue
            failures.append("/".join(map(str, error.absolute_path)) + ": " + error.message)
        # JSON Schema treats 1.0 as an integer; version and count contracts do not.
        if isinstance(value, dict):
            repair = definition in {"repair_evidence", "repair_policy"}
            version = value.get("schema_version") if definition == "evidence" or repair else value.get("execution_contract", {}).get("schema_version") if isinstance(value.get("execution_contract"), dict) else None
            versions = (1, 2) if repair else (2, 3, 4)
            if type(version) is not int or version not in versions:
                failures.append(f"execution/evidence schema_version must be an integer in {versions}")
            if definition == "evidence" and isinstance(value.get("counts"), dict):
                if any(type(n) is not int for n in value["counts"].values()):
                    failures.append("counts must contain integers, not booleans or floats")
        return failures

    def policy_failures(self, policy: Any, *, placeholders: bool = False) -> list[str]:
        failures = self.shape(policy, "policy", placeholders=placeholders)
        if failures or (placeholders and has_placeholders(policy)):
            return failures
        if "repair_review" in policy:
            from repair_review import policy_failures
            try:
                failures.extend(policy_failures(policy["repair_review"], policy, self.repair_schema()))
            except (OSError, ValueError, SchemaError) as exc:
                return [f"repair schema is unavailable or invalid: {exc}"]
        contract = policy["execution_contract"]
        historical = contract.get("historical_evidence_records", [])
        if "historical_evidence_records" in contract and contract["schema_version"] != 4:
            return ["historical evidence selection requires execution schema 4; old records need no rewrite"]
        historical_paths = [row["path"] for row in historical]
        if len(historical_paths) != len(set(historical_paths)) or set(historical_paths) & set(contract["evidence_records"]):
            failures.append("historical evidence paths must be unique and disjoint from selected current evidence")
        for path in historical_paths:
            try:
                logical_path(path)
            except ValueError as exc:
                failures.append(f"historical evidence requires exact normalized paths: {exc}")
        from testing_controls import policy_control_failures
        failures.extend(policy_control_failures(policy))
        if failures:
            return failures
        ids = [command["id"] for command in policy["commands"]]
        if len(ids) != len(set(ids)):
            failures.append("command IDs must be unique")
        if contract["canonical_coverage_matrix"] is None and not contract["coverage_not_applicable_reason"]:
            failures.append("non-applicable coverage matrix requires a concrete reason")
        paths = [contract["canonical_policy"], *contract["evidence_records"], *historical_paths]
        additional = contract.get("additional_evidence_templates", [])
        paths.extend(additional)
        if set(additional) & set(SURFACES):
            failures.append("additional evidence templates must not duplicate built-in test surfaces")
        if any(not path.endswith(".md") for path in additional):
            failures.append("additional evidence templates must be exact Markdown file paths")
        for path in additional:
            try:
                logical_path(path)
            except ValueError as exc:
                failures.append(f"additional evidence template: {exc}")
        if contract["canonical_coverage_matrix"] is not None:
            paths.append(contract["canonical_coverage_matrix"])
        for command in policy["commands"]:
            execution = command["execution"]
            resource_errors = resource_failures(execution["resources"])
            failures.extend(f"{command['id']}: {failure}" for failure in resource_errors)
            if not resource_errors:
                failures.extend(f"{command['id']}: {failure}" for failure in effect_resource_failures(execution["effects"], execution["resources"]))
            paths.extend(execution["configuration_paths"])
            paths.extend(execution.get("harness_inputs", []))
            if execution["kind"] == "automated-test" and not execution["suite_patterns"]:
                failures.append(f"{command['id']}: automated tests need target-owned suite patterns")
            for pattern in execution["suite_patterns"]:
                try:
                    PathSpec(pattern)
                except ValueError as exc:
                    failures.append(f"{command['id']}: invalid suite pattern: {exc}")
            if execution["kind"] in {"metadata-check", "static-analysis"} and execution["proof_boundary"] != "static-metadata":
                failures.append(f"{command['id']}: static commands cannot declare behavioral proof")
            expected_environment = {"disposable-db-writes": "disposable", "shared-db-writes": "shared-review"}
            for effect, environment in expected_environment.items():
                if effect in execution["effects"] and execution["environment"] != environment:
                    failures.append(f"{command['id']}: {effect} requires environment {environment}")
            if execution["kind"] == "automated-test" and execution["proof_boundary"] == "manual":
                failures.append(f"{command['id']}: automated tests cannot declare manual proof")
        if any(not is_target_relative_path(p) for p in paths):
            failures.append("policy, matrix, configuration and evidence paths must be contained target-relative paths")
        command_texts = [
            text for command in policy["commands"] for text in [
                *command["execution"]["prerequisites"],
                *command["execution"]["suite_patterns"],
                command["execution"]["filtering"]["syntax_or_reason"],
            ]
        ]
        for text in [contract["review_authority"], contract["coverage_not_applicable_reason"], *paths, *command_texts]:
            if isinstance(text, str) and (is_placeholder(text) or is_unresolved_value(text)):
                failures.append("execution contract contains an unresolved owner, reason or path")
        return failures

    def evidence_failures(self, record: Any, command: dict[str, Any], execution_contract: dict[str, Any]) -> list[str]:
        failures = self.shape(record, "evidence")
        if failures:
            return failures
        execution = command["execution"]
        from testing_controls import record_control_failures
        failures.extend(record_control_failures(record, command, execution_contract))
        failures.extend(resource_failures(record["resources"]))
        if failures:
            return failures
        resource_key = lambda item: (item["kind"], item["id"], item["namespace"] or "", item["access"], item["isolation"])
        if sorted(record["resources"], key=resource_key) != sorted(execution["resources"], key=resource_key):
            failures.append("observed resources must match the selected command contract")
        counts, files = record["counts"], record["files"]
        if counts["executed"] > 0:
            failures.extend(execution_authority_failures(record, execution, execution_contract))
        if counts["executed"] != counts["passed"] + counts["failed"] or counts["discovered"] != counts["executed"] + counts["skipped"] + counts.get("not_run", 0):
            failures.append("test counts do not conserve discovered, executed, passed, failed, skipped and not_run cases")
        if record["proof_boundary"] != execution["proof_boundary"]:
            failures.append("evidence cannot broaden the command's proof boundary")
        if record["environment"] != execution["environment"]:
            failures.append("observed environment must match the selected command contract")
        if is_placeholder(record["authorization_source"]) or is_unresolved_value(record["authorization_source"]):
            failures.append("authorization source must be resolved, not an assertion of availability")
        if record["filter"] is not None and execution["filtering"]["state"] != "supported":
            failures.append("unsupported or unknown filtering cannot be used or silently broadened")
        if record["state"] in {"authored", "discovered", "skipped", "blocked"} and (counts["executed"] or record["claim"] != "none"):
            failures.append("unexecuted or blocked states cannot claim executed proof")
        if record["state"] == "passed" and (counts["executed"] == 0 or counts["failed"]):
            failures.append("passed requires observed execution with zero failed cases")
        if record["state"] == "failed" and counts["failed"] == 0:
            failures.append("failed requires a failed case")
        behavioral = record["claim"] in {"focused", "suite", "full"}
        if behavioral and (record["state"] != "passed" or execution["kind"] != "automated-test" or record["proof_boundary"] == "static-metadata"):
            failures.append("behavioral claims require passed automated tests, not metadata or discovery")
        selected, executed, universe = map(set, (files["selected"], files["executed"], files["universe"]))
        excluded = [item["path"] for item in files["excluded"]]
        if any(is_placeholder(item["reason"]) or is_unresolved_value(item["reason"]) for item in files["excluded"]):
            failures.append("excluded files require concrete resolved reasons")
        if len(excluded) != len(set(excluded)) or selected & set(excluded) or not executed <= selected:
            failures.append("file selection, execution and exclusions are inconsistent")
        if record["claim"] in {"suite", "full"} and (not universe or selected | set(excluded) != universe or executed != selected):
            failures.append("suite claims require a reconciled universe and execution of all selected files")
        if record["claim"] == "full" and (excluded or counts["skipped"] or counts.get("not_run", 0) or record["filter"] is not None or execution["suite_scope"] != "full"):
            failures.append("full coverage cannot exclude, skip or filter cases or use a partial command")
        if record["claim"] == "full" and execution["proof_boundary"] in {"mocked-interface", "browser-mocked", "manual", "static-metadata"}:
            failures.append("mocked, manual or static evidence must retain its narrower proof claim")
        if behavioral and not executed:
            failures.append("behavioral claims require executed files")
        if execution["kind"] == "automated-test" and bool(counts["executed"]) != bool(executed):
            failures.append("executed test counts and executed file evidence must agree")
        if counts["executed"] > 0 and record["result_artifact"] is None:
            failures.append("executed tests require a digest-bound result artifact")
        required = set(execution["configuration_paths"]) | selected
        if execution_contract["canonical_coverage_matrix"] is not None:
            required.add(execution_contract["canonical_coverage_matrix"])
        if not required <= set(record["input_sha256"]):
            failures.append("input hashes must bind selected tests and configuration files")
        if any(record["input_sha256"].get(path) is None for path in required):
            failures.append("selected tests, configuration and coverage owner require content hashes, not absence markers")
        paths = [*record["input_sha256"], *selected, *executed, *universe, *excluded]
        if record["result_artifact"]:
            paths.append(record["result_artifact"]["path"])
        if any(not is_target_relative_path(path) for path in paths):
            failures.append("evidence paths must be contained target-relative paths")
        return failures


def surface_binding_failures(text: str) -> list[str]:
    text = text.removeprefix("\ufeff").replace("\r\n", "\n")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return ["missing test execution policy binding"]
    try:
        metadata = safe_load(text.split("\n---\n", 1)[0][4:])
    except (YAMLError, ValueError, TypeError) as exc:
        return [f"invalid policy binding: {exc}"]
    return [] if isinstance(metadata, dict) and metadata.get("alatyr_test_execution") == BINDING else ["test surface must defer timing, RED and coverage writes to canonical target policy"]
