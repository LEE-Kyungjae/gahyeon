#!/usr/bin/env python3
"""Inspect facial shape channels in a donor FBX without modifying the source."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import bpy


ARKIT_52 = {
    "browdownleft", "browdownright", "browinnerup", "browouterupleft",
    "browouterupright", "cheekpuff", "cheeksquintleft", "cheeksquintright",
    "eyeblinkleft", "eyeblinkright", "eyelookdownleft", "eyelookdownright",
    "eyelookinleft", "eyelookinright", "eyelookoutleft", "eyelookoutright",
    "eyelookupleft", "eyelookupright", "eyesquintleft", "eyesquintright",
    "eyewideleft", "eyewideright", "jawforward", "jawleft", "jawopen",
    "jawright", "mouthclose", "mouthdimpleleft", "mouthdimpleright",
    "mouthfrownleft", "mouthfrownright", "mouthfunnel", "mouthleft",
    "mouthlowerdownleft", "mouthlowerdownright", "mouthpressleft",
    "mouthpressright", "mouthpucker", "mouthright", "mouthrolllower",
    "mouthrollupper", "mouthshruglower", "mouthshrugupper", "mouthsmileleft",
    "mouthsmileright", "mouthstretchleft", "mouthstretchright", "mouthupperupleft",
    "mouthupperupright", "nosesneerleft", "nosesneerright", "tongueout",
}


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(values)


def normalize_channel(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def classify_expression_channel(name):
    normalized = normalize_channel(name)
    if normalized in ARKIT_52:
        return "arkit-52"
    if normalized.startswith(("viseme", "v_", "mouth")) or "phoneme" in normalized:
        return "viseme-or-mouth"
    if any(term in normalized for term in ("eye", "brow", "jaw", "cheek", "nose", "tongue")):
        return "facial-expression"
    return "unclassified"


def inspect_expression_donor(source, donor_id):
    if not source.is_file():
        raise FileNotFoundError(source)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    meshes = []
    for item in bpy.context.scene.objects:
        if item.type != "MESH" or item.data.shape_keys is None:
            continue
        keys = [block.name for block in item.data.shape_keys.key_blocks if block.name != "Basis"]
        action = (
            item.data.shape_keys.animation_data.action
            if item.data.shape_keys.animation_data else None
        )
        meshes.append({
            "object": item.name,
            "vertexCount": len(item.data.vertices),
            "shapeKeyCount": len(keys),
            "shapeKeys": [
                {
                    "source": name,
                    "normalized": normalize_channel(name),
                    "classification": classify_expression_channel(name),
                }
                for name in keys
            ],
            "activeShapeAction": action.name if action else None,
            "activeShapeActionFrameRange": list(action.frame_range) if action else None,
        })
    return {
        "schemaVersion": 1,
        "id": donor_id,
        "status": "inspected-draft-expression-donor",
        "source": str(source.resolve()),
        "sourceBytes": source.stat().st_size,
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "fps": bpy.context.scene.render.fps,
        "sceneFrameRange": [bpy.context.scene.frame_start, bpy.context.scene.frame_end],
        "shapeMeshes": meshes,
        "arkitExactChannelCount": sum(
            1 for mesh in meshes for key in mesh["shapeKeys"]
            if key["classification"] == "arkit-52"
        ),
        "humanApproved": False,
        "releaseEligible": False,
    }


def main():
    args = parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite inspection: {args.output}")
    report = inspect_expression_donor(args.input, args.id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "id": report["id"],
        "shapeMeshes": [
            {"object": mesh["object"], "shapeKeyCount": mesh["shapeKeyCount"]}
            for mesh in report["shapeMeshes"]
        ],
        "arkitExactChannelCount": report["arkitExactChannelCount"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
