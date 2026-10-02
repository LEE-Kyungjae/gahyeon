#!/usr/bin/env python3
"""Inspect a donor FBX skeleton and animation without modifying the source."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


HUMANOID_TERMS = (
    "root", "pelvis", "hip", "spine", "chest", "neck", "head",
    "clavicle", "shoulder", "upperarm", "lowerarm", "forearm", "hand",
    "thigh", "upperleg", "calf", "lowerleg", "foot", "toe",
)


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--id", required=True)
    return parser.parse_args(values)


def classify_humanoid_bones(bones):
    return [
        bone.name for bone in bones
        if any(term in bone.name.lower().replace("_", "") for term in HUMANOID_TERMS)
    ]


def inspect_motion_donor(source, donor_id):
    if not source.is_file():
        raise FileNotFoundError(source)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    armatures = [item for item in bpy.context.scene.objects if item.type == "ARMATURE"]
    if not armatures:
        raise RuntimeError("donor contains no armature")
    inventories = []
    for armature in armatures:
        bones = list(armature.data.bones)
        action = armature.animation_data.action if armature.animation_data else None
        inventories.append({
            "object": armature.name,
            "boneCount": len(bones),
            "deformBoneCount": sum(1 for bone in bones if bone.use_deform),
            "roots": [bone.name for bone in bones if bone.parent is None],
            "humanoidCandidates": classify_humanoid_bones(bones),
            "bones": [
                {
                    "name": bone.name,
                    "parent": bone.parent.name if bone.parent else None,
                    "deform": bone.use_deform,
                }
                for bone in bones
            ],
            "activeAction": action.name if action else None,
            "activeActionFrameRange": list(action.frame_range) if action else None,
        })
    return {
        "schemaVersion": 1,
        "id": donor_id,
        "status": "inspected-draft",
        "source": str(source.resolve()),
        "sourceBytes": source.stat().st_size,
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "fps": bpy.context.scene.render.fps,
        "sceneFrameRange": [bpy.context.scene.frame_start, bpy.context.scene.frame_end],
        "armatures": inventories,
        "actions": [
            {"name": action.name, "frameRange": list(action.frame_range)}
            for action in bpy.data.actions
        ],
        "humanApproved": False,
        "releaseEligible": False,
    }


def main():
    args = parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite inspection: {args.output}")
    report = inspect_motion_donor(args.input, args.id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "id": report["id"],
        "armatures": [
            {"object": item["object"], "boneCount": item["boneCount"], "roots": item["roots"]}
            for item in report["armatures"]
        ],
        "actions": report["actions"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
