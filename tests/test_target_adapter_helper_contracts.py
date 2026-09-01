from __future__ import annotations

from dataclasses import dataclass
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.files import missing_target_files  # noqa: E402
from target_adapter_validation.manifest_paths import (  # noqa: E402
    manifest_path_mismatches,
)


class Host:
    def __init__(self, root: Path) -> None:
        self.root = root

    def target_path(self, relpath: str) -> Path:
        return self.root / relpath


@dataclass(frozen=True)
class Scalar:
    value: str


@dataclass(frozen=True)
class Manifest:
    scalars: dict[tuple[str, str], Scalar]


class TargetAdapterHelperContractTests(unittest.TestCase):
    def test_missing_target_files_reports_only_absent_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".ai/assistant").mkdir(parents=True)
            (root / ".ai/assistant/help.md").write_text("help", encoding="utf-8")

            self.assertEqual(
                missing_target_files(
                    Host(root),
                    [
                        ".ai/assistant/help.md",
                        ".ai/assistant/missing.md",
                    ],
                ),
                [".ai/assistant/missing.md"],
            )

    def test_manifest_path_mismatches_returns_missing_and_wrong_scalars(self) -> None:
        manifest = Manifest(
            scalars={
                ("operations", "help"): Scalar(".ai/assistant/help.md"),
                ("operations", "flow"): Scalar(".ai/assistant/wrong.md"),
            }
        )

        mismatches = manifest_path_mismatches(
            manifest,
            {
                ("operations", "help"): ".ai/assistant/help.md",
                ("operations", "flow"): ".ai/assistant/flow.md",
                ("operations", "missing"): ".ai/assistant/missing.md",
            },
        )

        self.assertEqual(
            [(mismatch.key, mismatch.expected) for mismatch in mismatches],
            [
                (("operations", "flow"), ".ai/assistant/flow.md"),
                (("operations", "missing"), ".ai/assistant/missing.md"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
