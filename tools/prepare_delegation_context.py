#!/usr/bin/env python3
"""Freeze measured inspect-only context before worker dispatch or expansion."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

from delegation_evidence import _validate_policy_limits
from source_worker_contract import load_source_worker_policy, validate_worker_packet

ROOT = Path(__file__).resolve().parents[1]
MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
INSTRUCTIONS = (
    "Inspect only. Use only this supplied packet. Do not read additional files, "
    "run commands, delegate, or write. If context is insufficient, return "
    "needs-expansion with exact paths and a reason; do not guess. "
    "Decisions, approvals, integration and acceptance remain primary-owned.\n"
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value: dict) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))


def measurement(data: bytes) -> dict:
    if not isinstance(data, bytes) or len(data) > MAX_ARTIFACT_BYTES:
        raise ValueError("context artifacts must be bounded UTF-8 bytes")
    text = data.decode("utf-8")
    return {"sha256": digest(data), "word_count": len(text.split()), "character_count": len(text)}


def read_artifact(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError(f"context artifact must be a bounded regular file: {path}")
    with path.open("rb") as stream:
        data = stream.read(MAX_ARTIFACT_BYTES + 1)
    measurement(data)
    return data


def _part(kind: str, name: str, data: bytes) -> bytes:
    measurement(data)
    return f"\n--- {kind}: {name} ---\n".encode("utf-8") + data + b"\n"


def validate_preflight(record: dict, packet: dict, policy: dict) -> None:
    _, _, limits = _validate_policy_limits(policy)
    required = {"schema_version", "record_kind", "packet_sha256", "policy_sha256", "max_context_words", "context", "initial_context_words", "source_inputs", "other_contexts", "other_context_words", "dispatch_performed", "native_limit_enforced"}
    if not isinstance(record, dict) or set(record) != required or type(record.get("schema_version")) is not int or record["schema_version"] != 1 or record.get("record_kind") != "alatyr-worker-context-preflight":
        raise ValueError("invalid worker context preflight contract")
    if record["packet_sha256"] != canonical_digest(packet) or record["policy_sha256"] != canonical_digest(policy):
        raise ValueError("worker context preflight packet or policy is stale")
    for name in ("max_context_words", "initial_context_words", "other_context_words"):
        if type(record[name]) is not int or record[name] < (0 if name == "other_context_words" else 1):
            raise ValueError(f"worker context preflight {name} must be a resolved integer")
    if record["max_context_words"] > limits["max_context_words_total"] or record["initial_context_words"] > packet["max_initial_words"]:
        raise ValueError("worker context preflight exceeds canonical context limits")
    if record["dispatch_performed"] is not False or record["native_limit_enforced"] is not False:
        raise ValueError("preflight cannot claim dispatch or native hard-limit enforcement")
    context = record["context"]
    if not isinstance(context, dict) or set(context) != {"sha256", "word_count", "character_count"} or not isinstance(context["sha256"], str) or len(context["sha256"]) != 64:
        raise ValueError("preflight requires a measured context artifact")
    if any(type(context[field]) is not int or context[field] < 1 for field in ("word_count", "character_count")):
        raise ValueError("preflight context measurements must be positive integers")
    if context["word_count"] < record["initial_context_words"] or context["word_count"] > record["max_context_words"] or context["word_count"] + record["other_context_words"] > limits["max_context_words_total"]:
        raise ValueError("worker context preflight exceeds its worker or aggregate budget")
    if not isinstance(record["source_inputs"], dict) or not isinstance(record["other_contexts"], list):
        raise ValueError("preflight source and sibling artifact bindings are required")
    for item in record["other_contexts"]:
        if not isinstance(item, dict) or set(item) != {"sha256", "word_count", "character_count"} or not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64 or any(type(item.get(field)) is not int or item[field] < 0 for field in ("word_count", "character_count")):
            raise ValueError("preflight sibling artifacts require valid measurements")
    if record["other_context_words"] != sum(item["word_count"] for item in record["other_contexts"]):
        raise ValueError("preflight sibling context total differs from its measurements")


def prepare(packet: dict, policy: dict, *, root: Path, prompt: bytes | None,
            bootstrap: dict[str, bytes], expansions: list[str], other_contexts: list[bytes],
            max_context_words: int | None = None, previous: tuple[dict, bytes] | None = None) -> tuple[dict, bytes]:
    validate_worker_packet(packet, policy["worker_packet_contract"], root=root)
    _, _, limits = _validate_policy_limits(policy)
    source_inputs = {}
    if previous is None:
        if prompt is None or not prompt.strip() or not bootstrap:
            raise ValueError("initial dispatch requires the actual prompt and explicit visible bootstrap artifacts")
        content = INSTRUCTIONS.encode() + _part("packet", "inspect-only", json.dumps(packet, sort_keys=True, indent=2).encode())
        content += _part("prompt", "current task", prompt)
        for name, value in bootstrap.items():
            content += _part("bootstrap", name, value)
        for path in packet["bounded_context"]:
            value = read_artifact(root / path)
            source_inputs[path] = digest(value)
            content += _part("source", path, value)
        initial_words = measurement(content)["word_count"]
        if initial_words > packet["max_initial_words"]:
            raise ValueError(f"initial context has {initial_words} words; packet limit is {packet['max_initial_words']}")
        limit = packet["max_initial_words"] if max_context_words is None else max_context_words
    else:
        prior, content = previous
        validate_preflight(prior, packet, policy)
        if measurement(content) != prior["context"]:
            raise ValueError("previous context artifact differs from its measurement")
        if prompt is not None or bootstrap:
            raise ValueError("expansion must retain the frozen prompt and bootstrap")
        source_inputs = dict(prior["source_inputs"])
        allowed_inputs = set(packet["bounded_context"]) | set(packet["conditional_context"])
        if set(packet["bounded_context"]) - source_inputs.keys() or any(path not in allowed_inputs or digest(read_artifact(root / path)) != value for path, value in source_inputs.items()):
            raise ValueError("previous source context is stale or outside the packet")
        initial_words = prior["initial_context_words"]
        limit = prior["max_context_words"] if max_context_words is None else max_context_words
        if type(limit) is not int or limit > prior["max_context_words"]:
            raise ValueError("expansion cannot increase the allocated worker context limit")
    if type(limit) is not int or limit < 1 or limit > limits["max_context_words_total"]:
        raise ValueError("worker context allocation must be positive and inside the canonical ceiling")
    if len(expansions) != len(set(expansions)):
        raise ValueError("duplicate expansion paths")
    for path in expansions:
        if path not in packet["conditional_context"] or path in source_inputs:
            raise ValueError(f"context expansion is undeclared or already delivered: {path}")
        value = read_artifact(root / path)
        source_inputs[path] = digest(value)
        content += _part("expansion", path, value)
    measured = measurement(content)
    others = [measurement(value) for value in other_contexts]
    if previous is not None:
        remaining_others = list(others)
        for item in previous[0]["other_contexts"]:
            if item not in remaining_others:
                raise ValueError("expansion cannot silently remove a sibling context reservation")
            remaining_others.remove(item)
    other_words = sum(value["word_count"] for value in others)
    if measured["word_count"] > limit or measured["word_count"] + other_words > limits["max_context_words_total"]:
        raise ValueError(f"measured worker context {measured['word_count']} words exceeds worker limit {limit} or aggregate limit {limits['max_context_words_total']} with {other_words} sibling words")
    record = {"schema_version": 1, "record_kind": "alatyr-worker-context-preflight",
        "packet_sha256": canonical_digest(packet), "policy_sha256": canonical_digest(policy),
        "max_context_words": limit, "context": measured, "initial_context_words": initial_words,
        "source_inputs": source_inputs, "other_contexts": others, "other_context_words": other_words,
        "dispatch_performed": False, "native_limit_enforced": False}
    validate_preflight(record, packet, policy)
    return record, content


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--prompt", type=Path)
    parser.add_argument("--bootstrap", type=Path, action="append", default=[])
    parser.add_argument("--expand", action="append", default=[], help="Exact packet-declared conditional source path.")
    parser.add_argument("--other-context", type=Path, action="append", default=[], help="Actual context artifact for every other allocated worker.")
    parser.add_argument("--max-context-words", type=int)
    parser.add_argument("--previous", type=Path, help="Previous frozen bundle directory, required for incremental delivery.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        if len(set(args.bootstrap)) != len(args.bootstrap) or len(set(args.other_context)) != len(args.other_context):
            raise ValueError("bootstrap and sibling artifacts must not be repeated")
        policy = load_source_worker_policy(ROOT / "tools/source_worker_policy.json", root=ROOT)
        packet = json.loads(read_artifact(args.packet))
        previous = (json.loads(read_artifact(args.previous / "preflight.json")), read_artifact(args.previous / "context.txt")) if args.previous else None
        record, content = prepare(packet, policy, root=ROOT,
            prompt=read_artifact(args.prompt) if args.prompt else None,
            bootstrap={str(path): read_artifact(path) for path in args.bootstrap}, expansions=args.expand,
            other_contexts=[read_artifact(path) for path in args.other_context],
            max_context_words=args.max_context_words, previous=previous)
        if args.write:
            output = args.output_dir.absolute()
            if output.exists() or output.is_symlink() or any(parent.is_symlink() for parent in output.parents):
                raise ValueError("frozen context output must be a new directory without symlink parents")
            output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=output.parent) as directory:
                staged = Path(directory) / "bundle"
                staged.mkdir()
                (staged / "context.txt").write_bytes(content)
                (staged / "preflight.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
                staged.rename(output)
        print(json.dumps({"write": args.write, "preflight": record, "limitation": "Visible supplied context only; no provider-native cutoff, dispatch, or acceptance is established."}, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
