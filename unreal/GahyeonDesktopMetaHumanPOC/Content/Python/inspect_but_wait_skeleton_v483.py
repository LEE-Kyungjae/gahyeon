"""Inspect post-import But-wait bone names before creating retarget chains."""

import json
from pathlib import Path

import unreal


MESH = "/Game/LivingCharacterPOC/v482/Donors/ButWait/segment-02/segment-02-frames-0323-0399"
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v483-but-wait-skeleton/report.json")


def inspect_but_wait_skeleton_v483():
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    mesh = unreal.load_asset(MESH)
    if mesh is None:
        raise RuntimeError(f"missing donor mesh: {MESH}")
    modifier = unreal.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):
        raise RuntimeError("SkeletonModifier rejected But-wait mesh")
    names = [str(value) for value in modifier.get_all_bone_names()]
    report = {
        "schemaVersion": 1, "iteration": "v483", "status": "read-only-skeleton-inspection",
        "mesh": MESH, "boneCount": len(names),
        "bones": [{"name": name, "parent": str(modifier.get_parent_name(name))} for name in names],
        "humanApproved": False, "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("BUT_WAIT_SKELETON=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_but_wait_skeleton_v483()
