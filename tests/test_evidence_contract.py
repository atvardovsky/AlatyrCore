from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from evidence_contract import contract_digest_at, current_contract_digest  # noqa: E402


class EvidenceContractTests(unittest.TestCase):
    def test_contract_digest_changes_only_for_selected_contract_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "framework").mkdir()
            contract = root / "framework" / "rule.md"
            contract.write_text("first\n", encoding="utf-8")
            unrelated = root / "README.md"
            unrelated.write_text("first\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)

            initial = current_contract_digest(root)
            unrelated.write_text("second\n", encoding="utf-8")
            self.assertEqual(current_contract_digest(root), initial)
            contract.write_text("second\n", encoding="utf-8")
            self.assertNotEqual(current_contract_digest(root), initial)

    def test_committed_and_worktree_contract_digests_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"], cwd=root, check=True
            )
            (root / "framework").mkdir()
            (root / "framework" / "rule.md").write_text("rule\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            self.assertEqual(
                contract_digest_at(commit, root),
                current_contract_digest(root),
            )

    def test_contract_digest_rejects_git_option_as_commit(self) -> None:
        self.assertIsNone(contract_digest_at("--output=/tmp/untrusted.tar"))


if __name__ == "__main__":
    unittest.main()
