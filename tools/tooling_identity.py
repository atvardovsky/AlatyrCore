"""Bounded reader and producer identity; labels never establish compatibility."""

from __future__ import annotations

import re

from target_validation_support import git_resolve_ref


def tooling_identity(producer, target, pin):
    revision = git_resolve_ref(producer.target, "HEAD")
    exact_pin = isinstance(pin, str) and re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", pin)
    identity = ("same-recorded-revision" if revision == pin else "different-recorded-revision") if exact_pin and revision else "unverified"
    catalog = producer.read_bytes_result(producer.target / "tools/target-adapter-contract-compatibility.json", max_bytes=128 * 1024)
    selected = target.read_bytes_result(target.target / ".ai/assistant/active-tasks.json", max_bytes=512 * 1024)
    reader = "not-observed"
    supported = []
    version = None
    if catalog.value is not None and selected.value is not None:
        from inspect_session_context import json_object
        try:
            contracts = json_object(catalog.value, "producer compatibility catalog")
            index = json_object(selected.value, "target task index")
            supported = contracts["contracts"]["analysis-strategies"]["artifacts"]["active-task-index"]["supported"]
            version = index["schema_version"]
            if (not isinstance(supported, list) or not supported
                    or any(type(item) is not int or item < 1 for item in supported)
                    or type(version) is not int):
                raise ValueError("reader versions must be positive integers")
            reader = "supported-format" if version in supported else "unsupported-format"
        except (ValueError, TypeError, KeyError, RecursionError):
            reader, supported = "invalid-contract", []
    elif catalog.status.exists or selected.status.exists:
        reader = "unverified"
    return {"producer_revision": revision, "revision_identity": identity,
            "reader_contract_sha256": catalog.digest, "selected_index_sha256": selected.digest,
            "active_task_reader": {"state": reader, "selected_schema": version, "supported": supported},
            "content_binding_scope": "selected compatibility catalog and task index; not full producer integrity",
            "authorization_granted": False, "acceptance_granted": False}
