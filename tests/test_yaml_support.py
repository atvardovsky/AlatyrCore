from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from yaml_support import SAFE_LOADER, safe_compose, safe_load  # noqa: E402


class YamlSupportTests(unittest.TestCase):
    def test_safe_load_matches_pyyaml_safe_loader(self) -> None:
        source = "root:\n  enabled: true\n  values: [one, two]\n  missing: null\n"

        self.assertEqual(safe_load(source), yaml.load(source, Loader=yaml.SafeLoader))

    def test_safe_load_rejects_python_object_construction(self) -> None:
        source = "!!python/object/apply:os.system ['echo unsafe']"

        with self.assertRaises(yaml.YAMLError):
            safe_load(source)

    def test_loader_is_a_safe_loader_implementation(self) -> None:
        self.assertIn(
            SAFE_LOADER,
            {yaml.SafeLoader, getattr(yaml, "CSafeLoader", None)},
        )

    def test_safe_compose_retains_line_marks(self) -> None:
        node = safe_compose("root:\n  child: value\n")

        self.assertIsNotNone(node)
        assert node is not None
        child = node.value[0][1].value[0][0]
        self.assertEqual(child.value, "child")
        self.assertEqual(child.start_mark.line, 1)


if __name__ == "__main__":
    unittest.main()
