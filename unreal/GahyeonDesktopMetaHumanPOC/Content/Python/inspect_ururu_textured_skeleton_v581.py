"""Inspect the actual UE bone names on textured Ururu."""

import json
from pathlib import Path

import unreal


MESH = "/Game/LivingCharacterPOC/v547/Characters/UruruTextured/Ururu_Textured_v545"
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v581-ururu-textured-skeleton/report.json")


def inspect_ururu_textured_skeleton_v581():
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    mesh = unreal.load_asset(MESH)
    if mesh is None:
        raise RuntimeError(f"missing Ururu mesh: {MESH}")
    modifier = unreal.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):
        raise RuntimeError("SkeletonModifier rejected Ururu mesh")
    names = [str(value) for value in modifier.get_all_bone_names()]
    report = {
        "schemaVersion": 1,
        "iteration": "v581",
        "status": "read-only-skeleton-inspection",
        "mesh": MESH,
        "boneCount": len(names),
        "bones": [{"name": name, "parent": str(modifier.get_parent_name(name))} for name in names],
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.SystemLibrary.quit_editor()


inspect_ururu_textured_skeleton_v581()
