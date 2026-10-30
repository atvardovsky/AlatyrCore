from __future__ import annotations

import sys
import json
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_release_drift as drift

from check_release_drift import (  # noqa: E402
    SCHEMA_CONTRACT_PATHS,
    contract_digest,
    materialize,
    nearest_release_baseline,
    nearest_tagged_baseline,
    prior_changelog_versions,
    release_checkpoint,
    unreleased_section_is_empty,
    validate_committed_report,
)
from record_release_checkpoint import checkpoint_record  # noqa: E402
from check_versioning import (  # noqa: E402
    validate_current_release_binding,
    validate_release_tag,
)


class CheckpointAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.baselines = self.root / "docs/releases/baselines"
        self.baselines.mkdir(parents=True)
        self.command("init", "-q")
        self.command("config", "user.name", "Fixture")
        self.command("config", "user.email", "fixture@example.invalid")
        (self.root / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n\n- None.\n\n## 3.0.0\n\n## 2.0.0\n\n## 1.0.0\n")
        self.commits = {}
        for number in (1, 2, 3):
            version = f"{number}.0.0"
            for path, value in (("VERSION", version), ("ADAPTER_SCHEMA_VERSION", "1"), ("TEMPLATE_VERSION", "1")):
                (self.root / path).write_text(value + "\n")
            self.command("add", ".")
            self.command("commit", "-qm", version)
            self.commits[version] = self.command("rev-parse", "HEAD")
            report = self.root / f"docs/releases/{version}-migration.md"
            bindings = [f"To framework version: `{version}`", "To adapter schema version: `1`",
                        "To template version: `1`", f"To contract SHA-256: `{'a' * 64}`"]
            if number > 1:
                previous = f"{number - 1}.0.0"
                bindings += [f"From manifest: `release-checkpoint:{previous}:framework/rule-registry.json`",
                             "To manifest: `source-tree:framework/rule-registry.json`",
                             f"From framework version: `{previous}`", "From adapter schema version: `1`",
                             "From template version: `1`", f"From contract SHA-256: `{'a' * 64}`",
                             "Source validation: `passed`", "Source validation commands:",
                             "- `python3 tools/check_all.py --profile full`", "Source validation result: `passed`",
                             "Source validation revision: `fixture`", "Source validation completed at: `2026-10-30T12:00:00Z`"]
            report.write_text("\n".join(bindings) + "\n")
            record = {"schema_version": 1 if number == 1 else 2, "baseline_kind": "source-release-checkpoint",
                      "framework_version": version, "publication_status": "untagged-release-checkpoint",
                      "migration_report": f"docs/releases/{version}-migration.md", "source_commit": self.commits[version],
                      "contract_sha256": "a" * 64, "adapter_schema_version": "1", "template_version": "1"}
            if number > 1:
                record.update(previous_baseline=f"release-checkpoint:{number - 1}.0.0",
                              migration_report_sha256=hashlib.sha256(report.read_bytes()).hexdigest())
            (self.baselines / f"{version}.json").write_text(json.dumps(record))
        self.addCleanup(patch.stopall)
        patch.object(drift, "ROOT", self.root).start()
        patch.object(drift, "RELEASE_BASELINE_DIR", self.baselines).start()

    def command(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, text=True, stderr=subprocess.STDOUT).strip()

    def test_dag_nodes_validated_once_and_later_invocations_are_fresh(self):
        with patch.object(drift, "_validate_release_checkpoint", wraps=drift._validate_release_checkpoint) as validate:
            drift.audit_release_checkpoints()
            self.assertCountEqual([call.args[0] for call in validate.call_args_list], ["1.0.0", "2.0.0", "3.0.0"])
            first = release_checkpoint("3.0.0")
            self.assertEqual(first.version, "3.0.0")
            self.assertEqual(validate.call_count, 6)
        (self.root / "docs/releases/2.0.0-migration.md").write_text("corrupt")
        with self.assertRaises(RuntimeError):
            drift.audit_release_checkpoints()

    def test_cached_and_uncached_results_match_and_seen_cannot_bypass_cycles(self):
        expected = release_checkpoint("3.0.0")
        with drift.scoped_release_checkpoints():
            self.assertEqual(release_checkpoint("3.0.0"), expected)
            self.assertEqual(release_checkpoint("2.0.0").version, "2.0.0")
            with self.assertRaisesRegex(RuntimeError, "cycle"):
                release_checkpoint("3.0.0", seen={"3.0.0"})
        for edges in ({"1.0.0": "1.0.0"}, {"1.0.0": "2.0.0", "2.0.0": "1.0.0"}):
            original = drift._validate_release_checkpoint
            def recursive(version, *, seen=None):
                if version in edges:
                    return release_checkpoint(edges[version], seen=seen)
                return original(version, seen=seen)
            with self.subTest(edges=edges), patch.object(drift, "_validate_release_checkpoint", side_effect=recursive):
                with self.assertRaisesRegex(RuntimeError, "cycle"):
                    release_checkpoint("1.0.0")
        self.assertIsNotNone(release_checkpoint("3.0.0"))

    def test_transitive_seen_constraints_match_cold_and_warm_results(self):
        for seen in ({"1.0.0"}, {"2.0.0"}, {"3.0.0"}, {"1.0.0", "2.0.0"}):
            with self.subTest(seen=seen):
                with self.assertRaises(RuntimeError) as cold:
                    release_checkpoint("3.0.0", seen=seen)
                with drift.scoped_release_checkpoints():
                    release_checkpoint("3.0.0")
                    with self.assertRaises(RuntimeError) as warm:
                        release_checkpoint("3.0.0", seen=seen)
                self.assertEqual(str(cold.exception), str(warm.exception))

    def test_crlf_prose_uses_text_newlines_but_report_hashes_remain_exact(self):
        for path in [self.root / "CHANGELOG.md", *self.root.glob("docs/releases/*-migration.md")]:
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        for path in self.baselines.glob("*.json"):
            data = json.loads(path.read_text())
            if data["schema_version"] == 2:
                data["migration_report_sha256"] = hashlib.sha256((self.root / data["migration_report"]).read_bytes()).hexdigest()
                path.write_text(json.dumps(data))
        self.assertEqual(release_checkpoint("3.0.0").version, "3.0.0")
        report = self.root / "docs/releases/3.0.0-migration.md"
        report.write_bytes(report.read_bytes().replace(b"\r\n", b"\n"))
        with self.assertRaisesRegex(RuntimeError, "migration report digest differs"):
            release_checkpoint("3.0.0")

    def test_input_changes_after_cache_warmup_invalidate_the_scope(self):
        paths = [self.baselines / "1.0.0.json", self.root / "docs/releases/1.0.0-migration.md", self.root / "CHANGELOG.md"]
        for path in paths:
            raw = path.read_bytes()
            for mutation in ("edit", "delete", "directory"):
                with self.subTest(path=path, mutation=mutation):
                    try:
                        with self.assertRaises((ValueError, RuntimeError)):
                            with drift.scoped_release_checkpoints():
                                release_checkpoint("3.0.0")
                                if mutation == "edit":
                                    path.write_bytes(raw + b"changed")
                                else:
                                    path.unlink()
                                    if mutation == "directory":
                                        path.mkdir()
                                release_checkpoint("3.0.0")
                    finally:
                        if path.is_dir():
                            path.rmdir()
                        path.write_bytes(raw)

    def test_added_checkpoint_and_negative_dependency_are_rechecked(self):
        for warm_missing in (False, True):
            path = self.baselines / "4.0.0.json"
            with self.subTest(warm_missing=warm_missing):
                try:
                    with self.assertRaisesRegex(RuntimeError, "inputs changed"):
                        with drift.scoped_release_checkpoints():
                            if warm_missing:
                                self.assertIsNone(release_checkpoint("4.0.0"))
                            release_checkpoint("3.0.0")
                            path.write_text("{}")
                finally:
                    path.unlink(missing_ok=True)

    def test_head_and_new_retargeted_or_deleted_tags_are_rechecked(self):
        original_head = self.command("rev-parse", "HEAD")
        with self.assertRaisesRegex(RuntimeError, "inputs changed"):
            with drift.scoped_release_checkpoints():
                release_checkpoint("3.0.0")
                self.command("commit", "--allow-empty", "-qm", "concurrent")
        self.command("reset", "--soft", original_head)
        for action in ("add", "move", "delete"):
            if action != "add":
                self.command("tag", "v0.0.0", self.commits["1.0.0"])
            with self.subTest(action=action), self.assertRaisesRegex(RuntimeError, "inputs changed"):
                with drift.scoped_release_checkpoints():
                    release_checkpoint("3.0.0")
                    if action == "delete":
                        self.command("tag", "-d", "v0.0.0")
                    else:
                        self.command("tag", "-f", "v0.0.0", self.commits["2.0.0"])
            if action != "delete":
                self.command("tag", "-d", "v0.0.0")

    def test_tag_precedence_uses_immutable_commit_and_missing_reports_fail(self):
        self.command("tag", "-a", "v2.0.0", "-m", "fixture", self.commits["2.0.0"])
        baseline, _ = nearest_release_baseline("3.0.0")
        self.assertEqual((baseline.label, baseline.ref), ("v2.0.0", self.commits["2.0.0"]))
        self.command("tag", "-d", "v2.0.0")
        (self.root / "docs/releases/2.0.0-migration.md").unlink()
        with self.assertRaisesRegex(RuntimeError, "migration report is missing"):
            release_checkpoint("3.0.0")

    def test_nonancestor_checkpoint_and_conflicting_identity_remain_rejected(self):
        self.command("checkout", "--orphan", "unrelated")
        self.command("commit", "--allow-empty", "-qm", "unrelated")
        with self.assertRaisesRegex(RuntimeError, "not an ancestor"):
            release_checkpoint("1.0.0")
        self.command("checkout", "-q", self.commits["3.0.0"])
        with drift.scoped_release_checkpoints():
            release_checkpoint("1.0.0")
            with self.assertRaisesRegex(RuntimeError, "differs from source_commit"):
                path = self.baselines / "2.0.0.json"
                data = json.loads(path.read_text())
                data["source_commit"] = self.commits["1.0.0"]
                path.write_text(json.dumps(data))
                release_checkpoint("2.0.0")


class CommittedReadTests(unittest.TestCase):
    def test_only_immutable_blobs_are_reused_and_only_within_one_audit(self):
        commit = "a" * 40
        with patch.object(drift, "require_git_text", return_value="content") as read:
            with drift.scoped_committed_reads():
                self.assertEqual(drift.read_at(commit, "VERSION"), "content")
                self.assertEqual(drift.read_at(commit, "VERSION"), "content")
                self.assertEqual(read.call_count, 1)
                for ref in ("HEAD", "v1.0.0", commit[:7]):
                    drift.read_at(ref, "VERSION")
                    drift.read_at(ref, "VERSION")
                self.assertEqual(read.call_count, 7)
                with patch.object(drift, "ROOT", ROOT / "other-fixture"):
                    drift.read_at(commit, "VERSION")
                self.assertEqual(read.call_count, 8)
            with drift.scoped_committed_reads():
                drift.read_at(commit, "VERSION")
            self.assertEqual(read.call_count, 9)
            drift.read_at(commit, "VERSION")
            self.assertEqual(read.call_count, 10)

    def test_missing_objects_are_not_cached_as_success(self):
        with patch.object(drift, "require_git_text", side_effect=[RuntimeError("missing"), "recovered"]) as read:
            with drift.scoped_committed_reads():
                with self.assertRaisesRegex(RuntimeError, "missing"):
                    drift.read_at("a" * 64, "VERSION")
                self.assertEqual(drift.read_at("a" * 64, "VERSION"), "recovered")
                self.assertEqual(drift.read_at("a" * 64, "VERSION"), "recovered")
            self.assertEqual(read.call_count, 2)

    def test_byte_and_entry_boundaries_fall_back_to_live_reads(self):
        for size in (3, 4, 5):
            with self.subTest(size=size), patch.object(drift, "MAX_COMMITTED_READ_BYTES", 4), \
                    patch.object(drift, "require_git_text", return_value="x" * size) as read:
                with drift.scoped_committed_reads():
                    drift.read_at("a" * 40, "VERSION")
                    drift.read_at("a" * 40, "VERSION")
                self.assertEqual(read.call_count, 2 if size > 4 else 1)
        with patch.object(drift, "MAX_COMMITTED_READ_ENTRIES", 2), \
                patch.object(drift, "require_git_text", return_value="x") as read:
            with drift.scoped_committed_reads():
                for index in range(3):
                    drift.read_at("a" * 40, str(index))
                    drift.read_at("a" * 40, str(index))
            self.assertEqual(read.call_count, 4)

    def test_current_files_are_never_cached(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(drift, "ROOT", Path(directory)):
            path = Path(directory) / "VERSION"
            with drift.scoped_committed_reads():
                path.write_text("first", encoding="utf-8")
                self.assertEqual(drift.read_current("VERSION"), "first")
                path.write_text("second", encoding="utf-8")
                self.assertEqual(drift.read_current("VERSION"), "second")


class ReleaseBaselineTests(unittest.TestCase):
    def test_historical_none_marker_is_empty_but_mixed_entries_are_not(self) -> None:
        self.assertTrue(unreleased_section_is_empty("## Unreleased\n\n- None.\n\n## 1.0.0\n"))
        self.assertFalse(unreleased_section_is_empty("## Unreleased\n\n- None.\n- Pending repair.\n\n## 1.0.0\n"))

    def test_release_checkpoint_requires_empty_unreleased_section(self) -> None:
        self.assertTrue(
            unreleased_section_is_empty(
                "# Changelog\n\n## Unreleased\n\n- No unreleased changes.\n\n## 1.0.0\n"
            )
        )
        self.assertFalse(
            unreleased_section_is_empty(
                "# Changelog\n\n## Unreleased\n\n- Pending change.\n\n## 1.0.0\n"
            )
        )

    def test_committed_report_requires_completed_source_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "docs/releases/2.0.0-migration.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "\n".join(
                    [
                        "From manifest: `baseline:framework/rule-registry.json`",
                        "To manifest: `source-tree:framework/rule-registry.json`",
                        "From framework version: `1.0.0`",
                        "To framework version: `2.0.0`",
                        "From adapter schema version: `1`",
                        "To adapter schema version: `1`",
                        "From template version: `1`",
                        "To template version: `2`",
                        "From contract SHA-256: `from-digest`",
                        "To contract SHA-256: `to-digest`",
                        "Source validation: `passed`",
                        "Source validation commands:",
                        "- `python3 tools/check_all.py --profile full`",
                        "Source validation result: `all checks passed`",
                        "Source validation revision: `fixture-tree`",
                        "Source validation completed at: `2026-09-04T12:00:00+00:00`",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            args = {
                "baseline": "baseline",
                "from_version": "1.0.0",
                "to_version": "2.0.0",
                "from_adapter": "1",
                "to_adapter": "1",
                "from_template": "1",
                "to_template": "2",
                "from_digest": "from-digest",
                "to_digest": "to-digest",
            }
            with patch("check_release_drift.ROOT", root), drift.scoped_committed_reads():
                self.assertEqual(validate_committed_report(**args), [])
                report.write_text(
                    report.read_text(encoding="utf-8").replace(
                        "Source validation: `passed`",
                        "Source validation: `pending`",
                    ),
                    encoding="utf-8",
                )
                self.assertTrue(validate_committed_report(**args))

                report.write_text(
                    report.read_text(encoding="utf-8")
                    .replace("Source validation: `pending`", "Source validation: `passed`")
                    .replace(
                        "Source validation completed at: `2026-09-04T12:00:00+00:00`",
                        "Source validation completed at: `2026-09-04 12:00:00`",
                    ),
                    encoding="utf-8",
                )
                failures = validate_committed_report(**args)
                self.assertTrue(
                    any("timezone-aware ISO-8601" in failure for failure in failures)
                )

    def test_prefers_nearest_available_checkpoint_over_distant_tag(self) -> None:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

        baseline, intervening = nearest_release_baseline(version)
        prior_versions = prior_changelog_versions(version)

        self.assertEqual(baseline.label, f"release-checkpoint:{baseline.version}")
        self.assertEqual(baseline.kind, "checkpoint")
        self.assertIn(baseline.version, prior_versions)
        self.assertEqual(intervening, prior_versions[: prior_versions.index(baseline.version)])

    def test_current_chain_uses_latest_checkpoint(self) -> None:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        baseline, _intervening = nearest_release_baseline(version)
        # The immediate prior changelog version has a reviewed checkpoint;
        # future releases must not leave this assertion pinned to alpha.91.
        previous_version = prior_changelog_versions(version)[0]
        checkpoint = release_checkpoint(previous_version)
        self.assertIsNotNone(checkpoint)
        self.assertEqual(baseline.label, f"release-checkpoint:{previous_version}")
        self.assertEqual(baseline.ref, checkpoint.ref)

    def test_unverified_historical_checkpoints_are_not_accepted(self) -> None:
        self.assertIsNone(release_checkpoint("0.1.0-alpha.34"))
        self.assertIsNone(release_checkpoint("0.1.0-alpha.47"))

    def test_alpha_50_checkpoint_uses_its_validated_release_commit(self) -> None:
        checkpoint = release_checkpoint("0.1.0-alpha.50")

        self.assertIsNotNone(checkpoint)
        self.assertEqual(
            checkpoint.ref,
            "edcbfa631d99216fe76287e0975c2222a4ba4e18",
        )

    def test_schema_2_checkpoint_rejects_modified_report(self) -> None:
        with patch("check_release_drift.file_sha256", return_value="0" * 64):
            with self.assertRaisesRegex(RuntimeError, "migration report digest differs"):
                release_checkpoint("0.1.0-alpha.61")

    def test_checkpoint_recorder_reproduces_alpha_61_identity(self) -> None:
        record = checkpoint_record("0.1.0-alpha.61", "489e329")
        self.assertEqual(record["schema_version"], 2)
        self.assertEqual(
            record["previous_baseline"], "release-checkpoint:0.1.0-alpha.60"
        )
        self.assertEqual(
            record["contract_sha256"],
            "a8109d28f8ef719a2ed53b1b2ddd841bab6472f3c14bb31551feb42697827c9a",
        )

    def test_committed_report_rejects_malformed_source_label(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "docs/releases/2.0.0-migration.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "\n".join(
                    [
                        "From manifest: `baseline:framework/rule-registry.json:framework/rule-registry.json`",
                        "To manifest: `source-tree:framework/rule-registry.json`",
                        "From framework version: `1.0.0`",
                        "To framework version: `2.0.0`",
                        "From adapter schema version: `1`",
                        "To adapter schema version: `1`",
                        "From template version: `1`",
                        "To template version: `2`",
                        "From contract SHA-256: `from-digest`",
                        "To contract SHA-256: `to-digest`",
                        "Source validation: `passed`",
                        "Source validation commands:",
                        "- `python3 tools/check_all.py --profile full`",
                        "Source validation result: `all checks passed`",
                        "Source validation revision: `fixture-tree`",
                        "Source validation completed at: `2026-09-04T12:00:00+00:00`",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            with patch("check_release_drift.ROOT", root):
                failures = validate_committed_report(
                    baseline="baseline",
                    from_version="1.0.0",
                    to_version="2.0.0",
                    from_adapter="1",
                    to_adapter="1",
                    from_template="1",
                    to_template="2",
                    from_digest="from-digest",
                    to_digest="to-digest",
                )
            self.assertTrue(any("missing release binding" in item for item in failures))

    def test_uses_nearest_real_tag_and_preserves_intervening_report_chain(self) -> None:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

        tag, intervening = nearest_tagged_baseline(version)

        self.assertEqual(tag, "v0.1.0-alpha.3")
        self.assertEqual(intervening[0], prior_changelog_versions(version)[0])
        self.assertEqual(intervening[-1], "0.1.0-alpha.4")
        self.assertEqual(
            prior_changelog_versions(version)[: len(intervening)], intervening
        )

    def test_all_shipped_schemas_are_release_contract_paths(self) -> None:
        schema_paths = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "schemas").rglob("*.json")
        }

        self.assertTrue(schema_paths)
        self.assertTrue(schema_paths.issubset(SCHEMA_CONTRACT_PATHS))

    def test_contract_digest_changes_with_schema_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "framework").mkdir()
            (root / "schemas").mkdir()
            (root / "templates" / "target").mkdir(parents=True)
            (root / "schemas/example.json").write_text("{}\n", encoding="utf-8")
            for name in ["VERSION", "ADAPTER_SCHEMA_VERSION", "TEMPLATE_VERSION"]:
                (root / name).write_text("1\n", encoding="utf-8")

            before = contract_digest(root)
            (root / "schemas/example.json").write_text(
                '{"type":"object"}\n', encoding="utf-8"
            )

            self.assertNotEqual(contract_digest(root), before)

    def test_materialize_restores_baseline_contract_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            materialize("HEAD", "framework", root)

            self.assertTrue((root / "framework" / "rule-registry.json").is_file())

    def test_release_tag_must_match_version(self) -> None:
        self.assertEqual(validate_release_tag("1.2.3", "v1.2.3"), [])
        self.assertTrue(validate_release_tag("1.2.3", "v1.2.4"))

    def test_current_release_binding_requires_tag_on_head(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "alatyr@example.invalid"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Alatyr Check"],
                cwd=root,
                check=True,
            )
            (root / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)

            self.assertTrue(validate_current_release_binding("1.2.3", root))
            subprocess.run(["git", "tag", "v1.2.3"], cwd=root, check=True)
            self.assertEqual(validate_current_release_binding("1.2.3", root), [])

            (root / "README.md").write_text("next\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-qam", "next"], cwd=root, check=True)
            self.assertTrue(validate_current_release_binding("1.2.3", root))


if __name__ == "__main__":
    unittest.main()
