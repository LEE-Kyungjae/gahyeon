#!/usr/bin/env python3
"""Build a deterministic Blender G1 scene plan from an extracted handoff package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


COLLECTIONS = [
    "G1_REFERENCES_CANONICAL",
    "G1_REFERENCES_SUPPORTING",
    "G1_MODEL_BODY",
    "G1_MODEL_FACE",
    "G1_MODEL_EYES_TEETH",
    "G1_MODEL_HAIR",
    "G1_MODEL_OUTFIT",
    "G1_RIG",
    "G1_GUIDES_NON_AUTHORITATIVE",
    "G1_EVIDENCE_CAMERAS",
]

# Neutral drafting guides only. These values make the scene immediately usable,
# but are deliberately not identity evidence and must be adjusted against the
# sealed canonical references before any candidate submission.
GUIDE_LANDMARKS_CM = {
    "ground": (0, 0, 0),
    "ankle": (0, 0, 8),
    "knee": (0, 0, 48),
    "hip": (0, 0, 92),
    "waist": (0, 0, 108),
    "shoulder_center": (0, 0, 142),
    "chin": (0, 0, 150),
    "eye_line": (0, 0, 162),
    "crown": (0, 0, 180),
    "shoulder_left": (-22, 0, 142),
    "elbow_left": (-48, 0, 125),
    "wrist_left": (-75, 0, 105),
    "shoulder_right": (22, 0, 142),
    "elbow_right": (48, 0, 125),
    "wrist_right": (75, 0, 105),
}

CAMERA_VIEWS = {
    "face-neutral-front": ((0, -180, 160), (0, 0, 160), 60),
    "face-neutral-three-quarter-left": ((-130, -130, 160), (0, 0, 160), 60),
    "face-neutral-three-quarter-right": ((130, -130, 160), (0, 0, 160), 60),
    "face-neutral-left-profile": ((-180, 0, 160), (0, 0, 160), 60),
    "face-neutral-right-profile": ((180, 0, 160), (0, 0, 160), 60),
    "body-neutral-front": ((0, -350, 90), (0, 0, 90), 220),
    "body-neutral-profile": ((350, 0, 90), (0, 0, 90), 220),
    "body-neutral-rear": ((0, 350, 90), (0, 0, 90), 220),
    "hair-front": ((0, -180, 170), (0, 0, 170), 70),
    "hair-side": ((180, 0, 170), (0, 0, 170), 70),
    "hair-rear": ((0, 180, 170), (0, 0, 170), 70),
    "hair-top": ((0, 0, 300), (0, 0, 165), 70),
    "outfit-front": ((0, -350, 95), (0, 0, 95), 220),
    "outfit-side": ((350, 0, 95), (0, 0, 95), 220),
    "outfit-rear": ((0, 350, 95), (0, 0, 95), 220),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contained_file(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe package-relative path: {relative}")
    resolved = (root / candidate).resolve()
    if root not in resolved.parents or not resolved.is_file() or resolved.is_symlink():
        raise ValueError(f"missing or unsafe handoff file: {relative}")
    return resolved


def build_plan(handoff_dir: Path) -> dict:
    root = handoff_dir.resolve()
    manifest_path = contained_file(root, "package-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("schemaVersion") != 2
            or manifest.get("purpose") != "G1-model-sheet-authoring"
            or manifest.get("characterId") != "gahyeon"):
        raise ValueError("unsupported G1 handoff package")

    files = manifest.get("files", [])
    inventory = {item.get("path"): item for item in files}
    if len(inventory) != len(files):
        raise ValueError("handoff file inventory contains duplicates")
    for relative, item in inventory.items():
        path = contained_file(root, relative)
        if path.stat().st_size != item.get("bytes") or digest(path) != item.get("sha256"):
            raise ValueError(f"handoff file failed integrity check: {relative}")

    work_order_path = contained_file(root, manifest.get("authoringWorkOrder", ""))
    work_order = json.loads(work_order_path.read_text(encoding="utf-8"))
    if (work_order.get("gate") != "G1"
            or work_order.get("status") != "ready-for-authoring"
            or work_order.get("productionTarget", {}).get("workingUnits") != "centimeters"):
        raise ValueError("handoff work order is not a centimeter-based ready G1 order")

    reference_by_index = {item["index"]: item for item in manifest.get("references", [])}
    evidence = work_order.get("requiredEvidence", [])
    views = [item.get("view") for item in evidence]
    if len(views) != 15 or len(set(views)) != 15:
        raise ValueError("G1 scene requires exactly 15 unique evidence views")

    used_indices = sorted({index for item in evidence for index in item.get("sourceAnchors", [])})
    for index in used_indices:
        item = reference_by_index.get(index)
        if item is None:
            raise ValueError(f"evidence anchor is missing from package: {index}")
        if item.get("classification") != "canonical":
            raise ValueError(f"supporting reference cannot drive G1 geometry: {index}")

    # Keep the complete handoff available to the artist. Supporting images are
    # useful cross-checks, while their sealed classification prevents them from
    # silently becoming neutral face/body geometry authority.
    references = []
    for index, item in sorted(reference_by_index.items()):
        path = contained_file(root, item["packagedPath"])
        if digest(path) != item.get("sha256"):
            raise ValueError(f"reference checksum mismatch: {index}")
        references.append({
            "index": index,
            "path": item["packagedPath"],
            "classification": item["classification"],
            "sha256": item["sha256"],
        })

    if set(views) != set(CAMERA_VIEWS):
        raise ValueError("G1 work order views do not match the sealed camera layout")
    cameras = []
    for item in evidence:
        location, target, scale = CAMERA_VIEWS[item["view"]]
        cameras.append({
            "name": f"CAM_G1_{item['view'].replace('-', '_').upper()}",
            "view": item["view"],
            "designAuthority": item["designAuthority"],
            "sourceAnchors": item["sourceAnchors"],
            "projection": "orthographic",
            "locationCm": list(location),
            "targetCm": list(target),
            "orthoScaleCm": scale,
        })

    return {
        "schemaVersion": 1,
        "characterId": "gahyeon",
        "gate": "G1",
        "purpose": "blender-authoring-bootstrap",
        "source": {
            "packageManifest": "package-manifest.json",
            "packageManifestSha256": digest(manifest_path),
            "workOrder": manifest["authoringWorkOrder"],
            "workOrderSha256": digest(work_order_path),
        },
        "scene": {
            "units": "centimeters",
            "unitSystem": "METRIC",
            "unitScale": 0.01,
            "neutralPose": "A-pose",
            "forwardAxis": "-Y",
            "upAxis": "Z",
            "collections": COLLECTIONS,
            "rootObject": "ROOT_Gahyeon_G1",
        },
        "authoringGuides": {
            "authority": "non-authoritative-adjustable",
            "basis": "generic-180cm-a-pose-starting-layout",
            "symmetryPlane": "X=0",
            "landmarksCm": {name: list(position)
                            for name, position in GUIDE_LANDMARKS_CM.items()},
        },
        "referenceImages": references,
        "evidenceCameras": cameras,
        "export": {
            "fbx": {"axisForward": "-Y", "axisUp": "Z", "applyUnitScale": True},
            "glb": {"format": "GLB", "exportYup": True},
        },
        "evidenceRender": {
            "resolutionX": 1024,
            "resolutionY": 1024,
            "fileFormat": "PNG",
            "colorMode": "RGBA",
            "transparentBackground": True,
        },
        "identityRules": work_order.get("identityRules", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = build_plan(args.handoff_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({"valid": True, "references": len(plan["referenceImages"]),
                      "cameras": len(plan["evidenceCameras"]),
                      "output": str(args.output.resolve())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
