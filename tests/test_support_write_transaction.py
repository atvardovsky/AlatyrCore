from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from support_write_transaction import SupportTransaction, support_writer_lock
from resource_access import resource_conflicts, resource_failures, command_resource_plan
from test_execution_contract import TestExecutionContract
from tests.test_test_execution_contract import policy, record


def resource(namespace=None, access="write", isolation="shared"):
    return {"kind": "database", "id": "fixture-db", "namespace": namespace, "access": access, "isolation": isolation}


class ResourceAccessTests(unittest.TestCase):
    def test_same_database_writes_conflict_and_reads_coexist(self):
        self.assertEqual(resource_conflicts([resource()], [resource()]), ["database:fixture-db"])
        self.assertEqual(resource_conflicts([resource(access="read")], [resource(access="read")]), [])

    def test_verified_namespaces_only_and_enclosing_resets(self):
        first, second = resource("schema-a", isolation="verified-isolated"), resource("schema-b", isolation="verified-isolated")
        self.assertEqual(resource_conflicts([first], [second]), [])
        second["isolation"] = "shared"
        self.assertTrue(resource_conflicts([first], [second]))
        self.assertTrue(resource_conflicts([first], [resource(access="exclusive")]))

    def test_invalid_and_credential_bearing_resources_fail_closed(self):
        for field in ("kind", "id", "namespace", "access", "isolation"):
            for value in (None, [], {}, True, 7, "unknown"):
                item = resource(); item[field] = value
                with self.subTest(field=field, value=value):
                    self.assertIsInstance(resource_failures([item]), list)
        for identity in ("unknown", "postgres://user:secret@host/db", "{DATABASE_ID}"):
            item = resource(); item["id"] = identity
            self.assertTrue(resource_failures([item]))
            with self.assertRaises(ValueError):
                resource_conflicts([item], [])

    def test_plan_reports_conflicts_without_executing_commands(self):
        data = policy()
        second = copy.deepcopy(data["commands"][0]); second["id"] = "browser"
        data["commands"].append(second)
        result = command_resource_plan(data, ["unit", "browser"])
        self.assertFalse(result["concurrent_eligible"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / ".ai/project/testing/test-first-policy.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(data))
            cli = subprocess.run([sys.executable, str(ROOT / "tools/plan_test_resources.py"), "--target", str(root), "--command", "unit", "--command", "browser"], capture_output=True, text=True)
            self.assertEqual(cli.returncode, 0, cli.stderr)
            self.assertFalse(json.loads(cli.stdout)["concurrent_eligible"])
            data["execution_contract"]["canonical_policy"] = "canonical-policy.json"
            path.write_text(json.dumps(data))
            canonical = copy.deepcopy(data); canonical["commands"][0]["execution"]["resources"][0]["id"] = "canonical-output"
            (root / "canonical-policy.json").write_text(json.dumps(canonical))
            cli = subprocess.run([sys.executable, str(ROOT / "tools/plan_test_resources.py"), "--target", str(root), "--command", "unit", "--command", "browser"], capture_output=True, text=True)
            self.assertNotEqual(cli.returncode, 0)
            self.assertIn("canonical project owner", cli.stderr)

    def test_executed_writes_need_matching_resources_and_coordination(self):
        contract, data, evidence = TestExecutionContract(), policy(), record()
        for mutate in (lambda r: r.update(resources=[]), lambda r: r["resource_coordination"].update(decision="unverified"), lambda r: r["resource_coordination"].update(evidence_ref="unknown")):
            changed = copy.deepcopy(evidence); mutate(changed)
            self.assertTrue(contract.evidence_failures(changed, data["commands"][0], data["execution_contract"]))


class SupportTransactionTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows junction behavior")
    def test_windows_junction_parent_cannot_redirect_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root, outside = Path(directory) / "target", Path(directory) / "outside"
            root.mkdir(); outside.mkdir()
            sentinel = outside / "index.json"; sentinel.write_bytes(b"outside")
            junction = root / "junction"
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)], capture_output=True, text=True)
            if result.returncode:
                self.skipTest("junction creation unavailable")
            try:
                with self.assertRaises(ValueError):
                    SupportTransaction(root).apply({junction / "index.json": b"bad"})
                self.assertEqual(sentinel.read_bytes(), b"outside")
            finally:
                junction.rmdir()

    def test_repeated_pass_cannot_adopt_or_erase_peer_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / "bootstrap.json"
            path.write_bytes(b"original")
            transaction = SupportTransaction(root)
            transaction.apply({path: b"pass-one"})
            path.write_bytes(b"peer-edit")
            with self.assertRaisesRegex(ValueError, "previously owned"):
                transaction.apply({path: b"pass-two"}, expected_inputs={path: b"peer-edit"})
            self.assertEqual(transaction.rollback(), ["bootstrap.json"])
            self.assertEqual(path.read_bytes(), b"peer-edit")

    def test_only_owned_postimages_roll_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            owned, created, peer = (root / name for name in ("owned.json", "created.json", "peer.json"))
            owned.write_bytes(b"before")
            transaction = SupportTransaction(root)
            transaction.apply({owned: b"after", created: b"created"})
            peer.write_bytes(b"peer")
            created.write_bytes(b"peer-edit")
            self.assertEqual(transaction.rollback(), ["created.json"])
            self.assertEqual(owned.read_bytes(), b"before")
            self.assertEqual(created.read_bytes(), b"peer-edit")
            self.assertEqual(peer.read_bytes(), b"peer")

    def test_symlink_leaf_and_parent_never_touch_outside_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root, outside = Path(directory) / "target", Path(directory) / "outside"
            root.mkdir(); outside.mkdir()
            sentinel = outside / "sentinel.json"; sentinel.write_bytes(b"outside")
            link = root / "link"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("symlinks unavailable")
            transaction = SupportTransaction(root)
            with self.assertRaises(ValueError):
                transaction.apply({link / "sentinel.json": b"bad"})
            link.unlink(); link.symlink_to(sentinel)
            with self.assertRaises(ValueError):
                transaction.apply({link: b"bad"})
            self.assertEqual(sentinel.read_bytes(), b"outside")

    def test_parent_replaced_before_rollback_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root, outside = Path(directory) / "target", Path(directory) / "outside"
            root.mkdir(); outside.mkdir()
            parent = root / "outputs"; parent.mkdir()
            path = parent / "index.json"; path.write_bytes(b"before")
            transaction = SupportTransaction(root); transaction.apply({path: b"after"})
            path.unlink(); parent.rmdir()
            try:
                parent.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("symlinks unavailable")
            sentinel = outside / "index.json"; sentinel.write_bytes(b"peer")
            self.assertEqual(transaction.rollback(), ["outputs/index.json"])
            self.assertEqual(sentinel.read_bytes(), b"peer")

    def test_competing_writer_times_out_before_mutating(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = "import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from support_write_transaction import support_writer_lock; " \
                      "exec('with support_writer_lock(Path(sys.argv[2]), timeout=0.1):\\n Path(sys.argv[2], \\\"unexpected\\\").write_text(\\\"bad\\\")')"
            with support_writer_lock(root):
                result = subprocess.run([sys.executable, "-c", program, str(ROOT / "tools"), str(root)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("lock timed out", result.stderr)
            self.assertFalse((root / "unexpected").exists())


if __name__ == "__main__":
    unittest.main()
