"""Project-knowledge target validation integration."""

from __future__ import annotations

from pathlib import Path

from project_knowledge import validate_project_knowledge
from target_adapter_validation.contract_compatibility import contract_compatibility
from target_adapter_validation.domain import DomainValidationHost
from target_validation_support import ManifestData, dotted


ROOT = Path(__file__).resolve().parents[2]
PROJECT_KNOWLEDGE_CONTRACT = contract_compatibility("project-knowledge")


def validate_project_knowledge_contract(self: DomainValidationHost, manifest: ManifestData | None) -> None:
    index_relpath = ".ai/project/knowledge/index.json"
    expected_manifest = {
        ("operations", "project_knowledge"): ".ai/assistant/flows/project-knowledge.flow.md",
        ("operations", "project_knowledge_promotion"): ".ai/assistant/templates/project-knowledge-promotion.json",
        ("operations", "project_knowledge_route_shard"): ".ai/assistant/templates/project-knowledge-route-shard.json",
        ("project_knowledge", "index"): index_relpath,
        ("project_knowledge", "route_shards"): ".ai/project/knowledge/routes",
        ("project_knowledge", "promotions"): ".ai/project/knowledge/promotions",
        ("project_knowledge", "routing"): ".ai/assistant/context/project-knowledge-routing.json",
        ("project_knowledge", "flow"): ".ai/assistant/flows/project-knowledge.flow.md",
        ("project_knowledge", "gate"): ".ai/assistant/gates/project-knowledge.md",
        ("project_knowledge", "promotion_template"): ".ai/assistant/templates/project-knowledge-promotion.json",
        ("project_knowledge", "route_shard_template"): ".ai/assistant/templates/project-knowledge-route-shard.json",
    }
    if manifest is not None:
        for key, expected in expected_manifest.items():
            scalar = manifest.scalars.get(key)
            if scalar is None or scalar.value != expected:
                self.error(
                    "PROJECT_KNOWLEDGE_MANIFEST_PATH",
                    f"{dotted(key)} must be {expected}",
                    ".ai/alatyr.yaml",
                )
        contract = manifest.scalars.get(("project_knowledge", "contract_version"))
        expected_contract_version = str(
            PROJECT_KNOWLEDGE_CONTRACT["manifest_contract_version"]
        )
        if contract is None or contract.value != expected_contract_version:
            self.error(
                "PROJECT_KNOWLEDGE_CONTRACT_VERSION",
                f"project_knowledge.contract_version must be {expected_contract_version}",
                ".ai/alatyr.yaml",
            )

    findings = validate_project_knowledge(
        self.target,
        ROOT / "schemas",
        allow_placeholders=self.allow_placeholders,
    )
    for finding in findings:
        self.add_finding(
            finding.level,
            finding.code,
            finding.message,
            finding.path,
        )

    index = self.load_json_object(
        self.target_path(index_relpath), "PROJECT_KNOWLEDGE_INDEX"
    )
    if index is None or manifest is None:
        return
    for manifest_field, index_field in {
        "owner": "owner",
        "review_policy": "review_policy",
        "retention_policy": "retention_policy",
        "redaction_policy": "redaction_policy",
    }.items():
        scalar = manifest.scalars.get(("project_knowledge", manifest_field))
        if scalar is None or scalar.value != index.get(index_field):
            self.error(
                "PROJECT_KNOWLEDGE_MANIFEST_POLICY_DRIFT",
                f"project_knowledge.{manifest_field} differs from index.{index_field}",
                ".ai/alatyr.yaml",
            )
