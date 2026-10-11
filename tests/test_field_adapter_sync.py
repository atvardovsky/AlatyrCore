from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from bootstrap_index import build_bootstrap_index, build_from_target
from change_package_contract import package_index_projection, package_index_projection_mismatches
from check_change_packages import changed_index_validator, git, valid_package_fixture
from context_catalog import ContextCatalogError, codebook_schema_version
from target_adapter_validation.context_catalogs import validate_context_catalog_contract
from target_validation_support import parse_manifest


class SemanticSchemaTests(unittest.TestCase):
    def test_schema_requires_supported_integer(self):
        for value in [None, True, False, "2", {}, [], 0, 3]:
            with self.subTest(value=value), self.assertRaises(ContextCatalogError):
                codebook_schema_version({"schema_version": value})
        self.assertEqual(codebook_schema_version({"schema_version": 2}), 2)

    def test_generator_checks_manifest_router_and_actual_index(self):
        manifest = "context_routing:\n  semantic_codebook_schema_version: 2\n"
        router = {"semantic_codebook": {"schema_version": 2}}
        args = (manifest, "# Map", json.dumps(router))
        result = build_bootstrap_index(*args, semantic_index_text='{"schema_version":2}')
        self.assertEqual(result["semantic_preload"]["codebook_schema_version"], 2)
        for bad in [1, True, "2", None, {}, []]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                build_bootstrap_index(manifest, "# Map", json.dumps({"semantic_codebook": {"schema_version": bad}}), semantic_index_text='{"schema_version":2}')
        with self.assertRaises(ValueError):
            build_bootstrap_index(manifest.replace(": 2", ": 1"), "# Map", json.dumps(router), semantic_index_text='{"schema_version":2}')

    def test_installed_validation_detects_independent_schema_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            shutil.copytree(ROOT / "templates/target", target, dirs_exist_ok=True)
            shutil.copytree(ROOT / "framework", target / ".ai/framework")
            bootstrap_path = target / ".ai/assistant/bootstrap-index.json"
            baseline = build_from_target(target)
            bootstrap_path.write_text(json.dumps(baseline), encoding="utf-8")
            router_path = target / ".ai/assistant/context-router.json"
            router = json.loads(router_path.read_text(encoding="utf-8"))
            manifest_path = target / ".ai/alatyr.yaml"
            manifest_text = manifest_path.read_text(encoding="utf-8")
            for surface in ["router", "bootstrap", "manifest"]:
                for bad in [1, None, True, {}, []]:
                    with self.subTest(surface=surface, bad=bad):
                        changed_router = copy.deepcopy(router)
                        changed_bootstrap = copy.deepcopy(baseline)
                        changed_manifest = manifest_text
                        if surface == "router":
                            changed_router["semantic_codebook"]["schema_version"] = bad
                        elif surface == "bootstrap":
                            changed_bootstrap["semantic_preload"]["codebook_schema_version"] = bad
                        else:
                            changed_manifest = manifest_text.replace("semantic_codebook_schema_version: 2", "semantic_codebook_schema_version: " + json.dumps(bad))
                        router_path.write_text(json.dumps(changed_router), encoding="utf-8")
                        bootstrap_path.write_text(json.dumps(changed_bootstrap), encoding="utf-8")
                        manifest_path.write_text(changed_manifest, encoding="utf-8")
                        validator = changed_index_validator(target)
                        validate_context_catalog_contract(validator, parse_manifest(manifest_path))
                        self.assertIn("CONTEXT_SEMANTIC_SCHEMA_DRIFT", {finding.code for finding in validator.findings})


class ResidualRiskProjectionTests(unittest.TestCase):
    def test_risk_projection_is_bounded_and_exactly_bound(self):
        record = {"validation": {"residual_risks": ["large risk " * 10000]}}
        projection = package_index_projection(record)
        self.assertLess(len(projection["residual_risk"]), 160)
        self.assertEqual(package_index_projection_mismatches(projection, record), ())
        record["validation"]["residual_risks"][0] += "changed"
        self.assertIn("residual_risk", package_index_projection_mismatches(projection, record))

    def test_changed_record_risk_drift_is_detected_in_unchanged_shard(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            path, record = valid_package_fixture(target)
            index_path = target / ".ai/assistant/change-packages/index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            shard_path = index_path.parent / "archive/index.json"
            shard_path.parent.mkdir()
            shard = {"schema_version": 1, "index_kind": "target-change-package-index-shard", "shard_id": "archive", "records": index["records"]}
            shard_path.write_text(json.dumps(shard), encoding="utf-8")
            import hashlib
            index["records"] = []
            index["shards"] = [{"shard_id": "archive", "path": shard_path.relative_to(target).as_posix(), "sha256": hashlib.sha256(shard_path.read_bytes()).hexdigest(), "record_count": 1}]
            index_path.write_text(json.dumps(index), encoding="utf-8")
            git(target, "add", ".")
            git(target, "commit", "-qm", "record risk projection")
            record["validation"]["residual_risks"] = ["Authenticated verification pending"]
            path.write_text(json.dumps(record), encoding="utf-8")
            validator = changed_index_validator(target)
            validator.check_change_package_index()
            self.assertTrue(any(f.code == "PACKAGE_INDEX_PROJECTION" and "residual_risk" in f.message for f in validator.findings))


if __name__ == "__main__":
    unittest.main()
