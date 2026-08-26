from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from evidence_contract import contract_digest_at, current_contract_digest  # noqa: E402


class EvidenceContractTests(unittest.TestCase):
    @staticmethod
    def initialize_repository(root: Path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.invalid"],
            cwd=root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=root, check=True
        )

    @staticmethod
    def commit(root: Path, message: str = "fixture") -> str:
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", message], cwd=root, check=True)
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def test_contract_digest_changes_only_for_selected_contract_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize_repository(root)
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
            self.initialize_repository(root)
            (root / "framework").mkdir()
            (root / ".gitattributes").write_bytes(b"* text=auto eol=lf\n")
            (root / "framework" / "rule.md").write_bytes(b"rule\r\n")
            commit = self.commit(root)

            self.assertEqual(
                contract_digest_at(commit, root),
                current_contract_digest(root),
            )

    def test_core_autocrlf_contract_digests_match_on_every_host(self) -> None:
        for autocrlf in ["true", "input"]:
            with self.subTest(core_autocrlf=autocrlf):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.initialize_repository(root)
                    subprocess.run(
                        ["git", "config", "core.autocrlf", autocrlf],
                        cwd=root,
                        check=True,
                    )
                    (root / "framework").mkdir()
                    (root / "framework" / "rule.md").write_bytes(b"rule\r\n")
                    commit = self.commit(root)

                    self.assertEqual(
                        contract_digest_at(commit, root),
                        current_contract_digest(root),
                    )

    def test_binary_contract_content_remains_byte_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize_repository(root)
            (root / ".gitattributes").write_bytes(b"* text=auto eol=lf\n")
            (root / "framework").mkdir()
            binary = root / "framework" / "fixture.bin"
            binary.write_bytes(b"\0binary\r\ncontent")
            commit = self.commit(root)

            self.assertEqual(
                contract_digest_at(commit, root), current_contract_digest(root)
            )

    def test_untracked_text_uses_canonical_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize_repository(root)
            (root / ".gitattributes").write_bytes(b"* text=auto eol=lf\n")
            (root / "framework").mkdir()
            contract = root / "framework" / "rule.md"
            contract.write_bytes(b"rule\n")
            lf_digest = current_contract_digest(root)
            contract.write_bytes(b"rule\r\n")

            self.assertEqual(current_contract_digest(root), lf_digest)

    def test_explicit_binary_attribute_preserves_crlf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize_repository(root)
            (root / ".gitattributes").write_bytes(b"*.bin -text\n")
            (root / "framework").mkdir()
            binary = root / "framework" / "fixture.bin"
            binary.write_bytes(b"binary\r\ncontent")
            commit = self.commit(root)

            self.assertEqual(
                contract_digest_at(commit, root), current_contract_digest(root)
            )

    def test_symlink_contract_content_remains_byte_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize_repository(root)
            (root / "framework").mkdir()
            link = root / "framework" / "rule-link.md"
            try:
                os.symlink("../README.md", link)
            except OSError as exc:
                self.skipTest(f"symlinks are unavailable: {exc}")
            commit = self.commit(root)

            self.assertEqual(
                contract_digest_at(commit, root), current_contract_digest(root)
            )

    def test_clean_transform_attribute_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize_repository(root)
            (root / ".gitattributes").write_bytes(b"*.md filter=fixture\n")
            (root / "framework").mkdir()
            (root / "framework" / "rule.md").write_bytes(b"rule\n")

            with self.assertRaisesRegex(ValueError, "requires a clean transform"):
                current_contract_digest(root)

    def test_contract_digest_rejects_git_option_as_commit(self) -> None:
        self.assertIsNone(contract_digest_at("--output=/tmp/untrusted.tar"))

    def test_historical_digest_ignores_current_checkout_attributes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize_repository(root)
            (root / "framework").mkdir()
            (root / "framework" / "rule.md").write_bytes(b"rule\r\n")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-qm", "historical fixture"],
                cwd=root,
                check=True,
            )
            historical = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            digest_before = contract_digest_at(historical, root)

            (root / ".gitattributes").write_text(
                "* text=auto eol=lf\n", encoding="utf-8"
            )
            subprocess.run(["git", "add", ".gitattributes"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-qm", "add checkout policy"],
                cwd=root,
                check=True,
            )

            self.assertEqual(contract_digest_at(historical, root), digest_before)


if __name__ == "__main__":
    unittest.main()
