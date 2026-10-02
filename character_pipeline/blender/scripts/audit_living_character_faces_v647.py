"""Read-only facial capability inventory for a supplied living-character BLEND."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import bpy


FACE_TOKENS = (
    "face", "head", "eye", "lid", "brow", "jaw", "mouth", "lip", "tongue",
    "cheek", "nose", "teeth", "tooth",
)


def classify_v647_face_bones(names):
    matches = []
    for name in names:
        separated = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
        tokens = {
            re.sub(r"\d+$", "", token.lower())
            for token in re.split(r"[^A-Za-z0-9]+", separated)
            if token
        }
        if tokens.intersection(FACE_TOKENS):
            matches.append(name)
    return sorted(matches)


def audit_v647_scene(character_id, source):
    meshes = []
    all_shape_keys = set()
    armatures = []
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            keys = []
            if obj.data.shape_keys:
                keys = [key.name for key in obj.data.shape_keys.key_blocks if key.name != "Basis"]
            all_shape_keys.update(keys)
            face_groups = classify_v647_face_bones(group.name for group in obj.vertex_groups)
            meshes.append({
                "name": obj.name,
                "vertexCount": len(obj.data.vertices),
                "polygonCount": len(obj.data.polygons),
                "materialSlots": [slot.material.name if slot.material else None for slot in obj.material_slots],
                "shapeKeyCount": len(keys),
                "shapeKeys": keys,
                "faceRelatedVertexGroups": face_groups,
            })
        elif obj.type == "ARMATURE":
            bone_names = [bone.name for bone in obj.data.bones]
            armatures.append({
                "name": obj.name,
                "boneCount": len(bone_names),
                "faceRelatedBones": classify_v647_face_bones(bone_names),
            })
    actions = []
    for action in bpy.data.actions:
        start, end = action.frame_range
        actions.append({
            "name": action.name,
            "frameRange": [float(start), float(end)],
            "frameDuration": float(end - start),
        })
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    return {
        "schemaVersion": 1,
        "iteration": "v649",
        "status": "read-only-facial-capability-audit",
        "character": character_id,
        "source": str(source),
        "sourceSha256": digest,
        "meshCount": len(meshes),
        "armatureCount": len(armatures),
        "shapeKeyCount": len(all_shape_keys),
        "shapeKeys": sorted(all_shape_keys),
        "faceRelatedBoneCount": len({bone for item in armatures for bone in item["faceRelatedBones"]}),
        "meshes": meshes,
        "armatures": armatures,
        "actions": actions,
        "decision": "capability-inventory-only; deformation render required before accepting any facial actuator",
        "humanApproved": False,
        "releaseEligible": False,
    }


def audit_v647_character():
    parser = argparse.ArgumentParser()
    parser.add_argument("--character", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(__import__("sys").argv[__import__("sys").argv.index("--") + 1:])
    source = args.source.resolve()
    if Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError(f"opened BLEND does not match requested source: {bpy.data.filepath}")
    if args.output.exists():
        raise RuntimeError(f"refusing to overwrite immutable report: {args.output}")
    report = audit_v647_scene(args.character, source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


audit_v647_character()
