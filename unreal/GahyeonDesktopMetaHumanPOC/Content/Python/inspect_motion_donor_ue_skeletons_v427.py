"""Read actual UE bone names for candidate motion-donor skeletal meshes."""

import json
from pathlib import Path

import unreal


MESHES = {
    "cyber-whitehair": "/Game/LivingCharacterPOC/v371/Donors/CyberIdle/whitehair_body_v2",
    "cyber-prefix": "/Game/LivingCharacterPOC/v371/Donors/CyberIdle/prefix_whitehair_body_v2",
    "hands-forward": "/Game/LivingCharacterPOC/v371/Donors/HandsForward/Hands_Forward_Gesture",
    "stand-sit": "/Game/LivingCharacterPOC/v374/Donors/StandSitClean/StandSit_Clean_v001",
}
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v427-motion-donor-ue-skeletons/report.json")


def inspect_motion_donor_ue_skeletons_v427():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite inspection: {OUTPUT}")
    records = {}
    for key, path in MESHES.items():
        mesh = unreal.load_asset(path)
        if mesh is None:
            records[key] = {"mesh": path, "available": False}
            continue
        modifier = unreal.SkeletonModifier()
        if not modifier.set_skeletal_mesh(mesh):
            raise RuntimeError(f"SkeletonModifier failed: {path}")
        names = [str(value) for value in modifier.get_all_bone_names()]
        records[key] = {
            "mesh": path, "available": True, "boneCount": len(names),
            "roots": [
                name for name in names
                if not str(modifier.get_parent_name(name))
                or str(modifier.get_parent_name(name)).lower() == "none"
            ],
            "bones": [{"name": name, "parent": str(modifier.get_parent_name(name))} for name in names],
        }
    report = {
        "schemaVersion": 1, "iteration": "v427",
        "status": "read-only-post-import-motion-donor-skeleton-inspection",
        "meshes": records, "mutatedAssets": [], "humanApproved": False, "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("MOTION_DONOR_V427_SKELETONS=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_motion_donor_ue_skeletons_v427()
