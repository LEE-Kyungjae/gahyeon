#!/usr/bin/env python3
"""Build an immutable MetaHuman Identity work order from a P27 selection receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_handoff(config: dict[str, Any], selection_path: Path, identity_path: Path,
                  display_profile_path: Path) -> dict[str, Any]:
    selection, identity, display = load(selection_path), load(identity_path), load(display_profile_path)
    if (config.get("schemaVersion") != 1 or config.get("stage") != "metahuman-identity-conform-input" or
            config.get("engine") != "Unreal Engine 5.6"):
        raise ValueError("unsupported MetaHuman handoff contract")
    if (selection.get("state") != "selection-reviewed" or selection.get("automatic") is not False or
            selection.get("productionMeshAllowed") is not False):
        raise ValueError("handoff requires a human-reviewed shape-only selection")
    selected = selection.get("selected", {})
    if selected.get("role") != "temporary-shape-estimate-for-metahuman-conform":
        raise ValueError("selected reconstruction has the wrong role")
    mesh = Path(selected.get("rawMesh", {}).get("path", ""))
    if (not mesh.is_absolute() or mesh.is_symlink() or not mesh.is_file() or
            digest(mesh) != selected.get("rawMesh", {}).get("sha256")):
        raise ValueError("selected reconstruction mesh checksum differs")
    shortlist = Path(selection.get("shortlist", {}).get("path", ""))
    if (not shortlist.is_absolute() or shortlist.is_symlink() or not shortlist.is_file() or
            digest(shortlist) != selection.get("shortlist", {}).get("sha256")):
        raise ValueError("selection shortlist checksum differs")
    state_path = Path(selected["candidate"]) / "postprocess-state.json"
    if (not state_path.is_file() or digest(state_path) != selected.get("postprocessStateSha256")):
        raise ValueError("selected postprocess state checksum differs")
    if identity.get("schemaVersion") != 1 or identity.get("characterId") != config["characterId"]:
        raise ValueError("identity authority differs from handoff character")
    if (display.get("profileId") != "looking-glass-go" or
            display.get("device", {}).get("panelResolution") != [1440, 2560] or
            display.get("quilt", {}).get("viewCount") != 66 or
            display.get("quilt", {}).get("failClosedWithoutCalibration") is not True):
        raise ValueError("display profile is not calibrated fail-closed Looking Glass Go")
    extension = mesh.suffix.lower().lstrip(".")
    if extension not in {"obj", "fbx", "glb", "gltf", "ply"}:
        raise ValueError("unsupported reconstruction source format")
    if len(config.get("requiredIdentityViews", [])) != 5 or not config.get("forbiddenClaims"):
        raise ValueError("handoff validation or claim policy is incomplete")
    return {
        "schemaVersion": 1, "characterId": config["characterId"], "iteration": config["iteration"],
        "stage": "metahuman-identity-conform-input", "state": "work-order-toolchain-blocked",
        "engine": config["engine"],
        "selectionReceipt": {"path": str(selection_path.resolve()), "sha256": digest(selection_path)},
        "sourceShape": {"path": str(mesh.resolve()), "sha256": digest(mesh), "format": extension,
                        "role": selected["role"], "model": selected["model"], "seed": selected["seed"],
                        "claim": "reconstruction-shape-reference-not-production-topology"},
        "postprocessState": {"path": str(state_path.resolve()), "sha256": digest(state_path)},
        "shortlist": {"path": str(shortlist.resolve()), "sha256": digest(shortlist)},
        "identityAuthority": {"path": str(identity_path.resolve()), "sha256": digest(identity_path)},
        "coordinateContract": config["targetCoordinateSystem"],
        "preImportOperations": config["requiredPreImportOperations"],
        "outputRequirement": {
            "scope": "neutral-head-neck-and-eyes-only", "format": ["obj", "fbx"],
            "separateWorkingCopyRequired": True, "overwriteSourceForbidden": True,
            "metahumanTopologyRequiredAfterConform": True
        },
        "captureProtocol": {"profile": str(display_profile_path.resolve()),
                            "profileSha256": digest(display_profile_path),
                            "resolution": [1440, 2560], "views": config["requiredIdentityViews"],
                            "quiltViewCount": 66, "quiltRequiresConnectedCalibration": True},
        "requiredUnrealActions": [
            "create MetaHuman Identity from normalized neutral head mesh",
            "promote and track neutral front frame, then solve identity",
            "conform MetaHuman template topology and retrieve rigged character",
            "verify DNA or RigLogic, face/body Control Rigs and separate meshes",
            "render fixed Looking Glass Go identity views and compare with canonical authority"
        ],
        "forbiddenClaimsUntilEvidence": config["forbiddenClaims"],
        "automaticApproval": False, "productionMeshAllowed": False,
    }


def verify_handoff(path: Path) -> dict[str, Any]:
    value = load(path)
    if (value.get("stage") != "metahuman-identity-conform-input" or
            value.get("state") != "work-order-toolchain-blocked" or
            value.get("automaticApproval") is not False or value.get("productionMeshAllowed") is not False):
        raise ValueError("selected MetaHuman handoff overclaims readiness")
    for key in ("selectionReceipt", "sourceShape", "postprocessState", "shortlist", "identityAuthority"):
        record = value.get(key, {}); target = Path(record.get("path", ""))
        if not target.is_absolute() or target.is_symlink() or not target.is_file() or digest(target) != record.get("sha256"):
            raise ValueError(f"handoff lineage differs: {key}")
    capture = value.get("captureProtocol", {}); profile = Path(capture.get("profile", ""))
    if (not profile.is_file() or digest(profile) != capture.get("profileSha256") or
            capture.get("resolution") != [1440, 2560] or capture.get("quiltViewCount") != 66 or
            capture.get("quiltRequiresConnectedCalibration") is not True or len(capture.get("views", [])) != 5):
        raise ValueError("handoff Looking Glass Go capture contract differs")
    coordinate = value.get("coordinateContract", {})
    if coordinate != {"unit": "centimeter", "upAxis": "+Z", "forwardAxis": "+X", "handedness": "left"}:
        raise ValueError("handoff coordinate contract differs")
    if value.get("outputRequirement", {}).get("overwriteSourceForbidden") is not True:
        raise ValueError("handoff must preserve reconstruction source")
    return {"valid": True, "state": value["state"], "views": 5,
            "displayProfile": "looking-glass-go", "productionMeshAllowed": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/metahuman_identity_handoff.json"))
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--identity", type=Path, default=Path("artifacts/gahyeon-ch/identity-reference.json"))
    parser.add_argument("--display-profile", type=Path,
                        default=Path("character_pipeline/unreal/render_pipeline/looking-glass-go.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        result = verify_handoff(args.output.resolve())
    else:
        if not args.selection: parser.error("--selection is required when building")
        if args.output.exists(): raise SystemExit(f"refusing to overwrite: {args.output}")
        result = build_handoff(load(args.config), args.selection.resolve(), args.identity.resolve(),
                               args.display_profile.resolve())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, "state": result["state"], "productionMeshAllowed": False}))
    return 0


if __name__ == "__main__": raise SystemExit(main())
