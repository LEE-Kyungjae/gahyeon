"""Small source-independent fixtures for character quality contract tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_source_pack(root: Path) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    face_views = [
        "front", "left-profile", "right-profile", "three-quarter", "front", "front",
        "high-angle", "low-angle", "three-quarter", "front", "front", "front",
    ]
    references = []
    for index, view in enumerate(face_views, 1):
        name = f"ChatGPT Image fixture {index:02d}.png"
        path = root / name
        path.write_bytes(f"canonical-face:{index}:{view}".encode())
        references.append({"index": index, "file": name, "sha256": _sha(path),
                           "kind": "face", "view": view, "identityAuthority": "canonical"})
    body_views = ["front", "right-profile", "three-quarter", "action", "front", "action"]
    for index, view in enumerate(body_views, 13):
        name = f"ChatGPT Image fixture {index:02d}.png"
        path = root / name
        path.write_bytes(f"canonical-body:{index}:{view}".encode())
        references.append({"index": index, "file": name, "sha256": _sha(path),
                           "kind": "full-body", "view": view,
                           "identityAuthority": "canonical"})
    supporting_path = root / "ChatGPT Image fixture 19.png"
    supporting_path.write_bytes(b"supporting-upper-body")
    supporting = [{
        "index": 19, "file": supporting_path.name, "sha256": _sha(supporting_path),
        "kind": "upper-body", "view": "front", "identityAuthority": "supporting",
        "allowedUses": ["identity-cross-check"],
        "excludedFrom": ["neutral-face-geometry", "primary-body-geometry", "canonical-rear-evidence"],
        "rationale": "Contract fixture supporting evidence only."
    }]
    identity = {
        "schemaVersion": 1, "characterId": "gahyeon", "status": "source-canon",
        "canonicalSource": "user-provided-originals",
        "sourceInventory": {"operatorDeclaredCount": 19, "presentCount": 19,
                            "status": "complete", "note": "Self-contained CI fixture."},
        "minimums": {"face": 12, "fullBody": 6},
        "references": references, "supportingReferences": supporting,
        "auxiliaryModels": [{"name": "fixture-lora", "totalSteps": 1,
                             "sha256": "1" * 64, "role": "general-concept",
                             "heroReferenceAllowed": False}],
    }
    identity_path = root / "identity-reference.json"
    identity_path.write_text(json.dumps(identity), encoding="utf-8")

    anchors = {
        "neutralFaceFront": [1], "faceThreeQuarter": [4], "faceLeftProfile": [2],
        "faceRightProfile": [3], "verticalFaceShape": [7, 8], "expressionRange": [5, 6],
        "bodyFront": [13, 17], "bodyProfile": [14], "bodyThreeQuarter": [15],
        "bodyMotion": [16, 18], "hairFront": [1, 9], "primaryOutfit": [13, 14, 15],
        "alternateOutfit": [17],
    }
    modeling = {
        "schemaVersion": 1, "characterId": "gahyeon",
        "identityManifest": identity_path.name,
        "authorityOrder": ["canonical original references", "approved artist-authored model sheet",
                           "approved 3D sculpt", "LoRA concept output"],
        "anchors": anchors,
        "geometryAuthority": {
            "masterNeutralFace": 1, "primaryFaceGeometry": [1, 2, 3, 4],
            "angleCrossChecks": [7, 8], "expressionOnly": [5, 6],
            "styleAndHairOnly": [9, 10], "primaryBodyGeometry": [13, 14, 15],
            "bodyMotionAndOutfitOnly": [16, 17, 18],
        },
        "missingRequiredCaptures": ["rear reference"],
        "rules": ["Fixture geometry remains canonical-only."],
        "nextGate": {"id": "G1", "name": "model-sheet", "status": "ready-for-authoring",
                     "approvalRequires": ["fixture review"]},
    }
    modeling_path = root / "modeling-input.json"
    modeling_path.write_text(json.dumps(modeling), encoding="utf-8")
    return identity_path, modeling_path
