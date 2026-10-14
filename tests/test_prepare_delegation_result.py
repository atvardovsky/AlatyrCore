import copy
import json
import sys
import unittest
import tempfile
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from prepare_delegation_result import prepare
from source_worker_contract import make_builtin_packet, load_source_worker_policy


class DelegationDraftTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_source_worker_policy(ROOT / "tools/source_worker_policy.json", root=ROOT)
        self.packet = make_builtin_packet(self.policy, "framework-rules")
        self.event = {"schema_version": 1, "event_kind": "worker-result-received", "backend_kind": "native-worker",
                      "worker_id": "observed-native-id", "packet_id": "observed-packet", "base_revision": "a" * 40}
        self.contents = {"context": b"bounded source context", "raw": b"observed result", "summary": b"result"}

    def test_draft_cannot_claim_primary_acceptance(self):
        result = prepare(self.packet, self.event, self.contents, self.policy)
        self.assertEqual(result["status"], "requires-review")
        self.assertEqual(result["satisfied_proof_obligation_ids"], [])
        self.assertEqual(result["scope_violation"], "unreviewed")
        self.assertEqual(result["raw_payload"]["word_count"], 2)

    def test_all_budget_boundaries_are_enforced(self):
        limits = {"context": 1000, "raw": self.packet["max_result_words"], "summary": self.packet["max_summary_words"]}
        self.policy["tree_policy"]["max_context_words_total"] = 1000
        for name, limit in limits.items():
            for delta in (-1, 0, 1):
                with self.subTest(name=name, delta=delta):
                    contents = dict(self.contents)
                    contents[name] = b"word " * (limit + delta)
                    if name == "summary":
                        contents["raw"] = b"raw " * limit
                    if delta > 0:
                        with self.assertRaises(ValueError): prepare(self.packet, self.event, contents, self.policy)
                    else:
                        prepare(self.packet, self.event, contents, self.policy)

    def test_malformed_event_and_missing_budget_are_rejected(self):
        for field in self.event:
            for bad in (None, {}, [], True, 2.5):
                mutant = dict(self.event)
                mutant[field] = bad
                with self.subTest(field=field, bad=bad), self.assertRaises(ValueError):
                    prepare(self.packet, mutant, self.contents, self.policy)
        for bad in (None, "unknown", {}, True, 0):
            policy = copy.deepcopy(self.policy)
            policy["tree_policy"]["max_context_words_total"] = bad
            with self.assertRaises(ValueError): prepare(self.packet, self.event, self.contents, policy)

    def test_malformed_packet_fields_return_contract_errors_not_type_crashes(self):
        for field in self.packet:
            for bad in (None, {}, [], True, 2.5):
                mutant = dict(self.packet)
                mutant[field] = bad
                with self.subTest(field=field, bad=bad):
                    try:
                        result = prepare(mutant, self.event, self.contents, self.policy)
                    except ValueError:
                        continue
                    self.assertEqual(result["status"], "requires-review")

    def test_cli_previews_without_writes_and_rejects_oversized_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in (("packet", self.packet), ("event", self.event)):
                (root / (name + ".json")).write_text(json.dumps(value))
            for name, value in self.contents.items():
                (root / (name + ".txt")).write_bytes(value)
            args = [sys.executable, str(ROOT / "tools/prepare_delegation_result.py")]
            for name in ("packet", "event", "context", "raw", "summary"):
                args.extend(["--" + name, str(root / (name + (".json" if name in {"packet", "event"} else ".txt")))])
            output = root / "evidence"
            args.extend(["--output-dir", str(output)])
            preview = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertFalse(output.exists())
            written = subprocess.run([*args, "--write"], capture_output=True, text=True)
            self.assertEqual(written.returncode, 0, written.stderr)
            self.assertEqual(json.loads((output / "result.json").read_text())["status"], "requires-review")
            self.assertNotEqual(subprocess.run([*args, "--write"], capture_output=True).returncode, 0)
            (root / "raw.txt").write_bytes(b"word " * (self.packet["max_result_words"] + 1))
            rejected = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("limit", rejected.stderr)
