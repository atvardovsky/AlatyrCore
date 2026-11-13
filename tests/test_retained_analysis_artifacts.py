from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from analysis_evidence import probe_binding
from analysis_strategy_contract import build_active_problem_model_projection
from publish_active_task import prepare_retention
from retained_analysis_artifacts import load_aliases, MAX_ARTIFACT_BYTES, MAX_ENTRIES, MAX_MANIFEST_BYTES
from support_write_transaction import SupportTransaction
from tests.active_task_fixture import ActiveTaskFixture
from tests.test_analysis_evidence import add_evidence


class RetainedAnalysisArtifactTests(ActiveTaskFixture):
    def setUp(self):
        super().setUp()
        self.artifact = add_evidence(self.model, self.target)
        self.model["analysis_evidence"]["selected_context"] = [self.bind(self.target / "design.md")]
        probe = self.model["analysis_evidence"]["probes"][0]
        probe["input_paths"] = [self.artifact]
        probe["result"]["input_sha256"] = {
            self.artifact: hashlib.sha256((self.target / self.artifact).read_bytes()).hexdigest()}
        probe["result"]["probe_sha256"] = probe_binding(self.model, probe)
        self.write_model()
        self.write_index()

    def retain(self):
        plan = prepare_retention(self.target, "fixture-task", "request:explicit-retention-review")
        SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
        self.task = json.loads((self.target / ".ai/assistant/active-tasks.json").read_text())["tasks"][0]
        return plan

    def manifest(self):
        binding = self.task["analysis_handoff"]["artifact_manifest"]
        path = self.target / binding["path"]
        return path, json.loads(path.read_text())

    def rewrite_manifest(self, manifest):
        path = self.target / self.task["analysis_handoff"]["artifact_manifest"]["path"]
        path.write_text(json.dumps(manifest))
        self.task["analysis_handoff"]["artifact_manifest"] = self.bind(path)
        self.write_index()

    def test_exact_retained_artifacts_validate_after_runtime_removal(self):
        before = self.model_path.read_bytes()
        plan = self.retain()
        self.assertEqual(self.model_path.read_bytes(), before)
        self.assertNotIn(self.model_path, plan.outputs)
        _, manifest = self.manifest()
        self.assertEqual(manifest["source_model"], self.task["problem_model"])
        self.assertEqual([row["source_path"] for row in manifest["artifacts"]], [self.artifact])
        shutil.rmtree(self.target / ".ai/.runtime")
        self.assertEqual(self.errors(self.check(selected=False)), set())
        self.assertIn("ACTIVE_TASK_REHYDRATION_REQUIRED", self.errors(self.check()))

    def test_current_task_never_substitutes_retained_artifact_for_missing_runtime_input(self):
        self.retain()
        (self.target / self.artifact).unlink()
        self.assertEqual(self.errors(self.check(selected=False)), set())
        self.assertIn("ANALYSIS_EVIDENCE_ARTIFACT", self.errors(self.check()))

    def test_changed_extant_original_or_retained_copy_is_rejected(self):
        self.retain()
        _, manifest = self.manifest()
        for path in (self.artifact, manifest["artifacts"][0]["retained"]["path"]):
            artifact = self.target / path
            original = artifact.read_bytes()
            artifact.write_bytes(original + b"changed\n")
            with self.subTest(path=path):
                self.assertIn("ACTIVE_TASK_ARTIFACT_RETENTION", self.errors(self.check(selected=False)))
            artifact.write_bytes(original)

    def test_extra_missing_duplicate_wrong_hash_or_wrong_model_mapping_is_rejected(self):
        self.retain()
        _, original = self.manifest()
        for kind in ("extra", "missing", "duplicate", "wrong-hash", "wrong-model"):
            manifest = copy.deepcopy(original)
            if kind == "extra":
                manifest["artifacts"].append({**manifest["artifacts"][0], "source_path": ".ai/.runtime/unknown.txt"})
            elif kind == "missing":
                manifest["artifacts"] = []
            elif kind == "duplicate":
                manifest["artifacts"].append(copy.deepcopy(manifest["artifacts"][0]))
            elif kind == "wrong-hash":
                manifest["artifacts"][0]["retained"]["sha256"] = "0" * 64
            else:
                manifest["source_model"]["sha256"] = "0" * 64
            self.rewrite_manifest(manifest)
            with self.subTest(kind=kind):
                self.assertIn("ACTIVE_TASK_ARTIFACT_RETENTION", self.errors(self.check(selected=False)))
        self.rewrite_manifest(original)

    def test_traversal_private_cross_task_and_symlink_destinations_are_rejected(self):
        self.retain()
        _, original = self.manifest()
        for path in ("../outside", ".env", ".ai/assistant/task-evidence/peer/artifact.txt"):
            manifest = copy.deepcopy(original)
            manifest["artifacts"][0]["retained"]["path"] = path
            self.rewrite_manifest(manifest)
            with self.subTest(path=path):
                self.assertIn("ACTIVE_TASK_ARTIFACT_RETENTION", self.errors(self.check(selected=False)))
        self.rewrite_manifest(original)
        retained = self.target / original["artifacts"][0]["retained"]["path"]
        retained.unlink()
        try:
            retained.symlink_to(self.target / self.artifact)
        except OSError as error:
            self.skipTest(str(error))
        self.assertIn("ACTIVE_TASK_ARTIFACT_RETENTION", self.errors(self.check(selected=False)))

    def test_model_and_projection_bytes_and_shared_task_binding_are_not_rewritten(self):
        self.model["task_binding"]["task_ids"].append("legacy-subtask")
        probe = self.model["analysis_evidence"]["probes"][0]
        probe["result"]["probe_sha256"] = probe_binding(self.model, probe)
        self.model_path.write_text(json.dumps(self.model, separators=(",", ":")))
        self.task["problem_model"] = self.bind(self.model_path)
        projection_path = self.target / self.model["active_projection"]["path"]
        projection = build_active_problem_model_projection(self.model,
            source_path=self.task["problem_model"]["path"], source_sha256=self.task["problem_model"]["sha256"])
        projection_path.write_text(json.dumps(projection, separators=(",", ":")))
        self.write_index()
        before = {path: path.read_bytes() for path in (self.model_path, projection_path)}
        self.retain()
        handoff = self.task["analysis_handoff"]
        self.assertEqual((self.target / handoff["model"]["path"]).read_bytes(), before[self.model_path])
        self.assertEqual((self.target / handoff["projection"]["path"]).read_bytes(), before[projection_path])
        self.assertEqual(self.errors(self.check(selected=False)), set())

    def test_retention_preserves_open_obligations_and_never_creates_completion(self):
        self.model["proof_obligations"][0].update(status="open", evidence_refs=[])
        self.model["analysis_evidence"]["review_challenges"][0]["status"] = "pending"
        self.model["review_results"][0].update(status="pending", evidence_refs=[])
        self.write_model()
        self.write_index()
        self.retain()
        self.assertEqual(self.task["state"], "active")
        self.assertIsNone(self.task["completion_evidence"])
        self.assertEqual(self.model["proof_obligations"][0]["status"], "open")

    def test_changed_planned_inputs_abort_without_partial_publication(self):
        plan = prepare_retention(self.target, "fixture-task", "request:explicit-retention-review")
        (self.target / self.artifact).write_bytes(b"changed after planning")
        with self.assertRaisesRegex(ValueError, "changed while planning"):
            SupportTransaction(self.target).apply(plan.outputs, expected_inputs=plan.inputs)
        self.assertFalse((self.target / ".ai/assistant/task-evidence").exists())

    def test_manifest_duplicate_keys_unknown_fields_and_manifest_hash_changes_fail(self):
        self.retain()
        path, original = self.manifest()
        for raw in (b'{"schema_version":1,"schema_version":1}',
                    json.dumps({**original, "authority": "granted"}).encode(),
                    b" " * (MAX_MANIFEST_BYTES + 1)):
            path.write_bytes(raw)
            self.task["analysis_handoff"]["artifact_manifest"] = self.bind(path)
            self.write_index()
            with self.subTest(bytes=len(raw)):
                self.assertIn("ACTIVE_TASK_ARTIFACT_RETENTION", self.errors(self.check(selected=False)))
        self.rewrite_manifest(original)
        path.write_bytes(path.read_bytes() + b"\n")
        self.assertIn("ACTIVE_TASK_ARTIFACT_RETENTION", self.errors(self.check(selected=False)))

    def test_private_sources_and_source_symlink_are_not_retained(self):
        original = self.target / self.artifact
        raw = original.read_bytes()
        original.unlink()
        outside = self.target / "source.txt"
        outside.write_bytes(raw)
        try:
            original.symlink_to(outside)
        except OSError as error:
            self.skipTest(str(error))
        with self.assertRaises(ValueError):
            prepare_retention(self.target, "fixture-task", "request:explicit-review")
        original.unlink()
        original.write_bytes(raw)
        self.model["analysis_evidence"]["selected_context"].append(
            {"path": ".ai/.runtime/secrets/private.json", "sha256": "0" * 64})
        self.write_model()
        self.write_index()
        with self.assertRaisesRegex(ValueError, "private artifact"):
            prepare_retention(self.target, "fixture-task", "request:explicit-review")

    def test_nonignored_inputs_are_not_hidden_by_mappings(self):
        self.retain()
        (self.target / "design.md").write_bytes(b"changed public normative input")
        self.assertIn("ANALYSIS_EVIDENCE_ARTIFACT", self.errors(self.check(selected=False)))
        _, manifest = self.manifest()
        manifest["artifacts"][0]["source_path"] = "design.md"
        self.rewrite_manifest(manifest)
        self.assertIn("ACTIVE_TASK_ARTIFACT_RETENTION", self.errors(self.check(selected=False)))

    def test_explicit_runtime_model_selection_still_uses_original_artifacts(self):
        self.retain()
        (self.target / self.artifact).unlink()
        from check_change_packages import changed_index_validator
        from target_adapter_validation.active_tasks import validate_active_tasks
        validator = changed_index_validator(self.target)
        validator.problem_models = [self.model_path]
        validator.current_task_id = None
        validate_active_tasks(validator)
        self.assertIn("ANALYSIS_EVIDENCE_ARTIFACT", self.errors(validator))

    def test_mapped_artifact_and_entry_limits_are_enforced(self):
        self.retain()
        _, manifest = self.manifest()
        manifest["artifacts"] *= MAX_ENTRIES + 1
        self.rewrite_manifest(manifest)
        self.assertIn("ACTIVE_TASK_ARTIFACT_RETENTION", self.errors(self.check(selected=False)))
        _, manifest = self.manifest()
        manifest["artifacts"] = manifest["artifacts"][:1]
        copied = self.target / manifest["artifacts"][0]["retained"]["path"]
        copied.write_bytes(b"x" * (MAX_ARTIFACT_BYTES + 1))
        self.rewrite_manifest(manifest)
        self.assertIn("ACTIVE_TASK_ARTIFACT_RETENTION", self.errors(self.check(selected=False)))

    def test_cli_retention_preview_is_non_mutating_and_rejects_authoring_modes(self):
        command = [sys.executable, str(ROOT / "tools/publish_active_task.py"), "--target", str(self.target),
                   "--task-id", "fixture-task", "--retain-existing", "--retention-review", "request:explicit-review"]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["write"])
        self.assertNotIn("analysis_handoff", json.loads((self.target / ".ai/assistant/active-tasks.json").read_text())["tasks"][0])
        self.assertFalse((self.target / ".ai/assistant/task-evidence").exists())
        for extra in (["--draft", self.artifact], ["--registration", self.artifact], ["--source-contour"]):
            result = subprocess.run(command + extra, capture_output=True, text=True)
            with self.subTest(extra=extra):
                self.assertNotEqual(result.returncode, 0)

    def test_immutable_output_conflicts_and_missing_review_are_rejected(self):
        self.retain()
        public = self.target / self.task["analysis_handoff"]["model"]["path"]
        public.write_bytes(b"conflicting retained model")
        with self.assertRaisesRegex(ValueError, "immutable retention output conflicts"):
            prepare_retention(self.target, "fixture-task", "request:explicit-review")
        with self.assertRaisesRegex(ValueError, "explicit retention review"):
            prepare_retention(self.target, "fixture-task", "none")

    def test_lineage_and_model_local_readers_do_not_leak_aliases(self):
        self.retain()
        (self.target / self.artifact).unlink()
        from check_change_packages import changed_index_validator
        from target_adapter_validation.active_tasks import lineage_model
        from target_adapter_validation.model_evidence import retained_artifact_locations
        from target_adapter_validation.prerequisites import validate_model_prerequisites
        validator = changed_index_validator(self.target)
        self.assertIsNotNone(lineage_model(validator, self.task))
        aliases = retained_artifact_locations(validator, self.task, self.model)
        def check(locations):
            start = len(validator.findings)
            validate_model_prerequisites(validator, self.model, "fixture", require_completion=False,
                                        artifact_locations=locations)
            return {finding.code for finding in validator.findings[start:] if finding.level == "error"}
        self.assertEqual(check(aliases), set())
        self.assertIn("ANALYSIS_EVIDENCE_ARTIFACT", check({}))
        self.assertEqual(check(aliases), set())

    def test_parent_symlink_and_portable_alias_collisions_are_rejected(self):
        self.retain()
        _, original = self.manifest()
        manifest = copy.deepcopy(original)
        manifest["artifacts"].append({**manifest["artifacts"][0],
                                      "source_path": manifest["artifacts"][0]["source_path"].upper()})
        self.rewrite_manifest(manifest)
        self.assertIn("ACTIVE_TASK_ARTIFACT_RETENTION", self.errors(self.check(selected=False)))
        self.rewrite_manifest(original)
        artifact = self.target / original["artifacts"][0]["retained"]["path"]
        parent = artifact.parent
        moved = parent.with_name("moved-artifacts")
        parent.rename(moved)
        try:
            parent.symlink_to(moved, target_is_directory=True)
        except OSError as error:
            self.skipTest(str(error))
        self.assertIn("ACTIVE_TASK_ARTIFACT_RETENTION", self.errors(self.check(selected=False)))

    def test_aggregate_byte_budget_below_at_above_unchanged_limit(self):
        for count in (3, 4, 5):
            content = b"x" * MAX_ARTIFACT_BYTES
            digest = hashlib.sha256(content).hexdigest()
            source = self.task["problem_model"]
            prefix = f".ai/assistant/task-evidence/fixture-task/{source['sha256']}/"
            logical = [f".ai/.runtime/input-{number}.txt" for number in range(count)]
            model = {"analysis_evidence": {"selected_context": [{"path": path, "sha256": digest} for path in logical]}}
            rows = [{"source_path": path, "retained": {"path": prefix + f"artifacts/{number}.blob", "sha256": digest}}
                    for number, path in enumerate(logical)]
            manifest = json.dumps({"schema_version": 1, "record_kind": "alatyr-retained-analysis-artifacts",
                                   "source_model": source, "artifacts": rows}).encode()
            manifest_binding = {"path": prefix + "artifact-manifest.json", "sha256": hashlib.sha256(manifest).hexdigest()}
            values = {manifest_binding["path"]: manifest, **{row["retained"]["path"]: content for row in rows}}
            def load():
                return load_aliases(self.target, "fixture-task", source, model, manifest_binding,
                                    read=lambda path, limit: values.get(path),
                                    is_ignored=lambda path: path.startswith(".ai/.runtime/"))
            with self.subTest(artifacts=count):
                if count <= 4:
                    self.assertEqual(len(load()), count)
                else:
                    with self.assertRaisesRegex(ValueError, "byte budget"):
                        load()
