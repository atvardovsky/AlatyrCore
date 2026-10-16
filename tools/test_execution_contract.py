"""Shared, non-executing test-policy and result-evidence invariants."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from path_spec import PathSpec
from yaml import YAMLError
from target_adapter_validation.context import TargetRepositoryView
from target_validation_support import is_placeholder, is_target_relative_path, is_unresolved_value
from yaml_support import safe_load

SCHEMA = Path(__file__).resolve().parents[1] / "schemas/test-execution-contract.schema.json"
BINDING = {"policy": ".ai/project/testing/test-first-policy.json", "timing": "target-policy",
           "red_evidence": "target-policy", "coverage_writes": "canonical-owner"}
SURFACES = (
    ".ai/assistant/skills/test-first-development/SKILL.md",
    ".ai/assistant/flows/test-first-change.flow.md",
    ".ai/assistant/gates/test-first-development.md",
    ".ai/assistant/templates/test-first-evidence.md",
)


def has_placeholders(value: Any) -> bool:
    if isinstance(value, dict):
        return any(has_placeholders(item) for item in value.values())
    if isinstance(value, list):
        return any(has_placeholders(item) for item in value)
    return is_placeholder(value)


class TestExecutionContract:
    __test__ = False

    def __init__(self):
        self.view = TargetRepositoryView(SCHEMA.parent)
        result = self.view.read_json_result(SCHEMA)
        if result.error:
            raise ValueError(result.error)
        self.schema = result.value
        try:
            Draft202012Validator.check_schema(self.schema)
        except SchemaError as exc:
            raise ValueError(f"invalid testing schema: {exc.message}") from exc

    def shape(self, value: Any, definition: str, *, placeholders: bool = False) -> list[str]:
        schema = {"$ref": f"#/$defs/{definition}", "$defs": self.schema["$defs"]}
        failures = []
        for error in Draft202012Validator(schema).iter_errors(value):
            if placeholders and isinstance(error.instance, str) and is_placeholder(error.instance):
                continue
            failures.append("/".join(map(str, error.absolute_path)) + ": " + error.message)
        # JSON Schema treats 1.0 as an integer; version and count contracts do not.
        if isinstance(value, dict):
            version = value.get("schema_version") if definition == "evidence" else value.get("execution_contract", {}).get("schema_version") if isinstance(value.get("execution_contract"), dict) else None
            if type(version) is not int or version != 1:
                failures.append("schema_version must be integer 1")
            if definition == "evidence" and isinstance(value.get("counts"), dict):
                if any(type(n) is not int for n in value["counts"].values()):
                    failures.append("counts must contain integers, not booleans or floats")
        return failures

    def policy_failures(self, policy: Any, *, placeholders: bool = False) -> list[str]:
        failures = self.shape(policy, "policy", placeholders=placeholders)
        if failures or (placeholders and has_placeholders(policy)):
            return failures
        contract = policy["execution_contract"]
        ids = [command["id"] for command in policy["commands"]]
        if len(ids) != len(set(ids)):
            failures.append("command IDs must be unique")
        if contract["canonical_coverage_matrix"] is None and not contract["coverage_not_applicable_reason"]:
            failures.append("non-applicable coverage matrix requires a concrete reason")
        paths = [contract["canonical_policy"], *contract["evidence_records"]]
        if contract["canonical_coverage_matrix"] is not None:
            paths.append(contract["canonical_coverage_matrix"])
        for command in policy["commands"]:
            execution = command["execution"]
            paths.extend(execution["configuration_paths"])
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
        counts, files = record["counts"], record["files"]
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
        if counts["executed"] > 0 and (record["authorization"] != "authorized" or record["availability"] != "available" or not record["prerequisites_satisfied"]):
            failures.append("execution requires current authorization, availability and satisfied prerequisites independently")
        timing = {"before-implementation": "pre-implementation-authorized", "after-manual-review": "manual-review-complete", "explicit-request-only": "explicit-request-authorized"}
        if execution["kind"] == "automated-test" and counts["executed"] > 0 and record["timing_disposition"] != timing[execution_contract["timing"]]:
            failures.append("execution timing disposition does not satisfy the target's review/authorization gate")
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
