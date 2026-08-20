from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from scaffold_target_structure import copy_file  # noqa: E402


class ScaffoldWriteTests(unittest.TestCase):
    def test_projected_content_is_written_as_exact_utf8_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.md"
            destination = root / "nested" / "projected.md"
            source.write_bytes(b"unused source\n")
            content = "first line\nsecond line\n"

            copy_file(source, destination, write=True, content=content)

            self.assertEqual(destination.read_bytes(), content.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
