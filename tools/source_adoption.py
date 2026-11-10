"""Source-owned adoption and minimal ignored projections, never a self-installer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from lifecycle_policy import POLICY as LIFECYCLE_POLICY, parse_policy
from request_values import fields, request_path, strings, text
from source_context_selection import source_json
from support_write_transaction import SupportTransaction, read_output, safe_output, support_writer_lock

ROOT = Path(__file__).resolve().parents[1]
POLICY = "tools/source_adoption.json"
MARKER = ".ai/assistant/source-adoption.json"
INDEX = ".ai/assistant/active-tasks.json"
MODES = frozenset({"source-equivalent", "conditional", "conformance-only"})
MAX_BYTES = 65536


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def render(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode()


def source_object(root: Path, path: str) -> tuple[bytes, dict]:
    request_path(path)
    raw = read_output(root, root / path, max_bytes=MAX_BYTES)
    if raw is None:
        raise ValueError("missing bounded source adoption input: " + path)
    return raw, source_json(raw.decode("utf-8"))


def assert_source_root(root: Path) -> None:
    if root.resolve() != ROOT.resolve():
        raise ValueError("source-contour adoption is restricted to the running AlatyrCore source root")
    if safe_output(root, root / ".ai/alatyr.yaml").exists():
        raise ValueError("source contour must not activate or overwrite a full installed target adapter")


def parse_source_policy(policy: dict) -> dict:
    fields(policy, {"schema_version", "policy_kind", "scope", "lifecycle_policy", "knowledge_catalog", "guide", "modules"}, "source adoption")
    if (type(policy["schema_version"]) is not int or policy["schema_version"] != 1
            or policy["policy_kind"] != "alatyr-source-adoption" or policy["scope"] != "source-repository"):
        raise ValueError("source adoption requires the exact source-repository schema-1 policy")
    for key in ("lifecycle_policy", "knowledge_catalog", "guide"):
        request_path(policy[key])
    return policy


def projection_marker(value: dict) -> dict:
    fields(value, {"schema_version", "record_kind", "policy_sha256", "lifecycle_sha256", "strategy_sha256"}, "source projection")
    if (type(value["schema_version"]) is not int or value["schema_version"] != 1
            or value["record_kind"] != "alatyr-source-runtime-projection"
            or not isinstance(value["strategy_sha256"], dict) or not value["strategy_sha256"]):
        raise ValueError("invalid source runtime projection")
    for name, digest in [(key, value[key]) for key in ("policy_sha256", "lifecycle_sha256")] + list(value["strategy_sha256"].items()):
        if (not isinstance(name, str) or not name or Path(name).name != name
                or not isinstance(digest, str) or len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)):
            raise ValueError("invalid source projection digest: " + str(name))
    return value


def policy_inputs(root: Path) -> tuple[dict, dict[str, bytes]]:
    raw, policy = source_object(root, POLICY)
    parse_source_policy(policy)
    inputs = {POLICY: raw}
    for key in ("lifecycle_policy", "knowledge_catalog", "guide"):
        request_path(policy[key])
        value = read_output(root, root / policy[key], max_bytes=MAX_BYTES)
        if value is None:
            raise ValueError("source adoption reference is missing: " + policy[key])
        inputs[policy[key]] = value
    parse_policy(inputs[policy["lifecycle_policy"]])
    modules = policy["modules"]
    _, catalog = source_object(root, "framework/capabilities.json")
    if (not isinstance(modules, dict) or not isinstance(catalog.get("modules"), dict)
            or set(modules) != set(catalog["modules"])):
        raise ValueError("source adoption must classify every capability module exactly once")
    for module, row in modules.items():
        fields(row, {"mode", "references"}, "source module " + module)
        if not isinstance(row["mode"], str) or row["mode"] not in MODES:
            raise ValueError("invalid source adoption mode: " + module)
        strings(row["references"], "source references", minimum=1)
        for path in row["references"]:
            request_path(path)
            if not safe_output(root, root / path).is_file():
                raise ValueError("missing source equivalent reference: " + path)
    knowledge = parse_knowledge(source_json(inputs[policy["knowledge_catalog"]].decode("utf-8")))
    owners = dict(inputs)
    for identity, item in knowledge["items"].items():
        if item["owner"] not in owners:
            owners[item["owner"]] = read_output(root, root / item["owner"], max_bytes=MAX_BYTES)
        validate_knowledge_owner(identity, item, owners[item["owner"]])
    return policy, inputs


def parse_knowledge(knowledge: dict) -> dict:
    fields(knowledge, {"schema_version", "catalog_kind", "items"}, "source knowledge")
    if (type(knowledge["schema_version"]) is not int or knowledge["schema_version"] != 1
            or knowledge["catalog_kind"] != "alatyr-source-knowledge-references"
            or not isinstance(knowledge["items"], dict) or not 1 <= len(knowledge["items"]) <= 32):
        raise ValueError("source knowledge requires a bounded reference catalog")
    for identity, item in knowledge["items"].items():
        text(identity, "source knowledge identity")
        fields(item, {"kind", "state", "owner", "heading", "aliases"}, "source knowledge item")
        if not isinstance(item["kind"], str) or item["kind"] not in {"architecture", "term", "incident-learning"}:
            raise ValueError("invalid source knowledge kind")
        if not isinstance(item["state"], str) or item["state"] not in {"observed", "proposed", "accepted", "contradicted"}:
            raise ValueError("invalid source knowledge decision state")
        request_path(item["owner"])
        text(item["heading"], "source heading")
        strings(item["aliases"], "source aliases")
    return knowledge


def validate_knowledge_owner(identity: str, item: dict, raw: bytes | None) -> None:
    if raw is None or not any(line.lstrip("# ") == item["heading"] for line in raw.decode().splitlines() if line.startswith("#")):
        raise ValueError("source knowledge owner/heading is missing: " + identity)


def desired_runtime(root: Path, *, _loaded: tuple[dict, dict[str, bytes]] | None = None) -> tuple[dict[str, bytes], dict[str, bytes]]:
    policy, source_inputs = policy_inputs(root) if _loaded is None else _loaded
    inputs = dict(source_inputs)
    outputs = {LIFECYCLE_POLICY: inputs[policy["lifecycle_policy"]]}
    strategy_hashes = {}
    directory = root / "templates/target/.ai/assistant/analysis-strategies"
    for path in sorted(directory.glob("*.json")):
        if path.name in {"index.json", "context-index.json"}:
            continue
        relative = path.relative_to(root).as_posix()
        raw = read_output(root, path, max_bytes=MAX_BYTES)
        if raw is None:
            raise ValueError("canonical source strategy disappeared: " + relative)
        inputs[relative] = raw
        outputs[".ai/assistant/analysis-strategies/" + path.name] = raw
        strategy_hashes[path.stem] = sha(raw)
    if not strategy_hashes:
        raise ValueError("source adoption requires canonical strategy descriptors")
    outputs[MARKER] = render({"schema_version": 1, "record_kind": "alatyr-source-runtime-projection",
        "policy_sha256": sha(inputs[POLICY]), "lifecycle_sha256": sha(outputs[LIFECYCLE_POLICY]),
        "strategy_sha256": strategy_hashes})
    return outputs, inputs


def assert_current(root: Path) -> dict[str, str]:
    """Cheap material-work guard; selected task validation owns strategy detail."""
    assert_source_root(root)
    raw, policy = source_object(root, POLICY)
    parse_source_policy(policy)
    marker_raw, marker = source_object(root, MARKER)
    projection_marker(marker)
    canonical = read_output(root, root / policy["lifecycle_policy"], max_bytes=MAX_BYTES)
    projected = read_output(root, root / LIFECYCLE_POLICY, max_bytes=MAX_BYTES)
    if (canonical is None or projected != canonical or marker["policy_sha256"] != sha(raw)
            or marker["lifecycle_sha256"] != sha(canonical)):
        raise ValueError("source adoption policy changed; explicitly reconcile the source projection before work")
    parse_policy(canonical)
    # Bind the compact control catalog, not all referenced owner documents.
    result = {POLICY: sha(raw), MARKER: sha(marker_raw), policy["lifecycle_policy"]: sha(canonical)}
    for path in (policy["knowledge_catalog"], "tools/source_adoption.py", "tools/source_scope.py",
                 "tools/lifecycle_checkpoints.py", "tools/run_lifecycle_checkpoint.py", "tools/lifecycle_policy.py",
                 "tools/request_brief.py", "tools/delivery_control.py", "tools/delivery_progress.py", "tools/delivery_receipts.py"):
        value = read_output(root, root / path, max_bytes=MAX_BYTES)
        if value is None:
            raise ValueError("missing source control input: " + path)
        result[path] = sha(value)
    return result


def assert_runtime_untracked(root: Path) -> None:
    from target_validation_support import GitEvidenceView
    git = GitEvidenceView(root)
    for path in (INDEX, LIFECYCLE_POLICY, MARKER, ".ai/.runtime/support-writer/transaction.lock"):
        if git.is_ignored(path) is not True or git.is_tracked(path) is not False:
            raise ValueError("source runtime must remain ignored and untracked: " + path)


def selected_strategy_inputs(root: Path, model: dict) -> dict[str, str]:
    """Hydrate only descriptors actually selected by the canonical model."""
    _, marker = source_object(root, MARKER)
    projection_marker(marker)
    ids = {model["primary_strategy_id"], *model["required_review_ids"]}
    inputs = {}
    for identity in ids:
        text(identity, "source strategy ID")
        request_path(identity)
        if Path(identity).name != identity:
            raise ValueError("invalid source strategy ID")
        source = "templates/target/.ai/assistant/analysis-strategies/" + identity + ".json"
        target = ".ai/assistant/analysis-strategies/" + identity + ".json"
        canonical = read_output(root, root / source, max_bytes=MAX_BYTES)
        projected = read_output(root, root / target, max_bytes=MAX_BYTES)
        if canonical is None or canonical != projected or marker["strategy_sha256"].get(identity) != sha(canonical):
            raise ValueError("selected source strategy changed; reconcile its projection: " + identity)
        inputs.update({source: sha(canonical), target: sha(projected)})
    return inputs


def reconcile(root: Path, *, write: bool = False, approve_policy_update: bool = False) -> dict:
    from target_validation_support import GitEvidenceView
    assert_source_root(root)
    outputs, inputs = desired_runtime(root)
    assert_runtime_untracked(root)
    git = GitEvidenceView(root)
    existing_marker = read_output(root, root / MARKER, max_bytes=MAX_BYTES)
    previous_outputs = None
    if existing_marker is not None:
        previous_outputs = projection_marker(source_json(existing_marker.decode()))
    expected = {root / path: value for path, value in inputs.items()}
    changes = []
    for path, desired in outputs.items():
        if git.is_ignored(path) is not True or git.is_tracked(path) is not False:
            raise ValueError("source projection outputs must be ignored and untracked: " + path)
        old = read_output(root, root / path, max_bytes=MAX_BYTES)
        expected[root / path] = old
        if old is not None and old != desired:
            if previous_outputs is None or not approve_policy_update:
                raise ValueError("existing source projection requires explicit policy-update approval: " + path)
            known = (previous_outputs["lifecycle_sha256"] if path == LIFECYCLE_POLICY else
                     previous_outputs["strategy_sha256"].get(Path(path).stem) if path != MARKER else sha(existing_marker))
            if sha(old) != known:
                raise ValueError("source projection was locally modified; preserve and reconcile it: " + path)
        if old != desired:
            changes.append(path)
    old_index = read_output(root, root / INDEX, max_bytes=512 * 1024)
    if old_index is None:
        if git.is_ignored(INDEX) is not True or git.is_tracked(INDEX) is not False:
            raise ValueError("source task index must be ignored and untracked")
        outputs[INDEX] = render({"schema_version": 1, "index_kind": "target-active-task-index", "tasks": []})
        expected[root / INDEX] = None
        changes.append(INDEX)
    else:
        from task_evidence_contract import task_schema
        if not task_schema("active-task-index").is_valid(source_json(old_index.decode())):
            raise ValueError("preserve invalid source task index for explicit repair")
        expected[root / INDEX] = old_index
    if write:
        with support_writer_lock(root):
            transaction = SupportTransaction(root)
            try:
                transaction.apply({root / path: raw for path, raw in outputs.items()}, expected_inputs=expected)
            except Exception:
                conflicts = transaction.rollback()
                if conflicts:
                    raise RuntimeError("source adoption rollback conflicts preserved")
                raise
    return {"write": write, "changed_paths": changes, "scope": "minimal ignored source runtime only",
            "authorization_granted": False, "acceptance_granted": False, "native_interception_verified": False}
