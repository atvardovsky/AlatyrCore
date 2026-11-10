"""Disposable, content-bound direct-import observations for source tooling."""

from __future__ import annotations

import hashlib
import json
import marshal
import sys
from pathlib import Path
from types import CodeType

from source_check_cache import SourceCheckCache

MAX_IMPORT_CACHE_RECORDS = 16
CONTRACT = "alatyr-source-import-scans-v1"


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def code_material(value: object) -> object:
    """Hash code without process-dependent intern or frozenset ordering."""
    if isinstance(value, CodeType):
        return {"code": marshal.dumps(value.replace(co_consts=()), 0).hex(),
                "constants": code_material(value.co_consts)}
    if isinstance(value, tuple):
        return {"tuple": [code_material(item) for item in value]}
    if isinstance(value, frozenset):
        return {"frozenset": sorted((code_material(item) for item in value), key=digest)}
    return {"constant": marshal.dumps(value, 0).hex()}


def code_identity(resolver: type) -> str:
    owners = (resolver, ImportScanCache, SourceCheckCache)
    code = [(owner.__name__, name, digest(code_material(value.__code__)))
            for owner in owners for name, value in vars(owner).items() if hasattr(value, "__code__")]
    code.extend((__name__, func.__name__, digest(code_material(func.__code__)))
                for func in (digest, code_material, code_identity))
    return digest(code)


class ImportScanCache:
    """Cache observations, never import code, manifests, approvals or decisions."""

    def __init__(self, root: Path, modules: dict[str, Path], resolver: type) -> None:
        self.root = root
        self.paths = {path.relative_to(root).as_posix(): path for path in modules.values()}
        inventory = sorted((name, path.relative_to(root).as_posix()) for name, path in modules.items())
        owners = (Path(__file__), Path(__file__).with_name("local_python_import_graph.py"),
                  Path(__file__).with_name("source_check_cache.py"))
        self.implementation_sources = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in owners}
        # Bind loaded code too: a concurrent source update must not label old code as new.
        self.resolver = resolver
        self.identity = {"contract": CONTRACT, "workspace": digest(str(root)),
            "runtime": [sys.implementation.name, sys.version, sys.platform],
            "inventory": digest(inventory),
            "implementation": digest([(path.name, sha) for path, sha in self.implementation_sources.items()]),
            "loaded_code": code_identity(resolver)}
        self.storage = SourceCheckCache(root)
        self.key = "graph-" + digest(self.identity)
        loaded = self.storage.load("imports", self.key).value
        self.entries = (loaded["entries"] if isinstance(loaded, dict)
                        and set(loaded) == {"identity", "entries"}
                        and loaded.get("identity") == self.identity
                        and isinstance(loaded.get("entries"), dict)
                        and len(loaded["entries"]) <= len(self.paths) else {})
        self.observed: dict[Path, str] = {}
        self.dirty = False
        self.hits = 0
        self.misses = 0

    def lookup(self, path: Path, raw: bytes) -> tuple[frozenset[Path], bool] | None:
        name = path.relative_to(self.root).as_posix()
        if self.paths.get(name) != path:
            raise ValueError("source import input outside captured inventory; retry without source cache: " + name)
        source_sha = hashlib.sha256(raw).hexdigest()
        self.observed[path] = source_sha
        item = self.entries.get(name)
        if isinstance(item, dict) and set(item) == {"source_sha256", "dependencies", "complete", "sha256"}:
            dependencies = item["dependencies"]
            if (item["source_sha256"] == source_sha and type(item["complete"]) is bool
                    and isinstance(dependencies, list) and all(isinstance(dep, str) for dep in dependencies)
                    and len(dependencies) == len(set(dependencies))
                    and all(dep in self.paths for dep in dependencies)
                    and item["sha256"] == digest({"path": name, **{k: v for k, v in item.items() if k != "sha256"}})):
                self.hits += 1
                return frozenset(self.paths[dep] for dep in dependencies), item["complete"]
        self.misses += 1
        return None

    def remember(self, path: Path, dependencies: frozenset[Path], complete: bool) -> None:
        name = path.relative_to(self.root).as_posix()
        if name not in self.paths:
            return
        item = {"source_sha256": self.observed[path],
                "dependencies": sorted(dep.relative_to(self.root).as_posix() for dep in dependencies),
                "complete": complete}
        item["sha256"] = digest({"path": name, **item})
        self.entries[name] = item
        self.dirty = True

    def verify(self, modules: dict[str, Path], *, resolution_modules: dict[str, Path]) -> None:
        for current in (modules, resolution_modules):
            inventory = sorted((name, path.relative_to(self.root).as_posix()) for name, path in current.items())
            if digest(inventory) != self.identity["inventory"]:
                raise ValueError("source import inventory changed during analysis; retry with current inputs")
        if code_identity(self.resolver) != self.identity["loaded_code"]:
            raise ValueError("source import implementation changed during analysis; retry with current inputs")
        for path, expected in {**self.observed, **self.implementation_sources}.items():
            try:
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError as exc:
                raise ValueError("source import input unavailable during analysis; retry: " + str(path)) from exc
            if actual != expected:
                raise ValueError("source import input changed during analysis; retry: " + str(path))

    def flush(self) -> None:
        if self.dirty:
            self.storage.store("imports", self.key, {"identity": self.identity, "entries": self.entries})
            self.dirty = False
            self.storage.prune("imports", max_records=MAX_IMPORT_CACHE_RECORDS)
