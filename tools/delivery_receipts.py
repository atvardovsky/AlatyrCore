"""Integrity and duration of recorded command runs, not test acceptance or execution."""

from __future__ import annotations

import math
from datetime import datetime
import hashlib

from inspect_session_context import json_object
from request_values import fields, request_path, text


MAX_RECORD_BYTES = 65536


def timestamp(value: object, label: str) -> float:
    text(value, label, 64)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone required")
        return parsed.timestamp()
    except (ValueError, OverflowError, OSError) as exc:
        raise ValueError(label + " requires a valid offset-aware timestamp") from exc


def sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(label + " requires lowercase SHA-256")
    return value


def artifact(value: object, label: str) -> dict:
    result = fields(value, {"path", "sha256"}, label)
    request_path(result["path"])
    sha256(result["sha256"], label + ".sha256")
    return result


def read_bound(context, target, binding: dict, inputs: dict, *, limit: int = MAX_RECORD_BYTES) -> bytes:
    from analysis_evidence import MAX_EVIDENCE_BYTES
    inputs[binding["path"]] = binding["sha256"]
    result = context.read_bytes_result(target / binding["path"], max_bytes=limit,
                                      aggregate_max_bytes=MAX_EVIDENCE_BYTES)
    if result.value is None:
        raise ValueError("missing or unreadable delivery artifact: " + binding["path"])
    digest = hashlib.sha256(result.value).hexdigest()
    if digest != binding["sha256"]:
        raise ValueError("delivery artifact digest differs: " + binding["path"])
    return result.value


def parse_receipt(raw: bytes) -> dict:
    try:
        document = json_object(raw, "delivery receipt")
    except RecursionError as exc:
        raise ValueError("delivery receipt nesting exceeds parser limits") from exc
    value = fields(document, {"schema_version", "record_kind", "request_id",
        "task_id", "command_id", "started_at", "finished_at", "result", "exit_code", "input_sha256",
        "result_artifact"}, "delivery receipt")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["record_kind"] != "alatyr-delivery-run-receipt":
        raise ValueError("delivery receipt requires schema 1 and alatyr-delivery-run-receipt kind")
    for key in ("request_id", "task_id", "command_id"):
        text(value[key], "receipt." + key)
    start, end = (timestamp(value[key], "receipt." + key) for key in ("started_at", "finished_at"))
    if not 0 <= end-start <= 86400:
        raise ValueError("receipt duration requires an ordered window of at most 86400 seconds")
    result, code = value["result"], value["exit_code"]
    if not isinstance(result, str) or result not in {"passed", "failed", "interrupted"}:
        raise ValueError("receipt.result requires passed, failed or interrupted")
    if result == "interrupted":
        if code is not None:
            raise ValueError("interrupted receipt requires null exit_code")
    elif type(code) is not int or not 0 <= code <= 255 or (result == "passed") != (code == 0):
        raise ValueError("receipt result and exit_code disagree")
    inputs = value["input_sha256"]
    if not isinstance(inputs, dict) or not 1 <= len(inputs) <= 32:
        raise ValueError("receipt.input_sha256 requires 1..32 exact inputs")
    for path, digest in inputs.items():
        request_path(path)
        sha256(digest, "receipt input digest")
    artifact(value["result_artifact"], "receipt.result_artifact")
    return value


def receipt_failures(context, target, brief: dict, history: dict, inputs: dict, *, preserved_count: int = 0) -> list[str]:
    from analysis_evidence import MAX_ARTIFACT_BYTES
    failures = []
    seen = set()
    observed = timestamp(history["progress"]["observed_at"], "progress.observed_at")
    started = timestamp(history["progress"]["started_at"], "progress.started_at")
    for index, row in enumerate(history["attempts"]):
        if "receipt" not in row:
            continue  # The predecessor validator alone permits retained legacy rows.
        binding = row["receipt"]
        if binding["path"] in seen or binding["sha256"] in seen:
            failures.append("delivery attempts cannot reuse a receipt")
            continue
        seen.add(binding["path"])
        seen.add(binding["sha256"])
        receipt = parse_receipt(read_bound(context, target, binding, inputs))
        for key in ("request_id", "task_id"):
            if key == "request_id" and index < preserved_count:
                continue  # Resume preserves accepted original receipt identities; new rows bind the new request.
            if receipt[key] != brief[key]:
                failures.append("delivery receipt differs in " + key)
        if receipt["command_id"] != row["command_id"]:
            failures.append("delivery receipt differs in command_id")
        expected = "failed" if row["result"] == "expected-red" else row["result"]
        if receipt["result"] != expected:
            failures.append("delivery attempt result differs from its receipt")
        start, end = (timestamp(receipt[key], key) for key in ("started_at", "finished_at"))
        if not started <= start <= end <= observed:
            failures.append("delivery receipt lies outside the observed task window")
        if row["duration_seconds"] != math.ceil(end-start):
            failures.append("delivery duration_seconds must equal the rounded-up receipt window")
        output = receipt["result_artifact"]
        if output["path"] != row["evidence_ref"]:
            failures.append("attempt evidence_ref must select its receipt's result artifact")
        read_bound(context, target, output, inputs, limit=MAX_ARTIFACT_BYTES)
    return failures
