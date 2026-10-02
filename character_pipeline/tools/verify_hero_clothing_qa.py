#!/usr/bin/env python3
"""Fail-closed modular clothing, Chaos Cloth and Go evidence verifier."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_clothing_contract(config: dict, binding: dict, base: Path) -> dict:
    if config.get("displayProfile") != "looking-glass-go" or config.get("resolution") != [1440, 2560]:
        raise ValueError("clothing QA must use Looking Glass Go")
    if binding.get("state") != "candidate" or binding.get("claim") != "production-clothing-candidate-not-approved":
        raise ValueError("production clothing candidate is absent")
    if set(binding.get("slots", {})) != set(config["requiredSlots"]):
        raise ValueError("modular clothing slots are incomplete")
    if set(binding.get("assets", {})) != set(config["requiredAssets"]):
        raise ValueError("clothing/Chaos Cloth assets are incomplete")
    if set(binding.get("pbrChannels", {})) != set(config["requiredPbrChannels"]):
        raise ValueError("clothing PBR channels are incomplete")
    if binding.get("modularity") != config["modularity"]:
        raise ValueError("clothing modularity policy is not proven")
    lods = binding.get("lods", [])
    screens = [item.get("screenSize") for item in lods]
    if len(lods) < 2 or len(screens) != len(set(screens)) or screens != sorted(screens, reverse=True):
        raise ValueError("clothing requires at least two descending unique LODs")
    editor_path = (base / binding["editorEvidence"]).resolve()
    editor = json.loads(editor_path.read_text()) if editor_path.is_file() else {}
    if (editor.get("schemaVersion") != 1
            or editor.get("kind") != "metahuman-production-clothing-editor-evidence"
            or editor.get("engine") != "5.6"
            or editor.get("editorRuntimeVerified") is not True
            or editor.get("automaticApproval") is not False
            or editor.get("qualityClaim") is not None):
        raise ValueError("Unreal Editor clothing evidence is missing")
    expected_assets = {"skeletalMesh": "SkeletalMesh", "materials": "MaterialInstanceConstant",
                       "physicsAsset": "PhysicsAsset", "clothConfig": "ChaosClothConfig",
                       "clothDataflow": "Dataflow"}
    observed_assets = editor.get("assets", {})
    for name, expected_class in expected_assets.items():
        item = observed_assets.get(name, {})
        if item.get("path") != binding["assets"][name] or item.get("class") != expected_class:
            raise ValueError(f"Editor clothing asset evidence differs: {name}")
    observed_slots = editor.get("slots", {})
    if set(observed_slots) != set(config["requiredSlots"]):
        raise ValueError("Editor clothing slots are incomplete")
    if len({item.get("path") for item in observed_slots.values()}) != len(observed_slots):
        raise ValueError("Editor clothing slots are not separate assets")
    if any(item.get("class") != "SkeletalMesh" for item in observed_slots.values()):
        raise ValueError("Editor clothing slots are not SkeletalMesh assets")
    checks = editor.get("checks", {})
    if set(checks) != set(config["runtimeChecks"]) or not all(checks.values()):
        raise ValueError("clothing runtime checks are incomplete")
    if editor.get("observedBodyPenetrations") != 0:
        raise ValueError("clothing body penetration was observed")
    manifest_path = (base / binding["captureManifest"]).resolve()
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    entries = {item.get("id"): item for item in manifest.get("captures", [])}
    if set(entries) != set(config["captures"]) or manifest.get("resolution") != [1440, 2560]:
        raise ValueError("clothing Go captures are incomplete")
    for capture_id, item in entries.items():
        path = (manifest_path.parent / item["file"]).resolve()
        if not path.is_file() or digest(path) != item.get("sha256"):
            raise ValueError(f"missing or changed clothing capture: {capture_id}")
        with Image.open(path) as image:
            if image.size != (1440, 2560):
                raise ValueError(f"clothing capture resolution mismatch: {capture_id}")
    if config["approvalPolicy"].get("automaticApproval") is not False:
        raise ValueError("clothing QA may not auto-approve")
    return {"valid": True, "slots": len(config["requiredSlots"]),
            "runtimeChecks": len(checks), "captures": len(entries), "lods": len(lods),
            "observedBodyPenetrations": 0, "automaticApproval": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/hero_clothing_qa.json"))
    parser.add_argument("--binding", type=Path, default=Path("character_pipeline/metahuman/validation/v001/clothing-binding.json"))
    args = parser.parse_args()
    print(json.dumps(validate_clothing_contract(
        json.loads(args.config.read_text()), json.loads(args.binding.read_text()),
        args.binding.parent.resolve())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
