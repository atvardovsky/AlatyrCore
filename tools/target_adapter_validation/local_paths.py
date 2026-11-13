"""Find local paths in text or decoded structured scalars without executing data."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
import json
import re
import base64
import hashlib
from pathlib import Path, PurePosixPath

from yaml import YAMLError, parse as parse_yaml
from yaml.events import AliasEvent, ScalarEvent, CollectionStartEvent, CollectionEndEvent
from yaml.nodes import MappingNode, ScalarNode, SequenceNode
from yaml_support import SAFE_LOADER, safe_compose_all

UNIX_LOCAL_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])/(?:home|Users|tmp|var/folders|private/tmp)/[^\s)`>\"']+")
WINDOWS_LOCAL_PATH_RE = re.compile(r"\b[A-Za-z]:\\(?:Users|Temp|tmp|Projects|projects|[^\\\s`\"']+)(?:\\[^\s`\"']+)*")
LOCAL_PATH_RE = re.compile(f"(?:{UNIX_LOCAL_PATH_RE.pattern})|(?:{WINDOWS_LOCAL_PATH_RE.pattern})")
MAX_SCAN_BYTES = 8 * 1024 * 1024
MAX_SCAN_NODES = 200_000
MAX_SCAN_DEPTH = 128
MAX_SCAN_MATCHES = 4096
MAX_HISTORY_FILE_BYTES = 4 * 1024 * 1024
MAX_HISTORY_TOTAL_BYTES = 16 * 1024 * 1024


def _history_read(host, name, budget):
    from target_adapter_validation.historical_evidence import _safe_file
    _, raw = _safe_file(host, name, limit=MAX_HISTORY_FILE_BYTES)
    budget[0] += len(raw)
    if budget[0] > MAX_HISTORY_TOTAL_BYTES or (host.target / name).stat().st_nlink != 1:
        raise ValueError('historical path binding exceeds byte budget or uses a hardlink')
    return raw


def _history_json(host, name, budget, optional=False):
    from target_adapter_validation.historical_evidence import _unique_fields
    path = host.target / name
    if optional and not host.context.status(path).exists:
        return None
    value = json.loads(_history_read(host, name, budget).decode('utf-8'), object_pairs_hook=_unique_fields)
    if not isinstance(value, dict):
        raise ValueError('historical authority inventory must be an object')
    return value


def _history_references(value):
    pending, result, visited = [value], set(), 0
    while pending:
        item = pending.pop()
        visited += 1
        if visited > 100_000 or len(pending) > 100_000:
            raise ValueError('historical current-authority reference graph is unbounded')
        if isinstance(item, dict):
            result.update(item[key] for key in ('path', 'file', 'record') if isinstance(item.get(key), str))
            for key, value in item.items():
                if key.endswith('_ref') and isinstance(value, str):
                    result.add(value)
                elif (key.endswith('_refs') or key in {'approval_records', 'evidence_records', 'canonical_owners'}) and isinstance(value, list):
                    result.update(ref for ref in value if isinstance(ref, str))
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return result


def _history_authority_paths(host, budget):
    from change_package_contract import historical_snapshot_task_is_distinct
    protected = {host.rel(path) for path in [*host.approval_records, *host.problem_models, *host.change_packages]}
    selected_models = {host.rel(path).casefold() for path in host.problem_models}
    active = _history_json(host, '.ai/assistant/active-tasks.json', budget, optional=True)
    active_raw = None if active is None else json.dumps(active).encode('utf-8')
    for path in [*host.problem_models, *host.approval_records]:
        protected.update(_history_references(_history_json(host, host.rel(path), budget)))
    index = _history_json(host, '.ai/assistant/change-packages/index.json', budget, optional=True)
    package_names = {host.rel(path) for path in host.change_packages}
    indexes = [] if index is None else [index]
    if index is not None:
        shards = index.get('shards', [])
        if not isinstance(shards, list) or len(shards) > 64:
            raise ValueError('historical authority shard inventory is malformed or unbounded')
        for shard in shards:
            if not isinstance(shard, dict) or not isinstance(shard.get('path'), str):
                raise ValueError('historical authority shard path is invalid')
            indexes.append(_history_json(host, shard['path'], budget))
    for item in indexes:
        records = item.get('records')
        if not isinstance(records, list) or len(records) > 1024:
            raise ValueError('historical authority record inventory is malformed or unbounded')
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get('record'), str):
                raise ValueError('historical authority record path is invalid')
            package_names.add(record['record'])
    if len(package_names) > 1024:
        raise ValueError('historical authority package inventory exceeds its bound')
    for name in sorted(package_names):
        package = _history_json(host, name, budget)
        incident = package.get('incident_continuity', {})
        model = incident.get('problem_model', {}) if isinstance(incident, dict) else {}
        selected_model = isinstance(model, dict) and isinstance(model.get('path'), str) and model['path'].casefold() in selected_models
        inert_history = (package.get('evidence_classification') == 'historical-record'
                        and package.get('status') in {'validated', 'complete'} and name not in protected
                        and not selected_model
                        and historical_snapshot_task_is_distinct(active_raw, host.current_task_id, package))
        if not inert_history:
            protected.add(name)
            plan = package.get('plan', {})
            if not isinstance(plan, dict):
                raise ValueError('current authority plan is malformed')
            if isinstance(plan.get('file'), str):
                protected.add(plan['file'])
            protected.update(_history_references(package))
    if active is not None:
        tasks = active.get('tasks')
        if not isinstance(tasks, list) or len(tasks) > 1024:
            raise ValueError('historical authority task inventory is malformed or unbounded')
        for task in tasks:
            if not isinstance(task, dict):
                raise ValueError('historical authority task is malformed')
            if task.get('state') == 'active':
                refs = [task.get('problem_model'), *(task.get('analysis_handoff') or {}).values()]
                protected.update(ref['path'] for ref in refs if isinstance(ref, dict) and isinstance(ref.get('path'), str))
                protected.update(_history_references(task))
                if task.get('task_id') == host.current_task_id:
                    model = task.get('problem_model')
                    if not isinstance(model, dict) or not isinstance(model.get('path'), str):
                        raise ValueError('selected task authority model is missing')
                    protected.update(_history_references(_history_json(host, model['path'], budget)))
    return protected


def _history_literals(row):
    if not isinstance(row, dict) or set(row) != {'path', 'sha256', 'literals_base64', 'reason'}:
        raise ValueError('historical path binding requires exact file, hash, encoded literals and reason')
    values, reason = row['literals_base64'], row['reason']
    if (not isinstance(reason, str) or not reason.strip() or len(reason) > 1024
            or not isinstance(values, list) or not 1 <= len(values) <= 64):
        raise ValueError('historical path binding reason or literal inventory is invalid')
    literals = []
    for value in values:
        if not isinstance(value, str) or not 1 <= len(value) <= 8192:
            raise ValueError('historical path binding encoded literal is invalid')
        raw = base64.b64decode(value, validate=True)
        literal = raw.decode('utf-8')
        if base64.b64encode(raw).decode('ascii') != value or not literal or '\x00' in literal:
            raise ValueError('historical path binding literal encoding is not canonical')
        literals.append(literal)
    if len(set(literals)) != len(literals):
        raise ValueError('historical path binding literals must be unique')
    return set(literals)


def historical_path_bindings(host):
    """Exact immutable historical values only; no namespace or current-config exemption."""
    entries = host.config.historical_local_path_bindings
    if entries == () or entries == []:
        return {}
    if not isinstance(entries, list) or not 1 <= len(entries) <= 64:
        raise ValueError('historical path bindings must be a bounded nonempty list')
    if host.config.source is None:
        raise ValueError('historical path bindings require the parsed configuration file binding')
    budget, result, names = [0], {}, set()
    if host.config.source is not None:
        from target_adapter_validation.historical_evidence import _selected_path
        config_name = _selected_path(host, Path(host.config.source)).as_posix()
        raw = _history_read(host, config_name, budget)
        if hashlib.sha256(raw).hexdigest() != host.config.source_sha256:
            raise ValueError('historical path binding configuration changed since parsing')
        config = _history_json(host, config_name, budget)
        if config.get('historical_local_path_bindings') != entries:
            raise ValueError('historical path binding configuration differs from parsed input')
    protected = {name.casefold() for name in _history_authority_paths(host, budget)}
    for row in entries:
        literals = _history_literals(row)
        name, digest = row['path'], row['sha256']
        if (not isinstance(name, str) or name != PurePosixPath(name).as_posix()
                or any(part in {'', '.', '..'} for part in name.split('/'))
                or any(char in name for char in '*?[]\\:\x00') or name != name.strip()
                or name.casefold() in names or name.casefold() in protected):
            raise ValueError('historical path binding is unsafe, duplicate or current authority')
        retained = re.fullmatch(r'\.ai/assistant/change-packages/[^/]+-retained-([a-f0-9]{64})-plan\.md', name)
        if (not name.startswith('.ai/assistant/task-evidence/') and retained is None
                or not isinstance(digest, str) or re.fullmatch(r'[a-f0-9]{64}', digest) is None
                or retained is not None and retained[1] != digest):
            raise ValueError('historical path binding lacks an exact retained identity')
        names.add(name.casefold())
        raw = _history_read(host, name, budget)
        if hashlib.sha256(raw).hexdigest() != digest or b'\x00' in raw:
            raise ValueError('historical path binding bytes are stale or binary')
        scan = scan_local_paths(raw.decode('utf-8'), Path(name).suffix, str(host.target))
        if scan.failures or not literals.issubset({match.value for match in scan.matches}):
            raise ValueError('historical path binding has incomplete coverage or absent literals')
        result[name] = literals
    return result


class _Pairs(list):
    pass


@dataclass(frozen=True)
class PathMatch:
    value: str
    line: int | None
    pointer: str | None = None
    kind: str = "text"
    member_path: tuple[int, ...] = ()
    scalar_start_line: int | None = None


@dataclass
class PathScan:
    matches: list[PathMatch] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def _pointer(parent: str, key: str) -> str:
    value = parent + "/" + key.replace("~", "~0").replace("/", "~1")
    if len(value) > 8192:
        raise ValueError("structured path location exceeds 8192 characters")
    return value


def _scan_scalar(result: PathScan, text: str, target: str, *, line: int | None,
                 pointer: str | None = None, kind: str = "text",
                 member_path: tuple[int, ...] = (), scalar_start_line: int | None = None) -> None:
    for offset, part in enumerate(text.splitlines(), start=0):
        target_found = False
        for match in LOCAL_PATH_RE.finditer(part):
            value = match.group(0)
            target_found = target_found or value == target
            if len(result.matches) >= MAX_SCAN_MATCHES:
                raise ValueError("local-path findings exceed the bounded scan limit")
            result.matches.append(PathMatch(value, None if line is None else line + offset, pointer, kind,
                                            member_path, scalar_start_line))
        if target and target in part and not target_found:
            if len(result.matches) >= MAX_SCAN_MATCHES:
                raise ValueError("local-path findings exceed the bounded scan limit")
            result.matches.append(PathMatch(target, None if line is None else line + offset, pointer, kind,
                                            member_path, scalar_start_line))


def _json_children(item, pointer, depth, members):
    if isinstance(item, _Pairs):
        for index, (key, child) in enumerate(item):
            location, member = _pointer(pointer, key), (*members, index)
            yield key, location, "key", depth + 1, member
            yield child, location, "value", depth + 1, member
    elif isinstance(item, list):
        for index, child in enumerate(item):
            yield child, _pointer(pointer, str(index)), "value", depth + 1, members


def _json_scalars(result: PathScan, value: object, target: str) -> None:
    stack = [iter([(value, "", "value", 0, ())])]
    visited = 0
    while stack:
        try:
            item, pointer, kind, depth, members = next(stack[-1])
        except StopIteration:
            stack.pop()
            continue
        visited += 1
        if visited > MAX_SCAN_NODES or depth > MAX_SCAN_DEPTH:
            raise ValueError("structured local-path scan exceeds node/depth limits")
        if isinstance(item, str):
            _scan_scalar(result, item, target, line=None, pointer=pointer, kind=kind, member_path=members)
        else:
            stack.append(iter(_json_children(item, pointer, depth, members)))


def _yaml_children(node, pointer, depth):
    if isinstance(node, MappingNode):
        for key, child in node.value:
            location = _pointer(pointer, key.value if isinstance(key, ScalarNode) else "<complex-key>")
            yield key, location, "key", depth + 1, False
            yield child, location, "value", depth + 1, False
    elif isinstance(node, SequenceNode):
        for index, child in enumerate(node.value):
            yield child, _pointer(pointer, str(index)), "value", depth + 1, False


def _yaml_scalars(result: PathScan, text: str, target: str) -> None:
    nodes, depth = 0, 0
    # Enforce graph budgets before allocating composed YAML nodes.
    for event in parse_yaml(text, Loader=SAFE_LOADER):
        if isinstance(event, (CollectionStartEvent, ScalarEvent, AliasEvent)):
            nodes += 1
            if nodes > MAX_SCAN_NODES or depth > MAX_SCAN_DEPTH:
                raise ValueError("structured local-path scan exceeds node/depth limits")
        if isinstance(event, CollectionStartEvent):
            depth += 1
        elif isinstance(event, CollectionEndEvent):
            depth -= 1
    stack = [iter((root, f"/documents/{index}", "value", 0, False)
                  for index, root in enumerate(safe_compose_all(text)))]
    active, visited, spans = set(), set(), []
    while stack:
        try:
            node, pointer, kind, depth, leaving = next(stack[-1])
        except StopIteration:
            stack.pop()
            continue
        if node is None:
            continue
        if depth == 0 and not leaving:
            # YAML aliases are document-local; prior graph IDs can be reused.
            active.clear()
            visited.clear()
        identity = id(node)
        if leaving:
            active.remove(identity)
            continue
        if identity in active:
            raise ValueError("cyclic YAML aliases make path coverage incomplete")
        if identity in visited:
            continue
        visited.add(identity)
        if len(visited) > MAX_SCAN_NODES or depth > MAX_SCAN_DEPTH:
            raise ValueError("structured local-path scan exceeds node/depth limits")
        active.add(identity)
        stack.append(iter([(node, pointer, kind, depth, True)]))
        if isinstance(node, ScalarNode):
            spans.append((node.start_mark.index, node.end_mark.index))
            _scan_scalar(result, node.value, target, line=None, pointer=pointer, kind=kind,
                         scalar_start_line=node.start_mark.line + 1)
        else:
            stack.append(iter(_yaml_children(node, pointer, depth)))
    # Comments and directives are not YAML scalar nodes; retain their path scan.
    start = 0
    offsets = [index for index, char in enumerate(text) if char == "\n"]
    for left, right in sorted(spans):
        if left >= start:
            _scan_scalar(result, text[start:left], target, line=bisect_right(offsets, start) + 1)
        start = max(start, right)
    _scan_scalar(result, text[start:], target, line=bisect_right(offsets, start) + 1)


def _json_fragments(text: str):
    """Yield complete quoted tokens in one pass, including malformed documents."""
    start, index, count = None, 0, 0
    while index < len(text):
        char = text[index]
        if start is not None and char == "\\":
            index += 2
            continue
        if char == '"':
            if start is None:
                start = index
            else:
                count += 1
                if count > MAX_SCAN_NODES:
                    raise ValueError("JSON fragment scan exceeds node limit")
                yield start, text[start:index + 1]
                start = None
        index += 1


def scan_local_paths(text: str, suffix: str, target: str) -> PathScan:
    result = PathScan()
    if len(text.encode("utf-8")) > MAX_SCAN_BYTES:
        result.failures.append("local-path input exceeds 8 MiB; split the artifact before acceptance")
        return result
    structured = suffix.casefold() in {".json", ".yaml", ".yml"}
    try:
        if suffix.casefold() == ".json":
            value = json.loads(text, object_pairs_hook=_Pairs)
            _json_scalars(result, value, target)
        elif structured:
            _yaml_scalars(result, text, target)
        else:
            _scan_scalar(result, text, target, line=1)
    except (ValueError, RecursionError, MemoryError, YAMLError) as exc:
        result.failures.append("structured local-path coverage is incomplete: " + str(exc)[:160])
        if isinstance(exc, MemoryError):
            return result
        if structured:
            try:
                _scan_scalar(result, text, target, line=1)
                if suffix.casefold() == ".json":
                    offsets = [index for index, char in enumerate(text) if char == "\n"]
                    for start, token in _json_fragments(text):
                        try:
                            value = json.loads(token)
                        except ValueError:
                            continue
                        _scan_scalar(result, value, target, line=None,
                                     scalar_start_line=bisect_right(offsets, start) + 1,
                                     kind="decoded-fragment")
            except (ValueError, MemoryError, RecursionError):
                pass  # The blocking incomplete finding above retains exhaustion.
    return result
