"""Find local paths in text or decoded structured scalars without executing data."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
import json
import re

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
