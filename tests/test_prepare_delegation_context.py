from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from prepare_delegation_context import prepare, measurement, validate_preflight
from prepare_delegation_result import prepare as prepare_result
from source_worker_contract import load_source_worker_policy, make_builtin_packet


class WorkerContextTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "core.txt").write_text("selected source")
        (self.root / "detail.txt").write_text("conditional evidence")
        self.policy = load_source_worker_policy(ROOT / "tools/source_worker_policy.json", root=ROOT)
        self.packet = make_builtin_packet(self.policy, "framework-rules")
        self.packet.update(bounded_context=["core.txt"], conditional_context=["detail.txt"], max_initial_words=1000)

    def bundle(self, **kwargs):
        args = dict(root=self.root, prompt=b"inspect selected behavior", bootstrap={"visible-host": b"inspect only"}, expansions=[], other_contexts=[], max_context_words=2000)
        args.update(kwargs)
        return prepare(self.packet, self.policy, **args)

    def test_actual_prompt_bootstrap_packet_and_file_are_measured(self):
        record, content = self.bundle()
        self.assertEqual(record["context"], measurement(content))
        for expected in (b"inspect selected behavior", b"visible-host", b"selected source", b"needs-expansion"):
            self.assertIn(expected, content)
        self.assertFalse(record["dispatch_performed"])
        self.assertFalse(record["native_limit_enforced"])

    def test_prompt_overhead_cannot_hide_behind_small_file_measurement(self):
        self.packet["max_initial_words"] = 200
        with self.assertRaisesRegex(ValueError, "initial context"):
            self.bundle(prompt=b"word " * 200)

    def test_worker_and_aggregate_below_at_above_boundaries(self):
        initial, _ = self.bundle()
        words = initial["context"]["word_count"]
        for delta in (-1, 0, 1):
            with self.subTest(kind="worker", delta=delta):
                if delta < 0:
                    with self.assertRaises(ValueError): self.bundle(max_context_words=words + delta)
                else:
                    self.bundle(max_context_words=words + delta)
        self.policy["tree_policy"]["max_context_words_total"] = 1000
        for delta in (-1, 0, 1):
            with self.subTest(kind="aggregate", delta=delta):
                kwargs = dict(other_contexts=[b"word " * (1000 - words + delta)], max_context_words=1000)
                if delta > 0:
                    with self.assertRaises(ValueError): self.bundle(**kwargs)
                else:
                    self.bundle(**kwargs)

    def test_expansion_retains_measured_prefix_and_cannot_drop_reservations(self):
        prior = self.bundle(other_contexts=[b"other worker"])
        expanded = self.bundle(previous=prior, prompt=None, bootstrap={}, expansions=["detail.txt"], other_contexts=[b"other worker"])
        self.assertTrue(expanded[1].startswith(prior[1]))
        self.assertGreater(expanded[0]["context"]["word_count"], prior[0]["context"]["word_count"])
        for kwargs in (dict(other_contexts=[]), dict(max_context_words=2001), dict(expansions=["../secret"]), dict(expansions=["detail.txt", "detail.txt"])):
            args = dict(previous=prior, prompt=None, bootstrap={}, expansions=["detail.txt"], other_contexts=[b"other worker"])
            args.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): self.bundle(**args)
        (self.root / "core.txt").write_text("changed source")
        with self.assertRaisesRegex(ValueError, "stale"):
            self.bundle(previous=prior, prompt=None, bootstrap={}, expansions=["detail.txt"], other_contexts=[b"other worker"])

    def test_stale_tampered_and_malformed_preflight_produce_diagnostics(self):
        prior = self.bundle()
        for field in prior[0]:
            for value in ({}, [], None, True, 2.5):
                mutant = copy.deepcopy(prior[0])
                mutant[field] = value
                with self.subTest(field=field, value=value):
                    try:
                        validate_preflight(mutant, self.packet, self.policy)
                    except ValueError:
                        continue
                    self.assertIn(field, ("source_inputs", "other_contexts"))
        with self.assertRaises(ValueError):
            self.bundle(previous=(prior[0], b"different"), prompt=None, bootstrap={})

    def test_invalid_required_budgets_and_portable_ceiling_are_rejected(self):
        for value in (None, {}, [], True, "unknown", 0, 32001):
            policy = copy.deepcopy(self.policy)
            policy["tree_policy"]["max_context_words_total"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                prepare(self.packet, policy, root=self.root, prompt=b"inspect", bootstrap={"host": b"visible"}, expansions=[], other_contexts=[])

    def test_actual_result_path_enforces_dispatch_allocation(self):
        # Use real source paths for the result helper's canonical packet validation.
        packet = make_builtin_packet(self.policy, "framework-rules")
        record, content = prepare(packet, self.policy, root=ROOT, prompt=b"inspect", bootstrap={"host": b"visible bootstrap"}, expansions=[], other_contexts=[], max_context_words=10000)
        event = {"schema_version": 1, "event_kind": "worker-result-received", "backend_kind": "native-worker", "worker_id": "worker", "packet_id": "packet", "base_revision": "a" * 40}
        contents = {"context": content, "raw": b"observed result", "summary": b"result"}
        self.assertEqual(prepare_result(packet, event, contents, self.policy, preflight=record)["status"], "requires-review")
        contents["context"] += b" extra" * (10001 - record["context"]["word_count"])
        with self.assertRaisesRegex(ValueError, "frozen worker limit"):
            prepare_result(packet, event, contents, self.policy, preflight=record)
        contents["context"] = b"wrong frozen packet"
        with self.assertRaisesRegex(ValueError, "frozen dispatch"):
            prepare_result(packet, event, contents, self.policy, preflight=record)

        contents["context"] = content
        for name, value in (("packet.json", packet), ("event.json", event), ("preflight.json", record)):
            (self.root / name).write_text(json.dumps(value))
        for name, value in contents.items():
            (self.root / (name + ".txt")).write_bytes(value)
        command = [sys.executable, str(ROOT / "tools/alatyr.py"), "prepare-worker-result", "--output-dir", str(self.root / "result")]
        for name in ("packet", "event", "context", "raw", "summary"):
            command.extend(["--" + name, str(self.root / (name + (".json" if name in {"packet", "event"} else ".txt")))])
        command.extend(["--context-preflight", str(self.root / "preflight.json")])
        valid = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertFalse((self.root / "result").exists())
        (self.root / "context.txt").write_bytes(content + b" extra" * (10001 - record["context"]["word_count"]))
        invalid = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("10001", invalid.stderr)
        self.assertIn("10000", invalid.stderr)
        self.assertNotIn("Traceback", invalid.stderr)

    def test_public_cli_previews_and_freezes_without_dispatch(self):
        packet = make_builtin_packet(self.policy, "framework-rules")
        for name, data in (("packet.json", json.dumps(packet).encode()), ("prompt.txt", b"inspect only"), ("bootstrap.txt", b"visible host context")):
            (self.root / name).write_bytes(data)
        command = [sys.executable, str(ROOT / "tools/alatyr.py"), "prepare-worker-context", "--packet", str(self.root / "packet.json"), "--prompt", str(self.root / "prompt.txt"), "--bootstrap", str(self.root / "bootstrap.txt"), "--output-dir", str(self.root / "bundle")]
        preview = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertFalse((self.root / "bundle").exists())
        result = subprocess.run([*command, "--write"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads((self.root / "bundle/preflight.json").read_text())
        self.assertEqual(record["context"], measurement((self.root / "bundle/context.txt").read_bytes()))
        self.assertNotEqual(subprocess.run([*command, "--write"], capture_output=True).returncode, 0)
