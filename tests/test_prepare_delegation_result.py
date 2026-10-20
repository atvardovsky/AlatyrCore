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
from delegation_evidence import validate_worker_result, worker_result_sha256


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

    def test_unicode_draft_hash_round_trips_through_production_validator(self):
        for worker_id in ("worker-ascii", "worker-\u00e9", "worker-\u65e5\u672c"):
            with self.subTest(worker_id=worker_id), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                event = dict(self.event, worker_id=worker_id)
                (root / "packet.json").write_text(json.dumps(self.packet))
                (root / "event.json").write_text(json.dumps(event))
                for name, content in self.contents.items():
                    (root / (name + ".txt")).write_bytes(content)
                command = [sys.executable, str(ROOT / "tools/prepare_delegation_result.py")]
                for name in ("packet", "event", "context", "raw", "summary"):
                    command.extend(["--" + name, str(root / (name + (".json" if name in {"packet", "event"} else ".txt")))])
                output = root / "draft"
                run = subprocess.run([*command, "--output-dir", str(output), "--write"], capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                path = output / "result.json"
                result = json.loads(path.read_text())
                node = {name: result[name] for name in ("result_id", "packet_id", "parent_packet_id", "node_id", "depth", "stop_reason_id", "summary_covers_result_ids", "proof_obligation_ids", "satisfied_proof_obligation_ids")}
                node.update(result_status="requires-review", max_result_words=self.packet["max_result_words"],
                    max_summary_words=self.packet["max_summary_words"], accepted_summary_evidence=result["accepted_summary"],
                    context_evidence={"path": "context.txt", "sha256": result["input_context_packet_sha256"],
                        "word_count": len(self.contents["context"].split()), "character_count": len(self.contents["context"].decode())},
                    context_words=len(self.contents["context"].split()), surface_refs=[], canonical_owner_refs=[])
                validate_worker_result(path, artifact_root=output, node=node, expected_base_revision=event["base_revision"],
                    allowed_stop_reasons={"semantic-decision-required"})
                self.assertEqual(worker_result_sha256(dict(reversed(list(result.items())))), result["subtree_sha256"])

    def test_cli_malformed_json_inputs_are_bounded_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "packet.json").write_text(json.dumps(self.packet))
            for name, value in self.contents.items():
                (root / (name + ".txt")).write_bytes(value)
            args = [sys.executable, str(ROOT / "tools/prepare_delegation_result.py")]
            for name in ("packet", "event", "context", "raw", "summary"):
                args.extend(["--" + name, str(root / (name + (".json" if name in {"packet", "event"} else ".txt")))])
            args.extend(["--output-dir", str(root / "output"), "--write"])
            cases = [b"[" * 2000 + b"]" * 2000, b"\xff", b"{", b"true", b"1" * 5000, b" " * (4 * 1024 * 1024 + 1)]
            for payload in cases:
                with self.subTest(size=len(payload)):
                    (root / "event.json").write_bytes(payload)
                    rejected = subprocess.run(args, capture_output=True, text=True)
                    self.assertEqual(rejected.returncode, 2, rejected.stderr)
                    self.assertNotIn("Traceback", rejected.stderr)
                    self.assertLess(len(rejected.stderr), 1500)
                    self.assertFalse((root / "output").exists())

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
            root = Path(directory).resolve()
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
