from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from source_check_manifest import (  # noqa: E402
    SourcePathIndex,
    broad_trigger_patterns,
    declaration_matches_source,
    declared_implementation_path,
    load_manifest,
    micro_routes,
    transitive_local_tool_dependencies,
    valid_manifest_path,
)
from local_python_import_graph import LocalPythonImportGraph  # noqa: E402


class SourceCheckManifestTests(unittest.TestCase):
    def test_reverse_dependency_closure_reaches_transitive_importers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = root / "tools"
            tools.mkdir()
            leaf = tools / "leaf.py"
            middle = tools / "middle.py"
            top = tools / "top.py"
            unrelated = tools / "unrelated.py"
            leaf.write_text("VALUE = 1\n", encoding="utf-8")
            middle.write_text("import leaf\n", encoding="utf-8")
            top.write_text("import middle\n", encoding="utf-8")
            unrelated.write_text("VALUE = 2\n", encoding="utf-8")

            impacted = LocalPythonImportGraph(root).reverse_dependents({leaf})

            self.assertEqual(
                impacted,
                {leaf.resolve(), middle.resolve(), top.resolve()},
            )

    def test_transitive_dependency_closure_reaches_shared_path_contract(self) -> None:
        dependencies = transitive_local_tool_dependencies(
            "tools/check_check_manifest.py"
        )
        self.assertIn("tools/source_check_manifest.py", dependencies)
        self.assertIn("tools/path_spec.py", dependencies)

    def test_transitive_dependency_closure_is_stable_across_repeated_reads(self) -> None:
        first = transitive_local_tool_dependencies("tools/check_check_manifest.py")
        second = transitive_local_tool_dependencies("tools/check_check_manifest.py")

        self.assertEqual(first, second)

    def test_source_path_index_tracks_parent_directories(self) -> None:
        index = SourcePathIndex.from_paths(
            [
                "tools/check_check_manifest.py",
                "docs/source-architecture.md",
                "framework/catalog/core/context-index.json",
            ]
        )

        self.assertTrue(declaration_matches_source("tools", index))
        self.assertTrue(declaration_matches_source("docs/source-architecture.md", index))
        self.assertTrue(declaration_matches_source("framework/catalog/**", index))
        self.assertFalse(declaration_matches_source("templates/target/**", index))

    def test_declared_implementation_path_accepts_literal_and_glob(self) -> None:
        check = {
            "implementation_paths": [
                "tools/check_check_manifest.py",
                "tools/target_adapter_validation/**",
            ]
        }

        self.assertTrue(
            declared_implementation_path(check, "tools/check_check_manifest.py")
        )
        self.assertTrue(
            declared_implementation_path(
                check, "tools/target_adapter_validation/debug_mode.py"
            )
        )
        self.assertFalse(declared_implementation_path(check, "tools/check_all.py"))

    def test_broad_trigger_patterns_are_diagnostic_only(self) -> None:
        check = {
            "trigger_paths": [
                "tools/check_check_manifest.py",
                "docs/**",
                "framework/catalog/core/**",
            ]
        }

        self.assertEqual(broad_trigger_patterns(check), ["docs/**"])

    def test_micro_routes_use_explicit_micro_trigger_paths(self) -> None:
        check = {
            "trigger_paths": ["**/*.md"],
            "micro_trigger_paths": ["docs/human/**"],
        }

        self.assertTrue(micro_routes(check, "docs/human/faq.md"))
        self.assertFalse(micro_routes(check, "README.md"))

    def test_micro_profile_requires_explicit_micro_trigger_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = root / "tools"
            tools.mkdir()
            (tools / "example.py").write_text("print('ok')\n", encoding="utf-8")
            manifest = tools / "check_manifest.json"
            manifest.write_text(
                """
{
  "schema_version": 2,
  "manifest_kind": "alatyr-source-checks",
  "defaults": {
    "profiles": ["full"],
    "platforms": ["all"],
    "write_scope": "none",
    "depends_on": [],
    "timeout_seconds": 30,
    "resource_class": "standard"
  },
  "checks": [
    {
      "id": "example",
      "command": ["tools/example.py"],
      "profiles": ["micro", "full"],
      "contract_inputs": ["tools/check_manifest.json"],
      "implementation_paths": ["tools/example.py"],
      "trigger_paths": ["tools/check_manifest.json", "tools/example.py"]
    }
  ]
}
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "micro_trigger_paths"):
                load_manifest(manifest, root=root)

    def test_load_manifest_normalizes_defaults_and_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = root / "tools"
            tools.mkdir()
            (tools / "example.py").write_text("print('ok')\n", encoding="utf-8")
            manifest = tools / "check_manifest.json"
            manifest.write_text(
                """
{
  "schema_version": 2,
  "manifest_kind": "alatyr-source-checks",
  "defaults": {
    "profiles": ["full"],
    "platforms": ["all"],
    "write_scope": "none",
    "depends_on": [],
    "timeout_seconds": 30,
    "resource_class": "standard"
  },
  "checks": [
    {
      "id": "example",
      "command": ["tools/example.py"],
      "contract_inputs": ["tools/check_manifest.json"],
      "implementation_paths": ["tools/example.py"],
      "trigger_paths": ["tools/check_manifest.json", "tools/example.py"]
    }
  ]
}
""".strip(),
                encoding="utf-8",
            )

            checks = load_manifest(manifest, root=root)

        self.assertEqual(checks[0]["id"], "example")
        self.assertEqual(checks[0]["always_for_changed"], False)
        self.assertEqual(checks[0]["resource_class"], "standard")

    def test_valid_manifest_path_rejects_escaping_paths(self) -> None:
        self.assertTrue(valid_manifest_path("tools/example.py"))
        self.assertTrue(valid_manifest_path("tools/**/*.py"))
        self.assertFalse(valid_manifest_path("../outside"))
        self.assertFalse(valid_manifest_path("/absolute/path"))
        self.assertFalse(valid_manifest_path("tools\\example.py"))


if __name__ == "__main__":
    unittest.main()
