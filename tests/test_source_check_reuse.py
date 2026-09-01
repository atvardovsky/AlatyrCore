from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from source_check_reuse import check_input_fingerprint, reuse_decisions  # noqa: E402
from source_state import SourceEntry  # noqa: E402


def check() -> dict[str, object]:
    return {
        "id": "example",
        "command": ["tools/example.py"],
        "contract_inputs": ["docs/example.md"],
        "implementation_paths": ["tools/example.py"],
    }


class SourceCheckReuseTests(unittest.TestCase):
    def test_input_fingerprint_changes_with_declared_content(self) -> None:
        first = {
            "docs/example.md": SourceEntry("file", 0o644, "aaa"),
            "tools/example.py": SourceEntry("file", 0o644, "bbb"),
            "unrelated.txt": SourceEntry("file", 0o644, "ccc"),
        }
        second = {
            **first,
            "docs/example.md": SourceEntry("file", 0o644, "changed"),
        }

        self.assertNotEqual(
            check_input_fingerprint(check(), first)["sha256"],
            check_input_fingerprint(check(), second)["sha256"],
        )

    def test_reuse_requires_matching_manifest_runtime_command_and_inputs(self) -> None:
        item = check()
        fingerprint = check_input_fingerprint(
            item,
            {
                "docs/example.md": SourceEntry("file", 0o644, "aaa"),
                "tools/example.py": SourceEntry("file", 0o644, "bbb"),
            },
        )
        source = {"manifest_sha256": "manifest"}
        environment = {"platform": "linux", "python": "python-3.13"}
        command = [sys.executable, "tools/example.py"]
        previous = {
            "schema_version": 2,
            "report_kind": "alatyr-source-check-run",
            "source": source,
            "environment": environment,
            "checks": [
                {
                    "id": "example",
                    "status": "passed",
                    "timed_out": False,
                    "command": command,
                    "input_fingerprint": fingerprint,
                }
            ],
        }

        decisions = reuse_decisions(
            selected=[item],
            previous_report=previous,
            current_source=source,
            current_environment=environment,
            input_fingerprints={"example": fingerprint},
            commands_by_id={"example": command},
        )

        self.assertTrue(decisions["example"]["reusable"])

        changed_environment = {"platform": "linux", "python": "python-3.10"}
        decisions = reuse_decisions(
            selected=[item],
            previous_report=previous,
            current_source=source,
            current_environment=changed_environment,
            input_fingerprints={"example": fingerprint},
            commands_by_id={"example": command},
        )

        self.assertFalse(decisions["example"]["reusable"])
        self.assertEqual(decisions["example"]["reason"], "python runtime changed")


if __name__ == "__main__":
    unittest.main()
