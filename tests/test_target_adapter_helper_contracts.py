from __future__ import annotations

import ast
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
    def test_target_validators_route_content_reads_through_validation_context(self) -> None:
        validation_root = ROOT / "tools" / "target_adapter_validation"
        paths = [ROOT / "tools" / "validate_target_adapter.py"]
        paths.extend(sorted(validation_root.glob("*.py")))
        source_owned_modules = {
            "contract_compatibility.py",
            "framework_baseline.py",
        }
        source_owned_receivers = {
            "ADAPTER_MANIFEST_SCHEMA",
            "DEBUG_SESSION_SCHEMA",
            "ENGINEERING_EVIDENCE_SCHEMA",
        }
        explicitly_external_functions = {
            "load_validator_config",
            "check_migration_diff_evidence",
        }
        violations: list[str] = []

        class ReadVisitor(ast.NodeVisitor):
            def __init__(self, path: Path, source: str) -> None:
                self.path = path
                self.source = source
                self.functions: list[str] = []

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self.functions.append(node.name)
                self.generic_visit(node)
                self.functions.pop()

            def visit_Call(self, node: ast.Call) -> None:
                function = node.func
                if not (
                    isinstance(function, ast.Attribute)
                    and function.attr in {"read_text", "read_bytes", "open"}
                ):
                    self.generic_visit(node)
                    return
                receiver = ast.get_source_segment(self.source, function.value) or ""
                routed = receiver in {
                    "self",
                    "context",
                    "sink",
                    "self.context",
                    "self.filesystem",
                }
                source_owned = (
                    self.path.name in source_owned_modules
                    or receiver in source_owned_receivers
                )
                external = bool(self.functions) and self.functions[-1] in (
                    explicitly_external_functions
                )
                context_implementation = self.path.name == "context.py"
                if not (routed or source_owned or external or context_implementation):
                    relative = self.path.relative_to(ROOT).as_posix()
                    violations.append(
                        f"{relative}:{node.lineno}: {receiver}.{function.attr}"
                    )
                self.generic_visit(node)

        for path in paths:
            source = path.read_text(encoding="utf-8")
            ReadVisitor(path, source).visit(ast.parse(source, filename=str(path)))

        self.assertEqual(violations, [])

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
