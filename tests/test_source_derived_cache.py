from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from local_python_import_graph import LocalPythonImportGraph
from source_import_cache import ImportScanCache, digest, MAX_IMPORT_CACHE_RECORDS
from source_check_cache import SourceCheckCache
import source_check_manifest as manifest
import check_all


class PersistentImportCacheTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        self.write("tools/start.py", "import pkg.leaf\n")
        self.write("tools/pkg/__init__.py", "from . import leaf\n")
        self.write("tools/pkg/leaf.py", "VALUE = 1\n")

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value.encode("utf-8") if isinstance(value, str) else value)
        return path

    def graph(self, enabled=True):
        return LocalPythonImportGraph(self.root, scan_cache_factory=ImportScanCache if enabled else None)

    def populate(self):
        graph = self.graph()
        results = {path: graph.scan(path) for path in graph.modules.values()}
        graph.flush_cache()
        return graph, results

    def record(self, graph):
        cache = graph._persistent_cache
        return cache.storage._path("imports", cache.key)

    def test_warm_results_match_cold_without_ast_parsing(self):
        first, expected = self.populate()
        warm = self.graph()
        with patch("local_python_import_graph.ast.parse", wraps=ast.parse) as parse:
            actual = {path: warm.scan(path) for path in warm.modules.values()}
        warm.flush_cache()
        self.assertEqual(actual, expected)
        self.assertEqual(parse.call_count, 0)
        self.assertEqual(warm._persistent_cache.hits, len(expected))
        canonical = self.graph(False)
        self.assertEqual(warm.transitive_dependencies(self.root / "tools/start.py"),
                         canonical.transitive_dependencies(self.root / "tools/start.py"))
        self.assertEqual(warm.reverse_dependents({self.root / "tools/pkg/leaf.py"}),
                         canonical.reverse_dependents({self.root / "tools/pkg/leaf.py"}))

    def test_same_bytes_in_distinct_packages_keep_source_identity(self):
        self.write("tools/other/__init__.py", "from . import leaf\n")
        self.write("tools/other/leaf.py", "VALUE = 2\n")
        self.populate()
        graph = self.graph()
        first = graph.scan(self.root / "tools/pkg/__init__.py")
        second = graph.scan(self.root / "tools/other/__init__.py")
        self.assertNotEqual(first.dependencies, second.dependencies)
        self.assertEqual(second, self.graph(False).scan(self.root / "tools/other/__init__.py"))

    def test_same_size_mtime_edit_invalidates_only_its_source_entry(self):
        self.write("tools/alt.py", "VALUE = 3\n")
        source = self.write("tools/start.py", "import pkg.leaf\n")
        self.populate()
        before = source.stat()
        source.write_bytes(b"import alt     \n")
        os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
        graph = self.graph()
        self.assertEqual(graph.scan(source), self.graph(False).scan(source))
        self.assertEqual(graph._persistent_cache.misses, 1)
        graph.scan(self.root / "tools/alt.py")
        self.assertEqual(graph._persistent_cache.hits, 1)

    def test_inventory_add_delete_and_rename_invalidate_resolution(self):
        source = self.write("tools/start.py", "import future\n")
        self.populate()
        added = self.write("tools/future.py", "VALUE = 1\n")
        for operation in ("added", "renamed", "deleted"):
            with self.subTest(operation=operation):
                if operation == "renamed":
                    added.rename(self.root / "tools/renamed.py")
                elif operation == "deleted":
                    (self.root / "tools/renamed.py").unlink()
                graph = self.graph()
                self.assertEqual(graph.scan(source), self.graph(False).scan(source))
                self.assertEqual(graph._persistent_cache.hits, int(operation == "deleted"))
                graph.flush_cache()

    def test_live_source_and_inventory_changes_reject_publication(self):
        for change in ("source", "new-module", "removed-module"):
            with self.subTest(change=change):
                self.write("tools/pkg/leaf.py", "VALUE = 1\n")
                graph = self.graph()
                graph.transitive_dependencies(self.root / "tools/start.py")
                graph.reverse_dependents({self.root / "tools/pkg/leaf.py"})
                if change == "source":
                    self.write("tools/pkg/leaf.py", "VALUE = 2\n")
                elif change == "new-module":
                    self.write("tools/new.py", "VALUE = 3\n")
                else:
                    (self.root / "tools/pkg/leaf.py").unlink()
                with self.assertRaisesRegex(ValueError, "source import (input|inventory)"):
                    graph.flush_cache()
                (self.root / "tools/new.py").unlink(missing_ok=True)

    def test_hash_and_parse_use_the_same_bytes_and_later_mutation_rejects(self):
        source = self.root / "tools/start.py"
        graph = self.graph()
        original = ast.parse
        def mutate(value, **kwargs):
            source.write_text("import nonexistent\n")
            return original(value, **kwargs)
        with patch("local_python_import_graph.ast.parse", side_effect=mutate):
            result = graph.scan(source)
        self.assertIn(self.root / "tools/pkg/leaf.py", result.dependencies)
        with self.assertRaisesRegex(ValueError, "input changed"):
            graph.flush_cache()
        self.assertFalse(self.record(graph).exists())

    def test_warm_clean_cache_still_checks_freshness(self):
        self.populate()
        graph = self.graph()
        graph.transitive_dependencies(self.root / "tools/start.py")
        self.assertFalse(graph._persistent_cache.dirty)
        self.write("tools/pkg/leaf.py", "VALUE = 2\n")
        with self.assertRaisesRegex(ValueError, "input changed"):
            graph.flush_cache()

    def test_incomplete_and_invalid_sources_retain_canonical_results(self):
        cases = (b"import importlib\nimportlib.import_module(name)\n", b"not valid python!", b"\xff",
                 b"import pkg.leaf\r\n", b"import pkg.leaf\r")
        for raw in cases:
            with self.subTest(raw=raw):
                source = self.write("tools/start.py", raw)
                cold = self.graph(False).scan(source)
                first = self.graph()
                self.assertEqual(first.scan(source), cold)
                first.flush_cache()
                self.assertEqual(self.graph().scan(source), cold)

    def test_malformed_entries_and_integrity_failures_fall_back(self):
        first, _ = self.populate()
        path = self.record(first)
        original = path.read_bytes()
        mutations = [("complete", []), ("complete", "true"), ("dependencies", [{}]),
                     ("dependencies", ["/outside.py"]), ("dependencies", ["../outside.py"]),
                     ("dependencies", ["tools/missing.py"]),
                     ("dependencies", ["tools/pkg/leaf.py", "tools/pkg/leaf.py"]),
                     ("source_sha256", None), ("sha256", "changed")]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                record = json.loads(original)
                item = record["payload"]["entries"]["tools/start.py"]
                item[field] = value
                if field != "sha256":
                    item["sha256"] = digest({"path": "tools/start.py", **{k: v for k, v in item.items() if k != "sha256"}})
                path.write_text(json.dumps(record))
                graph = self.graph()
                self.assertEqual(graph.scan(self.root / "tools/start.py"), self.graph(False).scan(self.root / "tools/start.py"))
                self.assertEqual(graph._persistent_cache.hits, 0)
        path.write_bytes(original)

    def test_boundaries_corruption_and_unavailable_storage_fall_back(self):
        first, _ = self.populate()
        path = self.record(first)
        original = path.read_bytes()
        for size in (len(original) - 1, len(original), len(original) + 1):
            with self.subTest(limit=size), patch("source_check_cache.MAX_CACHE_RECORD_BYTES", size):
                graph = self.graph()
                self.assertEqual(graph.scan(self.root / "tools/start.py"), self.graph(False).scan(self.root / "tools/start.py"))
                self.assertEqual(graph._persistent_cache.hits, int(size >= len(original)))
        for raw in (b"{", b"[" * 2000 + b"]" * 2000):
            path.write_bytes(raw)
            graph = self.graph()
            self.assertEqual(graph.scan(self.root / "tools/start.py"), self.graph(False).scan(self.root / "tools/start.py"))
        with patch.object(SourceCheckCache, "load", side_effect=OSError("unavailable")):
            graph = self.graph()
        self.assertIsNone(graph._persistent_cache)
        self.assertEqual(graph.scan(self.root / "tools/start.py"), self.graph(False).scan(self.root / "tools/start.py"))
        graph = self.graph()
        graph.scan(self.root / "tools/start.py")
        with patch.object(graph._persistent_cache.storage, "store", side_effect=OSError("unwritable")):
            graph.flush_cache()

    def test_runtime_workspace_and_implementation_are_separate_identities(self):
        graph = self.graph()
        first = graph._persistent_cache.key
        with patch("source_import_cache.sys.version", "different runtime"):
            self.assertNotEqual(self.graph()._persistent_cache.key, first)
        with patch("source_import_cache.CONTRACT", "future-contract"):
            self.assertNotEqual(self.graph()._persistent_cache.key, first)
        other = self.root / "other"
        shutil.copytree(self.root / "tools", other / "tools")
        subprocess.run(["git", "init", "-q"], cwd=other, check=True)
        self.assertNotEqual(LocalPythonImportGraph(other, scan_cache_factory=ImportScanCache)._persistent_cache.key, first)

    def test_fresh_processes_reuse_scans_across_hash_seeds(self):
        script = """
import ast, json, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
from local_python_import_graph import LocalPythonImportGraph
from source_import_cache import ImportScanCache
root = Path(sys.argv[2])
graph = LocalPythonImportGraph(root, scan_cache_factory=ImportScanCache)
with patch('local_python_import_graph.ast.parse', wraps=ast.parse) as parse:
    graph.scan(root / 'tools/start.py')
    graph.flush_cache()
print(json.dumps({'key': graph._persistent_cache.key, 'parses': parse.call_count}))
"""
        results = []
        for seed in ("1", "2", "3"):
            result = subprocess.run([sys.executable, "-B", "-c", script, str(ROOT / "tools"), str(self.root)],
                                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": seed},
                                    capture_output=True, text=True, check=True)
            results.append(json.loads(result.stdout))
        self.assertEqual(len({value["key"] for value in results}), 1)
        self.assertEqual([value["parses"] for value in results], [1, 0, 0])

    def test_off_never_constructs_storage_and_writers_remain_atomic(self):
        with patch("source_import_cache.SourceCheckCache", side_effect=AssertionError("cold path used storage")):
            graph = self.graph(False)
            graph.scan(self.root / "tools/start.py")
            graph.flush_cache()
        def writer(path):
            graph = self.graph()
            result = graph.scan(path)
            graph.flush_cache()
            return result
        paths = [self.root / "tools/start.py", self.root / "tools/pkg/leaf.py"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            actual = list(pool.map(writer, paths))
        self.assertEqual(actual, [self.graph(False).scan(path) for path in paths])
        for path in paths:
            self.assertEqual(self.graph().scan(path), self.graph(False).scan(path))

    def test_symlinked_cache_and_pruning_failure_use_canonical_results(self):
        first, expected = self.populate()
        record = self.record(first)
        external = self.write("outside.json", record.read_bytes())
        record.unlink()
        try:
            record.symlink_to(external)
        except OSError:
            self.skipTest("symlinks unavailable")
        graph = self.graph()
        self.assertEqual(graph.scan(self.root / "tools/start.py"), expected[self.root / "tools/start.py"])
        self.assertEqual(graph._persistent_cache.hits, 0)
        record.unlink()
        with patch.object(graph._persistent_cache.storage, "prune", side_effect=FileNotFoundError("concurrent eviction")):
            graph.flush_cache()
        self.assertTrue(record.is_file())

    def test_retention_below_at_and_above_limit(self):
        for count in (MAX_IMPORT_CACHE_RECORDS - 1, MAX_IMPORT_CACHE_RECORDS, MAX_IMPORT_CACHE_RECORDS + 1):
            with self.subTest(count=count):
                first = self.graph()
                directory = self.record(first).parent
                shutil.rmtree(directory, ignore_errors=True)
                first = self.graph()
                for index in range(count - 1):
                    first._persistent_cache.storage.store("imports", "old-" + str(index), {})
                first.scan(self.root / "tools/start.py")
                first.flush_cache()
                self.assertEqual(len(list(directory.glob("*.json"))), min(count, MAX_IMPORT_CACHE_RECORDS))

    def test_linked_worktrees_have_distinct_partitions(self):
        subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty", "-qm", "fixture"], cwd=self.root, check=True)
        worktree = self.root.parent / (self.root.name + "-linked")
        self.addCleanup(shutil.rmtree, worktree, True)
        subprocess.run(["git", "worktree", "add", "--detach", "-q", str(worktree)], cwd=self.root, check=True)
        shutil.copytree(self.root / "tools", worktree / "tools")
        first = self.graph()._persistent_cache
        other = LocalPythonImportGraph(worktree, scan_cache_factory=ImportScanCache)._persistent_cache
        self.assertNotEqual(first.key, other.key)
        self.assertNotEqual(first.storage.root, other.storage.root)

    def test_loaded_resolver_change_invalidates_even_with_same_source_bytes(self):
        first = self.graph()._persistent_cache.key
        original = LocalPythonImportGraph._resolve_relative
        def replacement(self, module, level, package):
            return original(self, module, level, package)
        with patch.object(LocalPythonImportGraph, "_resolve_relative", replacement):
            self.assertNotEqual(self.graph()._persistent_cache.key, first)

    def test_changed_resolution_map_or_loaded_code_cannot_publish(self):
        graph = self.graph()
        graph.modules["absent"] = self.root / "tools/pkg/leaf.py"
        self.write("tools/start.py", "import absent\n")
        graph.scan(self.root / "tools/start.py")
        with self.assertRaisesRegex(ValueError, "inventory changed"):
            graph.flush_cache()
        graph = self.graph()
        graph.scan(self.root / "tools/start.py")
        original = LocalPythonImportGraph._resolve_relative
        def replacement(self, module, level, package):
            return original(self, module, level, package)
        with patch.object(LocalPythonImportGraph, "_resolve_relative", replacement):
            with self.assertRaisesRegex(ValueError, "implementation changed"):
                graph.flush_cache()

    def test_transient_source_read_failure_requires_retry_not_unverified_fallback(self):
        graph = self.graph()
        source = self.root / "tools/start.py"
        with patch.object(Path, "read_bytes", side_effect=OSError("transient")):
            with self.assertRaisesRegex(ValueError, "input unavailable"):
                graph.scan(source)
        self.assertFalse(self.record(graph).exists())

    def test_record_replacement_during_open_is_rejected(self):
        first, expected = self.populate()
        record = self.record(first)
        raw = record.read_bytes()
        replacement = self.write("replacement.json", raw)
        original_open = os.open
        def swap(path, *args, **kwargs):
            if Path(path) == record:
                os.replace(replacement, record)
            return original_open(path, *args, **kwargs)
        with patch("source_check_cache.os.open", side_effect=swap):
            graph = self.graph()
            self.assertEqual(graph.scan(self.root / "tools/start.py"), expected[self.root / "tools/start.py"])
        self.assertEqual(graph._persistent_cache.hits, 0)

    def test_relative_and_absolute_symlink_cache_roots_do_not_redirect_writes(self):
        storage = SourceCheckCache(self.root)
        destination = self.root / "outside-cache"
        foreign = self.write("outside-cache/imports/foreign.json", "retain me")
        storage.root.parent.mkdir(parents=True, exist_ok=True)
        try:
            storage.root.symlink_to(destination, target_is_directory=True)
        except OSError:
            self.skipTest("symlinks unavailable")
        self.assertIsNone(self.graph()._persistent_cache)
        absolute_git_path = SimpleNamespace(returncode=0, stdout=str(storage.root), stderr="")
        with patch("source_check_cache.subprocess.run", return_value=absolute_git_path):
            self.assertIsNone(self.graph()._persistent_cache)
        self.assertEqual(foreign.read_text(), "retain me")
        self.assertEqual(list(destination.rglob("*.json")), [foreign])


class SourceCacheInvocationTests(unittest.TestCase):
    def tearDown(self):
        manifest.configure_import_cache("off", "full")

    def test_acceptance_modes_never_construct_persistent_storage(self):
        for profile in ("full", "release"):
            with self.subTest(profile=profile), patch("source_import_cache.SourceCheckCache", side_effect=AssertionError("acceptance used storage")):
                manifest.configure_import_cache("off", profile)
                self.assertIsNone(manifest.source_import_graph()._persistent_cache)
                with self.assertRaisesRegex(ValueError, "full/release"):
                    manifest.configure_import_cache("local", profile)

    def test_canonical_parser_rejects_source_cache_for_acceptance_before_loading(self):
        for profile in ("full", "release"):
            with self.subTest(profile=profile), patch.object(sys, "argv", ["check_all.py", "--profile", profile, "--source-cache", "local", "--list"]), \
                    patch.object(check_all, "load_manifest", side_effect=AssertionError("manifest loaded")), \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    check_all.main()
                self.assertEqual(result.exception.code, 2)

    def test_invocation_reset_clears_both_dependency_memos(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            source = root / "tools/start.py"
            for name in ("first", "second"):
                (root / f"tools/{name}.py").write_text("VALUE = 1\n")
            with patch.object(manifest, "ROOT", root):
                for mode, dependency in (("local", "first"), ("off", "second"), ("local", "first")):
                    source.write_text(f"import {dependency}\n")
                    manifest.configure_import_cache(mode, "fast")
                    expected = frozenset({f"tools/{dependency}.py"})
                    self.assertEqual(manifest.direct_local_tool_dependencies("tools/start.py"), expected)
                    self.assertEqual(manifest.transitive_local_tool_dependencies("tools/start.py"), expected)
                    manifest.flush_import_cache()

    def test_list_cli_cold_warm_corrupt_and_invalidated_parity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "tools", root / "tools", ignore=shutil.ignore_patterns("__pycache__"))
            (root / "tools/cache_probe.py").write_text("import cache_dependency\n")
            (root / "tools/cache_dependency.py").write_text("VALUE = 1\n")
            manifest_path = root / "tools/check_manifest.json"
            data = json.loads(manifest_path.read_text())
            data["checks"] = [{"id": "cache-probe", "command": ["tools/cache_probe.py"],
                               "profiles": ["fast", "full", "release"],
                               "contract_inputs": ["tools/check_manifest.json"],
                               "implementation_paths": ["tools/cache_probe.py"], "derive_trigger_paths": True}]
            manifest_path.write_text(json.dumps(data))
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty", "-qm", "fixture"], cwd=root, check=True)
            base = [sys.executable, "-B", str(root / "tools/check_all.py"), "--profile", "fast", "--list"]
            environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            def run(mode):
                result = subprocess.run([*base, "--source-cache", mode], cwd=root, env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                return result.stdout
            expected = run("off")
            self.assertEqual(run("local"), expected)
            self.assertEqual(run("local"), expected)
            cache = SourceCheckCache(root)
            records = list((cache.root / "imports").glob("*.json"))
            self.assertTrue(records)
            for path in records:
                path.write_text("{")
            self.assertEqual(run("local"), expected)
            with (root / "tools/cache_probe.py").open("a") as stream:
                stream.write("\n# Changed input must be freshly scanned.\n")
            self.assertEqual(run("local"), run("off"))
            before = {path.name: path.read_bytes() for path in (cache.root / "imports").glob("*.json")}
            for profile in ("full", "release"):
                result = subprocess.run([sys.executable, "-B", str(root / "tools/check_all.py"), "--profile", profile, "--list"], cwd=root, env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            after = {path.name: path.read_bytes() for path in (cache.root / "imports").glob("*.json")}
            self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
