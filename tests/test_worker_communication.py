from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from delegation_evidence import DelegationEvidenceError, validate_execution_tree
from session_presence_store import git_identity
from test_source_worker_contract import policy_fixture, recursive_execution_fixture
from worker_communication import MAX_VIEW_BYTES, encode_view, project_group, read_source, validate_communication, validate_successor, verify_bindings


SESSION = "00000000-0000-4000-8000-000000000001"
TREE = "00000000-0000-4000-8000-000000000002"


class WorkerCommunicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / ".gitignore").write_text("runtime/\n", encoding="utf-8")
        self.tree = recursive_execution_fixture(self.root)
        self.source = self.root / "tools/source_worker_contract.py"
        self.source.parent.mkdir()
        self.source.write_text("selected evidence", encoding="utf-8")
        _, _, repository = git_identity(self.root)
        self.tree["communication"] = {
            "schema_version": 1, "session_uid": SESSION, "tree_uid": TREE,
            "repository_id": repository,
            "worktree_id": hashlib.sha256(os.fsencode(str(self.root))).hexdigest(),
            "generation": 1, "state": "active", "groups": [
                {"parent_node_id": "root", "source_bindings": [], "updates": []},
                {"parent_node_id": "coordinator", "source_bindings": [
                    {"path": "tools/source_worker_contract.py", "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest()}],
                 "updates": [{"id": "update-1", "sender_node_id": "coordinator",
                              "recipient_node_ids": ["child"], "kind": "finding",
                              "summary": "Evidence remains review-required; obligation is unresolved.",
                              "source_refs": ["tools/source_worker_contract.py"]}]},
            ],
        }
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        self.ledger = self.runtime / "tree.json"

    def nodes(self, tree=None):
        return {row["node_id"]: row for row in (tree or self.tree)["nodes"]}

    def view(self, **kwargs):
        values = dict(session_uid=SESSION, tree_uid=TREE,
                      repository_id=self.tree["communication"]["repository_id"],
                      worktree_id=self.tree["communication"]["worktree_id"],
                      parent_node_id="coordinator", participant_node_id="child",
                      expected_generation=1, read_source=lambda path: read_source(self.root, path))
        values.update(kwargs)
        return project_group(self.tree, **values)

    def save(self):
        raw = json.dumps(self.tree).encode()
        self.ledger.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def command(self, *, parent="coordinator", participant="child", digest=None):
        digest = digest or self.save()
        return [sys.executable, str(ROOT / "tools/alatyr.py"), "worker-communication",
                "--target", str(self.root), "inspect", "--tree", "runtime/tree.json",
                "--session-uid", SESSION, "--tree-uid", TREE,
                "--parent-node", parent, "--participant-node", participant,
                "--expected-generation", "1", "--expected-sha256", digest]

    def test_parent_scoped_view_and_progress_are_derived_not_accepted(self):
        self.tree["nodes"][0]["status"] = "RUNNING"
        self.tree["nodes"][1]["status"] = "RUNNING"
        self.tree["nodes"][2]["status"] = "RUNNING"
        view = self.view()
        self.assertEqual(view["state"], "review-required")
        self.assertEqual(view["progress"], [{"node_id": "child", "status": "RUNNING"}])
        self.assertEqual(len(view["updates"]), 1)
        self.assertFalse(view["authorization_granted"])
        self.assertFalse(view["acceptance_granted"])
        self.assertFalse(view["execution_permitted"])
        outer = self.view(parent_node_id="root", participant_node_id="coordinator")
        self.assertEqual(outer["updates"], [])
        self.assertEqual(outer["source_bindings"], [])

    def test_each_identity_and_generation_mismatch_fails(self):
        for field, value in (("session_uid", TREE), ("tree_uid", SESSION),
                             ("repository_id", "a" * 64), ("worktree_id", "b" * 64),
                             ("expected_generation", 2), ("parent_node_id", "root"),
                             ("participant_node_id", "root")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.view(**{field: value})

    def test_cross_group_delivery_and_scope_escapes_are_rejected(self):
        update = self.tree["communication"]["groups"][1]["updates"][0]
        for sender, recipients in (("root", ["child"]), ("child", ["root"]),
                                   ("coordinator", ["coordinator"]), ("missing", ["child"])):
            mutated = copy.deepcopy(self.tree)
            mutated["communication"]["groups"][1]["updates"][0].update(
                sender_node_id=sender, recipient_node_ids=recipients)
            with self.subTest(sender=sender), self.assertRaises(ValueError):
                validate_communication(mutated, self.nodes(mutated))
        update["source_refs"] = ["private/secret.txt"]
        with self.assertRaisesRegex(ValueError, "unbound"):
            self.view()
        group = self.tree["communication"]["groups"][1]
        group["source_bindings"] = [{"path": "private/secret.txt", "sha256": "a" * 64}]
        with self.assertRaisesRegex(ValueError, "scope"):
            self.view()

    def test_worker_to_sibling_requires_parent_relay(self):
        tree = copy.deepcopy(self.tree)
        sibling = copy.deepcopy(tree["nodes"][2])
        sibling.update(node_id="sibling", packet_id="packet-sibling", coverage_key="sibling")
        tree["nodes"].append(sibling)
        group = tree["communication"]["groups"][1]
        group["updates"][0].update(sender_node_id="child", recipient_node_ids=["sibling"])
        with self.assertRaisesRegex(ValueError, "parent review"):
            validate_communication(tree, self.nodes(tree))
        group["updates"][0]["recipient_node_ids"] = ["coordinator"]
        validate_communication(tree, self.nodes(tree))

    def test_cancelled_closed_or_terminal_nodes_never_propose_execution(self):
        for state in ("closed", "cancelled", "active"):
            self.tree["communication"]["state"] = state
            view = self.view()
            self.assertEqual(view["state"], "historical-or-cancelled")
            self.assertFalse(view["execution_permitted"])

    def test_current_sources_required_but_unrelated_group_is_not_hydrated(self):
        self.source.write_text("changed by another session")
        with self.assertRaisesRegex(ValueError, "source changed"):
            self.view()
        self.view(parent_node_id="root", participant_node_id="coordinator")

    def test_full_canonical_validator_rejects_invalid_optional_communication(self):
        validate_execution_tree(self.tree, policy_fixture(), artifact_root=self.root)
        self.tree["communication"]["groups"][1]["updates"][0]["recipient_node_ids"] = ["root"]
        with self.assertRaisesRegex(DelegationEvidenceError, "parent group"):
            validate_execution_tree(self.tree, policy_fixture(), artifact_root=self.root)

    def test_full_validator_rejects_stale_active_sources_and_legacy_still_passes(self):
        self.source.write_text("changed")
        with self.assertRaisesRegex(DelegationEvidenceError, "source changed"):
            validate_execution_tree(self.tree, policy_fixture(), artifact_root=self.root)
        del self.tree["communication"]
        validate_execution_tree(self.tree, policy_fixture(), artifact_root=self.root)

    def test_malformed_json_types_never_crash(self):
        paths = [("state",), ("generation",), ("groups",), ("session_uid",),
                 ("groups", 1, "parent_node_id"), ("groups", 1, "source_bindings"),
                 ("groups", 1, "updates", 0, "kind"),
                 ("groups", 1, "updates", 0, "recipient_node_ids"),
                 ("groups", 1, "updates", 0, "source_refs"),
                 ("groups", 1, "updates", 0, "summary")]
        for path in paths:
            for value in ({}, [], None, True, 2.5, "unknown"):
                if path[-1] == "summary" and value == "unknown":
                    value = " "
                mutated = copy.deepcopy(self.tree)
                owner = mutated["communication"]
                for part in path[:-1]:
                    owner = owner[part]
                owner[path[-1]] = value
                with self.subTest(path=path, value=value), self.assertRaises(ValueError):
                    validate_communication(mutated, self.nodes(mutated))

    def test_duplicate_messages_sources_parents_and_path_traversal_fail(self):
        for mutation in ("updates", "source_bindings"):
            tree = copy.deepcopy(self.tree)
            rows = tree["communication"]["groups"][1][mutation]
            rows.append(copy.deepcopy(rows[0]))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_communication(tree, self.nodes(tree))
        for path in ("../secret", "/secret", "C:/secret", "tools/../secret", "tools//secret", "tools\\secret"):
            tree = copy.deepcopy(self.tree)
            tree["communication"]["groups"][1]["source_bindings"][0]["path"] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_communication(tree, self.nodes(tree))

    def test_byte_boundary_is_measured_in_exact_delivered_encoding(self):
        for size in (MAX_VIEW_BYTES - 10, MAX_VIEW_BYTES - 9, MAX_VIEW_BYTES - 8):
            value = {"x": "a" * size}
            raw = (json.dumps(value, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
            if len(raw) > MAX_VIEW_BYTES:
                with self.assertRaises(ValueError): encode_view(value)
            else:
                self.assertEqual(encode_view(value), raw)
        with self.assertRaises(ValueError): encode_view({"x": "\U0001f600" * 4000})

    def test_real_cli_is_read_only_and_rejects_stale_snapshot_and_duplicate_json(self):
        command = self.command()
        before = self.ledger.read_bytes()
        run = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertFalse(json.loads(run.stdout)["execution_permitted"])
        self.ledger.write_bytes(before + b" ")
        run = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn("snapshot changed", run.stderr)
        malformed = b'{"nodes":[],"nodes":[]}'
        self.ledger.write_bytes(malformed)
        command[-1] = hashlib.sha256(malformed).hexdigest()
        run = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertNotIn("Traceback", run.stderr)

    def test_real_cli_publication_is_cas_scoped_and_cannot_reopen(self):
        self.tree["nodes"][0]["status"] = "RUNNING"
        command = self.command(parent="root", participant="root")
        command[5] = "publish"
        candidate = copy.deepcopy(self.tree)
        candidate["communication"]["generation"] = 2
        candidate["communication"]["state"] = "cancelled"
        path = self.runtime / "candidate.json"
        path.write_text(json.dumps(candidate), encoding="utf-8")
        command += ["--candidate", "runtime/candidate.json", "--write"]
        run = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["generation"], 2)
        run = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn("snapshot changed", run.stderr)
        late = copy.deepcopy(candidate)
        late["communication"].update(generation=3, state="active")
        with self.assertRaisesRegex(ValueError, "terminal"):
            validate_successor(candidate, late)

    def test_publication_cannot_change_progress_scope_identity_or_generation(self):
        self.tree["nodes"][0]["status"] = "RUNNING"
        for change in ("status", "session_uid", "generation"):
            candidate = copy.deepcopy(self.tree)
            candidate["communication"]["generation"] = 2
            if change == "status": candidate["nodes"][0]["status"] = "DONE"
            elif change == "session_uid": candidate["communication"]["session_uid"] = TREE
            else: candidate["communication"]["generation"] = 3
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_successor(self.tree, candidate)

    def test_read_view_reuses_each_selected_source_and_checks_mutation(self):
        calls = []
        self.view(read_source=lambda path: (calls.append(path), self.source.read_bytes())[1])
        self.assertEqual(calls, ["tools/source_worker_contract.py"])
        import inspect_worker_communication as cli
        command = self.command()
        original = cli.read_source
        reads = []
        def changing(target, path):
            reads.append(path)
            result = original(target, path)
            if reads.count("runtime/tree.json") == 2:
                return result + b" "
            return result
        with patch.object(sys, "argv", command[2:]), patch.object(cli, "read_source", side_effect=changing):
            self.assertEqual(cli.main(), 1)

    def test_parallel_publication_has_one_winner_without_partial_bytes(self):
        self.tree["nodes"][0]["status"] = "RUNNING"
        command = self.command(parent="root", participant="root")
        command[5] = "publish"
        candidate = copy.deepcopy(self.tree)
        candidate["communication"]["generation"] = 2
        path = self.runtime / "candidate.json"
        raw = json.dumps(candidate).encode()
        path.write_bytes(raw)
        command += ["--candidate", "runtime/candidate.json", "--write"]
        first = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        second = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        a, b = first.communicate(timeout=30), second.communicate(timeout=30)
        self.assertEqual(sorted([first.returncode, second.returncode]), [0, 1], (a, b))
        self.assertEqual(self.ledger.read_bytes(), raw)

    def test_worker_publication_nonignored_ledger_and_symlink_sources_fail(self):
        self.tree["nodes"][0]["status"] = "RUNNING"
        command = self.command()
        command[5] = "publish"
        candidate = copy.deepcopy(self.tree)
        candidate["communication"]["generation"] = 2
        (self.runtime / "candidate.json").write_text(json.dumps(candidate))
        command += ["--candidate", "runtime/candidate.json", "--write"]
        run = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn("primary coordinator", run.stderr)
        command = self.command(parent="root", participant="root")
        command[5] = "publish"
        (self.root / ".gitignore").write_text("")
        run = subprocess.run(command + ["--candidate", "runtime/candidate.json", "--write"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn("Git-ignored", run.stderr)

    def test_identity_cli_and_parser_reject_abbreviations_and_duplicates(self):
        run = subprocess.run([sys.executable, str(ROOT / "tools/alatyr.py"), "worker-communication",
                              "--target", str(self.root), "identity"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["repository_id"], self.tree["communication"]["repository_id"])
        for args in (["--expected-generation", "2"], ["--expected-g", "2"], ["--expected-sha256", "-h"]):
            run = subprocess.run(self.command() + args, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)

    def test_summary_and_update_count_below_at_above_limits(self):
        for count in (15, 16, 17):
            tree = copy.deepcopy(self.tree)
            group = tree["communication"]["groups"][1]
            example = group["updates"][0]
            group["updates"] = [dict(example, id=f"update-{number}") for number in range(count)]
            if count > 16:
                with self.assertRaises(ValueError): validate_communication(tree, self.nodes(tree))
            else:
                validate_communication(tree, self.nodes(tree))
        for count in (1199, 1200, 1201):
            tree = copy.deepcopy(self.tree)
            tree["communication"]["groups"][1]["updates"][0]["summary"] = "x" * count
            if count > 1200:
                with self.assertRaises(ValueError): validate_communication(tree, self.nodes(tree))
            else:
                validate_communication(tree, self.nodes(tree))

    def test_terminal_primary_rejects_late_update_even_with_active_channel(self):
        successor = copy.deepcopy(self.tree)
        successor["communication"]["generation"] = 2
        with self.assertRaisesRegex(ValueError, "terminal primary"):
            validate_successor(self.tree, successor)

    def publish_candidate(self, candidate):
        command = self.command(parent="root", participant="root")
        command[5] = "publish"
        (self.runtime / "candidate.json").write_text(json.dumps(candidate), encoding="utf-8")
        return subprocess.run(command + ["--candidate", "runtime/candidate.json", "--write"], capture_output=True, text=True)

    def test_missing_candidate_channel_reports_error_without_traceback_or_write(self):
        self.tree["nodes"][0]["status"] = "RUNNING"
        candidate = copy.deepcopy(self.tree)
        del candidate["communication"]
        run = self.publish_candidate(candidate)
        self.assertEqual(run.returncode, 1)
        self.assertIn("retain its channel", run.stderr)
        self.assertNotIn("Traceback", run.stderr)
        self.assertEqual(json.loads(self.ledger.read_bytes()), self.tree)

    def test_stale_current_sources_can_be_reconciled_in_a_successor(self):
        self.tree["nodes"][0]["status"] = "RUNNING"
        outer, inner = self.tree["communication"]["groups"]
        outer["source_bindings"] = copy.deepcopy(inner["source_bindings"])
        outer["updates"] = [dict(inner["updates"][0], id="outer-1", sender_node_id="coordinator", recipient_node_ids=["root"])]
        self.source.write_text("new evidence")
        with self.assertRaisesRegex(ValueError, "source changed"):
            self.view(parent_node_id="root", participant_node_id="root")
        candidate = copy.deepcopy(self.tree)
        candidate["communication"]["generation"] = 2
        for group in candidate["communication"]["groups"]:
            group["source_bindings"][0]["sha256"] = hashlib.sha256(self.source.read_bytes()).hexdigest()
        run = self.publish_candidate(candidate)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(self.ledger.read_bytes()), candidate)

    def oversized(self, tree):
        group = tree["communication"]["groups"][0]
        group["updates"] = [{"id": f"oversized-{i}", "sender_node_id": "coordinator", "recipient_node_ids": ["root"],
                             "kind": "context-request", "summary": "\u00e9" * 1200, "source_refs": []} for i in range(5)]

    def test_oversized_successor_is_rejected_and_oversized_current_can_be_repaired(self):
        self.tree["nodes"][0]["status"] = "RUNNING"
        candidate = copy.deepcopy(self.tree)
        candidate["communication"]["generation"] = 2
        self.oversized(candidate)
        run = self.publish_candidate(candidate)
        self.assertEqual(run.returncode, 1)
        self.assertIn("byte limit", run.stderr)
        self.assertEqual(json.loads(self.ledger.read_bytes()), self.tree)
        self.oversized(self.tree)
        candidate = copy.deepcopy(self.tree)
        candidate["communication"]["generation"] = 2
        candidate["communication"]["groups"][0]["updates"] = []
        run = self.publish_candidate(candidate)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_self_binding_and_tracked_runtime_ledger_cannot_be_published(self):
        self.tree["nodes"][0]["status"] = "RUNNING"
        digest = self.save()
        candidate = copy.deepcopy(self.tree)
        candidate["communication"]["generation"] = 2
        candidate["communication"]["groups"][0]["source_bindings"] = [{"path": "runtime/tree.json", "sha256": digest}]
        run = self.publish_candidate(candidate)
        self.assertEqual(run.returncode, 1)
        self.assertIn("own mutable ledger", run.stderr)
        candidate["communication"]["groups"][0]["source_bindings"] = []
        subprocess.run(["git", "-C", str(self.root), "add", "-f", "runtime/tree.json"], check=True)
        run = self.publish_candidate(candidate)
        self.assertEqual(run.returncode, 1)
        self.assertIn("untracked runtime", run.stderr)

    def test_source_aggregate_budget_and_reuse(self):
        records = [{"path": "one", "sha256": hashlib.sha256(b"abcd").hexdigest()},
                   {"path": "two", "sha256": hashlib.sha256(b"abcd").hexdigest()}]
        for limit in (7, 8, 9):
            with patch("worker_communication.MAX_BINDING_BYTES", limit):
                if limit < 8:
                    with self.assertRaisesRegex(ValueError, "aggregate byte"):
                        verify_bindings(records, lambda path: b"abcd")
                else:
                    verify_bindings(records, lambda path: b"abcd")
        calls = []
        verify_bindings(records + records, lambda path: (calls.append(path), b"abcd")[1])
        self.assertEqual(calls, ["one", "two"])
        with self.assertRaises(ValueError):
            self.view(expected_generation=True)

    def test_legacy_full_validation_does_not_import_communication(self):
        del self.tree["communication"]
        with patch.dict(sys.modules, {"worker_communication": None}):
            validate_execution_tree(self.tree, policy_fixture(), artifact_root=self.root)

    def test_real_linked_worktree_and_separate_clone_reject_foreign_channel(self):
        subprocess.run(["git", "-C", str(self.root), "add", ".gitignore", "tools/source_worker_contract.py"], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Fixture", "-c",
                        "user.email=fixture@example.invalid", "commit", "-qm", "Fixture"], check=True)
        command = self.command()
        linked = self.root / "linked"
        subprocess.run(["git", "-C", str(self.root), "worktree", "add", "--detach", str(linked), "HEAD"],
                       check=True, capture_output=True)
        clone = self.root / "clone"
        subprocess.run(["git", "clone", "-q", str(self.root), str(clone)], check=True, capture_output=True)
        for target in (linked, clone):
            (target / "runtime").mkdir()
            (target / "runtime/tree.json").write_bytes(self.ledger.read_bytes())
            args = command.copy()
            args[4] = str(target)
            run = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(run.returncode, 1, run.stdout)
            self.assertIn("binding differs", run.stderr)

    def test_unrelated_group_diagnostics_do_not_echo_private_values_or_keys(self):
        group = self.tree["communication"]["groups"][1]
        group["updates"][0]["summary"] = {"private-marker": "private-value"}
        run = subprocess.run(self.command(parent="root", participant="root"), capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn("summary", run.stderr)
        self.assertNotIn("private-marker", run.stderr)
        self.assertNotIn("private-value", run.stderr)
        command = self.command(parent="root", participant="root")
        raw = b'{"private-marker":1,"private-marker":2}'
        self.ledger.write_bytes(raw)
        command[-1] = hashlib.sha256(raw).hexdigest()
        run = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertNotIn("private-marker", run.stderr)
        self.assertNotIn("Traceback", run.stderr)

    def test_unsupported_glob_path_is_rejected_before_git_publication(self):
        self.tree["nodes"][0]["status"] = "RUNNING"
        (self.runtime / "a.json").write_text("unrelated tracked file")
        subprocess.run(["git", "-C", str(self.root), "add", "-f", "runtime/a.json"], check=True)
        self.ledger = self.runtime / "[a].json"
        command = self.command(parent="root", participant="root")
        command[5], command[7] = "publish", "runtime/[a].json"
        candidate = copy.deepcopy(self.tree)
        candidate["communication"]["generation"] = 2
        (self.runtime / "candidate.json").write_text(json.dumps(candidate))
        run = subprocess.run(command + ["--candidate", "runtime/candidate.json", "--write"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn("glob markers", run.stderr)
        self.assertEqual(json.loads(self.ledger.read_bytes()), self.tree)

    def test_case_aliases_share_a_writer_lock_and_have_one_winner(self):
        from inspect_worker_communication import ledger_lock_key
        self.tree["nodes"][0]["status"] = "RUNNING"
        command = self.command(parent="root", participant="root")
        alias = self.ledger.with_name("TREE.json")
        if not alias.exists() or not os.path.samefile(alias, self.ledger):
            self.skipTest("case-insensitive filesystem required; exercised by portable CI")
        self.assertEqual(ledger_lock_key(alias), ledger_lock_key(self.ledger))
        command[5] = "publish"
        other = command.copy()
        other[7] = "runtime/TREE.json"
        for number, args in enumerate((command, other)):
            candidate = copy.deepcopy(self.tree)
            candidate["communication"]["generation"] = 2
            candidate["communication"]["groups"][0]["updates"] = [{
                "id": f"case-{number}", "sender_node_id": "root", "recipient_node_ids": ["coordinator"],
                "kind": "progress", "summary": f"candidate {number}", "source_refs": []}]
            path = f"runtime/candidate-{number}.json"
            (self.root / path).write_text(json.dumps(candidate))
            args.extend(["--candidate", path, "--write"])
        first = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        second = subprocess.Popen(other, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        a, b = first.communicate(timeout=30), second.communicate(timeout=30)
        self.assertEqual(sorted([first.returncode, second.returncode]), [0, 1], (a, b))

    def test_lock_identity_survives_atomic_ledger_replacement(self):
        from inspect_worker_communication import ledger_lock_key
        self.save()
        before = ledger_lock_key(self.ledger)
        replacement = self.runtime / "replacement.json"
        replacement.write_bytes(self.ledger.read_bytes())
        os.replace(replacement, self.ledger)
        self.assertEqual(ledger_lock_key(self.ledger), before)

    def test_case_alias_cannot_self_bind_the_mutable_ledger(self):
        self.tree["nodes"][0]["status"] = "RUNNING"
        digest = self.save()
        alias = self.ledger.with_name("TREE.json")
        if not alias.exists() or not os.path.samefile(alias, self.ledger):
            self.skipTest("case-insensitive filesystem required; exercised by portable CI")
        candidate = copy.deepcopy(self.tree)
        candidate["communication"]["generation"] = 2
        candidate["communication"]["groups"][0]["source_bindings"] = [{"path": "runtime/TREE.json", "sha256": digest}]
        run = self.publish_candidate(candidate)
        self.assertEqual(run.returncode, 1)
        self.assertIn("own mutable ledger", run.stderr)


if __name__ == "__main__":
    unittest.main()
