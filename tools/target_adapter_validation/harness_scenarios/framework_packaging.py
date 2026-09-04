"""Target-validator scenarios for framework packaging."""

from __future__ import annotations

from .common import (
    FRAMEWORK_ROOT,
    ROOT,
    findings_payload,
    json,
    projected_framework_contents,
    result_code,
    validator,
    write_json,
)


def run(target: Path, failures: list[str]) -> None:
    pack_target = target / "pack-target"
    framework_target = pack_target / ".ai" / "framework"
    framework_target.mkdir(parents=True)
    manifest_path = pack_target / ".ai" / "alatyr.yaml"
    manifest_path.write_text("framework:\n  pack: core\n", encoding="utf-8")
    for name, content in projected_framework_contents("core").items():
        destination = framework_target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            destination.write_bytes((FRAMEWORK_ROOT / name).read_bytes())
        else:
            destination.write_bytes(content.encode("utf-8"))
    pack_validator = validator(pack_target, ROOT)
    pack_validator.check_framework_baseline()
    pack_drift = [
        finding
        for finding in pack_validator.findings
        if finding.code.startswith("FRAMEWORK_")
    ]
    if pack_drift:
        failures.append(
            "fresh selective framework pack must match its projected baseline: "
            + ", ".join(finding.code for finding in pack_drift)
        )

    inventory_path = framework_target / "file-inventory.json"
    original_inventory = inventory_path.read_bytes()
    inventory = json.loads(original_inventory.decode("utf-8"))
    inventory["files"][0]["sha256"] = "0" * 64
    write_json(inventory_path, inventory)
    tampered_inventory_validator = validator(pack_target, ROOT)
    tampered_inventory_validator.check_framework_baseline()
    tampered_inventory_codes = {
        finding.code for finding in tampered_inventory_validator.findings
    }
    if "FRAMEWORK_PACK_INVENTORY_DIGEST_DRIFT" not in tampered_inventory_codes:
        failures.append("selective pack must detect a self-declared digest change")
    if "FRAMEWORK_PACK_INVENTORY_CONTENT_DRIFT" not in tampered_inventory_codes:
        failures.append("selective pack must detect projected inventory tampering")
    if result_code(
        tampered_inventory_validator.findings, strict_warnings=False
    ) != 1:
        failures.append("framework integrity drift must fail without strict warnings")
    drift_payload = findings_payload(
        tampered_inventory_validator.findings,
        target=pack_target,
        strict_warnings=False,
    )
    if drift_payload.get("adapter_health", {}).get("state") != "blocked":
        failures.append("framework integrity drift must block adapter health")
    if drift_payload.get("counts", {}).get("blocking_warnings", 0) < 1:
        failures.append("validator JSON must count blocking warnings")
    inventory_path.write_bytes(original_inventory)

    registry_path = framework_target / "rule-registry.json"
    original_registry = registry_path.read_bytes()
    registry = json.loads(original_registry.decode("utf-8"))
    registry["rules"] = registry["rules"][1:]
    write_json(registry_path, registry)
    tampered_registry_validator = validator(pack_target, ROOT)
    tampered_registry_validator.check_framework_baseline()
    if "FRAMEWORK_PACK_REGISTRY_DRIFT" not in {
        finding.code for finding in tampered_registry_validator.findings
    }:
        failures.append("selective pack must detect projected registry tampering")
    registry_path.write_bytes(original_registry)
