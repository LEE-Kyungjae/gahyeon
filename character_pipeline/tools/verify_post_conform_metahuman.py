#!/usr/bin/env python3
"""Verify real editor evidence and five immutable Looking Glass Go post-conform renders."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(contract_path: Path, uri: str) -> Path:
    path = (contract_path.parent / uri).resolve()
    if not path.is_file():
        raise ValueError(f"missing evidence: {path}")
    return path


def validate_post_conform_contract(contract_path: Path) -> dict:
    value = json.loads(contract_path.read_text(encoding="utf-8"))
    if value.get("state") != "candidate":
        raise ValueError("post-conform contract is not a candidate")
    binding = json.loads(resolve(contract_path, value["binding"]).read_text(encoding="utf-8"))
    if binding.get("state") != "candidate" or binding.get("claim") != "metahuman-candidate-not-approved":
        raise ValueError("MetaHuman candidate binding is absent or overclaims quality")
    required_assets = (
        "metahumanIdentity", "heroBlueprint", "faceSkeletalMesh", "bodySkeletalMesh",
        "faceControlRig", "bodyControlRig",
    )
    if any(not binding.get("assets", {}).get(name) for name in required_assets):
        raise ValueError("candidate binding has missing asset paths")
    if not binding.get("assets", {}).get("grooms"):
        raise ValueError("candidate binding has no Groom")
    editor = json.loads(resolve(contract_path, value["editorEvidence"]).read_text(encoding="utf-8"))
    if editor.get("editorRuntimeVerified") is not True or editor.get("readyForPostConformRender") is not True:
        raise ValueError("Unreal Editor asset evidence is incomplete")
    if editor.get("dnaOrRigLogicBound") is not True:
        raise ValueError("DNA/RigLogic binding has not been verified")
    if not all(editor.get("checks", {}).values()):
        raise ValueError("one or more MetaHuman asset checks failed")
    render = value.get("renderEvidence", {})
    if render.get("profile") != "looking-glass-go" or render.get("resolution") != [1440, 2560]:
        raise ValueError("post-conform renders are not bound to Looking Glass Go")
    manifest_path = resolve(contract_path, render["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = render.get("views", [])
    if manifest.get("resolution") != [1440, 2560] or manifest.get("views") is None:
        raise ValueError("render manifest has invalid resolution or views")
    entries = {item.get("view"): item for item in manifest["views"]}
    if set(entries) != set(expected) or len(expected) != 5:
        raise ValueError("exactly five fixed identity views are required")
    for view in expected:
        item = entries[view]
        image_path = resolve(contract_path, f"{render['directory']}/{item['file']}")
        if digest(image_path) != item.get("sha256"):
            raise ValueError(f"render checksum mismatch: {view}")
        with Image.open(image_path) as image:
            if image.size != (1440, 2560):
                raise ValueError(f"render resolution mismatch: {view}")
    comparison = value.get("comparison", {})
    if comparison.get("identityScoreMayBeEmitted") is not False or comparison.get("automaticApproval") is not False:
        raise ValueError("post-conform evidence may not auto-score or auto-approve identity")
    return {"valid": True, "iteration": value["iteration"], "views": 5,
            "displayProfile": "looking-glass-go", "automaticApproval": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate_post_conform_contract(args.contract.resolve())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
