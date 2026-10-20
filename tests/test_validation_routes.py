from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_change_packages import changed_index_validator
from target_adapter_validation.validation_contract import validate_validation_contract, DELEGATE_PATH
from target_validation_support import parse_manifest
from validation_route_contract import validation_route_failures
from context_planning import ContextPlanRequest, plan_target_context
from tests.test_context_planning import TargetFixture, write_json
from context_catalog import word_count, file_digest


class ValidationRouteTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name)
        self.contract = json.loads((ROOT / "templates/target/.ai/assistant/validation-contract.json").read_text())
        self.route = {"inspection": "adapter-health", "completion": "current-change"}
        self.profile = self.target / ".ai/assistant/context/profiles/framework-upgrade.json"
        write_json(self.profile, {"validation_entrypoints": self.route})
        write_json(self.target / ".ai/assistant/context-router.json", {"profile_index": {"framework-upgrade": {"descriptor": self.profile.relative_to(self.target).as_posix()}}})
        write_json(self.target / ".ai/assistant/validation-contract.json", self.contract)
        path = self.target / DELEGATE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "templates/target" / DELEGATE_PATH, path)
        self.manifest = self.target / ".ai/alatyr.yaml"
        self.manifest.write_text("schema_version: 76\nvalidation:\n  contract: .ai/assistant/validation-contract.json\n")

    def codes(self):
        checked = changed_index_validator(self.target)
        validate_validation_contract(checked, parse_manifest(self.manifest))
        return {item.code for item in checked.findings if item.level == "error"}

    def test_registered_contract_path_validates_typed_routes(self):
        self.assertEqual(self.codes(), set())
        for bad in (None, {}, [], True, "current-change", {"inspection": "current-change", "completion": "adapter-health"}, {"inspection": "adapter-health", "completion": "missing"}):
            write_json(self.profile, {"validation_entrypoints": bad})
            with self.subTest(bad=bad):
                self.assertIn("VALIDATION_ROUTE_INVALID", self.codes())

    def test_missing_route_requires_current_schema_but_preserves_legacy_readability(self):
        write_json(self.profile, {})
        self.assertIn("VALIDATION_ROUTE_MISSING", self.codes())
        self.manifest.write_text("schema_version: 75\n")
        self.assertNotIn("VALIDATION_ROUTE_MISSING", self.codes())

    def test_completion_cannot_use_auxiliary_success_or_archive_audit(self):
        for coverage in ("structural-only", "manual"):
            contract = copy.deepcopy(self.contract)
            contract["entrypoints"]["current-change"]["coverage"] = coverage
            self.assertTrue(validation_route_failures(self.route, contract))
        self.assertTrue(validation_route_failures(dict(self.route, completion="archive-audit"), self.contract))
        contract = copy.deepcopy(self.contract)
        contract["entrypoints"]["current-change"]["final_evidence_eligible"] = False
        self.assertTrue(validation_route_failures(self.route, contract))

    def test_malformed_entrypoint_fields_fail_without_type_errors(self):
        for field in ("command", "coverage", "final_evidence_eligible"):
            for value in ({}, [], None, True, 4, "unknown"):
                contract = copy.deepcopy(self.contract)
                contract["entrypoints"]["current-change"][field] = value
                with self.subTest(field=field, value=value):
                    failures = validation_route_failures(self.route, contract)
                    if field == "command" and isinstance(value, str) or field == "final_evidence_eligible" and value is True:
                        continue  # Semantic command validation remains owned by the canonical parser.
                    self.assertTrue(failures)

    def test_context_plan_returns_bound_prefixes_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            fixture = TargetFixture(target)
            fixture.build()
            profile = fixture.assistant / "context/profiles/code-local.json"
            descriptor = json.loads(profile.read_text())
            descriptor["validation_entrypoints"] = self.route
            write_json(profile, descriptor)
            write_json(fixture.assistant / "validation-contract.json", self.contract)
            catalog_path = fixture.assistant / "context-index.json"
            catalog = json.loads(catalog_path.read_text())
            for item in catalog["entries"]:
                if item["path"] == "context/profiles/code-local.json":
                    item.update(estimated_words=word_count(profile), content_digest=file_digest(profile))
            write_json(catalog_path, catalog)
            request = ContextPlanRequest(target, profile="code-local", operation="product-change")
            result = plan_target_context(request)
            self.assertEqual(result["status"], "ready", result)
            route = result["validation_route"]
            self.assertFalse(route["execution_performed"])
            self.assertFalse(route["authorization_granted"])
            self.assertEqual(route["entrypoints"]["completion"]["id"], "current-change")
            self.assertEqual(route["contract_sha256"], file_digest(fixture.assistant / "validation-contract.json"))
            contract_path = fixture.assistant / "validation-contract.json"
            contract_path.write_bytes(contract_path.read_bytes().replace(b"\n", b"\r\n"))
            self.assertEqual(plan_target_context(request)["validation_route"]["contract_sha256"], file_digest(contract_path))
            old_digest = result["plan_digest"]
            contract = copy.deepcopy(self.contract)
            contract["parity"]["result_evidence"] = "changed evidence guidance"
            write_json(fixture.assistant / "validation-contract.json", contract)
            self.assertNotEqual(plan_target_context(request)["plan_digest"], old_digest)
            contract["entrypoints"]["current-change"]["coverage"] = "manual"
            write_json(fixture.assistant / "validation-contract.json", contract)
            self.assertEqual(plan_target_context(request)["status"], "blocked")
            for value in ({}, [], None, True, 4):
                contract["entrypoints"]["current-change"]["coverage"] = value
                write_json(fixture.assistant / "validation-contract.json", contract)
                with self.subTest(coverage=value):
                    self.assertEqual(plan_target_context(request)["status"], "blocked")
            contract = copy.deepcopy(self.contract)
            del contract["entrypoints"]["current-change"]["command"]
            write_json(fixture.assistant / "validation-contract.json", contract)
            self.assertEqual(plan_target_context(request)["status"], "blocked")
