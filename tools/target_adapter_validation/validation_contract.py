"""Validate target-local checker coverage and canonical-result boundaries."""

from __future__ import annotations

import ast
import contextlib
import io
import json
import re
import runpy
import shlex
from functools import lru_cache
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Protocol

import jsonschema

from target_validation_support import is_placeholder
from task_acceptance_binding import task_arguments
from validation_route_contract import validation_route_failures
from target_validation_support import is_target_relative_path


CONTRACT_PATH = ".ai/assistant/validation-contract.json"
VALIDATION_CONTRACT_SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "schemas/alatyr-validation-contract.schema.json"
)
ENTRYPOINTS = ("adapter-health", "current-change", "archive-audit")
DELEGATE_PATH = ".ai/assistant/tools/alatyr_delegate.py"
SOURCE_DELEGATE_PATH = (
    Path(__file__).resolve().parents[2]
    / "templates/target/.ai/assistant/tools/alatyr_delegate.py"
)
PYTHON_LAUNCHER = re.compile(
    r"^(?:python(?:3(?:\.\d+)?)?|py)(?:\.exe)?$",
    re.IGNORECASE,
)
PY_LAUNCHER = re.compile(r"^py(?:\.exe)?$", re.IGNORECASE)
PY_VERSION_SELECTOR = re.compile(r"^-\d+(?:\.\d+)?$")
SHELL_CONTROL = re.compile(
    r"(?:[;&|<>`$*?]|[\r\n#]|%[A-Za-z_][A-Za-z0-9_]*%|![A-Za-z_][A-Za-z0-9_]*!)"
)
REQUIRED_PREFIX_BINDINGS = {
    "validate-current": (
        ("--diff-ref", "ALATYR_CONTRACT_DIFF_REF"),
        ("--approval-record", ".ai/assistant/approvals/ALATYR_CONTRACT.json"),
        ("--change-package", ".ai/assistant/change-packages/ALATYR_CONTRACT.json"),
    ),
}
DELEGATE_PATH_FIELDS = (
    "target", "framework_source", "approval_record", "change_package", "problem_model",
)
EXPECTED_DELEGATES = {
    "adapter-health": {
        "delegate_operation": "status",
        "operation": "status",
        "validation_phase": "not-applicable",
        "validation_scope": "not-applicable",
        "approval_archive_mode": "not-applicable",
        "requires_diff_ref": False,
        "requires_approval_records": False,
        "requires_change_packages": False,
    },
    "current-change": {
        "delegate_operation": "validate-current",
        "operation": "validate-adapter",
        "validation_phase": "acceptance",
        "validation_scope": "full",
        "approval_archive_mode": "full",
        "requires_diff_ref": True,
        "requires_approval_records": True,
        "requires_change_packages": True,
    },
    "archive-audit": {
        "delegate_operation": "archive-audit",
        "operation": "validate-adapter",
        "validation_phase": "acceptance",
        "validation_scope": "full",
        "approval_archive_mode": "full",
        "requires_diff_ref": False,
        "requires_approval_records": False,
        "requires_change_packages": False,
    },
}


class FindingSink(Protocol):
    allow_placeholders: bool

    def target_path(self, relpath: str) -> Path: ...
    def is_target_file(self, relpath: str | Path) -> bool: ...
    def read_text(self, path: Path) -> str: ...
    def load_json_object(self, path: Path, code_prefix: str) -> dict[str, Any] | None: ...
    def error(self, code: str, message: str, path: str | None = None) -> None: ...
    def warn(self, code: str, message: str, path: str | None = None) -> None: ...
    def info(self, code: str, message: str, path: str | None = None) -> None: ...


def _option_count(arguments: list[str], option: str) -> int:
    return sum(
        token == option or token.startswith(f"{option}=")
        for token in arguments
    )


def _machine_local_path(value: Any) -> bool:
    text = str(value)
    return (
        PurePosixPath(text).is_absolute()
        or bool(PureWindowsPath(text).anchor)
        or text.startswith("~")
    )


def _delegate_uses_machine_paths(parsed: Any) -> bool:
    for field in DELEGATE_PATH_FIELDS:
        supplied = getattr(parsed, field, None)
        values = supplied if isinstance(supplied, list) else [supplied]
        if any(value is not None and _machine_local_path(value) for value in values):
            return True
    return False


@lru_cache(maxsize=1)
def _shipped_delegate_parser_factory() -> Any:
    namespace = runpy.run_path(
        str(SOURCE_DELEGATE_PATH),
        run_name="_alatyr_shipped_delegate_contract",
    )
    factory = namespace.get("build_parser")
    if not callable(factory):
        raise ValueError("shipped delegate does not expose build_parser()")
    return factory


def _shipped_delegate_parser_failure(
    arguments: list[str],
    *,
    expected_operation: str,
) -> tuple[Any | None, str | None]:
    completed = list(arguments)
    for option, placeholder in REQUIRED_PREFIX_BINDINGS.get(
        expected_operation, ()
    ):
        if _option_count(completed, option) == 0:
            completed.extend([option, placeholder])
    if expected_operation == "validate-current" and "--require-task-acceptance" in completed:
        for option, placeholder in (("--task-id", "ALATYR_CONTRACT_TASK"), ("--task-class", "standard-task")):
            if _option_count(completed, option) == 0:
                completed.extend([option, placeholder])

    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        parser = _shipped_delegate_parser_factory()()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            parsed = parser.parse_args(completed)
        task_arguments(task_id=getattr(parsed, "task_id", None), task_class=getattr(parsed, "task_class", None), required=getattr(parsed, "require_task_acceptance", False))
    except SystemExit as exc:
        output = stderr.getvalue() or stdout.getvalue()
        detail = output.strip().splitlines()[-1] if output.strip() else "no diagnostic"
        return None, f"exit {exc.code}: {detail}"
    except ValueError as exc:
        return None, str(exc)
    except Exception as exc:  # fail closed if the trusted parser cannot be evaluated
        return None, f"internal failure: {exc}"
    return parsed, None


def _direct_delegate_invocation_failures(
    command: str,
    *,
    entrypoint: str,
    expected_operation: str,
) -> list[tuple[str, str]]:
    if SHELL_CONTROL.search(command):
        return [
            (
                "VALIDATION_CONTRACT_DELEGATE_ARGUMENTS",
                f"{entrypoint} canonical command must not contain shell composition or comments",
            )
        ]
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return [
            (
                "VALIDATION_CONTRACT_DELEGATE_COMMAND",
                f"{entrypoint} canonical command cannot be parsed: {exc}",
            )
        ]
    if not tokens or not PYTHON_LAUNCHER.fullmatch(tokens[0]):
        return [
            (
                "VALIDATION_CONTRACT_DELEGATE_COMMAND",
                f"{entrypoint} canonical command must directly invoke the delegate with Python",
            )
        ]

    position = 1
    if PY_LAUNCHER.fullmatch(tokens[0]) and position < len(tokens):
        if PY_VERSION_SELECTOR.fullmatch(tokens[position]):
            position += 1
    if position >= len(tokens) or tokens[position] != DELEGATE_PATH:
        return [
            (
                "VALIDATION_CONTRACT_DELEGATE_COMMAND",
                f"{entrypoint} canonical command must execute {DELEGATE_PATH} directly",
            )
        ]
    position += 1
    selected_operation = tokens[position] if position < len(tokens) else None
    if selected_operation != expected_operation:
        actual = selected_operation if selected_operation is not None else "missing"
        return [
            (
                "VALIDATION_CONTRACT_DELEGATE_OPERATION",
                f"{entrypoint} must select delegate operation {expected_operation}, got {actual}",
            )
        ]
    position += 1
    delegate_arguments = tokens[position - 1 :]
    parsed, parser_failure = _shipped_delegate_parser_failure(
        delegate_arguments,
        expected_operation=expected_operation,
    )
    if parser_failure is not None:
        return [
            (
                "VALIDATION_CONTRACT_DELEGATE_ARGUMENTS",
                f"{entrypoint} canonical command is rejected by the shipped "
                f"delegate parser ({parser_failure})",
            )
        ]

    failures: list[tuple[str, str]] = []
    if _delegate_uses_machine_paths(parsed):
        failures.append((
            "VALIDATION_CONTRACT_ABSOLUTE_PATH",
            f"{entrypoint} command contains machine-local absolute paths",
        ))
    if _option_count(delegate_arguments, "--target") != 1 or str(parsed.target) != ".":
        failures.append((
            "VALIDATION_CONTRACT_DELEGATE_ARGUMENTS",
            f"{entrypoint} canonical command must contain exactly one --target . binding",
        ))
    single_value_options = {"--target", "--framework-source", "--diff-ref", "--task-id", "--task-class"}
    duplicates = sorted(
        option
        for option in single_value_options
        if _option_count(delegate_arguments, option) > 1
    )
    if duplicates:
        failures.append((
            "VALIDATION_CONTRACT_DELEGATE_ARGUMENTS",
            f"{entrypoint} canonical command repeats single-value options: {', '.join(duplicates)}",
        ))
    return failures


def _delegate_implementation_failure(
    sink: FindingSink,
    target_delegate: Path,
) -> str | None:
    if not sink.is_target_file(target_delegate):
        return "installed canonical delegate is unavailable"
    if target_delegate.is_symlink():
        return "installed canonical delegate must not be a symbolic link"
    target_text = sink.read_text(target_delegate)
    try:
        source_text = SOURCE_DELEGATE_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return f"source canonical delegate is unavailable: {exc}"
    try:
        target_tree = ast.dump(ast.parse(target_text), include_attributes=False)
    except SyntaxError as exc:
        return f"installed canonical delegate is not valid Python: {exc.msg}"
    try:
        source_tree = ast.dump(ast.parse(source_text), include_attributes=False)
    except SyntaxError as exc:  # pragma: no cover - source checks own this invariant
        return f"source canonical delegate is not valid Python: {exc.msg}"
    if target_tree != source_tree:
        return (
            "installed canonical delegate semantics differ from the shipped source; "
            "use target-equivalent coverage for a reviewed custom implementation"
        )
    return None


def validate_validation_contract(sink: FindingSink, manifest: Any) -> None:
    if manifest is not None:
        pointer = manifest.scalars.get(("validation", "contract"))
        if pointer is not None and pointer.value != CONTRACT_PATH:
            sink.error(
                "VALIDATION_CONTRACT_POINTER",
                f"manifest validation.contract must be {CONTRACT_PATH}",
                ".ai/alatyr.yaml",
            )
    contract = sink.load_json_object(
        sink.target_path(CONTRACT_PATH), "VALIDATION_CONTRACT"
    )
    if contract is None:
        return
    try:
        schema = json.loads(VALIDATION_CONTRACT_SCHEMA.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        sink.error(
            "VALIDATION_CONTRACT_SCHEMA",
            str(exc),
            str(VALIDATION_CONTRACT_SCHEMA),
        )
        return
    try:
        jsonschema.validate(contract, schema)
    except jsonschema.ValidationError as exc:
        sink.error(
            "VALIDATION_CONTRACT_SCHEMA",
            exc.message,
            CONTRACT_PATH,
        )
        return

    schema_version = contract["schema_version"]
    validate_profile_validation_routes(sink, manifest, contract)
    entrypoints = contract["entrypoints"]
    canonical_coverage = any(
        entrypoints[entrypoint]["coverage"] == "canonical-delegate"
        for entrypoint in ENTRYPOINTS
    )
    if schema_version >= 2 and canonical_coverage:
        implementation_failure = _delegate_implementation_failure(
            sink,
            sink.target_path(DELEGATE_PATH),
        )
        if implementation_failure is not None:
            sink.error(
                "VALIDATION_CONTRACT_DELEGATE_CONTENT",
                implementation_failure,
                DELEGATE_PATH,
            )
    structural_only: list[str] = []
    for operation in ENTRYPOINTS:
        entry = entrypoints[operation]
        command = entry["command"]
        coverage = entry["coverage"]
        if is_placeholder(command):
            report = sink.warn if sink.allow_placeholders else sink.error
            report(
                "VALIDATION_CONTRACT_COMMAND_UNRESOLVED",
                f"{operation} command is unresolved",
                CONTRACT_PATH,
            )
        try:
            command_tokens = shlex.split(command)
        except ValueError:
            command_tokens = []
        # Canonical commands use parsed values below; unknown local checkers
        # retain lexical portability checks without pretending to parse their CLI.
        absolute_tokens = [] if schema_version >= 2 and coverage == "canonical-delegate" else [
            token for token in command_tokens
            if _machine_local_path(token.partition("=")[2]
                                   if token.startswith("--") and "=" in token else token)
        ]
        if absolute_tokens:
            sink.error(
                "VALIDATION_CONTRACT_ABSOLUTE_PATH",
                f"{operation} command contains machine-local absolute paths",
                CONTRACT_PATH,
            )
        if schema_version == 1:
            if coverage == "canonical-delegate" and "validate_target_adapter" not in command:
                sink.error(
                    "VALIDATION_CONTRACT_FALSE_CANONICAL_CLAIM",
                    f"{operation} claims canonical delegation without naming the canonical validator",
                    CONTRACT_PATH,
                )
        else:
            delegate = entry.get("canonical_delegate")
            if coverage == "canonical-delegate":
                expected = EXPECTED_DELEGATES[operation]
                for code, message in _direct_delegate_invocation_failures(
                    command,
                    entrypoint=operation,
                    expected_operation=str(expected["delegate_operation"]),
                ):
                    sink.error(
                        code,
                        message,
                        CONTRACT_PATH,
                    )
                if not isinstance(delegate, dict):
                    sink.error(
                        "VALIDATION_CONTRACT_DELEGATE_MISSING",
                        f"{operation} canonical delegation requires structured delegate metadata",
                        CONTRACT_PATH,
                    )
                else:
                    expected_metadata = {
                        key: value
                        for key, value in expected.items()
                        if key != "delegate_operation"
                    }
                    drift = sorted(
                        key
                        for key, value in expected_metadata.items()
                        if delegate.get(key) != value
                    )
                    if drift:
                        sink.error(
                            "VALIDATION_CONTRACT_DELEGATE_DRIFT",
                            f"{operation} canonical delegate differs for: {', '.join(drift)}",
                            CONTRACT_PATH,
                        )
            elif delegate is not None:
                sink.error(
                    "VALIDATION_CONTRACT_DELEGATE_UNCLAIMED",
                    f"{operation} has canonical delegate metadata without canonical-delegate coverage",
                    CONTRACT_PATH,
                )
        if coverage in {"structural-only", "manual"}:
            structural_only.append(operation)
        if entry["final_evidence_eligible"] and coverage not in {
            "canonical-delegate",
            "target-equivalent",
        }:
            sink.error(
                "VALIDATION_CONTRACT_FINAL_EVIDENCE",
                f"{operation} cannot be final-evidence eligible with {coverage} coverage",
                CONTRACT_PATH,
            )

    if structural_only:
        sink.warn(
            "VALIDATION_CONTRACT_LIMITED",
            "target-local validation is not canonical for: "
            + ", ".join(structural_only),
            CONTRACT_PATH,
        )
    if schema_version == 1:
        sink.warn(
            "VALIDATION_CONTRACT_LEGACY",
            "schema version 1 cannot prove canonical delegation structurally; migrate to version 2",
            CONTRACT_PATH,
        )
    sink.info(
        "VALIDATION_CONTRACT_CHECKED",
        "target-local validation coverage is explicit; local success is not canonical success",
        CONTRACT_PATH,
    )


__all__ = ["validate_validation_contract"]


def validate_profile_validation_routes(sink: FindingSink, manifest: Any, contract: dict[str, Any]) -> None:
    router_path = ".ai/assistant/context-router.json"
    if not sink.is_target_file(router_path):
        return  # The router stage owns missing-router diagnostics.
    router = sink.load_json_object(sink.target_path(router_path), "VALIDATION_ROUTE_ROUTER")
    if not isinstance(router, dict):
        return
    required = False
    if manifest is not None:
        scalar = manifest.scalars.get(("schema_version",))
        required = scalar is not None and scalar.value.isdigit() and int(scalar.value) >= 76
    entry = router.get("profile_index", {}).get("framework-upgrade") if isinstance(router.get("profile_index"), dict) else None
    path = entry.get("descriptor") if isinstance(entry, dict) else None
    if path is not None:
        if not isinstance(path, str) or "\\" in path or not is_target_relative_path(path) or not sink.is_target_file(path):
            sink.error("VALIDATION_ROUTE_PROFILE", "framework-upgrade descriptor is missing or unsafe", router_path)
            return
        profile = sink.load_json_object(sink.target_path(path), "VALIDATION_ROUTE_PROFILE")
    else:
        profiles = router.get("profiles")
        profile = profiles.get("framework-upgrade") if isinstance(profiles, dict) else None
        path = router_path
    if not isinstance(profile, dict) or "validation_entrypoints" not in profile:
        if required:
            sink.error("VALIDATION_ROUTE_MISSING", "framework-upgrade requires typed inspection and completion entrypoints", path)
        return
    for failure in validation_route_failures(profile["validation_entrypoints"], contract):
        sink.error("VALIDATION_ROUTE_INVALID", failure, path)
