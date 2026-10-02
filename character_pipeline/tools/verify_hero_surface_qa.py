#!/usr/bin/env python3
"""Fail-closed validation for production MetaHuman skin and eye evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_surface_contract(config: dict, binding: dict, base: Path) -> dict:
    if config.get("displayProfile") != "looking-glass-go" or config.get("resolution") != [1440, 2560]:
        raise ValueError("surface QA must use Looking Glass Go")
    if binding.get("state") != "candidate" or binding.get("claim") != "production-surface-candidate-not-approved":
        raise ValueError("production surface candidate is absent")
    if not binding.get("skinMaterialInstance") or not binding.get("eyeMaterialInstances"):
        raise ValueError("skin or eye material binding is absent")
    minimum = config["skin"]["minimumTextureResolution"]
    for channel in config["skin"]["requiredChannels"]:
        item = binding.get("textures", {}).get(channel)
        if not item:
            raise ValueError(f"missing skin channel: {channel}")
        path = (base / item["file"]).resolve()
        if not path.is_file() or digest(path) != item.get("sha256"):
            raise ValueError(f"missing or changed texture: {channel}")
        with Image.open(path) as image:
            if min(image.size) < minimum:
                raise ValueError(f"skin channel below 4K: {channel}")
    if set(binding.get("zoneMasks", {})) != set(config["skin"]["requiredZones"]):
        raise ValueError("skin zone masks are incomplete")
    if set(binding.get("eyeParts", {})) != set(config["eyes"]["requiredParts"]):
        raise ValueError("physical eye parts are incomplete")
    evidence_path = (base / binding["editorEvidence"]).resolve()
    evidence = json.loads(evidence_path.read_text()) if evidence_path.is_file() else {}
    if (evidence.get("schemaVersion") != 1
            or evidence.get("kind") != "metahuman-production-surface-editor-evidence"
            or evidence.get("engine") != "5.6"
            or evidence.get("editorRuntimeVerified") is not True
            or evidence.get("automaticApproval") is not False
            or evidence.get("qualityClaim") is not None
            or not all(evidence.get("checks", {}).values())):
        raise ValueError("Unreal Editor surface evidence is incomplete")
    editor_skin = evidence.get("skin", {})
    editor_eyes = evidence.get("eyes", {})
    if editor_skin.get("materialInstance") != binding["skinMaterialInstance"]:
        raise ValueError("Editor skin binding differs")
    if set(editor_skin.get("textureChannels", {})) != set(config["skin"]["requiredChannels"]):
        raise ValueError("Editor skin texture channels are incomplete")
    if any(item.get("class") != "Texture2D" or min(item.get("dimensions", [0, 0])) < minimum
           for item in editor_skin["textureChannels"].values()):
        raise ValueError("Editor skin textures are not observed 4K Texture2D assets")
    if set(editor_eyes.get("parts", {})) != set(config["eyes"]["requiredParts"]):
        raise ValueError("Editor physical eye parts are incomplete")
    if set(editor_eyes.get("materialInstances", [])) != set(binding["eyeMaterialInstances"]):
        raise ValueError("Editor eye material bindings differ")
    manifest_path = (base / binding["captureManifest"]).resolve()
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    required = {item["id"] for item in config["captures"]}
    entries = {item.get("id"): item for item in manifest.get("captures", [])}
    if set(entries) != required or manifest.get("resolution") != [1440, 2560]:
        raise ValueError("surface close-up captures are incomplete or not Go-sized")
    for capture_id, item in entries.items():
        path = (manifest_path.parent / item["file"]).resolve()
        if not path.is_file() or digest(path) != item.get("sha256"):
            raise ValueError(f"missing or changed capture: {capture_id}")
        with Image.open(path) as image:
            if image.size != (1440, 2560):
                raise ValueError(f"capture resolution mismatch: {capture_id}")
    if config["approvalPolicy"].get("automaticApproval") is not False:
        raise ValueError("surface QA may not auto-approve")
    return {"valid": True, "skinChannels": len(config["skin"]["requiredChannels"]),
            "skinZones": len(config["skin"]["requiredZones"]),
            "eyeParts": len(config["eyes"]["requiredParts"]), "captures": len(required),
            "automaticApproval": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/hero_surface_qa.json"))
    parser.add_argument("--binding", type=Path, default=Path("character_pipeline/metahuman/validation/v001/surface-binding.json"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    binding = json.loads(args.binding.read_text())
    print(json.dumps(validate_surface_contract(config, binding, args.binding.parent.resolve())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
