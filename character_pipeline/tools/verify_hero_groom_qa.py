#!/usr/bin/env python3
"""Fail-closed production Groom, binding, LOD and Go capture verifier."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_groom_contract(config: dict, binding: dict, base: Path) -> dict:
    if config.get("displayProfile") != "looking-glass-go" or config.get("resolution") != [1440, 2560]:
        raise ValueError("Groom QA must use Looking Glass Go")
    if binding.get("state") != "candidate" or binding.get("claim") != "production-groom-candidate-not-approved":
        raise ValueError("production Groom candidate is absent")
    if set(binding.get("groups", {})) != set(config["requiredGroups"]):
        raise ValueError("Groom groups are incomplete")
    if set(binding.get("features", {})) != set(config["requiredFeatures"]):
        raise ValueError("canonical Groom features are incomplete")
    if set(binding.get("bindings", {})) != set(config["requiredBindings"]):
        raise ValueError("Unreal Groom bindings are incomplete")
    lods = binding.get("lods", [])
    modes = {item.get("mode") for item in lods}
    if "strands" not in modes or not (modes & set(config["lodPolicy"]["fallbackAllowed"])):
        raise ValueError("Groom requires strands and cards/mesh fallback")
    screen_sizes = [item.get("screenSize") for item in lods]
    if (len(screen_sizes) != len(set(screen_sizes)) or
            screen_sizes != sorted(screen_sizes, reverse=True)):
        raise ValueError("Groom LOD screen sizes must be unique and descending")
    editor_path = (base / binding["editorEvidence"]).resolve()
    editor = json.loads(editor_path.read_text()) if editor_path.is_file() else {}
    if (editor.get("schemaVersion") != 1
            or editor.get("kind") != "metahuman-production-groom-editor-evidence"
            or editor.get("engine") != "5.6"
            or editor.get("editorRuntimeVerified") is not True
            or editor.get("automaticApproval") is not False
            or editor.get("qualityClaim") is not None):
        raise ValueError("Unreal Editor Groom evidence is missing")
    assets = editor.get("assets", {})
    expected_bindings = binding["bindings"]
    expected_assets = {
        "groom": ("groom-asset", "GroomAsset"),
        "binding": ("groom-binding-asset", "GroomBindingAsset"),
        "targetSkeletalMesh": ("target-skeletal-mesh", "SkeletalMesh"),
        "physicsAsset": ("physics-asset", "PhysicsAsset"),
        "materialInstance": ("material-instance", "MaterialInstanceConstant"),
    }
    for name, (binding_name, expected_class) in expected_assets.items():
        item = assets.get(name, {})
        if item.get("path") != expected_bindings[binding_name] or item.get("class") != expected_class:
            raise ValueError(f"Editor Groom asset evidence differs: {name}")
    if {item.get("mode") for item in editor.get("lods", [])} != modes:
        raise ValueError("Editor-observed Groom LOD modes differ")
    checks = editor.get("checks", {})
    if set(checks) != set(config["runtimeChecks"]) or not all(checks.values()):
        raise ValueError("Groom runtime checks are incomplete")
    manifest_path = (base / binding["captureManifest"]).resolve()
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    entries = {item.get("id"): item for item in manifest.get("captures", [])}
    if set(entries) != set(config["captures"]) or manifest.get("resolution") != [1440, 2560]:
        raise ValueError("Groom Go captures are incomplete")
    for capture_id, item in entries.items():
        path = (manifest_path.parent / item["file"]).resolve()
        if not path.is_file() or digest(path) != item.get("sha256"):
            raise ValueError(f"missing or changed Groom capture: {capture_id}")
        with Image.open(path) as image:
            if image.size != (1440, 2560):
                raise ValueError(f"Groom capture resolution mismatch: {capture_id}")
    if config["approvalPolicy"].get("automaticApproval") is not False:
        raise ValueError("Groom QA may not auto-approve")
    return {"valid": True, "groups": len(config["requiredGroups"]),
            "features": len(config["requiredFeatures"]), "runtimeChecks": len(checks),
            "captures": len(entries), "lods": len(lods), "automaticApproval": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/hero_groom_qa.json"))
    parser.add_argument("--binding", type=Path, default=Path("character_pipeline/metahuman/validation/v001/groom-binding.json"))
    args = parser.parse_args()
    print(json.dumps(validate_groom_contract(
        json.loads(args.config.read_text()), json.loads(args.binding.read_text()),
        args.binding.parent.resolve())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
