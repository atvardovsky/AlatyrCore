#!/usr/bin/env python3
"""Prepare measured worker-result drafts from explicit runtime artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

from delegation_evidence import _validate_policy_limits, enforce_character_limit, load_json_object, worker_result_sha256
from source_worker_contract import load_source_worker_policy, validate_worker_packet
from prepare_delegation_context import validate_preflight, measurement, canonical_digest, read_artifact
from worker_handoff import compact_handoff, handoff

ROOT = Path(__file__).resolve().parents[1]


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def prepare(packet: dict, event: dict, contents: dict[str, bytes], policy: dict, preflight: dict | None = None) -> dict:
    validate_worker_packet(packet, policy["worker_packet_contract"], root=ROOT)
    required = {"schema_version", "event_kind", "backend_kind", "worker_id", "packet_id", "base_revision"}
    if not isinstance(event, dict) or set(event) != required or type(event.get("schema_version")) is not int or event["schema_version"] != 1:
        raise ValueError("runtime event must have the exact worker-result-received contract")
    if event.get("event_kind") != "worker-result-received":
        raise ValueError("runtime event is not a received worker result")
    if not isinstance(event.get("backend_kind"), str) or event["backend_kind"] not in policy["runtime_capability_contract"]["backend_kinds"]:
        raise ValueError("runtime backend is unsupported")
    for field in ("worker_id", "packet_id", "base_revision"):
        if not isinstance(event.get(field), str) or not event[field].strip():
            raise ValueError(f"runtime event {field} is required")
    _, _, limits = _validate_policy_limits(policy)
    artifacts = {}
    for name, data in contents.items():
        text = data.decode("utf-8")
        artifacts[name] = {"path": name + ".txt", "sha256": sha(data),
                           "word_count": len(text.split()), "character_count": len(text)}
    if set(artifacts) != {"context", "raw", "summary"}:
        raise ValueError("context, raw, and summary artifacts are required")
    ceilings = {"context": limits["max_context_words_total"],
                "raw": min(packet["max_result_words"], limits["max_result_words_total"]),
                "summary": min(packet["max_summary_words"], limits["max_primary_summary_words_total"])}
    for name, limit in ceilings.items():
        if artifacts[name]["word_count"] > limit:
            raise ValueError(f"{name} has {artifacts[name]['word_count']} words; limit is {limit}")
        enforce_character_limit(artifacts[name]["character_count"], limit, name)
    if artifacts["summary"]["word_count"] > artifacts["raw"]["word_count"]:
        raise ValueError("accepted-summary candidate exceeds raw result size")
    if preflight is not None:
        validate_preflight(preflight, packet, policy)
        frozen = contents["context"].decode("utf-8")[:preflight["context"]["character_count"]].encode("utf-8")
        if measurement(frozen) != preflight["context"]:
            raise ValueError("observed context does not retain the frozen dispatch artifact")
        words = artifacts["context"]["word_count"]
        if words > preflight["max_context_words"] or words + preflight["other_context_words"] > limits["max_context_words_total"]:
            raise ValueError(f"observed context has {words} words; frozen worker limit is {preflight['max_context_words']}")
        enforce_character_limit(artifacts["context"]["character_count"], preflight["max_context_words"], "observed worker context")
        enforce_character_limit(
            artifacts["context"]["character_count"] + sum(item["character_count"] for item in preflight["other_contexts"]),
            limits["max_context_words_total"], "observed aggregate context",
        )
    result = {"schema_version": 3, "result_kind": "alatyr-normalized-worker-result",
        "result_id": event["worker_id"] + ":result", "packet_id": event["packet_id"],
        "parent_packet_id": packet["parent_packet_id"], "node_id": event["worker_id"],
        "depth": packet["depth"], "base_revision": event["base_revision"],
        "status": "requires-review", "measurement_state": "observed",
        "input_context_packet_sha256": artifacts["context"]["sha256"],
        "raw_payload": artifacts["raw"], "accepted_summary": artifacts["summary"],
        "summary_covers_result_ids": [], "child_result_sha256": [],
        "evidence_manifest": [], "findings": [], "touched_surfaces": [],
        "tools_used": [event["backend_kind"]], "scope_violation": "unreviewed", "authorization_concern": "unreviewed",
        "proof_obligation_ids": packet["proof_obligation_ids"], "satisfied_proof_obligation_ids": [],
        "validation": ["artifacts measured; provider provenance and semantic review remain primary-owned"],
        "stop_reason_id": "semantic-decision-required"}
    if preflight is not None:
        result["validation"].append("frozen context preflight verified: " + canonical_digest(preflight))
    result["subtree_sha256"] = worker_result_sha256(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("packet", "event", "context", "raw", "summary", "output-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--context-preflight", type=Path, help="Frozen dispatch preflight; enforce its worker allocation against observed context.")
    parser.add_argument("--metrics", type=Path, help="Optional explicit advisory timing/rework observations; never acceptance evidence.")
    parser.add_argument("--compact", action="store_true", help="Return the compact handoff instead of the full result draft.")
    args = parser.parse_args()
    try:
        policy = load_source_worker_policy(ROOT / "tools/source_worker_policy.json", root=ROOT)
        packet = load_json_object(args.packet, "worker packet")
        event = load_json_object(args.event, "runtime event")
        contents = {name: read_artifact(getattr(args, name)) for name in ("context", "raw", "summary")}
        preflight = load_json_object(args.context_preflight, "context preflight") if args.context_preflight else None
        result = prepare(packet, event, contents, policy, preflight=preflight)
        metrics = load_json_object(args.metrics, "cooperation metrics") if args.metrics else None
        draft = None
        serialized_result = None
        if args.compact or metrics is not None:
            draft, serialized_result = handoff(result, packet, contents, metrics)
        if args.write:
            output = args.output_dir.absolute()
            if output.exists() or output.is_symlink() or any(parent.is_symlink() for parent in output.parents):
                raise ValueError("output directory must be new and must not cross symbolic links")
            output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
                staged = Path(temporary) / "result"
                staged.mkdir()
                for name, data in contents.items():
                    (staged / (name + ".txt")).write_bytes(data)
                if serialized_result is None:
                    serialized_result = (json.dumps(result, indent=2) + "\n").encode("utf-8")
                (staged / "result.json").write_bytes(serialized_result)
                records = [("packet.json", packet), ("runtime-event.json", event)]
                if draft is not None:
                    records.append(("handoff.json", draft))
                for name, data in records:
                    (staged / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                if preflight is not None:
                    (staged / "preflight.json").write_text(json.dumps(preflight, indent=2) + "\n", encoding="utf-8")
                staged.rename(output)
        print(json.dumps({"write": args.write, "status": "requires-review", **({"handoff": compact_handoff(draft)} if args.compact else {"result": result}),
                          "limitation": "draft only; not dispatch, provider verification, primary acceptance, or an execution tree"}, indent=2))
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
