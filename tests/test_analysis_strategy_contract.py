from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from analysis_strategy_contract import (  # noqa: E402
    load_json_object,
    validate_installed_strategy_templates,
)


class InstalledAnalysisTemplateTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        directory = tempfile.TemporaryDirectory()
        target = Path(directory.name)
        template_root = target / ".ai/assistant/templates"
        template_root.mkdir(parents=True)
        for name in ["problem-model.json", "problem-model-active-projection.json"]:
            shutil.copy2(
                ROOT / "templates/target/.ai/assistant/templates" / name,
                template_root / name,
            )
        return directory, target

    def schemas(self) -> tuple[dict[str, object], dict[str, object]]:
        return (
            load_json_object(ROOT / "schemas/alatyr-problem-model.schema.json"),
            load_json_object(
                ROOT / "schemas/alatyr-problem-model-active-projection.schema.json"
            ),
        )

    def test_current_templates_materialize_against_canonical_schemas(self) -> None:
        directory, target = self.fixture()
        self.addCleanup(directory.cleanup)

        failures = validate_installed_strategy_templates(target, *self.schemas())

        self.assertEqual(failures, {})

    def test_stale_template_versions_are_rejected(self) -> None:
        directory, target = self.fixture()
        self.addCleanup(directory.cleanup)
        model_path = target / ".ai/assistant/templates/problem-model.json"
        projection_path = (
            target / ".ai/assistant/templates/problem-model-active-projection.json"
        )
        model = json.loads(model_path.read_text(encoding="utf-8"))
        projection = json.loads(projection_path.read_text(encoding="utf-8"))
        model["schema_version"] = 2
        projection["schema_version"] = 1
        model_path.write_text(json.dumps(model), encoding="utf-8")
        projection_path.write_text(json.dumps(projection), encoding="utf-8")

        failures = validate_installed_strategy_templates(target, *self.schemas())

        self.assertIn("problem_model", failures)
        self.assertIn("active_projection", failures)
        self.assertTrue(any("4 was expected" in error for error in failures["problem_model"]))
        self.assertTrue(
            any("3 was expected" in error for error in failures["active_projection"])
        )

    def test_missing_required_template_field_is_rejected(self) -> None:
        directory, target = self.fixture()
        self.addCleanup(directory.cleanup)
        model_path = target / ".ai/assistant/templates/problem-model.json"
        model = json.loads(model_path.read_text(encoding="utf-8"))
        model.pop("lifecycle_model")
        model_path.write_text(json.dumps(model), encoding="utf-8")

        failures = validate_installed_strategy_templates(target, *self.schemas())

        self.assertTrue(
            any("lifecycle_model" in error for error in failures["problem_model"])
        )


if __name__ == "__main__":
    unittest.main()
