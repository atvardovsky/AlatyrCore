from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from report_support_costs import build_installed_report, render_text
from support_topic_layout import REVIEW_WORDS, assess_topic_layout


def document(words: int) -> str:
    text = "# Guide\n\nShared constraint.\n\n## First\n\nFirst rule.\n\n## Second\n\n"
    return text + "word " * (words - len(text.split()))


class TopicLayoutTests(unittest.TestCase):
    def test_below_at_above_review_boundary(self):
        for delta, expected in ((-1, "keep-cohesive"), (0, "propose-topic-review"), (1, "propose-topic-review")):
            text = document(REVIEW_WORDS + delta)
            report = assess_topic_layout([("docs/guide.md", text)])
            row = report["documents"][0]
            self.assertEqual(row["disposition"], expected)
            self.assertEqual(row["source_sha256"], hashlib.sha256(text.encode()).hexdigest())
            self.assertEqual(row["words"], REVIEW_WORDS + delta)
            self.assertFalse(report["automatic_migration_performed"])

    def test_index_and_shared_context_are_charged_without_claiming_dependency_coverage(self):
        row = assess_topic_layout([("guide.md", document(2000))])["documents"][0]
        model = row["single_topic_model"]
        self.assertGreater(model["retained_non_topic_words"], 0)
        self.assertGreater(model["index_words_estimate"], 0)
        self.assertEqual(model["body_reduction_vs_existing_section_extraction_percent"], 0)
        self.assertEqual(model["required_dependency_cost"], "unmeasured")
        self.assertLess(model["reduction_vs_whole_percent_min"], model["reduction_vs_whole_percent_max"])

    def test_ambiguous_ids_and_unsplit_content_require_boundary_review(self):
        for text in ("# Guide\n" + "word " * 2000, document(2000) + "\n## First\nDuplicate"):
            row = assess_topic_layout([("guide.md", text)])["documents"][0]
            self.assertEqual(row["disposition"], "review-boundaries")
            self.assertNotIn("single_topic_model", row)

    def test_fenced_headings_are_not_topics_and_empty_documents_are_safe(self):
        text = "# Guide\n```markdown\n## False\n```\n" + "word " * 2000
        rows = assess_topic_layout([("empty.md", ""), ("guide.md", text)])["documents"]
        self.assertEqual(rows[0]["disposition"], "keep-cohesive")
        self.assertEqual(rows[1]["unique_h2_topics"], 0)

    def test_repeated_fenced_example_cannot_hide_retained_context(self):
        text = "# Guide\n```markdown\n## First\nsame\n```\n\n## First\nsame\n"
        row = assess_topic_layout([("guide.md", text)])["documents"][0]
        self.assertEqual(row["single_topic_model"]["retained_non_topic_words"], 7)
        indented = "# Guide\n   ## First\nfirst\n##\tSecond\nsecond\n"
        self.assertEqual(assess_topic_layout([("guide.md", indented)])["documents"][0]["unique_h2_topics"], 2)

    def test_iterable_limits_are_enforced_before_consuming_unbounded_inputs(self):
        def excessive(value):
            for _ in range(65):
                yield value
            raise AssertionError("consumed beyond input limit")

        with self.assertRaisesRegex(ValueError, "at most 64"):
            assess_topic_layout(excessive(("guide.md", "")))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "at most 64"):
                build_installed_report(Path(directory), layout_review=True, layout_paths=excessive("guide.md"))

    def test_empty_iterators_and_lists_retain_automatic_selection_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            for paths in ([], iter(())):
                result = build_installed_report(Path(directory), layout_review=True, layout_paths=paths)
                self.assertIn("not exhaustive", result["topic_layout"]["selection"])
            self.assertNotIn("topic_layout", build_installed_report(Path(directory), layout_paths=iter(())))

    def test_project_candidates_are_not_crowded_out_by_framework_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            framework = root / ".ai/framework"
            framework.mkdir(parents=True)
            for index in range(16):
                (framework / f"{index}.md").write_text(document(3000))
            project = root / ".ai/project"
            project.mkdir()
            (project / "guide.md").write_text(document(2000))
            (project / "excluded.md").write_text(document(4000))
            (project / "ignored.md").write_text(document(4000))
            (project / "support-policy.json").write_text(json.dumps({
                "exclusions": [{"pattern": ".ai/project/excluded.md"}],
                "ignored_paths": [{"pattern": ".ai/project/ignored.md"}],
            }))
            report = build_installed_report(root, layout_review=True)
        self.assertEqual([row["path"] for row in report["topic_layout"]["documents"]], [".ai/project/guide.md"])

    def test_duplicate_inputs_and_excessive_scope_are_rejected(self):
        for entries in ([('a.md', ''), ('a.md', '')], [(f'{i}.md', '') for i in range(65)]):
            with self.assertRaises(ValueError):
                assess_topic_layout(entries)

    def test_default_report_does_not_run_layout_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("support_topic_layout.assess_topic_layout") as assess:
                report = build_installed_report(Path(directory))
        assess.assert_not_called()
        self.assertNotIn("topic_layout", report)

    def test_selected_file_bounds_and_symlink_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with self.assertRaisesRegex(ValueError, "at most 64"):
                build_installed_report(root, layout_review=True, layout_paths=[f"{i}.md" for i in range(65)])
            large = root / "large.md"
            large.write_bytes(b"x" * (1024 * 1024 + 1))
            with self.assertRaisesRegex(ValueError, "1 MiB"):
                build_installed_report(root, layout_review=True, layout_paths=["large.md"])
            link = root / "link.md"
            try:
                link.symlink_to(large)
            except (OSError, NotImplementedError):
                return
            with self.assertRaisesRegex(ValueError, "symlinks"):
                build_installed_report(root, layout_review=True, layout_paths=["link.md"])

    def test_explicit_external_docs_use_fresh_bytes_without_changing_default_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = root / "docs/guide.md"
            path.parent.mkdir()
            path.write_text(document(2000))
            first = build_installed_report(root, layout_review=True, layout_paths=["docs/guide.md"])
            path.write_text(document(2100))
            second = build_installed_report(root, layout_review=True, layout_paths=["docs/guide.md"])
        self.assertEqual(first["support_surfaces"]["files"], 0)
        self.assertNotEqual(first["topic_layout"]["documents"][0]["source_sha256"], second["topic_layout"]["documents"][0]["source_sha256"])
        self.assertIn("proposal-only", render_text(second))

    def test_inventory_and_layout_share_fresh_per_invocation_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = root / ".ai/project/guide.md"
            path.parent.mkdir(parents=True)
            path.write_text(document(2000))
            first = build_installed_report(root, layout_review=True)
            path.write_text(document(2100))
            second = build_installed_report(root, layout_review=True)
            default = build_installed_report(root)
        self.assertEqual(first["support_surfaces"]["words"], 2000)
        self.assertEqual(second["support_surfaces"]["words"], 2100)
        self.assertEqual(second["topic_layout"]["documents"][0]["words"], 2100)
        self.assertEqual(default["support_surfaces"]["words"], 2100)

    def test_public_cli_is_read_only_and_rejects_unsafe_or_missing_bindings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = root / "guide.md"
            path.write_text(document(2000))
            command = [sys.executable, str(ROOT / "tools/alatyr.py"), "support-costs"]
            good = subprocess.run([*command, "--target", str(root), "--layout-review", "--layout-path", "guide.md"], capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertEqual(json.loads(good.stdout)["topic_layout"]["status"], "proposal-only")
            self.assertEqual(list(root.iterdir()), [path])
            self.assertEqual(path.read_text(), document(2000))
            for arguments in (
                ["--layout-review"],
                ["--target", str(root), "--layout-path", "guide.md"],
                ["--target", str(root), "--layout-review", "--layout-path", "../guide.md"],
                ["--target", str(root), "--layout-review", "--layout-path", str(path)],
                ["--target", str(root), "--layout-review", "--layout-path", "missing.md"],
                ["--target", str(root), "--layout-review", "--layout-path", ".ai/framework/rules.md"],
            ):
                result = subprocess.run([*command, *arguments], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0, arguments)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
