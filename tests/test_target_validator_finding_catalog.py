from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from render_target_validator_findings import (  # noqa: E402
    CODE_PATTERN,
    collect,
    json_object_loader_prefix,
    source_paths,
)


class TargetValidatorFindingCatalogTests(unittest.TestCase):
    def test_catalog_contains_only_concrete_finding_codes(self) -> None:
        catalog = collect()
        codes = {entry["code"] for entry in catalog["finding_codes"]}

        self.assertTrue(codes)
        self.assertTrue(all(CODE_PATTERN.fullmatch(code) for code in codes))
        self.assertNotIn("{prefix}_INVALID_JSON", codes)

    def test_json_object_loader_codes_are_expanded(self) -> None:
        catalog = collect()
        codes = {entry["code"] for entry in catalog["finding_codes"]}
        prefixes: set[str] = set()
        for path in source_paths():
            relpath = path.relative_to(ROOT).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"))
            prefixes.update(
                prefix
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                for prefix in [json_object_loader_prefix(node, relpath)]
                if prefix is not None
            )

        self.assertGreaterEqual(len(prefixes), 10)
        for prefix in prefixes:
            self.assertIn(f"{prefix}_INVALID_JSON", codes)
            self.assertIn(f"{prefix}_INVALID_SHAPE", codes)

    def test_json_object_loader_rejects_dynamic_prefixes(self) -> None:
        call = ast.parse("self.load_json_object(path, prefix)").body[0].value
        with self.assertRaisesRegex(ValueError, "literal finding-code prefix"):
            json_object_loader_prefix(call, "fixture.py")


if __name__ == "__main__":
    unittest.main()
