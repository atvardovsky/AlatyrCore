import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import scaffold_target_structure as scaffold
from target_adapter_validation.harness_scenarios.common import validator
from target_adapter_validation.context import TargetRepositoryView
from target_adapter_validation.analysis_strategies import load_problem_model_schema


class OperationReuseTests(unittest.TestCase):
    def test_scaffold_loads_continuity_and_shared_surfaces_once_per_run(self):
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(target=Path(directory), profile="full", framework_pack="matched",
                                   enable_module=[], assistant_surface=[], write=False, overwrite_existing=False)
            with patch.object(scaffold, "load_surfaces", wraps=scaffold.load_surfaces) as surfaces, patch.object(
                scaffold, "projected_continuity_policy", wraps=scaffold.projected_continuity_policy
            ) as continuity:
                result = scaffold.run_scaffold(args)
            self.assertFalse(result.blocked)
            self.assertEqual(surfaces.call_count, 1)
            self.assertEqual(continuity.call_count, 1)

    def test_approval_shape_and_scope_share_json_and_reject_invalid_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            path = target / "approval.json"
            for content in (b'{"scope":{},"diff":{}}', b'{', b'[]', b'null', b'\xff'):
                with self.subTest(content=content):
                    path.write_bytes(content)
                    instance = validator(target)
                    original = json.loads
                    with patch("target_adapter_validation.context.json.loads", wraps=original) as parse:
                        instance.load_approval_scope(path)
                        instance.check_approval_record_shape([path])
                    parses = [call for call in parse.call_args_list if call.args and call.args[0] == content.decode("utf-8", errors="replace")]
                    self.assertLessEqual(len(parses), 1)
                    if content != b'{"scope":{},"diff":{}}':
                        self.assertTrue(instance.findings)

    def test_schema_reuse_does_not_hide_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "model.json"
            path.write_text('{"type":"object"}')
            view = TargetRepositoryView(root)
            with patch("target_adapter_validation.analysis_strategies.PROBLEM_MODEL_SCHEMA", path):
                first = load_problem_model_schema(view)
                self.assertIs(load_problem_model_schema(view), first)
                path.write_text('{"type":"string"}')
                self.assertTrue(view.finalize())
                self.assertEqual(load_problem_model_schema(TargetRepositoryView(root))["type"], "string")

    def test_cached_approval_reader_preserves_path_escape_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir()
            outside = root / "outside.json"
            outside.write_text('{"scope":{},"diff":{}}')
            instance = validator(target)
            self.assertIsNone(instance.load_approval_scope(outside))
            self.assertIn("TARGET_PATH_ESCAPE", {finding.code for finding in instance.findings})
